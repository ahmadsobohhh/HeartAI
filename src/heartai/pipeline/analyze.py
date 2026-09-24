from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import time
from uuid import uuid4

import nibabel as nib
import numpy as np

from heartai.assets import ROOT, sha256
from heartai.inference.predictor import segment_scan
from heartai.preprocessing.loader import load_scan, scan_info
from heartai.reconstruction.marching_cubes import nifti_affine_mm
from heartai.reconstruction.mesh_export import RAS_MM_TO_GLB
from heartai.pipeline.reconstruct import reconstruct_labels


def write_json(path: Path, value: dict) -> None:
    """Atomic updates keep a future status reader from seeing partial JSON."""
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def analyze_case(
    scan_path: str | Path,
    case_id: str | None = None,
    *,
    cases_dir: str | Path | None = None,
    device: str = "auto",
    threads: int = 4,
) -> dict:
    """Run real CT inference, surfaces, and voxel measurements in a new case.

    Existing IDs are never overwritten. Errors leave a failed manifest and raise.
    All manifest artifact paths are relative to the case directory.
    """
    started = time.perf_counter()
    case_id = uuid4().hex[:12] if case_id is None else case_id
    if not re.fullmatch(r"[a-f0-9]{8,32}", case_id):
        raise ValueError("case_id must be 8–32 lowercase hexadecimal characters")
    case_dir = Path(cases_dir or ROOT / "results/cases").resolve() / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict = {
        "schema_version": 1, "case_id": case_id, "status": "inspecting", "history": [],
        "structures": [], "absent_structures": [], "measurements": {}, "artifacts": {},
        "warnings": [], "coordinates": {
            "measurements": "NIfTI world RAS, millimeters; volume in mm3 and mL",
            "stl": "RAS millimeters (STL has no intrinsic unit metadata)",
            "glb": "Y-up meters: x=R/1000, y=S/1000, z=-A/1000",
            "ras_mm_to_glb": RAS_MM_TO_GLB.tolist(),
        },
    }

    def stage(name: str) -> None:
        manifest["status"] = name
        manifest["history"].append({"stage": name, "at": datetime.now(timezone.utc).isoformat()})
        write_json(case_dir / "manifest.json", manifest)
        print(f"[{case_id}] {name}", flush=True)

    def relative(path: Path | str) -> str:
        return Path(path).relative_to(case_dir).as_posix()

    try:
        stage("inspecting")
        source = Path(scan_path).resolve()
        # Validate before inference and require known physical units for measurements.
        scan = load_scan(source)
        affine_mm = nifti_affine_mm(scan)
        if scan.header.get_xyzt_units()[0] != "mm":
            raise ValueError("Inference requires NIfTI spatial units in mm; convert units explicitly first")
        manifest["input"] = scan_info(scan)
        del scan
        suffix = ".nii.gz" if source.name.lower().endswith(".nii.gz") else ".nii"
        input_path = case_dir / "input" / ("scan" + suffix)
        input_path.parent.mkdir()
        shutil.copyfile(source, input_path)
        manifest["input"]["sha256"] = sha256(input_path)
        manifest["artifacts"]["input"] = relative(input_path)

        stage("segmenting")  # Existing callable includes exact preprocessing and overlay.
        inference = segment_scan(input_path, case_dir, device=device, threads=threads)
        prediction = case_dir / "segmentation/prediction.nii.gz"
        preview = case_dir / "previews/overlay.png"
        prediction.parent.mkdir()
        preview.parent.mkdir()
        Path(inference["segmentation_path"]).replace(prediction)
        Path(inference["overlay_path"]).replace(preview)
        # Only remove known intermediate files in this freshly created case.
        (case_dir / "reports/scan.json").unlink()
        for directory in ("reports", "segmentations", "overlays"):
            (case_dir / directory).rmdir()
        inference.update(input_path=relative(input_path), segmentation_path=relative(prediction),
                         overlay_path=relative(preview))
        write_json(case_dir / "inference_report.json", inference)
        manifest["model"] = {
            "name": inference["model"], "version": "0.2.7", "device": inference["device"],
            "checkpoint_sha256": inference["checkpoint_sha256"],
        }
        manifest["artifacts"].update(segmentation=relative(prediction), overlay=relative(preview),
                                      inference_report="inference_report.json")
        image = nib.load(prediction)
        if list(image.shape) != manifest["input"]["shape"]:
            raise ValueError("Segmentation shape differs from input")
        np.testing.assert_allclose(nifti_affine_mm(image), affine_mm, atol=1e-4)
        labels = np.asarray(image.dataobj)
        reconstruction = reconstruct_labels(labels, affine_mm, case_dir, stage)
        for key in ("structures", "absent_structures", "warnings", "measurements"):
            manifest[key] = reconstruction[key]
        manifest["artifacts"].update(reconstruction["artifacts"])
        write_json(case_dir / "measurements.json", {
            "case_id": case_id, "coordinate_system": "RAS millimeters",
            "method": "Occupied voxel cells; all components; world-axis-aligned bounds",
            "structures": manifest["measurements"],
        })
        manifest["artifacts"]["measurements"] = "measurements.json"
        manifest["timing"] = {
            "inference_seconds": inference["inference_seconds"],
            "inference_pipeline_seconds": inference["total_seconds"],
            "reconstruction_seconds": reconstruction["reconstruction_seconds"],
            "measurement_seconds": reconstruction["measurement_seconds"],
            "total_seconds": time.perf_counter() - started,
        }
        stage("complete")
        print(f"Manifest: {case_dir / 'manifest.json'}", flush=True)
        return manifest
    except Exception as error:
        manifest["failed_stage"] = manifest["status"]
        manifest["error"] = f"{type(error).__name__}: {error}"
        manifest["timing"] = {"total_seconds": time.perf_counter() - started}
        stage("failed")
        raise
