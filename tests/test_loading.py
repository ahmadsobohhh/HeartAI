import nibabel as nib
import numpy as np
import pytest

from heartai.preprocessing.loader import load_scan, save_segmentation, scan_info


@pytest.fixture
def scan_path(tmp_path):
    # Non-RAS, anisotropic input catches accidental axis/spacing assumptions.
    affine = np.array([[0, -2, 0, 41], [1.5, 0, 0, -23], [0, 0, -4, 90], [0, 0, 0, 1.]])
    image = nib.Nifti1Image(np.arange(7*8*9, dtype=np.float32).reshape(7, 8, 9), affine)
    image.set_qform(affine, 1)
    image.set_sform(affine, 2)
    image.header.set_xyzt_units("mm")
    path = tmp_path / "ct.nii.gz"
    nib.save(image, path)
    return path


def test_loading_and_spacing(scan_path):
    scan = load_scan(scan_path)
    info = scan_info(scan)
    assert info["shape"] == [7, 8, 9]
    assert info["spacing_mm"] == [1.5, 2, 4]
    assert info["orientation"] == ["A", "L", "I"]
    assert info["intensity_range"] == [0, 503]


def test_save_preserves_grid_forms_and_integer_labels(scan_path, tmp_path):
    scan = load_scan(scan_path)
    labels = np.zeros(scan.shape, np.uint8)
    labels[1:4, 2:5, 3:7] = 46
    saved = nib.load(save_segmentation(labels, scan, tmp_path / "prediction.nii.gz"))
    np.testing.assert_array_equal(saved.get_fdata(), labels)
    np.testing.assert_allclose(saved.affine, scan.affine)
    np.testing.assert_allclose(saved.get_qform(), scan.get_qform())
    np.testing.assert_allclose(saved.get_sform(), scan.get_sform())
    assert saved.header.get_zooms() == scan.header.get_zooms()
    assert saved.header.get_xyzt_units() == scan.header.get_xyzt_units()
    assert saved.header["qform_code"] == 1
    assert saved.header["sform_code"] == 2
    assert saved.get_data_dtype() == np.uint8


@pytest.mark.parametrize("shape", [(3, 4), (3, 4, 5, 2)])
def test_reject_non_3d(tmp_path, shape):
    path = tmp_path / "bad.nii.gz"
    nib.save(nib.Nifti1Image(np.zeros(shape), np.eye(4)), path)
    with pytest.raises(ValueError, match="3-D"):
        load_scan(path)


@pytest.mark.parametrize("value", [np.nan, np.inf])
def test_reject_nonfinite(tmp_path, value):
    data = np.zeros((3, 4, 5))
    data[1, 1, 1] = value
    path = tmp_path / "bad.nii.gz"
    nib.save(nib.Nifti1Image(data, np.eye(4)), path)
    with pytest.raises(ValueError, match="non-finite"):
        load_scan(path)


def test_reject_wrong_output_shape(scan_path, tmp_path):
    with pytest.raises(ValueError, match="shape"):
        save_segmentation(np.zeros((2, 3, 4)), load_scan(scan_path), tmp_path / "bad.nii.gz")


def test_reject_fractional_output(scan_path, tmp_path):
    with pytest.raises(ValueError, match="integer"):
        save_segmentation(np.full((7, 8, 9), 0.5), load_scan(scan_path), tmp_path / "bad.nii.gz")
