# HeartAI — End-to-End Product Specification for Codex

## 0. Mission

HeartAI is a medical-AI research/portfolio application that turns a cardiac CT scan into an interactive 3D visualization using a real pretrained segmentation engine.

The V1 "wow factor" engine is **TotalSegmentator**.

The product should make this workflow feel simple:

```text
Cardiac CT
    ↓
Upload to HeartAI
    ↓
TotalSegmentator
    ↓
Anatomical segmentation
    ↓
3D reconstruction
    ↓
Interactive medical viewer
    ↓
Measurements + exports
```

The application should look and feel like a serious medical visualization workstation, not a generic 3D website.

The primary visual goal is inspired by workflows built with 3D Slicer / SlicerHeart:
- real CT volume
- segmented anatomical structures
- interactive 3D anatomy
- transparency
- clipping / cutaway views
- structure isolation
- measurements
- exportable models

HeartAI is **not a medical device** and is **not clinically validated**.

Use only public/de-identified scans during development.

---

# 1. Important Project Strategy

Do NOT try to invent a segmentation model in V1.

V1 is product engineering around a strong pretrained segmentation engine.

Use:

```text
TotalSegmentator
```

for the primary segmentation path.

The engineering contribution in V1 is:

```text
input ingestion
→ segmentation orchestration
→ model execution
→ output validation
→ anatomical structure selection
→ 3D reconstruction
→ measurements
→ medical volume rendering
→ backend
→ frontend
→ interactive controls
→ exports
→ reproducible deployment
```

Later phases will add:

```text
V2:
MONAI-based fine-tuning / ML experiments

V3:
NVIDIA Warp / Newton physics simulation
```

Do NOT implement V2 or V3 until V1 is complete.

---

# 2. Why TotalSegmentator

TotalSegmentator is a pretrained medical segmentation system for CT/MR anatomy.

Official repository:

https://github.com/wasserth/TotalSegmentator

For CT, the default command is:

```bash
TotalSegmentator -i ct.nii.gz -o segmentations
```

The default CT `total` task is the initial V1 engine.

The default task is openly available and provides segmentation for a large number of anatomical structures.

The V1 application must use the actual output classes documented by the installed TotalSegmentator version.

Do NOT hard-code assumptions without reading the installed model's label map.

---

# 3. Licensing Boundary

The default `total` task is the safe default for V1.

There is also a higher-detail cardiac task:

```text
heartchambers_highres
```

which may provide:

```text
myocardium
atrium_left
ventricle_left
atrium_right
ventricle_right
aorta
pulmonary_artery
```

However this task is licensed separately.

Free non-commercial licenses may be available, while commercial use requires the appropriate commercial license.

Therefore:

1. Build V1 so that the default `total` task works with no special license.
2. Make segmentation engines/tasks configurable.
3. If a valid `heartchambers_highres` license is installed locally, support it as an OPTIONAL enhanced cardiac mode.
4. Never silently depend on a restricted task.
5. Never commit a license key to Git.
6. Never expose license credentials to the frontend.

Environment variable example:

```text
TOTALSEG_LICENSE=...
```

If no license is present, HeartAI must still work in default mode.

---

# 4. Final V1 Experience

The finished user experience should be:

```text
Open HeartAI
    ↓
Choose a CT scan
    ↓
Click Analyze
    ↓
Upload
    ↓
Segment anatomy
    ↓
Generate 3D structures
    ↓
Calculate measurements
    ↓
Open results
```

The results screen should provide:

```text
3D medical viewer
CT volume rendering
segmentation overlays
structure visibility controls
opacity controls
clipping / cutaway controls
measurements
model information
segmentation preview
download/export buttons
```

The 3D result must come from the actual scan.

Do NOT use a stock heart model.

---

# 5. Architecture

Use this architecture:

```text
                        HEARTAI

                  Next.js / React
                        │
                        │ HTTP
                        ▼
                     FastAPI
                        │
         ┌──────────────┼───────────────┐
         │              │               │
         ▼              ▼               ▼
  TotalSegmentator   Measurements   Artifact Service
         │                              │
         ▼                              │
   Segmentation                         │
         │                              │
         ├─────────────┐                │
         ▼             ▼                │
      Meshes       Volume data          │
         │             │                │
         └──────┬──────┘                │
                ▼                       │
           Frontend viewer ◄────────────┘
                │
                ▼
              VTK.js
```

---

# 6. Viewer Technology

The primary medical visualization engine should be:

```text
VTK.js
```

Keep React / Next.js for the surrounding application.

Do NOT use React Three Fiber / Three.js as the primary medical volume renderer.

