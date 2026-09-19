import shutil
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from backend.app.schemas import CaseAccepted, CaseStatus
from backend.app.services.analysis import AnalysisService, validate_upload

router = APIRouter(prefix="/api/cases", tags=["cases"])


def service(request: Request) -> AnalysisService:
    return request.app.state.analysis


@router.post("", status_code=202, response_model=CaseAccepted)
async def create_case(request: Request, file: UploadFile = File(...)) -> dict:
    worker = service(request)
    name = (file.filename or "").lower()
    suffix = ".nii.gz" if name.endswith(".nii.gz") else ".nii" if name.endswith(".nii") else None
    if suffix is None:
        await file.close()
        raise HTTPException(415, "Upload a .nii or .nii.gz CT file")
    if not worker.slots.acquire(blocking=False):
        await file.close()
        raise HTTPException(429, "Analysis queue is full; try again after a case finishes")
    case_id = uuid4().hex[:12]
    path = worker.settings.uploads_dir / (case_id + suffix)
    try:
        size = 0
        with path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > worker.settings.max_upload_bytes:
                    raise HTTPException(413, "Upload exceeds the 256 MiB limit")
                target.write(chunk)
        await run_in_threadpool(validate_upload, path, worker.settings)
        worker.submit(case_id, path)
    except Exception:
        path.unlink(missing_ok=True)
        worker.slots.release()
        raise
    finally:
        await file.close()
    return {"case_id": case_id, "status": "queued"}


@router.post("/demo", status_code=202, response_model=CaseAccepted)
async def create_demo(request: Request) -> dict:
    worker = service(request)
    if not worker.settings.demo_path.is_file():
        raise HTTPException(404, "Demo scan unavailable; run scripts/download_assets.py")
    if not worker.slots.acquire(blocking=False):
        raise HTTPException(429, "Analysis queue is full")
    case_id = uuid4().hex[:12]
    path = worker.settings.uploads_dir / f"{case_id}.nii.gz"
    try:
        await run_in_threadpool(shutil.copyfile, worker.settings.demo_path, path)
        worker.submit(case_id, path)
    except Exception:
        path.unlink(missing_ok=True)
        worker.slots.release()
        raise
    return {"case_id": case_id, "status": "queued"}


@router.get("/{case_id}")
def get_case(case_id: str, request: Request) -> dict:
    return service(request).read(case_id)


@router.get("/{case_id}/status", response_model=CaseStatus)
def get_status(case_id: str, request: Request) -> dict:
    return service(request).read(case_id)


@router.get("/{case_id}/measurements")
def measurements(case_id: str, request: Request) -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    return FileResponse(worker.artifact(case_id, result["artifacts"]["measurements"]),
                        media_type="application/json", filename="measurements.json")


@router.get("/{case_id}/segmentation")
def segmentation(case_id: str, request: Request) -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    return FileResponse(worker.artifact(case_id, result["artifacts"]["segmentation"]),
                        media_type="application/gzip", filename="segmentation.nii.gz")


@router.get("/{case_id}/overlay")
def overlay(case_id: str, request: Request) -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    return FileResponse(worker.artifact(case_id, result["artifacts"]["overlay"]), media_type="image/png")


@router.get("/{case_id}/meshes/{structure}")
def mesh(case_id: str, structure: str, request: Request, format: Literal["glb", "stl"] = "glb") -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    artifacts = result["artifacts"]
    path = artifacts.get("combined_glb") if structure == "heart" and format == "glb" else artifacts.get("meshes", {}).get(structure, {}).get(format)
    if path is None:
        raise HTTPException(404, "Structure or format not available")
    return FileResponse(worker.artifact(case_id, path), filename=f"{structure}.{format}",
                        media_type="model/gltf-binary" if format == "glb" else "model/stl")
