"""Prepare an immutable cardiac-only package for Slicer, without inference."""
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from heartai.assets import sha256
from heartai.structures import SUPPORTED_STRUCTURES, discover_structures


def prepare_case(case_dir: Path, output_dir: Path) -> Path:
    case_dir, output_dir = Path(case_dir).resolve(), Path(output_dir).resolve()
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError("Only completed cases can be opened for review")

    def artifact(key: str) -> Path:
        path = (case_dir / manifest["artifacts"][key]).resolve()
        if not path.is_relative_to(case_dir):
            raise ValueError("Artifact path escapes the case directory")
        return path

    ct_path, prediction_path = artifact("input"), artifact("segmentation")
    ct, prediction = nib.load(ct_path), nib.load(prediction_path)
    if len(ct.shape) != 3 or ct.shape != prediction.shape:
        raise ValueError("CT and prediction must share a 3-D grid")
    if not np.allclose(ct.affine, prediction.affine, atol=1e-4, rtol=0):
        raise ValueError("CT and prediction physical geometry differs")
    if any(img.header.get_xyzt_units()[0] != "mm" for img in (ct, prediction)):
        raise ValueError("CT and prediction must specify millimeter units")
    ct_hash = sha256(ct_path)
    if ct_hash != manifest["input"]["sha256"]:
        raise ValueError("Original CT hash differs from the case manifest")
    labels = np.asarray(prediction.dataobj)
    present = discover_structures(labels)
    if not present:
        raise ValueError("No supported cardiac labels to review")
    cardiac = np.where(np.isin(labels, [s.label_id for s in SUPPORTED_STRUCTURES.values()]), labels, 0).astype(np.uint8)
    output_dir.mkdir(parents=True, exist_ok=False)
    label_path = output_dir / "cardiac_labels.nii.gz"
    image = nib.Nifti1Image(cardiac, ct.affine, ct.header.copy())
    image.set_data_dtype(np.uint8)
    for form in ("qform", "sform"):
        matrix, code = getattr(ct, f"get_{form}")(coded=True)
        getattr(image, f"set_{form}")(matrix, int(code))
    nib.save(image, label_path)
    package = {
        "schema_version": 1, "case_id": manifest["case_id"],
        "ct_path": str(ct_path), "ct_sha256": ct_hash,
        "prediction_path": str(prediction_path), "prediction_sha256": sha256(prediction_path),
        "cardiac_labels_path": str(label_path), "cardiac_labels_sha256": sha256(label_path),
        "model": manifest["model"], "warnings": manifest.get("warnings", []),
        "review_state": "draft", "structures": [
            {"name": name, "label": spec.label, "label_id": spec.label_id,
             "color": spec.color, "present": name in present}
            for name, spec in SUPPORTED_STRUCTURES.items()
        ],
    }
    destination = output_dir / "review_package.json"
    destination.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    return destination
