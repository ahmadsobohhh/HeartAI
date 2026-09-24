# Slicer review and return workflow

## Install

1. Open [the official download page](https://download.slicer.org/).
2. Choose **Windows / Stable Release**. On September 20, 2026 this is **5.12.4, revision 34645**.
3. Run the downloaded installer and keep its default installation folder. Open Slicer once to verify that it starts.
4. SlicerHeart is optional for this first checkpoint. To add it, open Slicer's Extension Manager, search for **SlicerHeart**, install it with its dependencies, and restart Slicer. See [official instructions](https://slicerheart.org/).

Slicer supplies its own Python runtime. Do not install HeartAI's PyTorch/MONAI dependencies into it. The existing HeartAI environment prepares the case; Slicer loads the prepared files.

## Open the real HeartAI case

Close an empty Slicer window before starting a new review session. From the HeartAI repository in PowerShell, replace the example path with the actual installed `Slicer.exe`:

```powershell
.\scripts\start_slicer.ps1 -SlicerPath 'C:\Users\Ahmad Soboh\AppData\Local\slicer.org\3D Slicer 5.12.4\Slicer.exe' -CaseId 788812d5bc03
```

The launcher validates the original case, creates a new package under `results/slicer/`, and starts Slicer with the original CT and an editable cardiac segmentation. It selects Segment Editor and a four-up layout. It does not require the web frontend or API server to be running.

Alternatively, a real prepared package already exists at `results/slicer/788812d5bc03-initial/review_package.json` on this workstation. In Slicer's Python console, run:

```python
exec(open(r"C:\Users\Ahmad Soboh\Desktop\HeartAI\scripts\open_slicer_case.py", encoding="utf-8").read())
load_heartai_case(r"C:\Users\Ahmad Soboh\Desktop\HeartAI\results\slicer\788812d5bc03-initial\review_package.json")
```

Inspect the CT and colored labels in all three planes before editing. Original case files are not overwritten. Use Segment Editor to select a structure, then Paint or Erase to edit its mask. Do not delete or add segments: retain an empty segment if removing a structure. Export rejects overlapping segments, changed reference geometry, and unknown label identities. These checks do not establish anatomical correctness.

## Save a draft and rebuild

Open Slicer's Python Interactor from the View menu. Load the helpers once (also works after reopening a saved scene):

```python
exec(open(r"C:\Users\Ahmad Soboh\Desktop\HeartAI\scripts\open_slicer_case.py", encoding="utf-8").read())
```

With the HeartAI segmentation selected in Segment Editor, export:

```python
draft = export_current_heartai_review("Ahmad", purpose="test edit", notes="Describe what you changed")
print(draft)
```

Use `purpose="anatomical review"` for actual inspection/correction or `purpose="no-edit round trip"` for an unchanged export. All exports remain **draft**, including those with an anatomical-review purpose. The helper prints a new directory such as `results/slicer/exports/<revision_id>`, containing `review.seg.nrrd`, `cardiac_labels.nii.gz`, and provenance in `review.json`.

In a PowerShell terminal in HeartAI, paste that printed directory:

```powershell
.\.venv\Scripts\python.exe scripts/import_slicer_review.py results/cases/788812d5bc03 'C:\full\path\printed\by\Slicer'
```

This validates the CT grid, label IDs, and source/output hashes, then writes a new `results/cases/788812d5bc03/reviews/<revision_id>/` containing the segmentation, GLB/STL meshes, measurements, overlay, and revision record. It never calls AI inference. Existing revision IDs cannot be overwritten. Failed builds retain an unpublished `.tmp-*` directory with `failure.json`.

To preserve the complete editable session, use **Save**, select a new **Medical Reality Bundle (.mrb)** location, and include the CT and segmentation. A tested session already exists at `results/slicer/runtime-validation/baseline.mrb`; open it with Slicer's Add Data. Keep the original case and review-package directories: the current revision helper verifies those files by absolute path. A `.seg.nrrd` alone does not carry the complete session/reference link required by the helper.

Revisions currently compare against the original AI prediction, not another revision. There is no clinical sign-off UI or automatic display of draft revisions in the web frontend yet.

## Verification status

- Real CTACardio loaded and reopened in Slicer 5.12.4 with all seven cardiac structures.
- Unchanged export: zero changed cardiac voxels; unchanged original measurements and physical geometry.
- Deliberate test edit: exactly one myocardium voxel removed; volume decreased by one voxel.
- Slicer runtime rejected overlap, changed mapping, unknown segments, and parent transforms.
- Forty non-integration Python tests passed. No training or inference was run for this round trip.

Full evidence, output paths, and remaining limitations: [SLICER_VALIDATION.md](SLICER_VALIDATION.md).

Full integration design and subsequent export/reconstruction gates: [SLICER_WORKFLOW.md](SLICER_WORKFLOW.md).
