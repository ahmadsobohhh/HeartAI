import nibabel as nib
import numpy as np
from numpy.typing import NDArray
from skimage.measure import marching_cubes
import trimesh


def validate_affine(affine: NDArray) -> NDArray:
    affine = np.asarray(affine, dtype=float)
    if (affine.shape != (4, 4) or not np.isfinite(affine).all()
            or not np.allclose(affine[3], [0, 0, 0, 1])
            or abs(np.linalg.det(affine[:3, :3])) < 1e-12):
        raise ValueError("Expected a finite, invertible spatial affine")
    return affine


def nifti_affine_mm(image: nib.spatialimages.SpatialImage) -> NDArray:
    """Reject unknown physical units rather than inventing millimeter measurements."""
    unit = image.header.get_xyzt_units()[0]
    scale = {"mm": 1., "meter": 1000., "micron": 0.001}.get(unit)
    if scale is None:
        raise ValueError("NIfTI spatial units are unknown; specify valid units before analysis")
    affine = validate_affine(image.affine).copy()
    affine[:3] *= scale
    return affine


def mask_to_mesh(mask: NDArray, affine_mm: NDArray) -> trimesh.Trimesh:
    """March at 0.5 in index space, then apply the entire affine once."""
    affine_mm = validate_affine(affine_mm)
    if mask.ndim != 3 or not np.isin(mask, [0, 1]).all() or not np.any(mask):
        raise ValueError("Expected a nonempty 3-D binary mask")
    # Padding closes surfaces at image/crop edges, including a single-voxel mask.
    vertices, faces, _, _ = marching_cubes(
        np.pad(mask.astype(np.uint8), 1), level=0.5,
        gradient_direction="ascent", allow_degenerate=False,
    )
    mesh = trimesh.Trimesh(vertices=vertices - 1, faces=faces, process=False)
    # Trimesh also reverses winding when this transform has negative determinant.
    mesh.apply_transform(affine_mm)
    mesh.units = "mm"
    validate_mesh(mesh)
    return mesh


def validate_mesh(mesh: trimesh.Trimesh) -> dict:
    if not len(mesh.vertices) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError("Empty or non-finite mesh")
    if mesh.faces.min() < 0 or mesh.faces.max() >= len(mesh.vertices):
        raise ValueError("Invalid triangle indices")
    if not np.all(mesh.extents > 0) or not np.all(mesh.area_faces > 0):
        raise ValueError("Degenerate mesh geometry")
    return {
        "vertices": len(mesh.vertices), "faces": len(mesh.faces),
        "bounds_mm": mesh.bounds.tolist(), "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
    }
