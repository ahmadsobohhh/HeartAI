import json
import time
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
    return Settings(cases_dir=tmp_path / "cases", uploads_dir=tmp_path / "uploads",
                    jobs_dir=tmp_path / "jobs", demo_path=tmp_path / "demo.nii.gz", max_pending=1)


@pytest.fixture
def scan(settings):
    image = nib.Nifti1Image(np.arange(64, dtype=np.float32).reshape(4, 4, 4), np.eye(4))
    image.header.set_xyzt_units("mm")
    nib.save(image, settings.demo_path)
    return settings.demo_path.read_bytes()


def test_health_errors_and_cors(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/api/cases/deadbeef").status_code == 404
        assert client.post("/api/cases/demo").status_code == 404
        assert client.post("/api/cases", files={"file": ("x.txt", b"bad")}).status_code == 415
        assert client.post("/api/cases", files={"file": ("x.nii.gz", b"bad")}).status_code == 422
        assert client.post("/api/cases", headers={"Content-Length": str(300*1024*1024)}).status_code == 413
        assert client.get("/health", headers={"Origin": "http://localhost:3000"}).headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "access-control-allow-origin" not in client.get("/health", headers={"Origin": "https://example.com"}).headers
        assert not list(settings.uploads_dir.iterdir())


def test_async_queue_and_failure(settings, scan, monkeypatch):
    entered, release = Event(), Event()
    def fail(*args, **kwargs):
        entered.set()
        release.wait(10)
        raise RuntimeError("Test checkpoint failure")
    monkeypatch.setattr(analysis, "analyze_case", fail)
    with TestClient(create_app(settings)) as client:
        try:
            response = client.post("/api/cases", files={"file": ("private-name.nii.gz", scan)})
            assert response.status_code == 202
            case = response.json()["case_id"]
            assert entered.wait(2)
            assert client.get("/health").status_code == 200
            assert client.get(f"/api/cases/{case}/status").json()["status"] == "queued"
            assert client.get(f"/api/cases/{case}/segmentation").status_code == 409
            assert client.post("/api/cases/demo").status_code == 429
            assert not list(settings.uploads_dir.glob("*private*"))
        finally:
            release.set()
        for _ in range(100):
            state = client.get(f"/api/cases/{case}/status").json()
            if state["status"] == "failed":
                break
            time.sleep(.01)
        assert state["status"] == "failed" and "checkpoint" in state["error"]


def test_completed_artifacts_and_path_confinement(settings):
    case = settings.cases_dir / "abcdef12"
    case.mkdir(parents=True)
    (case / "measurements.json").write_text('{"structures":{"aorta":{"volume_ml":1.5}}}')
    (case / "aorta.glb").write_bytes(b"glTF-test-only")
    (case / "prediction.nii.gz").write_bytes(b"test-only")
    manifest = {"case_id": "abcdef12", "status": "complete", "artifacts": {
        "measurements": "measurements.json", "segmentation": "prediction.nii.gz",
        "overlay": "../outside.png", "meshes": {"aorta": {"glb": "aorta.glb"}},
        "combined_glb": "aorta.glb"}}
    (case / "manifest.json").write_text(json.dumps(manifest))
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/cases/abcdef12").json()["status"] == "complete"
        assert client.get("/api/cases/abcdef12/measurements").json()["structures"]["aorta"]["volume_ml"] == 1.5
        assert client.get("/api/cases/abcdef12/meshes/aorta").content.startswith(b"glTF")
        assert client.get("/api/cases/abcdef12/meshes/heart").status_code == 200
        assert client.get("/api/cases/abcdef12/meshes/missing").status_code == 404
        assert client.get("/api/cases/abcdef12/meshes/aorta?format=exe").status_code == 422
        assert client.get("/api/cases/abcdef12/segmentation").status_code == 200
        assert client.get("/api/cases/abcdef12/overlay").status_code == 404


def test_restart_marks_interrupted_job_failed(settings):
    settings.jobs_dir.mkdir(parents=True)
    (settings.jobs_dir / "abcdef12.json").write_text('{"case_id":"abcdef12","status":"queued"}')
    with TestClient(create_app(settings)) as client:
        result = client.get("/api/cases/abcdef12/status").json()
        assert result["status"] == "failed" and "restart" in result["error"]
