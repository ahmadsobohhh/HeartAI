# HeartAI — V1 Product Build Specification

## Current Status

Milestone 1 is COMPLETE.

The repository already contains a working pretrained MONAI inference pipeline.

The existing system can:

```text
Cardiac CT (.nii/.nii.gz)
        ↓
MONAI preprocessing
        ↓
Pretrained MONAI segmentation model
        ↓
Predicted 3D segmentation
        ↓
Saved NIfTI segmentation
```

A real cardiac CT has already successfully passed through the pretrained model.

DO NOT restart or replace this inference work unless required to expose it cleanly to the application.

DO NOT train or fine-tune any model.

The goal now is to turn the existing AI inference system into a complete interactive HeartAI application.

---

# 1. Product Goal

Build a polished local-first web application that allows a user to:

1. Upload a supported cardiac CT scan.
2. Run the existing pretrained MONAI segmentation pipeline.
3. See processing status.
4. View the resulting segmentation.
5. Convert segmented anatomy into 3D meshes.
6. Explore the reconstructed anatomy interactively in the browser.
7. Toggle individual anatomical structures.
8. View automatically calculated anatomical measurements.
9. Download/export generated segmentation and 3D model files.

The finished workflow should be:

```text
                    HEARTAI

                Upload Cardiac CT
                        │
                        ▼
                 FastAPI Backend
                        │
                        ▼
             Existing MONAI Pipeline
                        │
                        ▼
                  Segmentation
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
      3D Reconstruction       Measurements
             │                     │
             └──────────┬──────────┘
                        │
                        ▼
                   API Results
                        │
                        ▼
                Next.js Frontend
                        │
                        ▼
             Interactive 3D Heart
```

HeartAI is a research/portfolio prototype.

It is NOT a clinically validated medical device.

---

# 2. Critical Rules

The existing inference pipeline already works.

Therefore:

DO NOT:

- train a model
- fine-tune model weights
- replace the pretrained model unnecessarily
- rewrite working inference code from scratch
- fabricate anatomical structures
- fabricate medical measurements
- fabricate AI outputs
- fabricate progress percentages
- claim clinical diagnosis
- build Newton/Warp physics yet
- build RAG/LLM features yet

This phase is PRODUCT ENGINEERING around the already-working AI.

Keep the AI inference implementation isolated so that V2 can later replace the pretrained model with a fine-tuned model without requiring frontend/backend changes.

---

# 3. Technology Stack

Backend:

```text
Python
FastAPI
Pydantic
PyTorch
MONAI
Nibabel
NumPy
scikit-image
trimesh
```

Frontend:

```text
Next.js
React
TypeScript
React Three Fiber
Three.js
@react-three/drei
```

Optional frontend styling:

```text
Tailwind CSS
shadcn/ui
```

Do not add unnecessary frameworks.

For V1, persistence can use the filesystem.

A database is NOT required initially.

---

# 4. Why This Architecture

The Python backend owns:

```text
medical image loading
preprocessing
MONAI inference
segmentation
mesh generation
measurements
generated files
```

The browser owns:

```text
upload UI
status UI
3D visualization
structure controls
measurements display
downloads
```

The frontend must NEVER try to run MONAI or PyTorch directly.

Architecture:

```text
Browser
  │
  │ HTTP
  ▼
FastAPI
  │
  ├── existing MONAI inference
  ├── measurements
  └── mesh generation
           │
           ▼
         GLB
           │
           ▼
React Three Fiber
```

---

# 5. Target Repository Structure

Preserve existing files where possible.

Target structure:

```text
HeartAI/
│
├── CODEX.md
├── README.md
├── .gitignore
├── requirements.txt
│
├── data/
│   ├── demo/
│   └── uploads/
│
├── models/
│
├── results/
│   └── cases/
│
├── src/
│   └── heartai/
│       │
│       ├── preprocessing/
│       │
│       ├── inference/
│       │
│       │   └── predictor.py
│       │
│       ├── pipeline/
│       │   └── analyze.py
│       │
│       ├── reconstruction/
│       │   ├── marching_cubes.py
│       │   └── mesh_export.py
│       │
│       └── measurements/
│           ├── volume.py
│           └── geometry.py
│
├── backend/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── schemas.py
│       │
│       ├── routes/
│       │   ├── health.py
│       │   └── cases.py
│       │
│       └── services/
│           └── analysis.py
│
├── frontend/
│   ├── app/
│   ├── components/
│   │   ├── UploadCard.tsx
│   │   ├── ProcessingStatus.tsx
│   │   ├── HeartViewer.tsx
│   │   ├── StructureControls.tsx
│   │   └── MeasurementsPanel.tsx
│   │
│   ├── lib/
│   │   └── api.ts
│   │
│   └── types/
│       └── heartai.ts
│
└── tests/
```

