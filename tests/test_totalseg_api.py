"""Isolated HTTP tests; full real inference is scripts/verify_backend_demo.py."""
import json
import time
from dataclasses import replace
from threading import Event

from fastapi.testclient import TestClient
import nibabel as nib
import numpy as np
import pytest

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services import analysis


@pytest.fixture
def settings(tmp_path):
    return Settings(cases_dir=tmp_path/'cases', uploads_dir=tmp_path/'uploads', jobs_dir=tmp_path/'jobs',
                    demo_path=tmp_path/'demo.nii.gz', max_pending=1)


def save_scan(path, values):
    image = nib.Nifti1Image(values, np.eye(4))
    image.header.set_xyzt_units('mm')
    nib.save(image, path)
    return path.read_bytes()


def test_new_artifacts_and_legacy_aliases(settings):
    case = settings.cases_dir/'PUBLIC-fixture'
    case.mkdir(parents=True)
    files = {'input/scan.nii.gz': b'test-volume', 'segmentations/heart.nii.gz': b'test-mask',
             'meshes/heart.glb': b'test-heart', 'meshes/cardiac.glb': b'test-combined',
             'meshes/heart.stl': b'test-stl', 'previews/axial.png': b'test-preview',
             'measurements.json': b'{"heart":{"volume_ml":1.0}}'}
    for name, data in files.items():
        path = case/name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
    manifest = {'case_id': case.name, 'schema_version': 2, 'status': 'complete',
                'input': {'path':'input/scan.nii.gz'}, 'segmentation': {'structures':['heart']},
                'structures': [{'name':'heart','glb':'meshes/heart.glb','stl':'meshes/heart.stl'}],
                'artifacts': {'measurements':'measurements.json','combined_glb':'meshes/cardiac.glb',
                              'previews':{'axial':'previews/axial.png'}},
                'artifact_sha256':{'segmentations\\heart.nii.gz':'test-only'}}
    (case/'manifest.json').write_text(json.dumps(manifest))
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/config').json()['engine']=='totalseg'
        prefix='/api/cases/'+case.name
        assert client.get(prefix+'/manifest').json()['schema_version']==2
        assert client.get(prefix+'/volume').content==b'test-volume'
        assert client.get(prefix+'/mesh/heart').content==b'test-heart'
        assert client.get(prefix+'/meshes/heart').content==b'test-heart'
        assert client.get(prefix+'/mesh/cardiac').content==b'test-combined'
        assert client.get(prefix+'/mesh/heart?format=stl').content==b'test-stl'
        assert client.get(prefix+'/segmentation/heart').content==b'test-mask'
        assert client.get(prefix+'/preview/axial').content==b'test-preview'
        assert client.get(prefix+'/overlay').content==b'test-preview'
        for route in ('segmentation','segmentation/missing','mesh/missing','preview/missing'):
            assert client.get(prefix+'/'+route).status_code==404
        manifest['input']['path']='../../outside'
        (case/'manifest.json').write_text(json.dumps(manifest))
        assert client.get(prefix+'/volume').status_code==404


@pytest.mark.parametrize('stage',['validating','validating_masks','reconstructing_and_measuring',
                                  'preparing_previews','validating_artifacts'])
def test_new_status_stages(settings,stage):
    case=settings.cases_dir/'test-case'
    case.mkdir(parents=True)
    (case/'manifest.json').write_text(json.dumps({'case_id':case.name,'status':stage}))
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/cases/test-case/status').json()['status']==stage
        assert client.get('/api/cases/test-case/manifest').status_code==409


@pytest.mark.parametrize('values',[np.ones((4,4,4),np.float32), np.full((4,4,4),np.nan,np.float32),
                                  np.ones((4,4,4,2),np.float32)])
def test_reject_invalid_voxel_data(settings,values):
    data=save_scan(settings.demo_path,values)
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/cases',files={'file':('x.nii.gz',data)}).status_code==422
        assert client.post('/api/cases/demo').status_code==422
        assert not list(settings.uploads_dir.iterdir())


def test_upload_success_and_worker_options(settings,monkeypatch):
    data=save_scan(settings.demo_path,np.arange(64,dtype=np.float32).reshape(4,4,4))
    entered, release=Event(),Event()
    def successful(path,case_id,**kwargs):
        assert kwargs['device']=='cpu' and 'totalseg_python' in kwargs
        assert 'threads' not in kwargs
        entered.set()
        release.wait(5)
        root=kwargs['cases_dir']/case_id
        root.mkdir()
        analysis.write_json(root/'manifest.json',{'case_id':case_id,'status':'complete','schema_version':2})
    monkeypatch.setattr(analysis,'analyze_case',successful)
    with TestClient(create_app(settings)) as client:
        try:
            response=client.post('/api/cases',files={'file':('../../private.nii.gz',data)})
            assert response.status_code==202
            case=response.json()['case_id']
            assert entered.wait(2)
            assert client.post('/api/cases/demo').status_code==429
            assert client.get('/health').status_code==200
        finally:
            release.set()
        for _ in range(100):
            if not list(settings.uploads_dir.iterdir()):
                break
            time.sleep(.01)
        assert client.get(f'/api/cases/{case}/manifest').json()['status']=='complete'
        assert not list(settings.uploads_dir.iterdir())


def test_byte_and_voxel_limits(settings):
    data=save_scan(settings.demo_path,np.arange(64,dtype=np.float32).reshape(4,4,4))
    with TestClient(create_app(replace(settings,max_upload_bytes=10))) as client:
        assert client.post('/api/cases',files={'file':('x.nii.gz',data)}).status_code==413
    with TestClient(create_app(replace(settings,max_voxels=1))) as client:
        assert client.post('/api/cases',files={'file':('x.nii.gz',data)}).status_code==422