Three.js may remain as a secondary dependency only if useful for export previews or UI-specific geometry.

VTK.js is preferred because the viewer must support:

```text
medical image volumes
GPU volume ray casting
color transfer functions
opacity transfer functions
segmentation surfaces
clipping
scientific spatial coordinates
camera interaction
surface + volume rendering together
```

---

# 7. Product Modes

V1 should support three visualization modes.

## Mode A — Full Anatomy

Use TotalSegmentator `total`.

Example structures may include:

```text
heart
aorta
lungs
ribs
vertebrae
major vessels
other available anatomy
```

Expose only the structures that actually exist in the installed task output.

This mode provides the initial "wow factor":

```text
grey CT
→ AI segmentation
→ many colored structures
→ isolate the heart
```

## Mode B — Cardiac Focus

Use the same TotalSegmentator output but show only relevant cardiac/thoracic structures by default.

Examples, subject to actual labels:

```text
heart
aorta
pulmonary artery if available
vena cava if available
lungs optional
```

If `heartchambers_highres` is legally configured, this mode can optionally switch to the high-resolution cardiac task.

## Mode C — CT Volume

Display the original CT with GPU volume rendering.

Allow segmentation surfaces to be overlaid on the CT.

---

# 8. Current Existing Work

There may already be a working MONAI inference pipeline in the repository.

Do not delete it.

Preserve it under an experimental or legacy engine abstraction.

The new architecture should allow:

```python
SegmentationEngine
    ├── TotalSegmentatorEngine
    └── MonaiEngine
```

But V1's default must be TotalSegmentator.

Do not overengineer this abstraction.

A small Python protocol/base class is enough.

Example:

```python
class SegmentationEngine(Protocol):
    def segment(self, input_path: Path, output_dir: Path) -> SegmentationResult:
        ...
```

The application must function with TotalSegmentator even if the MONAI path is unused.

---

# 9. Repository Structure

Preserve useful existing files.

Target:

```text
HeartAI/
│
├── CODEX.md
├── README.md
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── .env.example
│
├── data/
│   ├── demo/
│   └── uploads/
│
├── results/
│   └── cases/
│
├── src/
│   └── heartai/
│       ├── __init__.py
│       │
│       ├── imaging/
│       │   ├── nifti.py
│       │   ├── dicom.py
│       │   └── metadata.py
│       │
│       ├── segmentation/
│       │   ├── base.py
│       │   ├── totalsegmentator.py
│       │   ├── monai.py
│       │   └── labels.py
│       │
│       ├── reconstruction/
│       │   ├── mesh.py
│       │   ├── transforms.py
│       │   └── export.py
│       │
│       ├── measurements/
│       │   ├── volume.py
│       │   ├── geometry.py
│       │   └── summary.py
│       │
│       ├── previews/
│       │   └── overlays.py
│       │
│       └── pipeline/
│           └── analyze.py
│
├── scripts/
│   ├── run_totalseg.py
│   ├── inspect_case.py
│   ├── analyze_case.py
│   └── validate_outputs.py
│
├── backend/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── schemas.py
│       ├── state.py
│       ├── routes/
│       │   ├── health.py
│       │   ├── cases.py
│       │   └── artifacts.py
│       └── services/
│           ├── jobs.py
│           └── analysis.py
│
├── frontend/
│   ├── app/
│   ├── components/
│   │   ├── UploadPanel.tsx
│   │   ├── ProcessingStatus.tsx
│   │   ├── MedicalViewer.tsx
│   │   ├── StructurePanel.tsx
│   │   ├── MeasurementPanel.tsx
│   │   ├── ViewerToolbar.tsx
│   │   ├── ModelInfo.tsx
│   │   └── DownloadPanel.tsx
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   └── vtk/
│   │       ├── volume.ts
│   │       ├── surfaces.ts
│   │       ├── transferFunctions.ts
│   │       └── clipping.ts
│   │
│   └── types/
│       └── heartai.ts
│
├── tests/
│   ├── test_nifti.py
│   ├── test_measurements.py
│   ├── test_mesh.py
│   ├── test_labels.py
│   └── test_pipeline.py
│
├── Dockerfile
├── docker-compose.yml
└── .github/
    └── workflows/
        └── ci.yml
```

Do not recreate already-working files only to match this tree.

---

# 10. Environment

Python:

```text
Python >= 3.10
```

Core Python dependencies:

```text
TotalSegmentator
torch
nibabel
SimpleITK
numpy
scipy
scikit-image
trimesh
fastapi
uvicorn
pydantic
python-multipart
pillow
```