Do not reorganize functioning Milestone 1 code unnecessarily.

---

# 6. First Task — Refactor Existing Inference Into a Callable Function

Before creating the web backend, inspect the currently working inference code.

The existing command currently behaves approximately like:

```bash
python scripts/run_inference.py data/demo/CTA-cardio.nii.gz
```

Create or expose a clean Python interface such as:

```python
result = run_inference(
    input_path="scan.nii.gz",
    output_dir="results/cases/demo-001"
)
```

The application should IMPORT and call the existing inference code.

Avoid launching another Python process with `subprocess` unless absolutely necessary.

The returned result should contain actual information such as:

```python
{
    "segmentation_path": "...",
    "input_shape": [...],
    "input_spacing_mm": [...],
    "inference_seconds": 0.0,
    "device": "cpu"
}
```

Do not fake unavailable values.

The original command-line script must continue to work.

---

# 7. Case Directory

Every analysis should receive a generated case ID.

Example:

```text
6f423dc8
```

Store outputs under:

```text
results/cases/<case_id>/
```

Example:

```text
results/cases/6f423dc8/
│
├── input/
│   └── scan.nii.gz
│
├── segmentation/
│   └── prediction.nii.gz
│
├── meshes/
│   ├── heart.glb
│   ├── aorta.glb
│   └── ...
│
├── previews/
│   └── overlay.png
│
├── measurements.json
└── manifest.json
```

Do not depend on original patient filenames.

Use generated IDs.

---

# 8. Segmentation Class Discovery

DO NOT assume the model outputs:

```text
LV
RV
LA
RA
etc.
```

Inspect the actual pretrained model's class mapping from Milestone 1.

Build:

```python
SUPPORTED_STRUCTURES = {
    ...
}
```

based ONLY on documented model labels.

HeartAI should expose only cardiac structures actually predicted by the selected model.

If the current whole-body MONAI model supports useful cardiac labels, extract those.

Ignore unrelated anatomy in the HeartAI UI unless useful.

Document exactly which structures HeartAI V1 supports.

---

# 9. 3D Mesh Generation

This is the next major technical milestone.

For each supported cardiac label:

```text
segmentation volume
        ↓
select label
        ↓
binary mask
        ↓
Marching Cubes
        ↓
triangle mesh
        ↓
physical coordinates
        ↓
optional smoothing
        ↓
GLB
```

Use:

```text
scikit-image.measure.marching_cubes
```

and:

```text
trimesh
```

unless another existing dependency is clearly better.

Critical requirement:

The segmentation exists in voxel coordinates.

The mesh must preserve REAL PHYSICAL SCALE.

Use:

```text
voxel spacing
affine transformation
```

from the NIfTI image.

Do not treat:

```text
x = voxel index
```

as:

```text
x = millimeters
```

without applying the proper transform.

---

# 10. Mesh Validation

Before building the frontend, validate meshes independently.

For each generated structure verify:

```text
vertices > 0
faces > 0
finite coordinates
reasonable bounding box
valid file created
```

Open at least one generated GLB/STL with an external viewer or Python visualization to confirm it is real.

Do not proceed to frontend 3D visualization until mesh generation is proven.

---

# 11. Combined Heart Model

Generate individual structure models when possible:

```text
left_ventricle.glb
right_ventricle.glb
aorta.glb
...
```

The frontend should preferably load them as separate meshes so structures can be independently:

```text
shown
hidden
selected
made transparent
focused
```

A single combined `heart.glb` may also be generated for export.

---

# 12. Anatomical Measurements

Calculate measurements directly from the segmentation.

Initial V1 measurements:

```text
structure volume
bounding-box dimensions
centroid
```

Volume:

```python
voxel_volume_mm3 = spacing_x * spacing_y * spacing_z

structure_volume_mm3 = voxel_count * voxel_volume_mm3

structure_volume_ml = structure_volume_mm3 / 1000
```

Every measurement must include units.

Example:

```json
{
    "aorta": {
        "volume_ml": 38.4,
        "centroid_mm": [12.3, 42.1, -18.7]
    }
}
```

Only display measurements that were actually calculated.

Do not derive medical conclusions from them.

---

# 13. Measurement Tests

Add unit tests for:

