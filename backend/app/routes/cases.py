import shutil
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from backend.app.schemas import CaseAccepted, CaseStatus, CaseManifest
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
        await run_in_threadpool(validate_upload, path, worker.settings)
        worker.submit(case_id, path)
    except Exception:
        path.unlink(missing_ok=True)
        worker.slots.release()
        raise
    return {"case_id": case_id, "status": "queued"}


@router.get("/{case_id}", response_model=CaseManifest)
def get_case(case_id: str, request: Request) -> dict:
    return service(request).read(case_id)


@router.get('/{case_id}/manifest', response_model=CaseManifest)
def manifest(case_id: str, request: Request) -> dict:
    return service(request).completed(case_id)


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
    path = result['artifacts'].get('segmentation')
    if path is None:
        raise HTTPException(404, 'This case has separate masks; use /segmentation/{structure}')
    return FileResponse(worker.artifact(case_id, path),
                        media_type="application/gzip", filename="segmentation.nii.gz")


@router.get("/{case_id}/overlay")
def overlay(case_id: str, request: Request) -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    path = result['artifacts'].get('overlay') or result['artifacts'].get('previews', {}).get('axial')
    if path is None:
        raise HTTPException(404, 'Overlay not available')
    return FileResponse(worker.artifact(case_id, path), media_type="image/png")


@router.get("/{case_id}/meshes/{structure}")
@router.get("/{case_id}/mesh/{structure}")
def mesh(case_id: str, structure: str, request: Request, format: Literal["glb", "stl"] = "glb") -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    artifacts = result["artifacts"]
    if result.get('schema_version') == 2:
        spec = next((s for s in result.get('structures', []) if s['name'] == structure), {})
        path = artifacts.get('combined_glb') if structure == 'cardiac' and format == 'glb' else spec.get(format)
    else:
        path = artifacts.get("combined_glb") if structure == "heart" and format == "glb" else artifacts.get("meshes", {}).get(structure, {}).get(format)
    if path is None:
        raise HTTPException(404, "Structure or format not available")
    return FileResponse(worker.artifact(case_id, path), filename=f"{structure}.{format}",
                        media_type="model/gltf-binary" if format == "glb" else "model/stl")


@router.get('/{case_id}/volume')
def volume(case_id: str, request: Request) -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    path = result.get('input', {}).get('path') or result['artifacts'].get('input')
    if not path:
        raise HTTPException(404, 'Source volume not available')
    target = worker.artifact(case_id, path)
    return FileResponse(target, filename=target.name,
                        media_type='application/gzip' if target.name.endswith('.gz') else 'application/octet-stream')


@router.get('/{case_id}/segmentation/{structure}')
def structure_mask(case_id: str, structure: str, request: Request) -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    if structure not in result.get('segmentation', {}).get('structures', []):
        raise HTTPException(404, 'Structure not available')
    relative = f'segmentations/{structure}.nii.gz'
    if relative not in result.get('artifact_sha256', {}):
        raise HTTPException(404, 'Mask artifact not recorded')
    return FileResponse(worker.artifact(case_id, relative), filename=f'{structure}.nii.gz', media_type='application/gzip')


@router.get('/{case_id}/preview/{view}')
def preview(case_id: str, view: str, request: Request) -> FileResponse:
    worker = service(request)
    result = worker.completed(case_id)
    relative = result['artifacts'].get('previews', {}).get(view)
    if not relative:
        raise HTTPException(404, 'Preview not available')
    return FileResponse(worker.artifact(case_id, relative), media_type='image/png')
