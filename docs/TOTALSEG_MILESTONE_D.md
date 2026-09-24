# Milestone D — unified CLI

The default CLI runs real TotalSegmentator inference, validates the complete installed label map, extracts the available cardiac subset, reconstructs meshes, measures geometry, creates three CT overlays, and writes a case manifest. Model execution stays in the isolated TotalSegmentator environment. Geometry uses the existing application environment. No training or backend/frontend work is included.

## Run

After the Python setup and TotalSegmentator installation documented in README, from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_case.py data/demo/CTA-cardio.nii.gz
```

This generates a new case ID. To supply a readable ID:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_case.py data/demo/CTA-cardio.nii.gz --case-id PUBLIC-001-new --device cpu
```

Existing case directories are refused without modification. `--cases-dir` changes the output parent. `--totalseg-python` or `HEARTAI_TOTALSEG_PYTHON` selects the inference environment's Python executable; otherwise the repository's `.venv-totalseg` is used (Windows and POSIX layouts supported). The caller needs the repository installed as a Python package, as in the existing `.venv` setup. This source-checkout CLI invokes the proven scripts under `scripts/`.

`total`, standard resolution, all output classes, and CPU are the current defaults. `--device gpu` explicitly requires a CUDA-capable installed PyTorch environment. This tested Windows installation uses CPU-only PyTorch; no AMD acceleration is claimed. There is no automatic reduction in model resolution when memory is limited. Model cache and telemetry behavior remain as documented for Milestone A.

