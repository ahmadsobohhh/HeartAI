# HeartAI V1 — TotalSegmentator

V1's segmentation path is powered by **TotalSegmentator**. HeartAI did not invent or train this model. The current checkpoint is **Milestone D**: one CLI command produces real segmentation, physical meshes, measurements, previews, and a case manifest. Research prototype; not for clinical use.

**Milestone A verified:** TotalSegmentator 2.18.0 completed standard `total` inference on public CTACardio using CPU in 501.81 seconds including first-use downloads. All 117 output masks passed grid/binary validation; 88 were nonempty, including heart, aorta, pulmonary vein, left atrial appendage, and both vena cavae. The real overlay was generated and visually inspected. Results are under `results/cases/PUBLIC-001-totalseg/`.

## Milestone B verified

The six cardiac masks were loaded with the source CT in **3D Slicer 5.12.4**. Geometry and exact voxel comparisons passed, including a saved-segmentation round trip. All six structures were visually checked in axial, coronal, and sagittal views, plus Slicer's native 3D display. Original TotalSegmentator and MONAI outputs remain unchanged.

Open `results/slicer/PUBLIC-001-totalseg-B-final/slicer/review.mrb` in Slicer to inspect the saved session. The same folder contains `cardiac.seg.nrrd` and the captured views; its parent contains the inventory and completion record. See [Milestone B evidence, limitations, and reproduction commands](docs/TOTALSEG_MILESTONE_B.md).

The aorta reaches the scan boundary; small disconnected heart and inferior-vena-cava components are preserved and documented. This is a technical alignment check, not clinical validation.

For future viewer debugging, correct Slicer alignment with incorrect HeartAI alignment suggests a viewer/spatial-conversion issue. Poor segmentation in both points toward the input/model.

## Milestone C verified

Six real cardiac structures now have individual GLB and STL exports, plus `meshes/cardiac.glb` with six named structures. The original patient origin and scale are preserved. Voxel volumes, surface areas, centroids, bounds, and mesh checks are recorded in `results/cases/PUBLIC-001-totalseg/milestone-c/`. Independent VTK rasterization in Slicer reproduced every original mask voxel from the exported STLs. The geometry tests pass (18 tests).

Open `results/cases/PUBLIC-001-totalseg/milestone-c/slicer-check-final/meshes-on-ct.mrb` in Slicer for the exported meshes over the original CT. STL coordinates are **RAS millimeters**; GLB coordinates are **(R,S,-A) meters**. Do not let an importer silently treat the STL as LPS. See [Milestone C measurements, evidence, and reproduction](docs/TOTALSEG_MILESTONE_C.md).

## Milestone D — unified CLI

