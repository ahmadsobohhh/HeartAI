import nibabel as nib
import numpy as np
import pytest

from heartai.measurements.geometry import measure_structure
from heartai.reconstruction.marching_cubes import mask_to_mesh
from heartai.reconstruction.totalseg_case import crop_binary_mask, mesh_measurements


def test_crop_preserves_full_affine_and_disconnected_components():
    mask = np.zeros((20, 21, 22), dtype=np.uint8)
    mask[3:9, 5:12, 4:10] = 1
    mask[15, 18, 20] = 1
    affine = np.array([[0, -2, .3, 53], [3, 0, 0, -17], [0, 0, -4, 101], [0, 0, 0, 1.]])
    crop, adjusted, edge = crop_binary_mask(mask, affine)
    assert not edge and crop.sum() == mask.sum()
    full = mask_to_mesh(mask, affine)
    cropped = mask_to_mesh(crop, adjusted)
    np.testing.assert_allclose(full.bounds, cropped.bounds)
    np.testing.assert_allclose(full.volume, cropped.volume)
    np.testing.assert_allclose(measure_structure(mask, affine)["centroid_mm"],
                               measure_structure(crop, adjusted)["centroid_mm"])


def test_one_ml_and_surface_volume_agreement():
    mask = np.ones((10, 10, 10), dtype=np.uint8)
    measurement = measure_structure(mask, np.eye(4))
    assert measurement["volume_ml"] == pytest.approx(1)
    checks = mesh_measurements(mask_to_mesh(mask, np.eye(4)), measurement)
    assert checks["mesh_voxel_volume_check_passed"]
    assert checks["surface_area_cm2"] == pytest.approx(checks["surface_area_mm2"]/100)


def test_small_object_discrepancy_is_reported_not_hidden():
    mask = np.ones((1, 1, 1), dtype=np.uint8)
    checks = mesh_measurements(mask_to_mesh(mask, np.eye(4)), measure_structure(mask, np.eye(4)))
    assert not checks["mesh_voxel_volume_check_passed"]


def test_scan_boundary_and_invalid_masks():
    mask = np.zeros((4, 5, 6), dtype=np.uint8)
    mask[0:2, 2:4, 1:3] = 1
    crop, affine, edge = crop_binary_mask(mask, np.eye(4))
    assert edge
    np.testing.assert_allclose(nib.affines.apply_affine(affine, [0, 0, 0]), [0, 2, 1])
    for invalid in (np.zeros_like(mask), mask.astype(float)+0.2, mask[:, :, 0]):
        with pytest.raises(ValueError):
            crop_binary_mask(invalid, np.eye(4))
