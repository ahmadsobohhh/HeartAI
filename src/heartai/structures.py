"""Cardiac subset of the verified MONAI 0.2.7 class map (docs/labels.json)."""
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Structure:
    label_id: int
    label: str
    color: str


SUPPORTED_STRUCTURES: dict[str, Structure] = {
    "aorta": Structure(7, "Aorta", "#ffb000"),
    "myocardium": Structure(44, "Myocardium", "#e85873"),
    "left_atrium": Structure(45, "Left atrium", "#5ac8fa"),
    "left_ventricle": Structure(46, "Left ventricle", "#3977eb"),
    "right_atrium": Structure(47, "Right atrium", "#72d38e"),
    "right_ventricle": Structure(48, "Right ventricle", "#bc85ed"),
    "pulmonary_artery": Structure(49, "Pulmonary artery", "#ff8552"),
}


def discover_structures(labels: NDArray) -> list[str]:
    if labels.ndim != 3 or labels.size == 0 or not np.isfinite(labels).all():
        raise ValueError("Segmentation must be a finite 3-D labelmap")
    values = np.unique(labels)
    if not np.equal(values, np.rint(values)).all() or values.min() < 0 or values.max() > 104:
        raise ValueError("Invalid MONAI segmentation labels")
    return [name for name, spec in SUPPORTED_STRUCTURES.items() if spec.label_id in values]


def extract_structure(labels: NDArray, name: str, affine_mm: NDArray) -> tuple[NDArray, NDArray, bool]:
    """Crop for efficiency, preserving the full-volume physical origin."""
    mask = labels == SUPPORTED_STRUCTURES[name].label_id
    indices = np.argwhere(mask)
    if not len(indices):
        raise ValueError(f"No predicted voxels for {name}")
    low, high = indices.min(axis=0), indices.max(axis=0) + 1
    touches_edge = bool(np.any(low == 0) or np.any(high == labels.shape))
    cropped = mask[tuple(slice(int(a), int(b)) for a, b in zip(low, high))].copy()
    shift = np.eye(4)
    shift[:3, 3] = low
    return cropped, np.asarray(affine_mm) @ shift, touches_edge