Legacy MONAI inference remains available explicitly, with its original case-ID and device rules:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_case.py data/demo/CTA-cardio.nii.gz --engine monai
```

The legacy Python API used by the existing backend remains unchanged. The CLI imports that API only when MONAI is selected.

## Package and status

Each case includes:

| Path | Contents |
| --- | --- |
| `input/scan.nii[.gz]` | Byte-for-byte local source copy with recorded SHA-256 |
| `segmentations/*.nii.gz` | Complete installed `total` output set, including empty masks |
| `meshes/<structure>.glb`, `.stl` | Real cardiac-focus surfaces |
| `meshes/cardiac.glb` | All reconstructed structures with separate names |
| `previews/{axial,coronal,sagittal}_overlay.png` | CT and predicted masks in canonical voxel planes |
| `previews/cardiac_overlay.png` | Earlier three-level axial inspection preview |
| `measurements.json` | Measured voxel volumes, mesh volumes/areas, centroids, bounds, components |
| `manifest.json` | Relative artifact paths, hashes, source metadata, actual labels, unavailable labels, timings, warnings, status |
| `logs.txt`, `inference.log` | Stage execution and actual model output |
| `run.json`, `upstream_report.json`, `installed_label_map.json`, `validation.json` | Original inference and validation evidence |
| `cardiac/cardiac_subset.json` | Validated subset with source-mask hashes and review coordinates |
| `reconstruction/` | Detailed geometry checks and retained intermediate reconstruction artifacts |

Stage starts, finishes, and elapsed seconds are logged. Incomplete timing values remain null until measured. Failures leave `status: failed`, the failing stage, and an error message; the CLI exits nonzero. Failed inference evidence stays in `inference/`. Successful inference files are moved into the case root, so the exact historical command in `run.json` refers to the original staging location. No existing run is overwritten or silently resumed.

The manifest becomes complete only after validation of mask grids/binary values, source hashes, mesh topology/coordinate round trips, and final artifact existence/hash checks. This means computational completion, not expert anatomical acceptance. Automated cases explicitly record Slicer review as `not_run`. The scripts do not manufacture a completed Milestone B review to permit reconstruction.

The initial cardiac proof still requires nonempty heart and aorta masks. Missing optional focus labels are recorded and skipped. No meshes are created for unavailable structures. Source masks retain all components; scan-boundary caps and disconnected components are reported. Preview planes preserve source voxels and physical axis spacing; oblique scans are not resampled into anatomical world planes and are labeled as canonical voxel planes.

## Independent Slicer review

For a newly generated case, use the same exported-mesh check as Milestone C:

```powershell
$env:HEARTAI_MESH_CASE = Join-Path (Get-Location) 'results/cases/PUBLIC-001-new'
$env:HEARTAI_MESH_RECONSTRUCTION_REPORT = 'reconstruction/reconstruction.json'
$env:HEARTAI_MESH_REVIEW_FOLDER = 'slicer-check'
$meshScript = Join-Path (Get-Location) 'scripts/verify_totalseg_meshes_in_slicer.py'
Start-Process -FilePath 'C:\Users\Ahmad Soboh\AppData\Local\slicer.org\3D Slicer 5.12.4\Slicer.exe' -ArgumentList @('--no-splash', '--ignore-slicerrc', '--python-script', ('"' + $meshScript + '"')) -WindowStyle Hidden -Wait
```

Adjust the installed Slicer path on another machine. This runs in a new Slicer process and closes it after saving; a fresh review folder is required. Open the saved `slicer-check/meshes-on-ct.mrb` scene to inspect CT and exported models. STL is RAS millimeters, while GLB is right-handed Y-up meters `(R,S,-A)/1000`; preserve those conventions when importing elsewhere.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_totalseg_pipeline.py tests/test_totalseg_reconstruction.py tests/test_geometry.py tests/test_pipeline.py
```

The pipeline tests isolate synthetic inference inside tests only, exercising real mesh export, measurement, preview creation, manifest serialization, missing optional labels, path containment, failure status, corrupt input, missing environment, and collision protection. Existing geometry and legacy MONAI orchestration tests are retained. Full inference is run manually for this milestone, never in ordinary CI.

## Execution evidence

The first two full-resolution CPU attempts (`PUBLIC-001-D` and `PUBLIC-001-D-retry`) failed during worker startup with memory-allocation / DLL-loading errors and retained failed manifests. An upstream configuration import also loaded PyTorch into the wrapper; the runner now performs that environment/configuration probe in a short-lived process so its extra PyTorch copy is released before inference. Retry evidence is recorded separately; failed runtimes are never presented as successful inference times.

The successful run is `results/cases/PUBLIC-001-D-final/`, executed with:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_case.py data/demo/CTA-cardio.nii.gz --case-id PUBLIC-001-D-final
```

TotalSegmentator **2.18.0**, task **total**, standard resolution, **CPU**. Actual inference-process time was **440.838 seconds**; the upstream prediction-only portion was **387.49 seconds**. Full CLI time was **616.849 seconds**, including 151.047 seconds for full mask validation/subset preparation, 12.611 seconds for reconstruction/measurements, and 8.053 seconds for orthogonal previews. Timings exclude the subsequent Slicer review.

All **117** class files passed validation; **88** were nonempty. Six cardiac structures were reconstructed. Their KJI voxel hashes match Milestone B exactly. The measured volumes match Milestone C: heart 495.029 mL, aorta 133.420 mL, pulmonary vein 20.247 mL, left atrial appendage 4.904 mL, superior vena cava 16.471 mL, inferior vena cava 25.498 mL. These are predicted-mask measurements, not clinical findings.

**33 tests passed in 5.84 seconds**, with 14 existing Matplotlib/Pyparsing deprecation warnings. Test output is saved at `results/milestone-d-tests.txt`; real CLI output is `results/milestone-d-final-cli.txt`. The upstream PyTorch deprecation warning did not prevent successful inference. The three generated orthogonal previews were opened and visually inspected.

The final case was independently checked in **3D Slicer 5.12.4**. All six exported STLs rasterized back onto the CT grid with **zero differing voxel centers**. The combined CT/mesh view and individual pulmonary-vein, left-appendage, superior-cava, and inferior-cava captures were opened and visually inspected, with no gross spatial mismatch. `slicer-check/verification.json` records executed checks; `completion.json` records this technical visual review. The saved scene is `slicer-check/meshes-on-ct.mrb`. The case manifest was subsequently updated with these review artifacts; this is separate from automated CLI completion.

Final hash checks confirmed the original public CT, all 117 Milestone A masks, and the three preserved MONAI outputs are unchanged. All final manifest artifact hashes were verified. The scan-truncated aorta and disconnected components remain documented limitations. No clinical validation is claimed.

**Milestone D complete. Stopped before Milestone E (backend integration).**
