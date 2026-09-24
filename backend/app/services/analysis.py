"""A bounded, single-worker queue. Inference runs outside the HTTP event loop."""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from pathlib import Path
import re
from threading import BoundedSemaphore

from fastapi import HTTPException
import nibabel as nib
import numpy as np

from backend.app.config import Settings
from heartai.pipeline.totalseg import analyze_case, write_json

logger = logging.getLogger(__name__)


def validate_upload(path: Path, settings: Settings) -> None:
    try:
        image = nib.load(path)
        if len(image.shape) != 3 or min(image.shape) < 1:
            raise ValueError("Expected a scalar 3-D CT")
        if int(np.prod(image.shape, dtype=np.int64)) > settings.max_voxels:
            raise ValueError("Volume exceeds the 128-million-voxel limit")
        if image.header.get_xyzt_units()[0] != "mm":
            raise ValueError("NIfTI spatial units must be mm")
        if not np.isfinite(image.affine).all() or abs(np.linalg.det(image.affine[:3, :3])) < 1e-12:
            raise ValueError("Invalid spatial affine")
        if image.dataobj.offset > 1024 * 1024:
            raise ValueError("NIfTI data offset exceeds the supported limit")
        data = image.get_fdata(dtype=np.float32)
        if not np.isfinite(data).all() or data.min() == data.max():
            raise ValueError("CT must contain finite, nonconstant intensities")
    except Exception as error:
        raise HTTPException(422, f"Invalid NIfTI: {error}") from error


class AnalysisService:
    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.engine not in ('totalseg', 'monai'):
            raise ValueError('HEARTAI_ENGINE must be totalseg or monai')
        for directory in (settings.cases_dir, settings.uploads_dir, settings.jobs_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.slots = BoundedSemaphore(settings.max_pending)
        # Queued/active work cannot survive a process restart; never pretend it did.
        for path in settings.jobs_dir.glob("*.json"):
            job = json.loads(path.read_text())
            if job["status"] not in ("complete", "failed"):
                manifest = settings.cases_dir / path.stem / "manifest.json"
                completed = manifest.exists() and json.loads(manifest.read_text())["status"] == "complete"
                job.update(status="complete" if completed else "failed")
                if not completed:
                    job["error"] = "Analysis interrupted by server restart; submit the scan again"
                write_json(path, job)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="heartai-analysis")

    def close(self) -> None:
        self.executor.shutdown(wait=True)

    def submit(self, case_id: str, path: Path) -> None:
        write_json(self.settings.jobs_dir / f"{case_id}.json", {"case_id": case_id, "status": "queued"})
        self.executor.submit(self._run, case_id, path)

    def _run(self, case_id: str, path: Path) -> None:
        try:
            if self.settings.engine == 'monai':
                from heartai.pipeline.analyze import analyze_case as legacy_analyze
                legacy_analyze(path, case_id, cases_dir=self.settings.cases_dir,
                               device=self.settings.device, threads=self.settings.threads)
            else:
                analyze_case(path, case_id, cases_dir=self.settings.cases_dir,
                             device=self.settings.device, totalseg_python=self.settings.totalseg_python)
            job = {"case_id": case_id, "status": "complete"}
        except Exception as error:
            logger.exception("Analysis failed for %s", case_id)
            job = {"case_id": case_id, "status": "failed", "error": str(error)}
        finally:
            path.unlink(missing_ok=True)
            self.slots.release()
        write_json(self.settings.jobs_dir / f"{case_id}.json", job)

    def read(self, case_id: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", case_id):
            raise HTTPException(404, "Case not found")
        manifest_path = self.settings.cases_dir / case_id / "manifest.json"
        job_path = self.settings.jobs_dir / f"{case_id}.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        job = json.loads(job_path.read_text()) if job_path.exists() else None
        if job and job["status"] == "failed":
            return {**(manifest or {}), **job}
        if manifest is not None:
            return manifest
        if job is not None:
            return job
        raise HTTPException(404, "Case not found")

    def completed(self, case_id: str) -> dict:
        case = self.read(case_id)
        if case["status"] != "complete":
            raise HTTPException(409, "Case is not complete")
        return case

    def artifact(self, case_id: str, relative: str) -> Path:
        root = (self.settings.cases_dir / case_id).resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(404, "Artifact not found")
        return path
