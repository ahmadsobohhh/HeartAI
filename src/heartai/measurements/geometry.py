import nibabel as nib
import numpy as np
from numpy.typing import NDArray
from scipy import ndimage

from heartai.measurements.volume import measure_volume
from heartai.reconstruction.marching_cubes import validate_affine


def measure_structure(mask: NDArray, affine_mm: NDArray) -> dict:
    """Measure occupied voxel cells in world RAS mm, not the smoothed surface."""
    affine_mm = validate_affine(affine_mm)
    result = measure_volume(mask, affine_mm)
    indices = np.argwhere(mask)
    if not len(indices):
        return {**result, "centroid_mm": None, "bounds_mm": None,
                "bounding_dimensions_mm": None, "connected_components": 0,
                "largest_component_voxels": 0}
    centers = nib.affines.apply_affine(affine_mm, indices)
    # Include each voxel's physical extent, not just its center. Row-wise sum
    # gives the extent of a transformed half-voxel on each world axis.
    half_extent = np.abs(affine_mm[:3, :3]).sum(axis=1) / 2
    low = centers.min(axis=0) - half_extent
    high = centers.max(axis=0) + half_extent
    components, count = ndimage.label(mask, structure=np.ones((3, 3, 3), dtype=bool))
    sizes = np.bincount(components.ravel())[1:]
    return {
        **result, "centroid_mm": nib.affines.apply_affine(affine_mm, indices.mean(axis=0)).tolist(),
        "bounds_mm": [low.tolist(), high.tolist()],
        "bounding_dimensions_mm": (high - low).tolist(),
        "connected_components": int(count), "largest_component_voxels": int(sizes.max()),
    }
