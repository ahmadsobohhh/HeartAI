import json

import nibabel as nib
import numpy as np
import pytest
import trimesh

from heartai.assets import ROOT
from heartai.measurements.volume import mm3_to_ml, voxel_volume_mm3, measure_volume
from heartai.measurements.geometry import measure_structure
from heartai.reconstruction.marching_cubes import mask_to_mesh, nifti_affine_mm
from heartai.reconstruction.mesh_export import export_structure, export_combined, RAS_MM_TO_GLB
from heartai.structures import SUPPORTED_STRUCTURES, discover_structures, extract_structure


def test_documented_labels():
    labels = json.loads((ROOT / "docs/labels.json").read_text())
    expected = ["aorta", "heart_myocardium", "heart_atrium_left", "heart_ventricle_left",
                "heart_atrium_right", "heart_ventricle_right", "pulmonary_artery"]
    assert [labels[str(s.label_id)] for s in SUPPORTED_STRUCTURES.values()] == expected


def test_extraction_preserves_coordinates():
    labels = np.zeros((10, 11, 12), np.uint8)
    labels[3:6, 4:7, 5:8] = 46
    labels[0, 0, 0] = 1  # unrelated spleen excluded
    affine = np.diag([-2., 3., 4., 1.])
    assert discover_structures(labels) == ["left_ventricle"]
    mask, cropped_affine, edge = extract_structure(labels, "left_ventricle", affine)
    assert mask.shape == (3, 3, 3) and mask.all() and not edge
    np.testing.assert_allclose(cropped_affine[:3, 3], [-6, 12, 20])
    np.testing.assert_allclose(mask_to_mesh(mask, cropped_affine).bounds,
                               mask_to_mesh(labels == 46, affine).bounds)


def test_empty_and_invalid_segmentation():
    assert discover_structures(np.zeros((2, 3, 4))) == []
    with pytest.raises(ValueError, match="No predicted voxels"):
        extract_structure(np.zeros((2, 3, 4)), "aorta", np.eye(4))
    with pytest.raises(ValueError, match="Invalid"):
        discover_structures(np.full((2, 3, 4), 7.5))


def test_volume_units_and_synthetic_mask():
    assert mm3_to_ml(1000) == 1
    affine = np.diag([-2., 3., 4., 1.])
    assert voxel_volume_mm3(affine) == pytest.approx(24)
    result = measure_volume(np.ones((2, 3, 4), bool), affine)
    assert result["voxel_count"] == 24
    assert result["volume_mm3"] == pytest.approx(576)
    assert result["volume_ml"] == pytest.approx(.576)


def test_centroid_and_cell_bounds():
    affine = np.array([[0, -3., 0, 30], [2., 0, 0, -10], [0, 0, -4., 40], [0, 0, 0, 1.]])
    result = measure_structure(np.ones((2, 3, 4), bool), affine)
    np.testing.assert_allclose(result["centroid_mm"], [27, -9, 34])
    np.testing.assert_allclose(result["bounding_dimensions_mm"], [9, 4, 16])
    assert result["connected_components"] == 1
    assert result["largest_component_voxels"] == 24


def test_shear_volume_not_spacing_product():
    affine = np.array([[2., 1., 0, 0], [0, 3., 0, 0], [0, 0, 4., 0], [0, 0, 0, 1.]])
    assert voxel_volume_mm3(affine) == pytest.approx(24)
    result = measure_structure(np.ones((1, 1, 1), bool), affine)
    np.testing.assert_allclose(result["bounding_dimensions_mm"], [3, 3, 4])


def test_empty_measurements():
    result = measure_structure(np.zeros((2, 3, 4), bool), np.eye(4))
    assert result["volume_ml"] == 0 and result["centroid_mm"] is None
    assert result["bounds_mm"] is None and result["connected_components"] == 0


def test_components_are_preserved():
    mask = np.zeros((8, 8, 8), bool)
    mask[1:3, 1:3, 1:3] = True
    mask[6, 6, 6] = True
    result = measure_structure(mask, np.eye(4))
    assert result["connected_components"] == 2
    assert result["voxel_count"] == 9
    assert result["largest_component_voxels"] == 8


@pytest.mark.parametrize("sign", [-1, 1])
def test_mesh_physical_bounds_and_winding(sign):
    mask = np.ones((2, 3, 4), bool)
    affine = np.diag([sign*2., 3., 4., 1.])
    affine[:3, 3] = [10, 20, 30]
    mesh = mask_to_mesh(mask, affine)
    np.testing.assert_allclose(mesh.extents, [4, 9, 16])
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
    assert np.isfinite(mesh.vertices).all()


def test_single_voxel_and_empty_mesh():
    mesh = mask_to_mesh(np.ones((1, 1, 1), bool), np.eye(4))
    np.testing.assert_allclose(mesh.bounds, [[-.5]*3, [.5]*3])
    with pytest.raises(ValueError, match="nonempty"):
        mask_to_mesh(np.zeros((2, 3, 4), bool), np.eye(4))


def test_mesh_full_affine_rotation_and_shear():
    mask = np.ones((2, 3, 4), bool)
    affine = np.array([[0, -3., .4, 10], [2., 0, 0, 20], [0, 0, 4., 30], [0, 0, 0, 1.]])
    native = mask_to_mesh(mask, np.eye(4))
    physical = mask_to_mesh(mask, affine)
    np.testing.assert_allclose(physical.vertices, nib.affines.apply_affine(affine, native.vertices))


def test_physical_units():
    image = nib.Nifti1Image(np.zeros((2, 3, 4)), np.eye(4))
    with pytest.raises(ValueError, match="unknown"):
        nifti_affine_mm(image)
    image.header.set_xyzt_units("meter")
    np.testing.assert_allclose(np.diag(nifti_affine_mm(image)), [1000, 1000, 1000, 1])


def test_export_roundtrip_and_combined_names(tmp_path):
    mesh = mask_to_mesh(np.ones((2, 3, 4), bool), np.diag([2., 3., 4., 1.]))
    paths = export_structure(mesh, tmp_path, "aorta", "#ffb000")
    assert all(p.stat().st_size > 0 for p in paths.values())
    glb = trimesh.load(paths["glb"], force="scene")
    expected = nib.affines.apply_affine(RAS_MM_TO_GLB, mesh.vertices)
    np.testing.assert_allclose(glb.bounds, [expected.min(axis=0), expected.max(axis=0)], atol=1e-7)
    shifted = mesh.copy()
    shifted.apply_translation([10, 20, 30])
    path = export_combined({"aorta": mesh, "left_atrium": shifted},
                           {"aorta": "#ffb000", "left_atrium": "#5ac8fa"}, tmp_path / "heart.glb")
    assert set(trimesh.load(path, force="scene").geometry) == {"aorta", "left_atrium"}
