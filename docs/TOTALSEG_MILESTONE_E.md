# Milestone E — TotalSegmentator backend

The existing FastAPI backend now uses the verified TotalSegmentator CLI pipeline by default. One bounded background worker performs real analysis while HTTP requests continue. The MONAI implementation, saved cases, and legacy artifact routes remain available. No frontend or volume-viewer work is included in this milestone.

## Start locally

Use the two Python environments installed for Milestone D. From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`. Use one worker and one server per job directory; the queue is in-process and serializes model runs. It accepts at most four pending jobs, returning 429 when full. The service is a local research prototype without authentication; bind to loopback. Graceful shutdown waits for queued work. Interrupted work is marked failed after a restart; completed cases remain available.

Defaults are `HEARTAI_ENGINE=totalseg`, `HEARTAI_DEVICE=cpu`, and the repository's `.venv-totalseg` inference environment. `HEARTAI_TOTALSEG_PYTHON` overrides the inference executable. Set environment variables before starting the server. `HEARTAI_ENGINE=monai` explicitly selects the preserved legacy pipeline; its supported devices remain `auto`, `cpu`, and `cuda`. The TotalSegmentator path accepts `cpu` or `gpu`, with GPU requiring the appropriate CUDA installation. No AMD acceleration was enabled.

## Routes

| Method | Route | Result |
| --- | --- | --- |
| GET | `/health` | HTTP readiness, demo availability, byte limit |
| GET | `/api/config` | Engine/task/device, input limits, supported formats |
| POST | `/api/cases` | Multipart `file`; validates and returns 202 with generated ID |
| POST | `/api/cases/demo` | Validate/copy configured public CT and queue real inference |
| GET | `/api/cases/{id}` | Current case or queued/failed job |
| GET | `/api/cases/{id}/status` | Actual stage, history, and errors |
| GET | `/api/cases/{id}/manifest` | Completed case manifest |
| GET | `/api/cases/{id}/measurements` | Measurements JSON |
| GET | `/api/cases/{id}/volume` | Original input NIfTI |
| GET | `/api/cases/{id}/segmentation/{structure}` | Recorded individual mask, including noncardiac classes |
| GET | `/api/cases/{id}/mesh/{structure}` | Individual GLB; `?format=stl` for STL |
| GET | `/api/cases/{id}/mesh/cardiac` | Combined cardiac GLB |
| GET | `/api/cases/{id}/preview/{view}` | `axial`, `coronal`, or `sagittal` PNG |

The plural `/meshes/{structure}` route is retained as an alias. For TotalSegmentator, `heart` means the actual whole-heart structure and `cardiac` means the combined scene. Legacy MONAI cases retain their old combined `heart` behavior. The old `/overlay` route serves the axial overlay on new cases. The old single `/segmentation` route returns a descriptive 404 for new multi-mask cases instead of returning an unrelated file or failing with a server error.

All 117 recorded masks can be downloaded for the public demo; only the six selected cardiac structures currently have meshes. Absent structures return 404. This does not add coronary arteries, heart chambers, or other geometry that the selected model did not produce.

## Validation and behavior

Uploads accept `.nii` and `.nii.gz`, at most 256 MiB and 128 million voxels. Before accepting a job, validation checks actual NIfTI readability, three-dimensional shape, millimeter units, finite/invertible affine, bounded data offset, and finite/nonconstant intensities. Corrupt payloads and invalid image contents return 422; unsupported extensions return 415; oversized files return 413. Files receive generated IDs rather than user-supplied names. Staging copies are removed after job completion/failure.

Artifact routes require completed cases (409 otherwise), resolve manifest-listed files within the case directory, and return 404 for absent artifacts. Existing readable CLI case IDs such as `PUBLIC-001-D-final` are supported, as well as generated API IDs. Pydantic status responses support every actual TotalSegmentator stage: `validating`, `segmenting`, `validating_masks`, `reconstructing_and_measuring`, `preparing_previews`, and `validating_artifacts`, followed by `complete` or `failed`. No invented percentages are returned.

Status `complete` means computational completion. Slicer review and clinical validation remain separate manifest fields. Geometry conventions, component retention, scan truncation, and model limitations remain those documented in Milestones C/D.

## Reproduce verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py tests/test_totalseg_api.py
# With a server running; this uploads the real public CT and executes inference:
.\.venv\Scripts\python.exe scripts/verify_backend_demo.py --url http://127.0.0.1:8000
```

The opt-in HTTP check polls actual status and health, then downloads every recorded mask, all individual cardiac GLBs/STLs, the combined GLB, the CT, measurements, and three previews. Every downloaded byte stream is checked against the manifest SHA-256. Full inference is never part of normal unit tests. A dropped client connection can be recovered with `--case-id <existing-id> --report <new-report.json>` without resubmitting inference. The verifier disables persistent connections to avoid idle keep-alive expiry races during long jobs.

## Execution evidence

The targeted API tests passed **15 tests**, with one existing Starlette/AnyIO deprecation warning. Results are saved in `results/milestone-e-api-tests.txt`.

The real multipart upload was accepted in **0.997 seconds**, creating case `387fecd63a6d` on the local test server at port 8765. The initial verifier observed `validating` and `segmenting`, then its polling connection dropped. The background job remained alive; verification resumed against the same ID, with no duplicate model run. Initial client evidence is preserved in `results/milestone-e-http.json`; resumed verification is recorded in `results/milestone-e-http-final.json`. Server logs are `results/milestone-e-server-stdout.txt` and `results/milestone-e-server-stderr.txt`.

Final completion evidence is recorded after the real job and download checks finish.
