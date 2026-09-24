"""No inference in CI: synthetic data is confined to these isolated tests."""
import json
from pathlib import Path
import subprocess
import sys

import nibabel as nib
import numpy as np
import pytest

from heartai.pipeline import totalseg as pipeline


@pytest.fixture
def source(tmp_path):
    image = nib.Nifti1Image(np.arange(8000, dtype=np.float32).reshape(20, 20, 20), np.eye(4))
    image.header.set_xyzt_units('mm')
    path = tmp_path / 'scan.nii.gz'
    nib.save(image, path)
    return path


def test_failure_manifest_and_collision(source, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ['test-only-inference'])
    monkeypatch.setattr(pipeline, 'run_script', fail)
    with pytest.raises(subprocess.CalledProcessError):
        pipeline.analyze_case(source, 'PUBLIC-test', cases_dir=tmp_path, totalseg_python=sys.executable)
    path = tmp_path / 'PUBLIC-test/manifest.json'
    before = path.read_bytes()
    record = json.loads(before)
    assert record['status'] == 'failed' and record['failed_stage'] == 'segmenting'
    assert record['timing']['segmenting_seconds'] >= 0
    assert record['artifacts'] == {}
    with pytest.raises(FileExistsError):
        pipeline.analyze_case(source, 'PUBLIC-test', cases_dir=tmp_path)
    assert before == path.read_bytes()


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'a/b', 'NUL', 'COM1'])
def test_bad_case_id(source, tmp_path, name):
    with pytest.raises(ValueError, match='case_id'):
        pipeline.analyze_case(source, name, cases_dir=tmp_path)


def test_invalid_scan_and_missing_environment(tmp_path, source):
    broken = tmp_path / 'bad.nii.gz'
    broken.write_bytes(b'not a NIfTI')
    with pytest.raises(nib.filebasedimages.ImageFileError):
        pipeline.analyze_case(broken, 'bad', cases_dir=tmp_path)
    assert json.loads((tmp_path / 'bad/manifest.json').read_text())['failed_stage'] == 'validating'
    with pytest.raises(FileNotFoundError, match='HEARTAI_TOTALSEG_PYTHON'):
        pipeline.analyze_case(source, 'missing', cases_dir=tmp_path, totalseg_python=tmp_path / 'absent.exe')


def test_artifact_validation_rejects_escape_and_missing(tmp_path):
    case = tmp_path / 'case'
    case.mkdir()
    (tmp_path / 'outside').write_bytes(b'outside')
    for path in ('../outside', 'missing'):
        with pytest.raises(ValueError, match='artifact'):
            pipeline.validate_artifacts(case, [path])
    (case / 'empty').touch()
    with pytest.raises(ValueError):
        pipeline.validate_artifacts(case, ['empty'])


def test_completed_case_is_self_contained(source, tmp_path, monkeypatch):
    """Mock only inference/inspection; execute real geometry, exports and previews."""
    def fixture_stage(python, script, arguments, log, **kwargs):
        if script == 'run_totalseg.py':
            scan, _, destination, *_ = arguments
            destination.mkdir()
            masks = destination / 'segmentations'
            masks.mkdir()
            image = nib.load(scan)
            mask = np.zeros(image.shape, np.uint8)
            mask[4:14, 4:14, 4:14] = 1
            nib.save(nib.Nifti1Image(mask, image.affine, image.header), masks / 'heart.nii.gz')
            record = {'engine': 'TEST ONLY', 'version': 'test', 'task': 'total', 'device': 'cpu',
                      'fast_mode': False, 'roi_subset': None, 'runtime_seconds': 0,
                      'input': {'path': str(scan)}}
            (destination / 'run.json').write_text(json.dumps(record))
            for name in ('installed_label_map.json', 'upstream_report.json'):
                (destination / name).write_text('{}')
            (destination / 'logs.txt').write_text('isolated test fixture only')
        elif script == 'inspect_totalseg.py':
            case = arguments[0]
            validation = {'status': 'passed', 'nonempty_structures': 1,
                          'structures': [{'name': 'heart', 'file': 'segmentations/heart.nii.gz'}]}
            (case / 'validation.json').write_text(json.dumps(validation))
            (case / 'previews').mkdir()
            # Produce a real PNG even in this isolated test, never demo output.
            from PIL import Image
            Image.new('RGB', (2, 2)).save(case / 'previews/cardiac_overlay.png')
        elif script == 'prepare_totalseg_review.py':
            case, output = arguments
            output.mkdir()
            path = case / 'segmentations/heart.nii.gz'
            spec = {'name': 'heart', 'label_id': 51, 'color': '#f26079', 'path': str(path),
                    'sha256': pipeline.file_hash(path), 'foreground_voxels': 1000,
                    'review_center_ras_mm': [8, 8, 8]}
            package = {'status': 'prepared_pending_slicer_review', 'ct_path': str(case / 'input/scan.nii.gz'),
                       'ct_sha256': pipeline.file_hash(case / 'input/scan.nii.gz'), 'engine': 'TEST ONLY',
                       'version': 'test', 'structures': [spec], 'output_inventory': [spec],
                       'unavailable_focus': [{'name': 'aorta', 'reason': 'test fixture absent'}],
                       'absent_task_labels': ['myocardium']}
            (output / 'cardiac_subset.json').write_text(json.dumps(package))
        else:
            raise AssertionError(script)
    monkeypatch.setattr(pipeline, 'run_script', fixture_stage)
    record = pipeline.analyze_case(source, 'test-complete', cases_dir=tmp_path, totalseg_python=sys.executable)
    case = tmp_path / 'test-complete'
    assert record['status'] == 'complete'
    assert record['review']['slicer'] == 'not_run'
    assert record['unavailable_focus'][0]['name'] == 'aorta'
    assert json.loads((case / 'measurements.json').read_text())['heart']['volume_ml'] == pytest.approx(1)
    assert json.loads((case / 'manifest.json').read_text()) == record
    assert all(pipeline.file_hash(case / path) == digest for path, digest in record['artifact_sha256'].items())
    for entry in record['history']:
        assert entry['seconds'] >= 0 and entry['finished_utc']