Frontend:

```text
Next.js
React
TypeScript
vtk.js
```

Optional UI:

```text
Tailwind CSS
shadcn/ui
lucide-react
```

Use only what improves the product.

---

# 11. TotalSegmentator Installation

Use the official Python package:

```bash
pip install TotalSegmentator
```

Verify:

```bash
TotalSegmentator --help
```

V1 default inference:

```bash
TotalSegmentator \
  -i scan.nii.gz \
  -o output_dir
```

CPU fallback:

```bash
TotalSegmentator \
  -i scan.nii.gz \
  -o output_dir \
  --fast
```

Do not assume `--fast` is equivalent in quality to the standard model.

Record which inference mode was used.

If only selected structures are required, investigate the official `--roi_subset` option rather than processing unnecessary classes.

---

# 12. Model Weight Management

TotalSegmentator normally downloads required model weights automatically when first used.

Do not commit those weights to Git.

Document their location if detectable.

Provide an optional setup step to download weights before a demo if supported by the installed package:

```bash
totalseg_download_weights -t total
```

For licensed tasks, only download weights if a valid license is configured.

The application should expose useful errors if model weights cannot be downloaded or found.

---

# 13. Supported Inputs

Initial V1 input:

```text
NIfTI:
.nii
.nii.gz
```

TotalSegmentator can support DICOM workflows, but do not make DICOM the first blocker.

After NIfTI is working end-to-end, add DICOM series ingestion.

DICOM requirements:

```text
directory or zip
one series / one patient scan
convert/prepare safely
remove unnecessary identifying metadata from test artifacts
```

Do not build PACS integration in V1.

---

# 14. Demo Dataset

Use only a public/de-identified CT with permission for research/demo use.

Keep the demo input separate from any private clinical files.

Do not commit a large dataset to Git unless redistribution is explicitly permitted.

README should document how to obtain the demo scan.

A demo case ID should be generic:

```text
PUBLIC-001
```

Never imply that a public demo scan came from a specific hospital unless the source documentation says so.

---

# 15. Segmentation Engine Implementation

Create:

```text
src/heartai/segmentation/totalsegmentator.py
```

Expose:

```python
def segment(
    input_path: Path,
    output_dir: Path,
    task: str = "total",
    device: str | None = None,
    fast: bool = False,
    roi_subset: list[str] | None = None,
) -> SegmentationResult:
    ...
```

Prefer the official Python API if it is stable and appropriate.

If the CLI is more robust for the installed version, wrapping the CLI is acceptable.

If using subprocess:

- pass arguments as a list
- never build a shell string from user input
- capture stdout/stderr
- enforce timeout
- surface useful errors
- never use `shell=True`

Return:

```python
@dataclass
class SegmentationResult:
    task: str
    output_dir: Path
    structures: list[str]
    runtime_seconds: float
    device: str
    fast_mode: bool
```

---

# 16. Structure Discovery

Do not assume every structure exists.

After TotalSegmentator completes:

1. inspect generated files / multilabel output
2. derive the actual list of structures
3. map filenames/label IDs to canonical names
4. expose the structures to the backend/frontend

Create a central structure metadata file.

Example:

```python
STRUCTURES = {
    "heart": {
        "display_name": "Heart",
        "group": "cardiac",
    },
    "aorta": {
        "display_name": "Aorta",
        "group": "cardiac",
    },
}
```

Do not put medical claims into this metadata.

---

# 17. Cardiac Structure Preset

Implement a UI preset:

```text
Cardiac Focus
```

It should automatically hide unrelated anatomy and show a curated set of structures that actually exist.

Do not fail if a requested preset structure is absent.

Example behavior:

```text
requested:
heart
aorta
pulmonary artery

actual output:
heart
aorta

→ show the two available structures
→ clearly report that pulmonary artery is unavailable in this task
```

---

# 18. High-Resolution Cardiac Mode

OPTIONAL.

If a valid TotalSegmentator license is available:

```text
task = heartchambers_highres
```

Support a mode titled:

```text
Detailed Cardiac Chambers
```

Potential structures:

```text
myocardium
left atrium
left ventricle
right atrium
right ventricle
aorta
pulmonary artery
```

Do not enable this mode unless the task successfully runs.

If unavailable:

```text
Detailed cardiac mode unavailable.
Default cardiac visualization remains available.
```

Do not block the app.

---

# 19. Output Format

Every case should have:

```text
results/cases/<case_id>/
│
├── input/
│   └── scan.nii.gz
│
├── segmentations/
│   ├── heart.nii.gz
│   ├── aorta.nii.gz
│   └── ...
│
├── meshes/
│   ├── heart.glb
│   ├── aorta.glb
│   └── ...
│
├── previews/
│   ├── axial_overlay.png
│   ├── coronal_overlay.png
│   └── sagittal_overlay.png
│
├── measurements.json
├── manifest.json
└── logs.txt
```

Not every task will have every structure.

The manifest is the source of truth.

---

# 20. Case Manifest

Example:

```json
{
  "case_id": "PUBLIC-001",
  "status": "complete",
  "input": {
    "shape": [512, 512, 321],
    "spacing_mm": [0.93, 0.93, 1.25],
    "orientation": "..."
  },
  "segmentation": {
    "engine": "TotalSegmentator",
    "task": "total",
    "fast_mode": false,
    "structures": ["heart", "aorta"]
  },
  "timing": {
    "segmentation_seconds": 0.0,
    "mesh_seconds": 0.0,
    "total_seconds": 0.0
  },
  "artifacts": {}
}
```

Never fill numbers with fake placeholders in real results.

Use null until measured.

---

# 21. 3D Reconstruction

For each desired binary mask:

```text
mask
↓
marching cubes
↓
surface mesh
↓
world-coordinate transform
↓
clean mesh
↓
compute normals
↓
optional smoothing
↓
GLB export
```

Use:

```text
scikit-image.measure.marching_cubes
trimesh
```

or VTK where it is clearly better.

The mesh must preserve real physical scale.

---

# 22. Critical Spatial Coordinate Rule

NIfTI volumes contain spatial information.

Never render raw voxel indices as physical coordinates without transformation.

Respect:

```text
affine
spacing
orientation
origin
direction
```

The generated mesh must align with the original CT.

Validation:

```text
load scan + segmentation in 3D Slicer
load generated mesh
verify alignment
```

If alignment is wrong, fix the coordinate pipeline before frontend work continues.

---

# 23. Surface Quality

Raw marching cubes may look ugly.

Implement optional medical-safe visual cleanup:

```text
remove tiny disconnected components
mesh cleaning
normal recalculation
light smoothing
```

Do not smooth so aggressively that anatomy is significantly altered.

Keep:

```text
raw mesh
display mesh
```

separate if useful.

Document smoothing parameters.

---

# 24. Measurements

Calculate objective geometric measurements.

Initial:

```text
volume
surface area
bounding dimensions
centroid
```

Volume:

```text
voxel_volume_mm3 =
spacing_x * spacing_y * spacing_z

structure_volume_ml =
count(mask) * voxel_volume_mm3 / 1000
```

Never display measurements without units.

Do not label model-derived geometry as a clinical diagnosis.

---

# 25. Measurement Validation

Unit-test all numerical measurement functions.

Synthetic example:

```text
10 × 10 × 10 voxels
1 mm isotropic spacing

volume = 1000 mm³ = 1 mL
```

Check mesh-derived volume against voxel-derived volume within a documented tolerance when appropriate.

---

# 26. CT Volume Rendering

The viewer must render the actual CT volume, not only meshes.

Use VTK.js GPU volume rendering.

Requirements:

```text
original CT scalar values
correct dimensions
correct spacing
correct orientation/world mapping
volume mapper
color transfer function
opacity transfer function
```

The user must be able to view:

```text
CT only
segmentation only
CT + segmentation
```

---

# 27. Transfer Functions

Create reusable medical visualization presets.

Initial presets:

```text
Soft Tissue
Contrast CT / Cardiac
Bone
Custom
```

Do not claim a preset is clinically optimized unless it comes from a documented source.

Allow user adjustments:

```text
window / level or transfer function range
opacity
```

The goal is visually useful exploration.

---

# 28. Cutaway / Clipping

A major visual goal is exposing internal anatomy.

Implement:

```text
axial clipping plane
sagittal clipping plane
coronal clipping plane
```

Controls:

```text
enable/disable
position slider
invert
reset
```

Apply clipping to:

```text
CT volume
segmentation surfaces
```

when technically feasible.

This feature is high priority because opaque outer surfaces hide important internal anatomy.

---

# 29. Medical Viewer Requirements

Create:

```text
MedicalViewer.tsx
```

It must support:

```text
rotate
pan
zoom
reset camera
fit to anatomy
structure selection
structure visibility
structure opacity
CT opacity
render preset
clipping
full screen
```

Optional later:

```text
crosshair
slice planes
measurement ruler
orientation cube
```

Do not block V1 on these optional features.

---

# 30. Rendering Style

The viewer should look like a serious research tool.

Use:

```text
dark neutral viewport
clear anatomical colors
good lighting for surfaces
no bloom
no particles
no neon effects
no fake heart animation
```

The UI should feel closer to:

```text
3D Slicer
medical workstation
engineering visualization
```

than a gaming website.

---

# 31. Structure Colors

Centralize colors.

Example only:

```typescript
const structureStyles = {
  heart: { color: "#...", opacity: 0.75 },
  aorta: { color: "#...", opacity: 0.9 },
}
```

Do not scatter values throughout the frontend.

Colors are visualization aids.

---

# 32. Processing Pipeline

Create:

```python
def analyze_case(
    input_path: Path,
    case_id: str,
    mode: str = "cardiac",
) -> AnalysisResult:
```

Pipeline:

```text
validate input
↓
create case directory
↓
read metadata
↓
run TotalSegmentator
↓
discover structures
↓
select desired visualization structures
↓
calculate measurements
↓
generate meshes
↓
generate overlays
↓
write manifest
↓
return result
```

Each stage should log start/end and runtime.

---

# 33. CLI First

Before FastAPI/frontend integration, this must work:

```bash
python scripts/analyze_case.py data/demo/CTA-cardio.nii.gz
```

It should produce real outputs.

Example console:

```text
HeartAI
Case: PUBLIC-001

✓ Loaded CT
✓ TotalSegmentator completed
✓ Found 117 structures
✓ Selected cardiac structures
✓ Generated 3D meshes
✓ Calculated measurements
✓ Created preview overlays

Results:
results/cases/PUBLIC-001/
```

The numbers shown must be actual.

---

# 34. CLI Validation

Before backend work:

1. run the pipeline on the demo scan
2. open masks in 3D Slicer
3. inspect anatomical alignment
4. open generated GLB/STL
5. verify scale
6. inspect measurements
7. document limitations

Do not proceed if the 3D outputs are obviously wrong.

---

# 35. FastAPI Backend

Create a local backend.

Required routes:

```text
GET /health

GET /api/config

POST /api/cases

GET /api/cases/{case_id}

GET /api/cases/{case_id}/status

GET /api/cases/{case_id}/manifest

GET /api/cases/{case_id}/measurements

GET /api/cases/{case_id}/volume

GET /api/cases/{case_id}/segmentation/{structure}

GET /api/cases/{case_id}/mesh/{structure}

GET /api/cases/{case_id}/preview/{view}
```

Use typed Pydantic responses.

---

# 36. Job Execution

Segmentation may be slow.

Request lifecycle:

```text
POST scan
↓
save upload
↓
create case ID
↓
start background analysis
↓
return immediately
```

Frontend polls status.

Statuses:

```text
uploaded
validating
segmenting
reconstructing
measuring
preparing_viewer
complete
failed
```

Use these exact logical stages or a similarly clear set.

Do not display fake numeric percentages.

---

# 37. Background Jobs

For V1 use a simple in-process worker/background task if reliable.

Do NOT introduce:

```text
Redis
Celery
Kafka
Kubernetes
```

unless needed.

Cloud scaling comes later.

Keep job execution modular enough to replace later.

---

# 38. Upload Validation

Accept:

```text
.nii
.nii.gz
```

Later:

```text
DICOM folder / zip
```

Validate:

```text
extension
actual readability
3D volume dimensions
reasonable file size
non-empty data
```

Sanitize filenames.

Generate server-side case IDs.

Do not trust uploaded filenames for filesystem paths.

---

# 39. Frontend

Use:

```text
Next.js
React
TypeScript
VTK.js
```

Main route:

```text
/
```

Application state:

```text
idle
uploading
processing
complete
error
```

Avoid unnecessary pages in V1.

---

# 40. Landing / Upload Screen

Design:

```text
HEARTAI
AI-Powered 3D Heart Reconstruction

Upload a cardiac CT scan
[NIfTI .nii / .nii.gz]

[ Drop Scan Here ]

Analysis Mode:
● Cardiac Focus
○ Full Anatomy
○ Detailed Cardiac Chambers (if licensed)

[ Analyze Scan ]

Research prototype — not for clinical use
```

Keep it polished and simple.

---

# 41. Processing View

Show real stages:

```text
Analyzing PUBLIC-001

✓ Scan validated
✓ Segmentation model loaded
● Segmenting anatomy
○ Building 3D models
○ Calculating measurements
○ Preparing viewer
```

When status changes, update UI.

Do not fake progress bars.

---

# 42. Results Layout

Target:

