# Milestone C — real reconstruction and measurements

Completed on the public CTACardio scan using the six reviewed TotalSegmentator 2.18.0 `total` masks from Milestones A/B. No new inference, training, licensed cardiac task, or invented anatomy. The existing MONAI outputs and all 117 source masks were retained.

## Actual results

| Structure | Mask volume (mL) | Mesh volume (mL) | Surface area (cm²) | Triangles |
| --- | ---: | ---: | ---: | ---: |
| heart | 495.029 | 494.769 | 559.588 | 132,946 |
| aorta | 133.420 | 133.159 | 326.530 | 71,968 |
| pulmonary_vein | 20.247 | 20.084 | 92.335 | 21,912 |
| atrial_appendage_left | 4.904 | 4.870 | 21.511 | 5,324 |
| superior_vena_cava | 16.471 | 16.420 | 48.680 | 10,644 |
| inferior_vena_cava | 25.498 | 25.398 | 88.342 | 19,144 |

These are measurements of the predicted masks, not ground-truth anatomy or clinical measurements. The whole-heart label does not provide separate chambers or myocardium. The aorta is truncated at the inferior scan boundary; its surface is closed at that boundary for export and volume comparison. All disconnected components remain, including the two-voxel heart island. No smoothing or decimation was applied. Surface areas therefore reflect the raw voxel-derived surfaces.

Reconstruction, measurements, export/reopening checks, and original-mask hashing took **17.924 seconds**, excluding Slicer validation. Every mesh is watertight with consistent winding, finite vertices/normals, positive volume, and nondegenerate triangles. Mesh volumes differ from voxel volumes by at most **0.809%**, within the predefined 5% engineering check. This threshold is not an accuracy metric.

## Physical coordinates and verification

The crop retains all foreground components and adjusts its affine by the original index offset. Marching cubes runs at the binary 0.5 boundary with zero padding. The full NIfTI affine is applied once, including translation, orientation, and voxel scale; no independent object centering occurs. Voxel volume uses the absolute affine determinant (1.089497169 mm³ per voxel here), divided by 1,000 for mL. Bounds and centroids are in original RAS millimeters.

STL stores raw **RAS millimeters**. STL itself carries no units or anatomical convention: select RAS explicitly when importing. The verification script reads raw STL points with VTK and creates Slicer model nodes in RAS, avoiding automatic LPS interpretation. GLB uses right-handed Y-up meters: `(R,S,-A)/1000`, retaining the patient origin. The inverse transform is recorded in reconstructable matrix form in `reconstruction.json`.

All six GLBs were reopened and every vertex checked in both directions after converting back to RAS mm. The largest deviation was less than **0.000008 mm** (float export precision), below the 0.001 mm tolerance. STL coordinates passed the same tolerance. The combined GLB was reopened and checked for all six named geometries and correct bounds.

In **3D Slicer 5.12.4**, exported STLs were independently transformed from RAS into the original CT index grid and rasterized with VTK. All six produced **zero differing voxel centers** against their original masks, including background. This verifies spatial and export fidelity; it is not a segmentation accuracy or Dice claim. Slicer saved the source CT and exported models together, and captured each structure on three orthogonal CT slices. The combined views and selected individual captures were visually inspected for gross shift, reflection, and scale errors.

## Artifacts

Root: `results/cases/PUBLIC-001-totalseg/milestone-c/` (generated outputs are Git-ignored).

| File | Contents |
| --- | --- |
| `meshes/<structure>.glb`, `.stl` | Six individual real surfaces in each format |
| `meshes/cardiac.glb` | Combined scene with six separate named structures |
| `measurements.json` | Voxel/mesh volume, area, centroid, bounds, dimensions, component counts |
| `reconstruction.json` | Input hashes, coordinates, topology, export checks, warnings, actual runtime |
| `completion.json` | Final acceptance record, inspected captures, provenance and preservation checks |
| `slicer-check-final/verification.json` | Independent executed mesh-to-mask checks and capture hashes |
| `slicer-check-final/meshes-on-ct.mrb` | Reopenable CT plus exported mesh scene |
| `slicer-check-final/four_up.png` | Real exported mesh contours over CT and a 3D view |
| `slicer-check-final/exported_meshes.png` | Slicer render of actual exported meshes |
| `slicer-final-stdout.txt`, `slicer-final-stderr.txt` | Final Slicer execution logs |

The earlier `slicer-check/` pass also passed exact rasterization but used a deprecated display call and a more distant camera. The final folder uses the supported display call and a closer camera. Neither pass changes mesh geometry.

## Reproduce

From the repository root, after Milestone B. This uses existing geometry dependencies in the preserved `.venv`; it does not invoke MONAI. On a fresh installation follow the repository's Python setup first. Choose a new output directory; existing evidence is never overwritten.

```powershell
.\.venv\Scripts\python.exe scripts/reconstruct_totalseg.py results/slicer/PUBLIC-001-totalseg-B-final results/cases/PUBLIC-001-totalseg/milestone-c-rerun
.\.venv\Scripts\python.exe -m pytest -q tests/test_geometry.py tests/test_totalseg_reconstruction.py
$env:HEARTAI_MESH_CASE = Join-Path (Get-Location) 'results/cases/PUBLIC-001-totalseg/milestone-c-rerun'
$env:HEARTAI_MESH_REVIEW_FOLDER = 'slicer-check-final'
$meshScript = Join-Path (Get-Location) 'scripts/verify_totalseg_meshes_in_slicer.py'
Start-Process -FilePath 'C:\Users\Ahmad Soboh\AppData\Local\slicer.org\3D Slicer 5.12.4\Slicer.exe' -ArgumentList @('--no-splash', '--ignore-slicerrc', '--python-script', ('"' + $meshScript + '"')) -WindowStyle Hidden -Wait
```

Use the actual installed Slicer path on another machine. The script closes only the newly launched process after saving. Review generated captures before recording visual completion. Reconstruction reports `reconstructed_pending_slicer_alignment`; Slicer separately reports `technical_checks_passed_visual_review_pending`. `completion.json` records this run's subsequent visual acceptance rather than letting an automated export claim human/expert anatomical validation.

**18 tests passed.** Tests cover physical units, full affine transforms, reflected orientation/winding, GLB round trips, centroids/bounds, crop translation, retained components, boundary detection, invalid masks, and the documented 1 mL example. Small synthetic arrays are used only in isolated geometry tests, never as demo anatomy.

Stopped at Milestone C. Milestone D (unified CLI), TotalSegmentator backend/frontend integration, and later viewer work remain outside this checkpoint.
