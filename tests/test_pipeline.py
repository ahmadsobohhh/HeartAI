"""Orchestration tests use isolated synthetic inference; the CLI uses the real model."""
import importlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

analysis = importlib.import_module("heartai.pipeline.analyze")


@pytest.fixture
def source(tmp_path):
    image = nib.Nifti1Image(np.arange(1000, dtype=np.float32).reshape(10, 10, 10),
                            np.diag([2., 3., 4., 1.]))
    image.header.set_xyzt_units("mm")
    path = tmp_path / "original_filename.nii.gz"
    nib.save(image, path)
    return path


def synthetic_inference(input_path, output_dir, **kwargs):
    image = nib.load(input_path)
    labels = np.zeros(image.shape, np.uint8)
    labels[2:5, 2:5, 2:5] = 46
    segmentation = output_dir / "segmentations/scan.nii.gz"
    overlay = output_dir / "overlays/scan.png"
    for folder in ("segmentations", "overlays", "reports"):
        (output_dir / folder).mkdir()
    nib.save(nib.Nifti1Image(labels, image.affine, image.header), segmentation)
    overlay.write_bytes(b"test-only preview placeholder")
    (output_dir / "reports/scan.json").write_text("{}")
    return {"segmentation_path": str(segmentation), "overlay_path": str(overlay),
            "model": "TEST ONLY", "device": "cpu", "checkpoint_sha256": "TEST ONLY",
            "inference_seconds": 0., "total_seconds": 0.}


def test_case_orchestration_and_serialization(source, tmp_path, monkeypatch):
    monkeypatch.setattr(analysis, "segment_scan", synthetic_inference)
    result = analysis.analyze_case(source, "abcdef12", cases_dir=tmp_path / "cases")
    case = tmp_path / "cases/abcdef12"
    assert result["status"] == "complete"
    assert [s["name"] for s in result["structures"]] == ["left_ventricle"]
    assert "aorta" in result["absent_structures"]
    assert result["measurements"]["left_ventricle"]["volume_ml"] == pytest.approx(.648)
    assert json.loads((case / "manifest.json").read_text()) == result
    assert (case / result["artifacts"]["segmentation"]).is_file()
    assert (case / result["artifacts"]["combined_glb"]).is_file()
    assert (case / "input/scan.nii.gz").is_file()
    assert not list(case.rglob("*original_filename*"))
    assert [entry["stage"] for entry in result["history"]] == [
        "inspecting", "segmenting", "reconstructing", "measuring", "complete"]


def test_collision_does_not_overwrite(source, tmp_path):
    case = tmp_path / "abcdef12"
    case.mkdir()
    (case / "manifest.json").write_text("keep")
    with pytest.raises(FileExistsError):
        analysis.analyze_case(source, "abcdef12", cases_dir=tmp_path)
    assert (case / "manifest.json").read_text() == "keep"


def test_invalid_id_cannot_escape(source, tmp_path):
    with pytest.raises(ValueError, match="case_id"):
        analysis.analyze_case(source, "../escape", cases_dir=tmp_path)


def test_failure_recorded_without_success(source, tmp_path, monkeypatch):
    def failure(*args, **kwargs):
        raise FileNotFoundError("TEST: checkpoint missing")
    monkeypatch.setattr(analysis, "segment_scan", failure)
    with pytest.raises(FileNotFoundError):
        analysis.analyze_case(source, "abcdef12", cases_dir=tmp_path)
    result = json.loads((tmp_path / "abcdef12/manifest.json").read_text())
    assert result["status"] == "failed" and result["failed_stage"] == "segmenting"
    assert "checkpoint missing" in result["error"]
    assert result["measurements"] == {} and "segmentation" not in result["artifacts"]


def test_invalid_nifti_records_failure(tmp_path):
    source = tmp_path / "bad.nii.gz"
    source.write_bytes(b"invalid scan")
    with pytest.raises(nib.filebasedimages.ImageFileError):
        analysis.analyze_case(source, "abcdef12", cases_dir=tmp_path / "cases")
    result = json.loads((tmp_path / "cases/abcdef12/manifest.json").read_text())
    assert result["status"] == "failed" and result["failed_stage"] == "inspecting"


def test_non_mm_input_rejected_before_inference(source, tmp_path):
    image = nib.load(source)
    image.header.set_xyzt_units("meter")
    other = tmp_path / "meters.nii.gz"
    nib.save(image, other)
    with pytest.raises(ValueError, match="requires NIfTI spatial units in mm"):
        analysis.analyze_case(other, "abcdef12", cases_dir=tmp_path / "cases")