```text
voxel volume
mm³ → mL conversion
empty mask
known synthetic mask
spacing handling
centroid calculation
```

Example:

```python
def test_mm3_to_ml():
    assert mm3_to_ml(1000) == 1.0
```

Measurement code must be independently testable without the AI model.

---

# 14. Unified Analysis Pipeline

Create:

```python
analyze_case(scan_path, case_id)
```

This should orchestrate:

```text
1. create case directory
2. inspect input
3. run existing AI inference
4. save segmentation
5. identify supported structures
6. generate meshes
7. calculate measurements
8. create preview
9. write manifest
10. return structured result
```

Example result:

```json
{
    "case_id": "6f423dc8",
    "status": "complete",
    "model": {
        "name": "MONAI wholeBody_ct_segmentation",
        "version": "0.2.7",
        "device": "cpu"
    },
    "structures": [
        "aorta"
    ],
    "measurements": {},
    "artifacts": {
        "segmentation": "...",
        "meshes": {},
        "overlay": "..."
    },
    "timing": {
        "inference_seconds": 11.4,
        "total_seconds": 14.2
    }
}
```

Values must come from actual execution.

---

# 15. Processing Status

The web application needs status information.

Use real stages:

```text
uploading
preprocessing
segmenting
reconstructing
measuring
complete
failed
```

Do NOT display fake percentages such as:

```text
72%
```

unless actual progress is known.

Instead show:

```text
✓ Scan uploaded
✓ Preprocessing complete
● Running AI segmentation
○ Building 3D model
○ Calculating measurements
```

This is more honest and still visually polished.

---

# 16. Backend API

Create a FastAPI application.

Required endpoints:

```text
GET /health

POST /api/cases

GET /api/cases/{case_id}

GET /api/cases/{case_id}/status

GET /api/cases/{case_id}/measurements

GET /api/cases/{case_id}/segmentation

GET /api/cases/{case_id}/meshes/{structure}
```

`POST /api/cases` accepts:

```text
multipart/form-data
```

with a supported `.nii` or `.nii.gz` file.

Response:

```json
{
    "case_id": "...",
    "status": "processing"
}
```

---

# 17. Background Processing

Inference may take several seconds or minutes.

Do NOT make the frontend wait on one giant blocking HTTP request if avoidable.

For V1, use a simple in-process background job approach.

Architecture:

```text
POST /api/cases
       ↓
save upload
       ↓
return case_id
       ↓
background analysis
       ↓
frontend polls status
```

Frontend may call:

```text
GET /api/cases/{case_id}/status
```

every 1–2 seconds while processing.

Do not introduce Redis/Celery yet.

Those can be added later for cloud scaling.

---

# 18. API Error Handling

Return useful errors for:

```text
unsupported file
invalid NIfTI
file too large
inference failure
missing checkpoint
mesh generation failure
case not found
```

Never return successful status with fabricated results.

Example:

```json
{
    "status": "failed",
    "error": "Unable to load NIfTI volume"
}
```

---

# 19. Backend CORS

During local development the frontend and backend may run separately.

Example:

```text
frontend:
http://localhost:3000

backend:
http://localhost:8000
```

Configure FastAPI CORS only for expected development origins.

Do not use unrestricted production CORS unnecessarily.

---

# 20. Frontend Application

Create a polished Next.js + TypeScript frontend.

Primary route:

```text
/
```

Application states:

```text
EMPTY
UPLOAD
PROCESSING
RESULTS
ERROR
```

Do not build multiple unnecessary pages.

The core experience should feel like one medical visualization workstation.

---

# 21. Initial Screen

Design something approximately like:

```text
┌────────────────────────────────────────────────────┐
│ HEARTAI                                            │
│ AI-Powered 3D Heart Reconstruction                 │
├────────────────────────────────────────────────────┤
│                                                    │
│                                                    │
│             Upload a cardiac CT scan               │
│                                                    │
│          ┌─────────────────────────────┐           │
│          │                             │           │
│          │  Drop .nii / .nii.gz here │           │
│          │                             │           │
│          └─────────────────────────────┘           │
│                                                    │
│                  [ Analyze ]                       │
│                                                    │
└────────────────────────────────────────────────────┘
```

Clearly state:

```text
Research prototype — not for clinical use.
```

Do not make the disclaimer visually overwhelming.

---

# 22. Processing Screen

After upload:

```text
┌────────────────────────────────────────────────────┐
│ Analyzing cardiac CT                               │
│                                                    │
│ ✓ Scan uploaded                                    │
│ ✓ Preprocessing complete                           │
│ ● Running AI segmentation                          │
│ ○ Reconstructing 3D anatomy                        │
│ ○ Calculating measurements                         │
│                                                    │
└────────────────────────────────────────────────────┘
```

