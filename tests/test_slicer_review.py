"""Synthetic revision contracts; actual Slicer serialization has a runtime test."""
import json

import nibabel as nib
import numpy as np
import pytest

from heartai.assets import sha256
from heartai.pipeline.review import accept_review
from heartai.slicer_package import prepare_case
from test_slicer_package import make_case


def make_export(tmp_path):
    case, labels, affine = make_case(tmp_path)
    package = json.loads(prepare_case(case, tmp_path / "package").read_text())
    export = tmp_path / "export"
    export.mkdir()
    cardiac = np.where(np.isin(labels, [7, 44]), labels, 0).astype(np.uint8)
    image = nib.Nifti1Image(cardiac, affine)
    image.header.set_xyzt_units("mm")
    nib.save(image, export / "cardiac_labels.nii.gz")
    (export / "review.seg.nrrd").write_bytes(b"isolated unit-test artifact; not a Slicer file")
    record = {k: package[k] for k in ("case_id", "ct_sha256", "prediction_sha256", "model", "structures")}
    record.update(revision_id="abcdef123456", review_state="draft", reviewer="test", purpose="test edit")
    refresh(export, record)
    return case, export, record


def refresh(export, record):
    record["artifacts"] = {name: sha256(export / name) for name in ("cardiac_labels.nii.gz", "review.seg.nrrd")}
    (export / "review.json").write_text(json.dumps(record))


def test_revision_rebuild_preserves_source_and_volume(tmp_path):
    case, export, record = make_export(tmp_path)
    source_hash = sha256(case / "pred.nii.gz")
    image = nib.load(export / "cardiac_labels.nii.gz")
    labels = np.array(image.dataobj)
    labels[2, 3, 5] = 44
    nib.save(nib.Nifti1Image(labels, image.affine, image.header), export / "cardiac_labels.nii.gz")
    refresh(export, record)
    result = accept_review(case, export)
    assert result["changed_voxels"] == 1
    assert result["changes"]["myocardium"] == {"added_voxels": 1, "removed_voxels": 0}
    assert result["measurements"]["myocardium"]["volume_ml"] == pytest.approx(2 * .8 * 1.2 * 2.5 / 1000)
    assert result["review_state"] == "draft"
    assert sha256(case / "pred.nii.gz") == source_hash
    with pytest.raises(FileExistsError):
        accept_review(case, export)


@pytest.mark.parametrize("fault,match", [("geometry", "grid"), ("labels", "label values"), ("hash", "hash"), ("mapping", "mapping")])
def test_invalid_revision_rejected(tmp_path, fault, match):
    case, export, record = make_export(tmp_path)
    image = nib.load(export / "cardiac_labels.nii.gz")
    labels, affine = np.array(image.dataobj), image.affine.copy()
    if fault == "geometry":
        affine[0, 3] += 1
    elif fault == "labels":
        labels[0, 0, 0] = 99
    elif fault == "mapping":
        record["structures"][0]["label_id"] = 99
    nib.save(nib.Nifti1Image(labels, affine, image.header), export / "cardiac_labels.nii.gz")
    refresh(export, record)
    if fault == "hash":
        (export / "review.seg.nrrd").write_bytes(b"altered")
    with pytest.raises(ValueError, match=match):
        accept_review(case, export)
    assert not (case / "reviews" / record["revision_id"]).exists()
