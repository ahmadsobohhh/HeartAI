"""Shared surface and measurement generation for AI predictions and revisions."""
from pathlib import Path
import time
from typing import Callable

import numpy as np
from heartai.measurements.geometry import measure_structure
from heartai.reconstruction.marching_cubes import mask_to_mesh, validate_mesh
from heartai.reconstruction.mesh_export import export_structure, export_combined
from heartai.structures import SUPPORTED_STRUCTURES, discover_structures, extract_structure


def reconstruct_labels(labels: np.ndarray, affine_mm: np.ndarray, output_dir: Path,
                       stage: Callable[[str], None] = lambda _: None) -> dict:
    names = discover_structures(labels)
    if not names:
        raise ValueError("No supported cardiac structures predicted")
    output_dir = Path(output_dir)
    result = {"structures": [], "warnings": [], "measurements": {}, "artifacts": {},
              "absent_structures": [n for n in SUPPORTED_STRUCTURES if n not in names]}
    stage("reconstructing")
    started = time.perf_counter()
    meshes, masks, artifacts = {}, {}, {}
    for name in names:
        spec = SUPPORTED_STRUCTURES[name]
        mask, cropped_affine, edge = extract_structure(labels, name, affine_mm)
        masks[name] = (mask, cropped_affine)
        mesh = mask_to_mesh(mask, cropped_affine)
        meshes[name] = mesh
        paths = export_structure(mesh, output_dir / "meshes", name, spec.color)
        artifacts[name] = {kind: path.relative_to(output_dir).as_posix() for kind, path in paths.items()}
        result["structures"].append({"name": name, "label": spec.label, "label_id": spec.label_id,
                                     "color": spec.color, "mesh": validate_mesh(mesh), "touches_scan_boundary": edge})
        if edge:
            result["warnings"].append(f"{name}: reaches scan boundary; mesh is capped at the field of view")
    combined = export_combined(meshes, {n: SUPPORTED_STRUCTURES[n].color for n in names}, output_dir / "meshes/heart.glb")
    result["artifacts"].update(meshes=artifacts, combined_glb=combined.relative_to(output_dir).as_posix())
    result["reconstruction_seconds"] = time.perf_counter() - started
    stage("measuring")
    started = time.perf_counter()
    for name, (mask, affine) in masks.items():
        measurement = measure_structure(mask, affine)
        result["measurements"][name] = measurement
        if measurement["connected_components"] > 1:
            result["warnings"].append(f"{name}: {measurement['connected_components']} disconnected components retained; all contribute to measurements and bounds")
    result["measurement_seconds"] = time.perf_counter() - started
    return result
