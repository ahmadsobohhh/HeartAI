# HeartAI — V1 Engineering Specification

## Goal

Build HeartAI end-to-end using an EXISTING PRETRAINED cardiac/medical segmentation model.

DO NOT train, fine-tune, or modify model weights in V1.

The goal of V1 is to build the complete product pipeline:

```text
Cardiac CT
    ↓
Preprocessing
    ↓
Pretrained AI model
    ↓
Cardiac segmentation
    ↓
3D reconstruction
    ↓
Anatomical measurements
    ↓
Backend API
    ↓
Interactive React/Three.js application
```

Once this entire system works, V2 will fine-tune the model on congenital cardiac CT data and compare performance.

---

# 1. Project Description

HeartAI is a medical-AI research prototype that converts cardiac CT scans into interactive patient-specific 3D heart models.

The system should:

1. Accept a supported cardiac CT volume.
2. Preprocess the scan.
3. Run a verified pretrained segmentation model.
4. Segment supported cardiac anatomy.
5. Reconstruct the segmentation into 3D meshes.
6. Calculate anatomical measurements.
7. Serve the results through a FastAPI backend.
8. Display the heart interactively using React and Three.js.
9. Allow individual anatomical structures to be inspected.

This is NOT a clinical medical device.

Do not claim that HeartAI diagnoses patients or is clinically validated.

---

# 2. Critical V1 Rule

## NO MODEL TRAINING

For V1:

DO NOT:

- train a U-Net
- fine-tune a model
- update model weights
- create a custom training loop
- run hyperparameter optimization
- claim a model was trained by this project

Use an existing pretrained model exactly as provided.

The first ML objective is simply:

```text
New CT
   ↓
existing pretrained model
   ↓
segmentation
```

Fine-tuning will be implemented separately in V2.

---

# 3. Pretrained Model Selection

Before implementing the inference pipeline, identify a VERIFIED pretrained model that supports cardiac CT segmentation.

Preferred sources, in order:

1. Official MONAI Model Zoo / MONAI Bundle
2. Model explicitly supported by MONAI
3. Well-maintained open-source medical segmentation model with published documentation

Prefer a model capable of segmenting useful structures such as:

- left ventricle
- right ventricle
- left atrium
- right atrium
- myocardium
- aorta
- pulmonary artery

However, DO NOT pretend that a model supports structures it does not actually support.

Codex must inspect the model's official documentation and determine:

- required input modality
- input format
- expected preprocessing
- supported classes
- checkpoint source
- model license
- inference procedure

Document these findings.

If no verified pretrained model supports the exact seven desired structures, use the best legitimate model available and document the limitation.

DO NOT train a new model merely to fill missing classes.

---

# 4. V1 Architecture

Target system:

```text
                    HEARTAI

                    Cardiac CT
                         │
                         ▼
                Image preprocessing
                         │
                         ▼
              Pretrained segmentation
                         │
                         ▼
                Segmentation mask
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
       Measurements             3D Meshes
             │                       │
             └───────────┬───────────┘
                         ▼
                       FastAPI
                         │
                         ▼
                React + Three.js
                         │
                         ▼
               Interactive 3D Heart
```

---

# 5. Repository Structure

Create:

```text
HeartAI/
│
├── CODEX.md
├── README.md
├── .gitignore
├── requirements.txt
├── pyproject.toml
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── demo/
│
├── models/
│
├── src/
│   └── heartai/
│       ├── preprocessing/
│       │   ├── loader.py
│       │   └── transforms.py
│       │
│       ├── inference/
│       │   ├── model.py
│       │   └── predictor.py
│       │
│       ├── reconstruction/
│       │   ├── mesh.py
│       │   └── export.py
│       │
│       ├── measurements/
│       │   ├── volume.py
│       │   └── geometry.py
│       │
│       └── pipeline/
│           └── analyze.py
│
├── scripts/
│   ├── inspect_scan.py
│   ├── run_inference.py
│   ├── generate_mesh.py
│   └── analyze_case.py
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── routes/
│   │   └── services/
│   └── tests/
│
├── frontend/
│
├── tests/
│
├── results/
│   ├── segmentations/
│   ├── meshes/
│   └── measurements/
│
├── Dockerfile
└── docker-compose.yml
```

