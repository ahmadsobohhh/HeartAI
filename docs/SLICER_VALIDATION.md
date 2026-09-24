# Slicer round-trip validation — September 20, 2026

This is technical integration evidence, not clinical validation. No model training, weight changes, or new inference was performed.

## Actual environment and data

- Windows, 3D Slicer 5.12.4, build 34645, application git revision `4e21c19`.
- SlicerHeart installed and loaded, revision `eae1bea`; its extension metadata is recorded in `results/slicer/runtime-validation/session-verification.json`.
- Public Slicer CTACardio, case `788812d5bc03`, original CT 512 × 512 × 321, approximately 0.934 × 0.934 × 1.25 mm.
- Existing MONAI wholeBody_ct_segmentation 0.2.7, low-resolution 3 mm prediction. Aorta 7, myocardium 44, left atrium 45, left ventricle 46, right atrium 47, right ventricle 48, pulmonary artery 49.
- This workflow uses core Slicer Segment Editor and segmentation representations. No specialized SlicerHeart valve tool or simulation was used.

## Observed checks

The real CT and all seven editable masks loaded into the four-up layout. The screenshot `results/slicer/runtime-validation/slicer-session.png` was inspected for gross alignment in axial, coronal, and sagittal views. This does not establish segmentation accuracy.

| Check | Observed result |
| --- | --- |
| Slicer no-edit export, revision `2d12b636f16d` | All cardiac voxels identical to source; zero changed voxels |
| Independent HeartAI rebuild | Original seven-structure measurements reproduced exactly |
| Slicer test edit, revision `9231aa46519b` | One myocardium voxel at KJI `[176,250,363]` removed |
| Myocardium volume decrease | 0.0010894971690191824 mL; expected voxel volume 0.0010894971690141376 mL (floating-point tolerance 1e-10) |
| Accepted segmentation geometry | Original shape, affine, millimeter units, qform/sform matrices and codes preserved |
| Original CT/prediction/package | SHA-256 hashes unchanged |
| Generated revision artifacts | Every recorded artifact hash verified |
| Saved `.mrb` reopen | Seven stable segment IDs, draft state, CT reference link retained |
| Slicer rejection guards | Overlap, unknown segment ID, changed label tag, and unresolved transform each rejected |
| Python tests | 40 passed, 2 real-inference integration tests deselected |

The deliberate edit is a software test, not an anatomical correction. The reopened session left on screen contains the original, unedited draft.

## Files

`results/slicer/runtime-validation/` contains the raw Slicer exports in the two revision directories, `baseline.mrb`, `result.json`, `verification.json`, `session-verification.json`, and the screenshot. `initial-headless-error.txt` retains the first failed no-main-window attempt; the successful tests require Slicer's normal GUI/layout manager.

Both accepted revisions are under `results/cases/788812d5bc03/reviews/<revision_id>/`. Each contains:

- `review.json`: draft state, parent case/model/input hashes, change counts, warnings, artifact hashes.
- `review.seg.nrrd`: native editable Slicer segmentation.
- `slicer_labels.nii.gz`: exact Slicer-exported NIfTI.
- `cardiac_labels.nii.gz`: accepted labels with original CT qform/sform metadata.
- `measurements.json`, `meshes/heart.glb`, seven individual GLB/STL pairs, and `previews/overlay.png`.

The current exporter additionally records parent revision (null, meaning original AI case) and installed SlicerHeart metadata. The two initial test exports predate those fields; their extension version is recorded separately in `session-verification.json`.

An initial reconstruction failed at Windows directory rename because the preview reader retained a compressed-image file handle. The preview now reads segmentation bytes with an explicitly closed file handle. Rebuilding both real exports succeeded; the failed unpublished staging directory remains for diagnosis.

## Reproduce technical checks

Use the user workflow in [SLICER_SETUP.md](SLICER_SETUP.md) for ordinary review. For this fixed demo regression test:

```powershell
& 'C:\Users\Ahmad Soboh\AppData\Local\slicer.org\3D Slicer 5.12.4\Slicer.exe' --no-splash --python-script "$PWD\scripts\test_slicer_roundtrip.py"
```

The Windows launcher returns before Slicer finishes. Wait for that test window to close and a newly written `results/slicer/runtime-validation/result.json`. It contains new baseline and edited export paths. Rebuild both:

```powershell
$roundtrip = Get-Content results/slicer/runtime-validation/result.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe scripts/import_slicer_review.py results/cases/788812d5bc03 $roundtrip.baseline
.\.venv\Scripts\python.exe scripts/import_slicer_review.py results/cases/788812d5bc03 $roundtrip.edited
.\.venv\Scripts\python.exe scripts/verify_slicer_outputs.py
.\.venv\Scripts\python.exe -m pytest -q -m 'not integration'
& 'C:\Users\Ahmad Soboh\AppData\Local\slicer.org\3D Slicer 5.12.4\Slicer.exe' --no-splash --python-script "$PWD\scripts\verify_slicer_session.py"
```

The last command reopens the scene, exercises rejection guards, writes a screenshot, and leaves the unedited case open. Regression scripts target this demo case and require its prepared initial package.

## Remaining scope

No human anatomical review or clinical sign-off has occurred. Drafts are not medical-grade outputs. Coarse 3 mm model boundaries, the truncated aorta, and disconnected LV components remain visible; Slicer does not improve the model automatically. Specialized valve/congenital labels are absent.

Current sessions depend on local absolute source paths. Standalone `.seg.nrrd` reattachment, revision chaining, structured human approval, and a dedicated export/review UI remain future work. Browser results continue to show the original AI case. Native-grid/extent checks are implemented; dedicated runtime tests for off-grid resampling and out-of-extent edits remain to be added.