With the existing `.venv` application environment and `.venv-totalseg` inference environment installed:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_case.py data/demo/CTA-cardio.nii.gz
```

TotalSegmentator is now the CLI default; `--engine monai` explicitly selects the preserved legacy path. Each run creates a new case and refuses to overwrite existing results. Use `--case-id PUBLIC-001-new` for a readable ID, or `--totalseg-python` to choose another inference environment.

The real CPU run at `results/cases/PUBLIC-001-D-final/` completed in **616.85 seconds**, including standard inference, validation, geometry, and previews. It produced 117 masks (88 nonempty), six cardiac structures as GLB/STL, a combined GLB, three orthogonal overlays, measurements, and `manifest.json` with relative paths and artifact hashes. All six cardiac predictions match the earlier reviewed masks voxel-for-voxel. **33 tests passed.** See [Milestone D evidence, limitations, and commands](docs/TOTALSEG_MILESTONE_D.md). TotalSegmentator backend integration is the next milestone.

## Reproduce Milestone A

Use a separate Python 3.12 environment to preserve the existing MONAI installation:

```powershell
py -3.12 -m venv .venv-totalseg
.\.venv-totalseg\Scripts\python.exe -m pip install -r requirements-totalseg-lock.txt
.\.venv-totalseg\Scripts\python.exe -m pip check
.\.venv-totalseg\Scripts\TotalSegmentator.exe --help
.\.venv-totalseg\Scripts\TotalSegmentator.exe --list-classes total
.\.venv-totalseg\Scripts\python.exe scripts/run_totalseg.py data/demo/CTA-cardio.nii.gz --output-dir results/cases/PUBLIC-001-totalseg --device cpu
.\.venv-totalseg\Scripts\python.exe scripts/inspect_totalseg.py results/cases/PUBLIC-001-totalseg
```

Run from the repository root. The lock file records the tested Windows environment, independently of the MONAI lock file. The public CT already exists locally; for a fresh checkout, obtain it with the preserved asset-download instructions below. [Scan provenance and conversion](docs/DATA.md) document Slicer's CTACardio sample and its immutable source checksum. No source scan or weights are committed.

Choose a **new output directory** on each inference run: the script refuses to overwrite an existing case. This is full `total` inference, with no ROI subset, no `--fast`, no training, and no licensed cardiac task. A four-hour subprocess timeout and captured stdout/stderr provide failure evidence. The CPU flag explicitly selects CPU; on a configured NVIDIA environment `--device gpu` requires available CUDA. The tested environment is CPU-only.

The runner downloads weights automatically to `models/totalsegmentator/nnunet/results/` by default and disables upstream usage telemetry in its local configuration. `TOTALSEG_HOME_DIR` or `TOTALSEG_WEIGHTS_PATH` can override the cache. Both the model cache and generated results are Git-ignored. The optional official pre-download command is:

```powershell
$env:TOTALSEG_HOME_DIR = Join-Path (Get-Location) 'models/totalsegmentator'
.\.venv-totalseg\Scripts\totalseg_download_weights.exe -t total
```

In 2.18.0 that pre-download command also fetches the 6 mm cropping model (298); the full default run itself uses models 291–295 at 1.5 mm. No pre-download is required when running the wrapper.

Outputs under the selected case directory:

| Path | Evidence |
| --- | --- |
| `segmentations/*.nii.gz` | Actual per-class masks, restored to the source CT grid |
| `run.json` | Executed argument list, software versions, device, input hash/geometry, process runtime and status |
| `upstream_report.json` | Official TotalSegmentator run/model report |
| `installed_label_map.json` | Complete `total` class map from the installed package |
| `logs.txt` | Actual model download, inference, and saving output |
| `validation.json` | Every mask's binary/grid checks and foreground count; available cardiac labels; checkpoint hashes |
| `previews/cardiac_overlay.png` | Real CT and mask overlay at three heart-containing axial levels |

`run.json` records inference completion separately from validation: successful inference is `segmented_pending_validation`, and `validation.json` must independently say `passed`. A failed command raises an error and retains a failed run report. The overlay losslessly reorients both CT and masks to RAS and respects physical voxel spacing. Its fixed CT display window does not affect model input. Empty mask files are distinguished from nonempty predictions.

See [Milestone A execution evidence and limitations](docs/TOTALSEG_MILESTONE_A.md) and the subsequently completed [Milestone B Slicer review](docs/TOTALSEG_MILESTONE_B.md). The official [TotalSegmentator project](https://github.com/wasserth/TotalSegmentator) documents the open `total` task and separately licensed `heartchambers_highres` task. These milestones use only `total`.

## Preserved MONAI proof-of-concept

The following sections describe the **existing MONAI implementation**, including its prior CLI, backend, frontend, meshes, and Slicer experiments. They remain available unchanged as the legacy proof-of-concept. They do not describe a completed TotalSegmentator frontend/backend integration.

The backend now defaults to TotalSegmentator. For the **legacy frontend** instructions below, explicitly select MONAI with `$env:HEARTAI_ENGINE = 'monai'` before launching its backend. TotalSegmentator viewer integration is a later milestone; the existing frontend does not yet consume the new case format.

Real pretrained cardiac CT inference, physical 3-D meshes, voxel-based measurements, and a three-slice inspection figure. **No training or fine-tuning.** The CLI, FastAPI backend, and Next.js frontend are implemented. The browser supports upload/demo analysis, actual processing stages, interactive anatomy, measurements, previews, and downloads.

## Open the application

The [complete application build specification](HEARTAI_BUILD_SPEC.md) defines the technician workflow, Slicer module, DICOM intake, higher-resolution/coronary model evaluation, review, packaging, and release gates. It distinguishes existing features from planned work.

**Slicer review workflow tested:** open the real CT and seven editable structures in 3D Slicer, export a draft revision, then rebuild meshes, measurements, and overlays without inference. [Exact launch, edit, save, and rebuild commands](docs/SLICER_SETUP.md). A real no-edit round trip preserved all cardiac voxels; a deliberate one-voxel edit changed volume by exactly one voxel. See [runtime validation and limitations](docs/SLICER_VALIDATION.md) and the [workflow specification](docs/SLICER_WORKFLOW.md). SlicerHeart is installed; this checkpoint uses Slicer's core Segment Editor, not valve analysis or simulation.

After completing the Python setup and asset download below, start the backend in one PowerShell terminal from the repository root:

```powershell
$env:HEARTAI_ENGINE = 'monai'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, use Node.js 22 or newer:

```powershell
cd frontend
npm ci
npm run dev
```

Open [HeartAI](http://127.0.0.1:3000) and choose **Try demo scan**, upload a `.nii`/`.nii.gz` cardiac CT, or reopen a saved case ID. Both servers must stay running. For a production build, replace `npm run dev` with `npm run build` followed by `npm start`. See [frontend setup and verification](docs/FRONTEND.md).

## Local API

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
$env:HEARTAI_ENGINE = 'monai'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open [API documentation](http://127.0.0.1:8000/docs). Upload a NIfTI or call the demo endpoint, poll real processing stages, and download completed artifacts. See [backend setup, endpoints, and tests](docs/BACKEND.md). Run a single server worker against the local case directories.

The selected model is the official MONAI `wholeBody_ct_segmentation` bundle v0.2.7, using its published **3 mm SegResNet checkpoint**. It predicts 104 foreground classes plus background. Cardiac classes include all four chambers, myocardium, aorta, and pulmonary artery. See [model verification](docs/MODEL.md), [all label IDs](docs/labels.json), and [public scan provenance](docs/DATA.md).

## Setup and reproduce (Windows PowerShell)

Run from this repository directory. Python **3.12** is recommended (tested with 3.12.5); 3.13 is not supported by this pinned stack.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe scripts/download_assets.py
.\.venv\Scripts\python.exe scripts/analyze_case.py data/demo/CTA-cardio.nii.gz --engine monai
```

`requirements-lock.txt` records the complete tested Windows environment; `requirements.txt` lists direct inference dependencies. The download command verifies immutable sources against SHA-256 checksums in `assets.json`. It downloads approximately 75 MB of model weights and 64 MB of CT data, plus small upstream documents. It converts the public Slicer NRRD to NIfTI and checks voxel values, spacing, origin, and direction; there is no cropping or resampling during that conversion. Inference accepts NIfTI only. Allow several GB of RAM and approximately 2 GB disk space including the Python environment.

To rerun the legacy MONAI CLI pipeline in the already configured environment:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_case.py data/demo/CTA-cardio.nii.gz --engine monai
```

Every run generates a new case ID under `results/cases/<case_id>/`. A case contains `input/scan.nii.gz`, `segmentation/prediction.nii.gz`, `previews/overlay.png`, seven individual GLBs and STLs when those labels are present, `meshes/heart.glb`, `measurements.json`, `inference_report.json`, and `manifest.json`. Missing classes are reported rather than invented. Existing case IDs are never overwritten. An optional `--case-id` accepts 8–32 lowercase hexadecimal characters; `--cases-dir`, `--device`, and `--threads` are also available.

The callable entry point is `heartai.pipeline.analyze.analyze_case(scan_path, case_id=None)`. It imports the original `segment_scan()` function directly. Manifest artifact paths are relative to the case directory. Failures raise an error and leave a failed manifest; stages represent actual operations, with no invented progress percentages.

**Physical coordinates:** measurements and STL vertices use NIfTI world RAS millimeters. GLB vertices use meters with the shared transform `(R,S,-A)/1000`, so superior is Y-up. No structure is centered independently. Volumes are computed from occupied voxels and the absolute affine determinant; bounding dimensions include complete voxel cells. See [geometry conventions and actual results](docs/CLI_VALIDATION.md). The analysis pipeline requires NIfTI spatial units explicitly set to `mm` before calling the existing model.

To inspect an exported mesh with a standalone Python visualization (replace the ID with the one printed by your run):

```powershell
.\.venv\Scripts\python.exe scripts/preview_mesh.py results/cases/599ffc561784/meshes/myocardium.glb --output results/cases/599ffc561784/previews/myocardium.png
```

The original inference-only command remains available:

```powershell
.\.venv\Scripts\python.exe scripts/run_inference.py data/demo/CTA-cardio.nii.gz
```

Inference-only outputs (overwritten on rerun of the same scan filename):

| File | Contents |
| --- | --- |
| `results/segmentations/CTA-cardio.nii.gz` | Full model labelmap, original CT grid, uint8 labels 0–104 |
| `results/overlays/CTA-cardio.png` | Original CT, cardiac labels, and overlay at three axial levels |
| `results/reports/CTA-cardio.json` | Actual device, timings, input geometry, shapes, hashes, and labels present |

The PNG displays the seven cardiac classes only; the NIfTI retains all predicted classes with the original upstream IDs. CT display uses a fixed soft-tissue window solely for visualization. This window is never used in model preprocessing.

## Device and other inputs

`--device auto` selects CUDA when PyTorch reports it available, otherwise CPU. This Windows machine has AMD graphics; the tested run used **CPU**, four threads, and PyTorch `2.4.1+cpu`. AMD GPU acceleration is not implemented in this milestone. The CUDA branch is implemented but has not been hardware-tested here. On an NVIDIA machine, install the matching CUDA build of PyTorch 2.4.1 using the [official PyTorch instructions](https://pytorch.org/get-started/previous-versions/#v241), then verify availability before using `--device cuda`.

```powershell
.\.venv\Scripts\python.exe scripts/inspect_scan.py data/demo/CTA-cardio.nii.gz
.\.venv\Scripts\python.exe scripts/run_inference.py C:\path\to\scan.nii.gz --device cpu --threads 4 --output-dir results
```

Input must be a finite 3-D CT volume with valid spatial metadata and CT intensities. NIfTI alone cannot prove that the modality is CT or that intensities are HU; the caller must provide an appropriate scan. The Python entry point is `heartai.inference.predictor.segment_scan(path)`.

## Tests

Normal tests use small synthetic volumes and need no model or medical dataset:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"
```

After downloading assets, exercise the official spatial transform round trip and run the real checkpoint again:

```powershell
$env:HEARTAI_RUN_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest -q -m integration
```

Tests cover loading, anisotropic spacing, orientation, NIfTI forms, invalid inputs, label validity, native output shape, and actual pretrained inference. They also cover structure extraction, empty masks, affine transformations (including reflection/shear), volume/centroid/bounds calculations, mesh export round trips, case manifests, failures, and overwrite protection. The integration test writes temporary outputs, leaving the demo result intact. Inference mocks are confined to isolated orchestration tests.

## Observed result and limits

The complete CLI run created case **599ffc561784** in **31.39 seconds** on CPU, including **11.57 seconds** of neural inference and **4.88 seconds** of reconstruction/export validation. All seven structures generated individual GLB/STL exports and a combined named GLB. All exported surfaces were finite, watertight, and consistently wound. The myocardium GLB was reopened and rendered independently. Measurements and full dimensions/centroids are recorded in [the CLI validation report](docs/CLI_VALIDATION.md).

The aorta reaches the scan boundary and its surface is capped at that boundary. The left-ventricle prediction contains three disconnected components, which inflate its bounding dimensions. All components are preserved and included in measurements; no postprocessing hides these limitations. Geometric validation is not clinical validation.

The demo used Slicer's public **CTACardio** CTA: 512 × 512 × 321 voxels, approximately 0.934 × 0.934 × 1.25 mm spacing. Official preprocessing produced a 1 × 160 × 160 × 134 tensor. The CPU model run took **11.62 seconds**, and the full pipeline took **25.61 seconds** on this machine; these are observations, not speed guarantees. All seven requested cardiac labels were present. The output restored the original geometry, and three axial overlays were visually inspected for gross alignment.

The 3 mm model gives coarse boundaries even though output is restored to the finer original grid. This is a general whole-body CT model, not a congenital cardiac or coronary-specific model. There is no ground-truth accuracy assessment or clinical validation here; a visually aligned mask does not establish anatomical accuracy. No Dice score is claimed. See [verification notes](docs/VALIDATION.md).

Downloaded scans, weights, and generated results are intentionally Git-ignored. Source files, asset hashes, and documentation reproduce the result. Following completion of the CLI milestone, the user authorized the remaining application in separate parts. The backend and frontend parts are implemented. Docker packaging remains a separate future checkpoint.
