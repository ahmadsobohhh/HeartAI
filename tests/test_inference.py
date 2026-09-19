import os
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest
import torch

from heartai.assets import ROOT
from heartai.inference.predictor import segment_scan
from heartai.preprocessing.transforms import inference_config

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.environ.get("HEARTAI_RUN_INTEGRATION") != "1",
    reason="Set HEARTAI_RUN_INTEGRATION=1 after downloading the public assets",
)]


def test_official_transform_spatial_roundtrip(tmp_path):
    affine = np.array([[0, -2., 0, 40], [1.5, 0, 0, -20], [0, 0, -4., 100], [0, 0, 0, 1]])
    ct = np.arange(17*19*21, dtype=np.float32).reshape(17, 19, 21)
    path = tmp_path / "anisotropic.nii.gz"
    nib.save(nib.Nifti1Image(ct, affine), path)
    parser = inference_config()
    batch = parser.get_parsed_content("preprocessing")({"image": str(path)})
    image = batch["image"]
    assert nib.aff2axcodes(image.affine) == ("R", "A", "S")
    np.testing.assert_allclose(nib.affines.voxel_sizes(image.affine.cpu().numpy()), [3, 3, 3])
    assert float(image.min()) == pytest.approx(-1)
    assert float(image.max()) == pytest.approx(1)
    # Synthetic logits check only inversion; they are never presented as model results.
    batch["pred"] = torch.zeros((2, *image.shape[1:]))
    batch["pred"][1] = 1
    result = parser.get_parsed_content("postprocessing")(batch)["pred"]
    assert tuple(result.shape) == (1, *ct.shape)
    np.testing.assert_allclose(result.affine, affine, atol=1e-5)
    assert set(torch.unique(result).tolist()) == {1}


def test_real_pretrained_inference(tmp_path):
    path = ROOT / "data/demo/CTA-cardio.nii.gz"
    report = segment_scan(path, tmp_path, device="cpu")
    ct = nib.load(path)
    prediction = nib.load(report["segmentation_path"])
    assert report["logits_shape"] == [1, 105, *report["preprocessed_shape"][1:]]
    assert prediction.shape == ct.shape
    np.testing.assert_allclose(prediction.affine, ct.affine)
    np.testing.assert_allclose(prediction.get_qform(), ct.get_qform())
    np.testing.assert_allclose(prediction.get_sform(), ct.get_sform())
    assert prediction.header.get_zooms() == ct.header.get_zooms()
    labels = prediction.get_fdata()
    assert np.isfinite(labels).all()
    assert np.equal(labels, labels.astype(np.uint8)).all()
    assert labels.min() >= 0 and labels.max() <= 104
    assert set(report["cardiac_labels_present"]) == {"7", "44", "45", "46", "47", "48", "49"}
    assert Path(report["overlay_path"]).is_file()
    # On the same device, compare with the saved demo when it is present.
    reference_path = ROOT / "results/segmentations/CTA-cardio.nii.gz"
    import json
    reference_report = ROOT / "results/reports/CTA-cardio.json"
    if (reference_path.exists() and reference_report.exists()
            and json.loads(reference_report.read_text())["device"] == "cpu"):
        np.testing.assert_array_equal(labels, nib.load(reference_path).get_fdata())
