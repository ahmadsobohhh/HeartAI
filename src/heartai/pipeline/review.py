"""Validate Slicer draft exports and rebuild derived artifacts without inference."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import time
from uuid import uuid4

import nibabel as nib
import numpy as np

from heartai.assets import sha256
from heartai.pipeline.reconstruct import reconstruct_labels
from heartai.preprocessing.loader import save_segmentation
from heartai.structures import SUPPORTED_STRUCTURES
from heartai.visualization import create_overlay


def accept_review(case_dir: Path, export_dir: Path) -> dict:
    """Accept technical geometry, not clinical correctness. Preserve draft state."""
    started = time.perf_counter()
    case_dir, export_dir = Path(case_dir).resolve(), Path(export_dir).resolve()
    parent = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    record = json.loads((export_dir / "review.json").read_text(encoding="utf-8"))
    if parent["status"] != "complete" or record["case_id"] != parent["case_id"]:
        raise ValueError("Review does not reference a completed parent case")
    revision_id = record["revision_id"]
    if not re.fullmatch(r"[a-f0-9]{12}", revision_id):
        raise ValueError("Invalid revision ID")
    destination = case_dir / "reviews" / revision_id
    if destination.exists():
        raise FileExistsError(f"Revision already exists: {revision_id}")
    if record["review_state"] != "draft" or not record.get("reviewer") or not record.get("purpose"):
        raise ValueError("Expected a draft with explicit reviewer and purpose")
    mapping = {s["name"]: s["label_id"] for s in record["structures"]}
    if len(mapping) != len(record["structures"]) or mapping != {n: s.label_id for n, s in SUPPORTED_STRUCTURES.items()}:
        raise ValueError("Unexpected or duplicated cardiac label mapping")
    def source(key):
        path = (case_dir / parent["artifacts"][key]).resolve()
        if not path.is_relative_to(case_dir):
            raise ValueError("Parent artifact escapes case directory")
        return path
    ct_path, prediction_path = source("input"), source("segmentation")
    if sha256(ct_path) != record["ct_sha256"] or record["ct_sha256"] != parent["input"]["sha256"] or sha256(prediction_path) != record["prediction_sha256"]:
        raise ValueError("Original CT or prediction hash mismatch")
    if record["model"] != parent["model"]:
        raise ValueError("Model provenance differs from parent")
    for name in ("cardiac_labels.nii.gz", "review.seg.nrrd"):
        if sha256(export_dir / name) != record["artifacts"][name]:
            raise ValueError("Export artifact hash mismatch")
    ct, edited = nib.load(ct_path), nib.load(export_dir / "cardiac_labels.nii.gz")
    if ct.shape != edited.shape or not np.allclose(ct.affine, edited.affine, atol=1e-4, rtol=0):
        raise ValueError("Reviewed labels differ from the original CT grid")
    if ct.header.get_xyzt_units()[0] != "mm" or edited.header.get_xyzt_units()[0] != "mm":
        raise ValueError("Review requires explicit millimeter units")
    labels = np.asarray(edited.dataobj)
    valid = [0] + [s.label_id for s in SUPPORTED_STRUCTURES.values()]
    if not np.isin(labels, valid).all():
        raise ValueError("Unexpected cardiac label values")
    original = np.asarray(nib.load(prediction_path).dataobj)
    baseline = np.where(np.isin(original, valid), original, 0)
    changes = {n: {"added_voxels": int(np.count_nonzero((labels == s.label_id) & (baseline != s.label_id))),
                   "removed_voxels": int(np.count_nonzero((baseline == s.label_id) & (labels != s.label_id)))}
               for n, s in SUPPORTED_STRUCTURES.items()}
    destination.parent.mkdir(exist_ok=True)
    staging = destination.parent / (".tmp-" + uuid4().hex)
    staging.mkdir()
    try:
        shutil.copyfile(export_dir / "review.seg.nrrd", staging / "review.seg.nrrd")
        shutil.copyfile(export_dir / "cardiac_labels.nii.gz", staging / "slicer_labels.nii.gz")
        save_segmentation(labels, ct, staging / "cardiac_labels.nii.gz")
        reconstruction = reconstruct_labels(labels, ct.affine, staging)
        measurements = {"case_id": parent["case_id"], "revision_id": revision_id,
                        "coordinate_system": "RAS millimeters", "structures": reconstruction["measurements"]}
        (staging / "measurements.json").write_text(json.dumps(measurements, indent=2), encoding="utf-8")
        preview = staging / "previews/overlay.png"
        create_overlay(ct_path, staging / "cardiac_labels.nii.gz", preview, label_title="Draft revision labels")
        output = {**record, "processing_status": "complete", "review_state": "draft",
                  "accepted_at": datetime.now(timezone.utc).isoformat(), "changes": changes,
                  "changed_voxels": int(np.count_nonzero(labels != baseline)),
                  "source_export_hashes": record["artifacts"],
                  "warnings": reconstruction["warnings"], "measurements": reconstruction["measurements"],
                  "absent_structures": reconstruction["absent_structures"],
                  "total_seconds": time.perf_counter() - started,
                  "artifacts": {p.relative_to(staging).as_posix(): sha256(p) for p in staging.rglob("*") if p.is_file()}}
        (staging / "review.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        staging.rename(destination)
        return {"directory": str(destination), **output}
    except Exception as error:
        (staging / "failure.json").write_text(json.dumps({"status": "failed", "error": str(error)}), encoding="utf-8")
        raise
