import numpy as np
from numpy.typing import NDArray

from heartai.reconstruction.marching_cubes import validate_affine


def mm3_to_ml(value: float) -> float:
    return float(value) / 1000.0


def voxel_volume_mm3(affine_mm: NDArray) -> float:
    # Equals spacing_x * spacing_y * spacing_z for orthogonal grids;
    # determinant also handles oblique/reflected/sheared physical coordinates.
    return float(abs(np.linalg.det(validate_affine(affine_mm)[:3, :3])))


def measure_volume(mask: NDArray, affine_mm: NDArray) -> dict:
    if mask.ndim != 3 or not np.isin(mask, [0, 1]).all():
        raise ValueError("Expected a 3-D binary mask")
    voxel_size = voxel_volume_mm3(affine_mm)
    count = int(np.count_nonzero(mask))
    volume = count * voxel_size
    return {"voxel_count": count, "voxel_volume_mm3": voxel_size,
            "volume_mm3": volume, "volume_ml": mm3_to_ml(volume)}