```text
┌──────────────────────────────────────────────────────────────┐
│ HeartAI                          PUBLIC-001    Export   Info  │
├────────────────────────────────────┬─────────────────────────┤
│                                    │ Anatomy                 │
│                                    │                         │
│                                    │ [Cardiac Focus ▼]       │
│                                    │                         │
│          MEDICAL VIEWER            │ ☑ CT Volume             │
│                                    │ ☑ Heart                 │
│       CT + 3D Segmentation         │ ☑ Aorta                 │
│                                    │ ...                     │
│                                    │                         │
│                                    │ Opacity                 │
│                                    │                         │
│                                    │ Measurements            │
│                                    │                         │
├────────────────────────────────────┴─────────────────────────┤
│ 3D View | CT/Segmentation | Model Info | Downloads          │
└──────────────────────────────────────────────────────────────┘
```

The viewer gets the majority of screen space.

---

# 43. Viewer Modes

Implement:

```text
CT Volume
Segmentation
Combined
Cutaway
```

Switching modes must not rerun segmentation.

It only changes rendering state.

---

# 44. Structure Panel

For every available displayed structure:

```text
checkbox visibility
color indicator
opacity control
focus button
measurement summary
```

Groups:

```text
Cardiac
Respiratory
Skeletal
Other
```

Do not dump 117 unchecked labels into a confusing flat list.

Use groups and search.

Default cardiac mode should show a small curated set.

---

# 45. Measurements Panel

Selected structure:

```text
Aorta

Volume
XX.X mL

Surface Area
XX.X cm²

Bounding Dimensions
XX × XX × XX mm
```

Only display measurements actually computed.

No normal/abnormal labels.

No treatment guidance.

---

# 46. Model Information

Expose:

```text
Segmentation Engine
TotalSegmentator

Task
total

Execution
CPU / CUDA

Fast Mode
Yes / No

Runtime
XX.X sec
```

If enhanced cardiac mode:

```text
Task
heartchambers_highres
```

Do not hide which third-party model produced the segmentation.

---

# 47. Segmentation Preview

Generate three representative overlays:

```text
axial
coronal
sagittal
```

Allow a tab:

```text
3D | 2D Preview
```

V1 does not require a complete diagnostic slice viewer.

---

# 48. Export

Allow:

```text
Download segmentation masks
Download selected GLB
Download selected STL if generated
Download measurements JSON
Download case manifest
```

Optional:

```text
Export package ZIP
```

The export package should not include source scans unless explicitly selected.

---

# 49. 3D Slicer Compatibility

HeartAI outputs should be easy to inspect in 3D Slicer.

Document:

```text
How to load original CT
How to load segmentation NIfTI
How to import STL/OBJ
```

Optional later:

```text
.seg.nrrd
```

Do not make `.seg.nrrd` a V1 blocker.

---

# 50. Slicer Validation Workflow

Use Slicer as ground truth for visualization debugging.

For each demo case:

```text
load original CT
load TotalSegmentator masks
enable 3D rendering
compare orientation
compare HeartAI viewer
```

If HeartAI looks wrong but Slicer looks correct:

```text
viewer/spatial conversion bug
```

If both look poor:

```text
segmentation/input issue
```

Document this debugging rule in README.

---

# 51. Performance

Track real timings:

```text
upload time
segmentation time
mesh generation time
measurement time
total analysis time
```

Do not optimize prematurely.

Start with correctness.

Potential later optimizations:

```text
roi_subset
GPU execution
cached results
lower-res preview
parallel mesh generation
```

---

# 52. CPU vs GPU

TotalSegmentator should work on CPU or supported GPU configurations.

The app must detect the runtime.

For CPU demos, support a faster/lower-resolution path if requested.

Do not claim GPU acceleration unless execution actually used it.

The user's local AMD GPU may not be usable through CUDA.

Cloud NVIDIA GPU support can be added later.

---

# 53. Cloud GPU Readiness

Do not make cloud infrastructure necessary for local V1.

But ensure analysis can later run on an NVIDIA machine.

Avoid Windows-only code.

Use environment-based configuration for:

```text
model cache
data directory
device
task
license
```

---

# 54. Error Handling

Handle:

```text
invalid NIfTI
corrupted volume
unsupported dimension
segmentation failure
model download failure
license error
out-of-memory
mesh generation failure
missing structure
frontend artifact load failure
```

Never return fake fallback geometry.

If analysis fails:

```json
{
  "status": "failed",
  "error": "..."
}
```

---

# 55. Medical Safety / Privacy

Use:

```text
public
synthetic
de-identified
```

data only for development.

Do not claim:

