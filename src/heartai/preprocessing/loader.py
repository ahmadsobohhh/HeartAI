from pathlib import Path

import nibabel as nib
import numpy as np


def load_scan(path):
    """Load a finite, scalar 3-D NIfTI in its native physical coordinates."""
    path = Path(path)
    if not str(path).lower().endswith((".nii", ".nii.gz")):
        raise ValueError("Input must be .nii or .nii.gz")
    scan = nib.load(path)
    if len(scan.shape) != 3 or min(scan.shape) < 1:
        raise ValueError("Expected a nonempty scalar 3-D CT")
    if not np.isfinite(scan.affine).all() or abs(np.linalg.det(scan.affine[:3, :3])) < 1e-10:
        raise ValueError("Invalid spatial affine")
    data = scan.get_fdata(dtype=np.float32)
    if not np.isfinite(data).all():
        raise ValueError("CT contains non-finite intensities")
    if data.min() == data.max():
        raise ValueError("CT has constant intensity")
    return scan


def scan_info(scan):
    data = scan.get_fdata(dtype=np.float32)
    return {
        "shape": list(scan.shape),
        "spacing_mm": [float(v) for v in scan.header.get_zooms()],
        "orientation": list(nib.aff2axcodes(scan.affine)),
        "affine": scan.affine.tolist(),
        "intensity_range": [float(data.min()), float(data.max())],
    }


def save_segmentation(labels, scan, output):
    labels = np.asarray(labels)
    if labels.shape != scan.shape:
        raise ValueError(f"Output shape {labels.shape} != input {scan.shape}")
    if not np.isfinite(labels).all() or not np.equal(labels, np.rint(labels)).all():
        raise ValueError("Segmentation must contain finite integer labels")
    if labels.min() < 0 or labels.max() > 104:
        raise ValueError("Labels outside verified model classes 0..104")
    header = scan.header.copy()
    header.set_data_dtype(np.uint8)
    header.set_slope_inter(1, 0)
    result = nib.Nifti1Image(labels.astype(np.uint8), scan.affine, header)
    # Preserve both coded forms, including different valid qform/sform matrices.
    result.set_qform(scan.get_qform(), int(scan.header["qform_code"]))
    result.set_sform(scan.get_sform(), int(scan.header["sform_code"]))
    result.header.set_slope_inter(1, 0)
    result.header["cal_min"] = 0
    result.header["cal_max"] = 104
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    nib.save(result, output)
    return output