Keep architecture simple.

Do not create unnecessary abstractions.

---

# 6. Input Format

V1 should initially support:

```text
NIfTI
.nii
.nii.gz
```

Do NOT implement DICOM support until NIfTI works end-to-end.

Later DICOM support can convert:

```text
DICOM series
    ↓
NIfTI
    ↓
HeartAI
```

The first goal is reliability, not supporting every medical format.

---

# 7. Medical Image Loading

Use:

- nibabel
- SimpleITK
- MONAI where appropriate

For every scan inspect:

```text
shape
voxel spacing
orientation
affine
intensity range
```

Never discard physical spacing information.

Physical coordinates are required for:

- correct 3D reconstruction
- correct volume measurements
- correct dimensions

---

# 8. Preprocessing

Use EXACTLY the preprocessing required by the selected pretrained model.

Possible operations include:

```text
orientation normalization
voxel resampling
intensity clipping
intensity normalization
cropping
channel conversion
```

Do not invent preprocessing.

Read the pretrained model's official configuration and reproduce it faithfully.

Training augmentation is NOT required because V1 performs inference only.

---

# 9. GPU Inference

HeartAI should support NVIDIA CUDA.

Conceptually:

```python
device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)
```

The model should execute inference on GPU when available.

Record:

```text
GPU used
model used
inference duration
input dimensions
```

CPU fallback is acceptable for development if supported.

Never claim CUDA acceleration if inference did not actually use CUDA.

---

# 10. Inference

Implement a clean function:

```python
result = segment_scan(path)
```

Conceptually:

```text
load scan
    ↓
preprocess
    ↓
pretrained model
    ↓
prediction
    ↓
restore spatial coordinates
    ↓
segmentation
```

Save:

```text
results/segmentations/<case_id>.nii.gz
```

The prediction must preserve physical-space information.

---

# 11. Segmentation Inspection

Before building any 3D application, verify predictions visually.

Create a script that displays:

```text
original CT
predicted segmentation
CT + segmentation overlay
```

Inspect several slices.

Do not continue to 3D reconstruction if the segmentation obviously does not align with the CT.

---

# 12. 3D Reconstruction

Convert each available segmented structure into a surface mesh.

Pipeline:

```text
segmentation mask
       ↓
binary structure mask
       ↓
marching cubes
       ↓
vertices + faces
       ↓
physical coordinate conversion
       ↓
mesh
```

Use one or more of:

```text
scikit-image
trimesh
VTK
```

Export browser-compatible models.

Preferred:

```text
GLB / GLTF
```

Optional:

```text
STL
OBJ
```

Preserve correct physical scale.

DO NOT treat voxel indices directly as millimeters.

---

# 13. Anatomical Measurements

Calculate measurements from segmentation masks.

Start with:

```text
structure volume
bounding-box dimensions
centroid
surface area where practical
```

Volume calculation:

```text
voxel_volume_mm3 =
spacing_x * spacing_y * spacing_z

volume_mm3 =
number_of_structure_voxels * voxel_volume_mm3

volume_ml =
volume_mm3 / 1000
```

Example output:

```json
{
  "left_ventricle": {
    "volume_ml": 42.1
  },
  "right_ventricle": {
    "volume_ml": 38.7
  }
}
```

Only calculate structures actually provided by the pretrained model.

---

# 14. End-to-End Python Pipeline

Create:

```text
src/heartai/pipeline/analyze.py
```

Main API:

```python
analyze_case(scan_path)
```

It should perform:

```text
scan
 ↓
load
 ↓
preprocess
 ↓
AI inference
 ↓
segmentation
 ↓
mesh reconstruction
 ↓
measurements
 ↓
results
```

Return something similar to:

```json
{
  "case_id": "demo-001",
  "structures": [],
  "measurements": {},
  "segmentation_path": "...",
  "mesh_paths": {},
  "inference_seconds": 0
}
```

This pipeline MUST work from a command line before backend/frontend work begins.

---

# 15. Command-Line Demo

This command should eventually work:

```bash
python scripts/analyze_case.py data/demo/heart.nii.gz
```

Output:

```text
Loading scan...
Preprocessing...
Running AI segmentation...
Generating meshes...
Calculating measurements...

Analysis complete.

Segmentation:
results/segmentations/demo-001.nii.gz

3D models:
results/meshes/demo-001/

Measurements:
results/measurements/demo-001.json
```

This is the first major V1 milestone.

---

# 16. FastAPI Backend

Only begin backend development once the command-line pipeline works.

Use:

```text
FastAPI
Pydantic
Uvicorn
```

Endpoints:

```text
GET /health

POST /api/analyze

GET /api/cases/{case_id}

GET /api/cases/{case_id}/measurements

GET /api/cases/{case_id}/mesh/{structure}
```

Example flow:

```text
upload scan
    ↓
backend saves file
    ↓
analyze_case()
    ↓
results saved
    ↓
JSON returned
```

---

# 17. Frontend

Use:

```text
Next.js
React
TypeScript
Three.js
React Three Fiber
```

Main experience:

```text
+---------------------------------------------+
|                   HeartAI                   |
+---------------------------------------------+
|                                             |
|             Upload Cardiac CT               |
|                                             |
|                [ Upload ]                   |
|                                             |
+---------------------------------------------+
```

After processing:

```text
+---------------------------------------------+
|                   HeartAI                   |
+--------------------------+------------------+
|                          |                  |
|                          | Measurements     |
|       3D HEART           |                  |
|                          | LV: ...           |
|                          | RV: ...           |
|                          |                  |
|                          | Structures       |
|                          | ☑ LV             |
|                          | ☑ RV             |
|                          | ☑ Aorta          |
+--------------------------+------------------+
```

---

# 18. Three.js Features

Required:

```text
rotate
zoom
pan
reset camera
hide/show structures
change opacity
focus structure
```

Each segmented anatomical structure should be separately controllable.

Do not add fancy animations until basic interaction works properly.

---

# 19. Slicer Integration

After the browser application works, add export compatibility with:

```text
3D Slicer
SlicerHeart
```

Allow users to export:

```text
segmentation NIfTI
STL/OBJ
```

Document how exported results can be loaded into Slicer.

Do not implement intervention simulation in V1.

That can be a later extension.

---

# 20. Testing

Required tests include:

```text
file loading
spacing extraction
volume calculation
mesh generation
model output shape
pipeline response
FastAPI health endpoint
```

Tests must use synthetic data when possible.

The full medical dataset must not be required for normal unit testing.

---

# 21. No Fake Results

Never invent:

```text
Dice scores
accuracy
clinical performance
inference speed
measurements
model capabilities
supported structures
```

All displayed values must come from actual execution.

---

# 22. No Clinical Claims

Do NOT say:

```text
HeartAI diagnoses heart disease.

HeartAI detects defects with clinical accuracy.

HeartAI replaces doctors.

HeartAI recommends treatment.
```

Instead:

```text
AI-assisted cardiac analysis

3D cardiac reconstruction

research prototype

model-generated segmentation
```

V1 primarily reconstructs anatomy.

Defect-specific classification will be a later ML phase.

---

# 23. V1 Development Order

Follow this order exactly:

```text
1. Create project structure
        ↓
2. Select and verify pretrained model
        ↓
3. Load test CT
        ↓
4. Reproduce model preprocessing
        ↓
5. Run pretrained inference
        ↓
6. Visualize segmentation
        ↓
7. Generate 3D meshes
        ↓
8. Calculate measurements
        ↓
9. Build analyze_case()
        ↓
10. Complete CLI demo
        ↓
11. Build FastAPI backend
        ↓
12. Build React frontend
        ↓
13. Add Three.js viewer
        ↓
14. Connect frontend → API
        ↓
15. Add Slicer export
        ↓
16. Dockerize
        ↓
17. Tests / CI
        ↓
18. README / demo
```

Do not begin the next major layer if the previous layer is broken.

---

# 24. Definition of V1 Complete

V1 is complete when this works:

```text
SUPPORTED CARDIAC CT
        ↓
PRETRAINED AI
        ↓
SEGMENTATION
        ↓
3D RECONSTRUCTION
        ↓
MEASUREMENTS
        ↓
FASTAPI
        ↓
REACT / THREE.JS
        ↓
INTERACTIVE HEART
```

A user should be able to upload a supported public/de-identified cardiac CT and receive:

- AI-generated segmentation
- reconstructed 3D anatomy
- structure measurements
- interactive browser visualization

without training or modifying the AI model.

---

# V1 Success Criteria

HeartAI V1 is considered working only when a real supported cardiac CT can be processed end-to-end and produces all of the following:

1. A saved AI segmentation:
   `prediction.nii.gz`

2. A visual CT + segmentation overlay that confirms the predicted anatomy aligns with the scan.

3. Patient-specific 3D meshes generated from the segmentation:
   - heart.glb or equivalent
   - individual structure meshes where supported

4. Anatomical measurements generated directly from the segmentation:
   - structure volumes
   - dimensions/geometry where implemented

5. A working command-line pipeline:

   ```bash
   python scripts/analyze_case.py <scan>

# 25. V2 — DO NOT IMPLEMENT YET

After V1 is complete, we will create a separate specification for ML experimentation.

V2 will include:

```text
target congenital cardiac dataset
        ↓
existing pretrained model
        ↓
baseline evaluation
        ↓
fine-tuning
        ↓
evaluation
        ↓
compare baseline vs fine-tuned model
```

Potential V2 additions:

```text
fine-tuning
Dice / HD95 evaluation
augmentation experiments
loss-function experiments
uncertainty estimation
segmentation quality control
cardiac geometry modeling
experimental CHD classification
```

Do NOT implement any of this during V1.

---

# 26. Instructions for Codex

When working on HeartAI:

1. Read this file completely before coding.
2. Work incrementally.
3. Inspect existing code before changing it.
4. Do not train or fine-tune models.
5. Verify pretrained model capabilities from documentation.
6. Never fabricate model capabilities.
7. Never fabricate output.
8. Keep code understandable for a developer learning ML.
9. Add comments where medical-image-specific behavior is non-obvious.
10. Test each major pipeline stage.
11. Keep ML inference separate from web/backend code.
12. Do not build the frontend until inference works.
13. Do not add unnecessary infrastructure.
14. If reality differs from this specification, document it rather than hiding it.

---

# 27. Codex's First Task

Start ONLY with:

## Milestone 1 — Pretrained AI Inference

Do the following:

1. Initialize/inspect the HeartAI repository.
2. Create the Python structure.
3. Add appropriate `.gitignore`.
4. Add dependency configuration.
5. Research/inspect verified pretrained cardiac CT segmentation options.
6. Select the best legitimate model for HeartAI V1.
7. Document exactly:
   - model name
   - source
   - license
   - input requirements
   - supported structures
   - preprocessing
8. Download/load the model.
9. Obtain or configure a public example CT.
10. Run inference.
11. Save the resulting segmentation.
12. Generate a CT + prediction overlay visualization.
13. Add a simple script to reproduce this result.
14. Document the commands in README.

STOP THERE.

Do not build meshes, FastAPI, React, or anything else until actual pretrained inference has successfully run.