```text
HIPAA compliance
PIPEDA compliance
FDA approval
Health Canada approval
clinical validation
diagnostic accuracy
```

unless these are actually established later.

UI footer:

```text
Research prototype. Not for clinical use.
```

---

# 56. No Fake Results Rule

Codex must never invent:

```text
model accuracy
Dice score
patient outcomes
measurements
runtime
number of detected structures
medical diagnosis
```

If unavailable:

```text
Not measured
```

or omit the value.

---

# 57. Testing

Python unit tests:

```text
input metadata loading
voxel spacing
volume conversion
centroid
bounding box
mesh coordinate transform
structure discovery
manifest serialization
```

Backend:

```text
health
upload rejection
case creation
case status
manifest retrieval
artifact retrieval
missing case
```

Frontend:

```text
TypeScript compile
lint
production build
```

No full segmentation run in normal CI.

---

# 58. Synthetic Test Data

Use small synthetic arrays for tests.

Example volume test:

```text
10 × 10 × 10 mask
1 mm spacing
= 1 mL
```

Mock TotalSegmentator only inside isolated unit/API tests.

The real demo application must use real TotalSegmentator output.

---

# 59. Docker

Only containerize after local end-to-end functionality works.

Eventually provide:

```text
backend container
frontend container
docker-compose.yml
```

Do not block the initial app on Docker.

A GPU-specific backend image can be added later.

---

# 60. CI

GitHub Actions:

```text
Python lint/test
backend tests
frontend lint
TypeScript typecheck
frontend production build
```

Do not download huge model weights or run segmentation in CI.

---

# 61. README

README should contain:

```text
What HeartAI does
Demo GIF/video
Architecture
Tech stack
TotalSegmentator attribution
Installation
Run instructions
Demo scan instructions
Viewer controls
Output files
Licensing notes
Limitations
Research disclaimer
Roadmap
```

Be explicit:

```text
Segmentation is powered by TotalSegmentator in V1.
HeartAI did not invent or train the V1 segmentation model.
```

This honesty improves the project.

---

# 62. Demo Script

Final 60–90 second demo:

```text
1. Show grey CT slices.
2. Click Analyze.
3. Show real segmentation stages.
4. Open result.
5. Show many anatomical structures briefly.
6. Switch to Cardiac Focus.
7. Hide lungs/ribs.
8. Show heart/aorta.
9. Turn on original CT volume.
10. Use cutaway plane.
11. Rotate inside/around anatomy.
12. Select a structure.
13. Show real measurement.
14. Export the 3D model.
```

No fake waiting animation.

For a live demo, pre-cache TotalSegmentator weights.

---

# 63. V1 Definition of Done

V1 is done only when a user can:

```text
upload a real supported public CT
↓
run TotalSegmentator
↓
receive real segmentation outputs
↓
view them correctly aligned in 3D
↓
render the source CT volume
↓
combine CT + segmentation
↓
hide/show structures
↓
adjust opacity
↓
use a cutaway/clipping plane
↓
view real measurements
↓
download generated outputs
```

And the same case has been independently sanity-checked in 3D Slicer.

---

# 64. V1.1 — Enhanced Cardiac Mode

Do only after base V1 works.

If licensing is available:

```text
TotalSegmentator heartchambers_highres
```

Add:

```text
left atrium
right atrium
left ventricle
right ventricle
myocardium
aorta
pulmonary artery
```

The UI can then offer:

```text
Cardiac Chambers
```

with each structure independently selectable.

Do not block V1 on this.

---

# 65. V2 — ML Work

DO NOT IMPLEMENT UNTIL V1 IS COMPLETE.

V2 will use MONAI/PyTorch to perform real ML experimentation.

Plan:

```text
choose congenital cardiac dataset
↓
run baseline model
↓
calculate Dice / HD95
↓
fine-tune pretrained model
↓
evaluate
↓
compare against baseline
↓
integrate improved model into same HeartAI pipeline
```

The entire product layer should remain reusable.

Potential V2 ML work:

```text
fine-tuning
augmentation experiments
loss-function experiments
uncertainty estimation
segmentation QC
cardiac geometry features
CHD classification
```

---

# 66. V3 — Physics

DO NOT IMPLEMENT UNTIL V1/V2 ARE STABLE.

Future:

```text
3D cardiac anatomy
+
virtual device
↓
NVIDIA Warp / Newton
↓
simplified physical simulation
```

Possible research demo:

```text
virtual septal closure device
contact
deformation
deployment
```

Do not claim physiologic accuracy without appropriate biomechanical validation.

Newton is not a magic heart simulator.

Material models, boundary conditions, geometry, contact, and validation would still be required.