Do not fabricate progress.

Poll the backend.

---

# 23. Results Screen

Main layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ HeartAI                                      Case: 6f423dc8 │
├────────────────────────────────┬─────────────────────────────┤
│                                │                             │
│                                │ Anatomy                     │
│                                │                             │
│                                │ ☑ Aorta                     │
│                                │ ☑ Heart structure           │
│          3D HEART              │                             │
│                                │ Measurements                │
│                                │                             │
│                                │ Volume: ... mL              │
│                                │                             │
│                                │ Model                       │
│                                │ MONAI ...                   │
│                                │                             │
├────────────────────────────────┴─────────────────────────────┤
│ Rotate • Zoom • Pan • Reset • Export                         │
└──────────────────────────────────────────────────────────────┘
```

The 3D visualization should dominate the page.

---

# 24. React Three Fiber Viewer

Use:

```text
three
@react-three/fiber
@react-three/drei
```

Create:

```text
HeartViewer.tsx
```

Responsibilities:

```text
load GLB models
set up camera
set up lighting
OrbitControls
render structures
selection
opacity
visibility
camera reset
```

Do NOT manually build WebGL rendering infrastructure.

Use React Three Fiber.

---

# 25. 3D Interaction

Required controls:

```text
left click + drag → rotate
scroll → zoom
right click / configured control → pan
reset camera
```

Structures should support:

```text
show/hide
opacity
selection
focus
```

When selected, display its name and measurements.

---

# 26. 3D Rendering Quality

Use tasteful lighting.

Recommended concepts:

```text
ambient light
directional light
environment lighting where appropriate
perspective camera
anti-aliasing
```

Do not use excessive visual effects.

No particles.

No glowing sci-fi heart.

No unnecessary animation.

This should look like a serious medical/research visualization application.

---

# 27. Structure Colors

Structures should be visually distinguishable.

Use a centralized structure configuration:

```typescript
type StructureStyle = {
    label: string
    color: string
}
```

Do not scatter structure colors throughout components.

Colors are visualization aids only and should not imply medical meaning unless documented.

---

# 28. Measurements Panel

Selecting a structure should display available measurements.

Example:

```text
AORTA

Volume
38.4 mL

Bounding dimensions
42 × 38 × 91 mm

Centroid
...
```

Do not display values unavailable for that structure.

---

# 29. Model Information

Include a small information panel:

```text
AI Model

MONAI wholeBody_ct_segmentation
Version 0.2.7

Compute
CPU

Inference
11.4 seconds
```

This is excellent for demonstrating that HeartAI is a real engineering system.

Use actual metadata generated by the backend.

---

# 30. Segmentation Preview

In addition to the 3D model, allow the user to view the generated 2D overlay image from Milestone 1.

Example tab:

```text
3D Model | Segmentation Preview
```

Do NOT build a full diagnostic DICOM workstation in V1.

A static/selected segmentation preview is sufficient.

---

# 31. Downloads

Allow downloading generated outputs:

```text
segmentation.nii.gz
heart.glb
individual GLB/STL files
measurements.json
```

Label downloads clearly.

---

# 32. API Client

Centralize frontend API communication.

Create:

```text
frontend/lib/api.ts
```

Do not scatter `fetch()` calls across components.

Functions should resemble:

```typescript
createCase(file)
getCase(caseId)
getCaseStatus(caseId)
getMeasurements(caseId)
```

Use TypeScript response types.

---

# 33. TypeScript Types

Define explicit types:

```typescript
type CaseStatus =
  | "uploading"
  | "preprocessing"
  | "segmenting"
  | "reconstructing"
  | "measuring"
  | "complete"
  | "failed"
```

Create interfaces for:

```text
CaseResult
Measurement
Structure
ModelInfo
Artifact
```

Avoid `any`.

---

# 34. Local Development

Target developer workflow:

Terminal 1:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:3000
```

Document exact commands.

---

# 35. Demo Case

Keep a public/de-identified demo scan configured locally.

The application should optionally expose:

```text
Try Demo Scan
```

ONLY if licensing permits bundling or downloading that scan.

Otherwise document where to obtain it.

Never commit restricted medical data.

---

# 36. Tests

Backend tests should cover:

```text
health endpoint
case creation validation
case status
measurement serialization
mesh endpoint
missing case
invalid upload
```

Core Python tests:

```text
mesh generation
coordinate transformation
volume measurement
empty segmentation
structure extraction
```

Frontend should at minimum pass:

```text
TypeScript compilation
ESLint
production build
```

Do not attempt complicated browser automation until basic functionality works.

---

# 37. Docker

Docker comes AFTER the local application works.

Do not start by containerizing broken software.

Eventually create:

```text
backend Dockerfile
frontend Dockerfile
docker-compose.yml
```

The initial Docker configuration may use CPU inference.

GPU deployment comes later.

---

# 38. V1 Definition of Done

HeartAI V1 is COMPLETE when this works from the UI:

```text
OPEN HEARTAI
      ↓
UPLOAD CARDIAC CT
      ↓
AI PROCESSES SCAN
      ↓
SEGMENTATION CREATED
      ↓
3D MESH GENERATED
      ↓
MEASUREMENTS CALCULATED
      ↓
RESULTS PAGE OPENS
      ↓
USER ROTATES 3D HEART
      ↓
USER HIDES/SHOWS STRUCTURES
      ↓
USER SELECTS STRUCTURE
      ↓
USER SEES REAL MEASUREMENTS
      ↓
USER CAN DOWNLOAD OUTPUTS
```

All outputs must originate from the real existing inference pipeline.

---

# 39. What V1 Does NOT Include

Do not implement yet:

```text
fine-tuning
training
CHD classification
LLM/RAG
Newton
Warp
biomechanical simulation
virtual device deployment
hospital PACS integration
user accounts
billing
cloud scaling
patient records
clinical recommendations
```

These belong to future phases.

---

# 40. Future Architecture

Keep code modular enough that later we can replace:

```text
pretrained_model
```

with:

```text
our_fine_tuned_model
```

without changing:

```text
frontend
API contracts
mesh generation
measurements
3D viewer
```

This separation is extremely important.

Expected future evolution:

```text
V1
Pretrained AI
    +
complete product pipeline

        ↓

V2
Fine-tuned cardiac AI
    +
model evaluation

        ↓

V3
NVIDIA Warp/Newton
    +
cardiac physics simulation
```

---

# 41. Coding Standards

Codex must:

- inspect existing code before modifying it
- preserve the working Milestone 1 inference
- write understandable code
- use type hints in Python
- use TypeScript types
- avoid giant files
- separate inference from web routes
- separate API code from React presentation
- avoid duplicate preprocessing implementations
- add tests for numerical calculations
- report real errors
- never silently replace real outputs with mock data
- never fabricate model results
- avoid unnecessary architecture
- test each milestone before proceeding

Mocks may only be used in isolated automated tests.

The actual application must use real analysis output.

---

# 42. Implementation Order

Codex must implement this phase in the following order:

```text
1. Inspect existing Milestone 1 implementation

2. Refactor existing inference into reusable function
        ↓
   verify original inference still works

3. Implement structure extraction
        ↓
   verify actual labels

4. Implement mesh generation
        ↓
   generate real GLB/STL

5. Validate mesh geometry

6. Implement anatomical measurements
        ↓
   test with synthetic masks

7. Implement analyze_case()
        ↓
   CT → segmentation → mesh → measurements

8. Run complete pipeline from CLI

9. Build FastAPI backend

10. Test API using real demo scan

11. Create Next.js frontend

12. Implement upload

13. Implement processing status

14. Implement React Three Fiber viewer

15. Connect real generated meshes

16. Add structure toggles / selection

17. Add measurements panel

18. Add segmentation preview

19. Add downloads

20. Polish UI

21. Run tests

22. Update README

23. STOP
```

Do not jump ahead.

---

# 43. Immediate Task

START NOW with steps 1–8 ONLY.

Do NOT build the frontend yet.

Specifically:

1. Inspect all existing Milestone 1 code.
2. Identify how inference is currently invoked.
3. Preserve the working MONAI inference implementation.
4. Refactor it into a clean reusable function if necessary.
5. Inspect the actual segmentation output and label mapping.
6. Implement extraction of HeartAI-relevant cardiac structures.
7. Implement physically correct 3D mesh generation.
8. Implement basic anatomical volume measurements.
9. Implement `analyze_case()`.
10. Run the complete CLI pipeline on the existing `CTA-cardio.nii.gz`.
11. Verify that real files are generated.
12. Report exactly:
    - structures found
    - segmentation output
    - generated meshes
    - calculated measurements
    - total processing time
    - failures/limitations

STOP after the CLI pipeline works.

Do not implement FastAPI or React until this milestone has been successfully verified.