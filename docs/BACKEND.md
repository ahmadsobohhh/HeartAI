# Local API — completed part 1

**Historical MONAI checkpoint.** The current default backend is TotalSegmentator; see [Milestone E setup, routes, and verification](TOTALSEG_MILESTONE_E.md). To reproduce the legacy behavior below, set `$env:HEARTAI_ENGINE = 'monai'` before starting the server. The timings and frontend notes below describe the preserved MONAI proof-of-concept.

The FastAPI backend wraps the verified `analyze_case()` function directly. There is no new inference implementation, training, database, or subprocess per analysis.

## Start

From the repository root, after the README setup/download steps:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Interactive API documentation: http://127.0.0.1:8000/docs

Use **one Uvicorn worker**. The in-process queue deliberately serializes analysis because inference and mesh generation share RAM and PyTorch settings. At most four uploads/analyses are pending at once; additional submissions return HTTP 429. Graceful shutdown waits for submitted work. After an abrupt restart, interrupted jobs are marked failed and can be submitted again. Completed cases persist on disk and are still readable after a restart, including earlier CLI cases.

Configuration is centralized in `backend/app/config.py`. The local service has no accounts or authentication: bind to loopback. CORS permits only localhost/127.0.0.1 port 3000. Do not start multiple servers against the same job directories.

## API contract

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | Readiness of HTTP service, demo availability, upload limit |
| POST | `/api/cases` | Multipart `file`, HTTP 202 with generated `case_id` and `queued` status |
| POST | `/api/cases/demo` | Queue the configured public Slicer demo; does not silently download files |
| GET | `/api/cases/{id}` | Case manifest or queued/failed job record |
| GET | `/api/cases/{id}/status` | Stage, history, and error when present |
| GET | `/api/cases/{id}/measurements` | Download real measurements JSON |
| GET | `/api/cases/{id}/segmentation` | Download segmentation NIfTI |
| GET | `/api/cases/{id}/overlay` | Display PNG overlay |
| GET | `/api/cases/{id}/meshes/{structure}` | Download individual GLB; `?format=stl` for STL |
| GET | `/api/cases/{id}/meshes/heart` | Download combined GLB |

Example using Windows curl:

```powershell
curl.exe -F "file=@data/demo/CTA-cardio.nii.gz" http://127.0.0.1:8000/api/cases
```

Poll the status URL every 1–2 seconds. Stages are `queued`, `inspecting`, `segmenting`, `reconstructing`, `measuring`, `complete`, or `failed`. `segmenting` includes the existing inference callable's preprocessing and overlay generation; the API does not invent finer progress. Artifact routes return 409 until completion. No percentages or model results are fabricated.

Inputs must be scalar 3-D `.nii`/`.nii.gz` CT volumes with millimeter spatial metadata. The upload limit is 256 MiB, with a 128-million-voxel limit. Header validation happens before accepting the job; full intensity validation happens in the analysis worker. Unsupported suffixes return 415; invalid NIfTI headers return 422; oversized uploads return 413; missing cases/artifacts return 404. Missing checkpoints and pipeline failures appear as failed job records. Uploaded files use generated IDs and staging copies are removed after processing. Original patient filenames are never used as filesystem paths.

All manifests use relative artifact paths. Downloads resolve only known manifest artifacts within the case directory; no arbitrary file path endpoint exists. The frontend should use the API URLs above, not the filesystem-relative manifest paths directly.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py
# With the server running, execute real pretrained inference through HTTP:
.\.venv\Scripts\python.exe scripts/test_api_demo.py
```

The HTTP smoke test performs a real multipart CT upload, checks health during background processing, polls completion, downloads segmentation/overlay/combined and individual GLBs, checks an STL, and verifies measurement serialization. It saves actual timings and download hashes to `results/api-validation.json`. Unit tests use mocks only for isolated error/queue behavior.

Verified run: case `0d71f0216825` was accepted in **0.53 seconds**, completed the actual pipeline in **34.93 seconds** on CPU, and passed all download/measurement checks. Health/status requests remained responsive during inference. The complete non-integration test suite passed **32 tests**; `pip check` reported no broken requirements. The new API tests cover upload rejection, queue saturation, asynchronous failure, status, missing cases, artifact containment, CORS, and restart recovery.

The Next.js upload/status interface and React Three Fiber viewer are now implemented. See [frontend setup and verification](FRONTEND.md).
