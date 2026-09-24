from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import Settings
from backend.app.routes.cases import router
from backend.app.services.analysis import AnalysisService
from backend.app.schemas import APIConfig


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.analysis = AnalysisService(config)
        yield
        app.state.analysis.close()

    app = FastAPI(title="HeartAI local research API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(config.origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
                       expose_headers=["Content-Disposition"])

    @app.middleware("http")
    async def size_limit(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > config.max_upload_bytes + 1024 * 1024):
            return JSONResponse({"detail": "Request body exceeds upload limit"}, status_code=413)
        return await call_next(request)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "demo_available": config.demo_path.is_file(), "max_upload_bytes": config.max_upload_bytes}

    @app.get('/api/config', response_model=APIConfig)
    def api_config():
        return {'engine': config.engine, 'task': 'total' if config.engine == 'totalseg' else 'legacy_monai',
                'device': config.device, 'fast_mode': False, 'max_upload_bytes': config.max_upload_bytes,
                'max_voxels': config.max_voxels, 'max_pending': config.max_pending,
                'supported_inputs': ['.nii', '.nii.gz'], 'clinical_validation': False}

    app.include_router(router)
    return app


app = create_app()
