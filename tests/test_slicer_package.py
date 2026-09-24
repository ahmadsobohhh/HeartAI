import json
import nibabel as nib
import numpy as np
import pytest

from heartai.assets import sha256
from heartai.slicer_package import prepare_case


def make_case(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    affine = np.diag([-0.8, 1.2, 2.5, 1.0])
    affine[:3, 3] = [12, -20, 30]
    labels = np.zeros((5, 6, 7), np.uint8)
    labels[1, 2, 3], labels[2, 3, 4], labels[3, 4, 5] = 7, 44, 1
    for name, data in (("ct", np.zeros(labels.shape, np.int16)), ("pred", labels)):
        image = nib.Nifti1Image(data, affine)
        image.header.set_xyzt_units("mm")
        nib.save(image, case / f"{name}.nii.gz")
    manifest = {"case_id": "12345678", "status": "complete", "model": {},
                "input": {"sha256": sha256(case / "ct.nii.gz")},
                "artifacts": {"input": "ct.nii.gz", "segmentation": "pred.nii.gz"}}
    (case / "manifest.json").write_text(json.dumps(manifest))
    return case, labels, affine


def test_package_preserves_grid_ids_and_original(tmp_path):
    case, labels, affine = make_case(tmp_path)
    original = sha256(case / "pred.nii.gz")
    destination = prepare_case(case, tmp_path / "package")
    package = json.loads(destination.read_text())
    result = nib.load(package["cardiac_labels_path"])
    expected = np.where(np.isin(labels, [7, 44]), labels, 0)
    np.testing.assert_array_equal(np.asarray(result.dataobj), expected)
    np.testing.assert_allclose(result.affine, affine)
    assert result.header.get_xyzt_units()[0] == "mm"
    assert sha256(case / "pred.nii.gz") == original
    assert [s["label_id"] for s in package["structures"] if s["present"]] == [7, 44]
    with pytest.raises(FileExistsError):
        prepare_case(case, tmp_path / "package")


def test_geometry_mismatch_rejected(tmp_path):
    case, labels, affine = make_case(tmp_path)
    affine[0, 3] += 1
    image = nib.Nifti1Image(labels, affine)
    image.header.set_xyzt_units("mm")
    nib.save(image, case / "pred.nii.gz")
    with pytest.raises(ValueError, match="geometry"):
        prepare_case(case, tmp_path / "package")


def test_changed_ct_rejected(tmp_path):
    case, labels, affine = make_case(tmp_path)
    image = nib.Nifti1Image(np.ones(labels.shape, np.int16), affine)
    image.header.set_xyzt_units("mm")
    nib.save(image, case / "ct.nii.gz")
    with pytest.raises(ValueError, match="hash"):
        prepare_case(case, tmp_path / "package")