---

# 67. Codex Behavior Rules

Codex must:

1. Read this file before major changes.
2. Inspect existing code before creating replacements.
3. Preserve working code.
4. Work one milestone at a time.
5. Actually run tests/commands when the environment permits.
6. Never claim success from code inspection alone when execution is possible.
7. Never fabricate medical data.
8. Never fabricate model outputs.
9. Never silently insert stock/demo 3D heart geometry.
10. Never silently replace TotalSegmentator output with mocks in the real application.
11. Keep numerical/spatial code well tested.
12. Explain non-obvious medical image transformations in comments.
13. Keep backend, segmentation, and viewer logic separated.
14. Prefer simple working architecture over unnecessary abstractions.
15. Stop and report real blockers instead of hacking around them with fake outputs.

---

# 68. Implementation Milestones

## Milestone A — TotalSegmentator Proof

Definition of done:

```text
TotalSegmentator installed
weights downloaded
demo CT runs
real segmentation files exist
outputs inspected
```

Command must be reproducible.

STOP and report.

---

## Milestone B — Cardiac Extraction

Definition of done:

```text
actual output structure list read
cardiac subset identified
cardiac masks validated
3D Slicer sanity check completed
```

STOP and report.

---

## Milestone C — 3D Reconstruction + Measurements

Definition of done:

```text
real meshes generated
world scale preserved
meshes align with CT
volume measurements calculated
unit tests pass
```

STOP and report.

---

## Milestone D — Unified CLI Pipeline

Definition of done:

```bash
python scripts/analyze_case.py <scan>
```

creates:

```text
segmentation
meshes
previews
measurements
manifest
```

STOP and report.

---

## Milestone E — Backend

Definition of done:

```text
upload
background processing
status
results
artifact endpoints
error handling
```

Test with real demo scan.

STOP and report.

---

## Milestone F — CT Volume Viewer

Definition of done:

```text
actual CT loads into VTK.js
correct orientation
correct scale
GPU volume rendering
rotate/pan/zoom
render preset
```

Compare against Slicer.

STOP and report.

---

## Milestone G — Segmentation Viewer

Definition of done:

```text
real TotalSegmentator anatomy overlays CT
structure visibility works
opacity works
selection works
```

STOP and report.

---

## Milestone H — Cutaway / Polish

Definition of done:

```text
clipping plane
Cardiac Focus preset
measurement panel
model info
downloads
professional UI
```

STOP and report.

---

## Milestone I — V1 Release

Definition of done:

```text
tests
README
demo recording
clean setup instructions
license documentation
research disclaimer
```

---

# 69. Immediate Task

START WITH MILESTONE A ONLY.

Do not build the frontend yet.

Do the following:

1. Inspect the current HeartAI repository.
2. Preserve the existing working MONAI proof-of-concept.
3. Install/verify the official TotalSegmentator package.
4. Record the installed TotalSegmentator version.
5. Verify the official `total` task.
6. Determine where model weights are stored/downloaded.
7. Use the existing public demo CT if compatible.
8. Run the default `total` task.
9. Record:
   - command
   - device
   - runtime
   - number of output structures
   - output directory
10. Inspect output labels/files.
11. Identify which cardiac structures are actually available.
12. Open/validate at least the cardiac masks programmatically.
13. Generate a small overlay preview.
14. Update README with exact reproduction steps.
15. Do not remove or alter the existing MONAI result.
16. Stop.

At the end report:

```text
TotalSegmentator version
input scan
task
device
runtime
structures produced
cardiac structures available
output paths
errors/warnings
next milestone readiness
```

Do not start mesh generation or frontend work until Milestone A is confirmed.

---

# 70. Suggested First Codex Prompt

Read `CODEX.md` completely before making changes.

We are building HeartAI V1 around **TotalSegmentator** for the segmentation/wow-factor path. Preserve the existing working MONAI proof-of-concept, but do not train or fine-tune anything.

Start with **Milestone A only**.

Inspect the repository, install and verify the official TotalSegmentator package, run the official default `total` CT task on our existing public demo CT, and save the real segmentation outputs. Verify the actual model/task version, actual output labels, device, runtime, and available cardiac structures. Generate one real CT + segmentation overlay preview.

Do not create any stock heart model, mock segmentation, fake measurements, fake runtime, or placeholder outputs.

Do not build the frontend, backend, meshes, or VTK viewer yet.

Actually execute the segmentation and validate its output. Stop when Milestone A is complete and give me a concise report of exactly what was produced, where it was saved, which cardiac structures are available, and any limitations or warnings.
