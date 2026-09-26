# Preserved MONAI proof-of-concept

Historical setup and measured results for the earlier MONAI implementation. Current TotalSegmentator usage is in the [main README](../README.md).


The following sections describe the **existing MONAI implementation**, including its prior CLI, backend, frontend, meshes, and Slicer experiments. They remain available unchanged as the legacy proof-of-concept. They do not describe a completed TotalSegmentator frontend/backend integration.

The backend now defaults to TotalSegmentator. For the **legacy frontend** instructions below, explicitly select MONAI with `$env:HEARTAI_ENGINE = 'monai'` before launching its backend. TotalSegmentator viewer integration is a later milestone; the existing frontend does not yet consume the new case format.

Real pretrained cardiac CT inference, physical 3-D meshes, voxel-based measurements, and a three-slice inspection figure. **No training or fine-tuning.** The CLI, FastAPI backend, and Next.js frontend are implemented. The browser supports upload/demo analysis, actual processing stages, interactive anatomy, measurements, previews, and downloads.

## Open the application

The [complete application build specification](../HEARTAI_BUILD_SPEC.md) defines the technician workflow, Slicer module, DICOM intake, higher-resolution/coronary model evaluation, review, packaging, and release gates. It distinguishes existing features from planned work.

**Slicer review workflow tested:** open the real CT and seven editable structures in 3D Slicer, export a draft revision, then rebuild meshes, measurements, and overlays without inference. [Exact launch, edit, save, and rebuild commands](SLICER_SETUP.md). A real no-edit round trip preserved all cardiac voxels; a deliberate one-voxel edit changed volume by exactly one voxel. See [runtime validation and limitations](SLICER_VALIDATION.md) and the [workflow specification](SLICER_WORKFLOW.md). SlicerHeart is installed; this checkpoint uses Slicer's core Segment Editor, not valve analysis or simulation.

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

Open [HeartAI](http://127.0.0.1:3000) and choose **Try demo scan**, upload a `.nii`/`.nii.gz` cardiac CT, or reopen a saved case ID. Both servers must stay running. For a production build, replace `npm run dev` with `npm run build` followed by `npm start`. See [frontend setup and verification](FRONTEND.md).

## Local API

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
$env:HEARTAI_ENGINE = 'monai'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open [API documentation](http://127.0.0.1:8000/docs). Upload a NIfTI or call the demo endpoint, poll real processing stages, and download completed artifacts. See [backend setup, endpoints, and tests](BACKEND.md). Run a single server worker against the local case directories.

The selected model is the official MONAI `wholeBody_ct_segmentation` bundle v0.2.7, using its published **3 mm SegResNet checkpoint**. It predicts 104 foreground classes plus background. Cardiac classes include all four chambers, myocardium, aorta, and pulmonary artery. See [model verification](MODEL.md), [all label IDs](labels.json), and [public scan provenance](DATA.md).

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

**Physical coordinates:** measurements and STL vertices use NIfTI world RAS millimeters. GLB vertices use meters with the shared transform `(R,S,-A)/1000`, so superior is Y-up. No structure is centered independently. Volumes are computed from occupied voxels and the absolute affine determinant; bounding dimensions include complete voxel cells. See [geometry conventions and actual results](CLI_VALIDATION.md). The analysis pipeline requires NIfTI spatial units explicitly set to `mm` before calling the existing model.

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

The complete CLI run created case **599ffc561784** in **31.39 seconds** on CPU, including **11.57 seconds** of neural inference and **4.88 seconds** of reconstruction/export validation. All seven structures generated individual GLB/STL exports and a combined named GLB. All exported surfaces were finite, watertight, and consistently wound. The myocardium GLB was reopened and rendered independently. Measurements and full dimensions/centroids are recorded in [the CLI validation report](CLI_VALIDATION.md).

The aorta reaches the scan boundary and its surface is capped at that boundary. The left-ventricle prediction contains three disconnected components, which inflate its bounding dimensions. All components are preserved and included in measurements; no postprocessing hides these limitations. Geometric validation is not clinical validation.

The demo used Slicer's public **CTACardio** CTA: 512 × 512 × 321 voxels, approximately 0.934 × 0.934 × 1.25 mm spacing. Official preprocessing produced a 1 × 160 × 160 × 134 tensor. The CPU model run took **11.62 seconds**, and the full pipeline took **25.61 seconds** on this machine; these are observations, not speed guarantees. All seven requested cardiac labels were present. The output restored the original geometry, and three axial overlays were visually inspected for gross alignment.

The 3 mm model gives coarse boundaries even though output is restored to the finer original grid. This is a general whole-body CT model, not a congenital cardiac or coronary-specific model. There is no ground-truth accuracy assessment or clinical validation here; a visually aligned mask does not establish anatomical accuracy. No Dice score is claimed. See [verification notes](VALIDATION.md).

Downloaded scans, weights, and generated results are intentionally Git-ignored. Source files, asset hashes, and documentation reproduce the result. Following completion of the CLI milestone, the user authorized the remaining application in separate parts. The backend and frontend parts are implemented. Docker packaging remains a separate future checkpoint.
