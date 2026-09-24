# Milestone B — cardiac extraction and Slicer sanity check

**Complete.** The actual 117-class TotalSegmentator output inventory was read, six nonempty cardiac masks were selected and validated, and the real CT plus masks were inspected in **3D Slicer 5.12.4** (reported revision `4e21c19`). This records the B checkpoint; the subsequent reconstruction is documented in [Milestone C](TOTALSEG_MILESTONE_C.md).

This uses the existing Milestone A prediction from TotalSegmentator 2.18.0, task `total`, standard resolution. No inference or training was rerun. The original MONAI code, environment, results, and existing Slicer session were preserved.

## Actual subset and findings

| Installed label ID | Structure | Foreground voxels | 26-connected component sizes |
| --- | --- | ---: | --- |
| 51 | heart | 454,365 | 454,363 + 2 |
| 52 | aorta | 122,460 | 122,460 |
| 53 | pulmonary_vein | 18,584 | 9,170 + 5,343 + 4,071 |
| 61 | atrial_appendage_left | 4,501 | 4,501 |
| 62 | superior_vena_cava | 15,118 | 15,118 |
| 63 | inferior_vena_cava | 23,403 | 22,865 + 538 |

All six masks are binary, nonempty, mutually disjoint, and occupy the original CT grid. Their foreground counts match Milestone A. The aorta reaches the inferior CT boundary (slice 0). Disconnected components are recorded without interpreting them as diagnoses or automatically deleting them. **Every original predicted voxel was retained.**

The task has no separate myocardium, left/right chamber, or pulmonary artery masks. The pulmonary-vein output is not a pulmonary-artery substitute. The remaining task outputs stay intact; no MONAI labels were mixed into this subset.

## Completed checks

1. Matched the full set of output filenames to the installed task map saved in Milestone A; recorded all 117 source-mask hashes and their existing foreground inventory.
2. Reopened the six selected masks using Nibabel. Checked shape, affine, binary values, foreground counts, overlap, boundary contact, and connected components. Verified component sizes account for every foreground voxel.
3. Loaded the original CT and each mask in Slicer. Compared Slicer's IJK-to-RAS matrices with the source NIfTI affine and checked dimensions. Compared mask byte hashes after explicitly converting Nibabel's IJK array order to Slicer's KJI order.
4. Imported the masks into one named Slicer segmentation. Compared every segment against the original mask on the CT grid with exact voxel equality.
5. Saved `cardiac.seg.nrrd`, reopened it in Slicer, and verified exact voxel hashes for all six segments again.
6. Captured each structure separately in axial, coronal, and sagittal views, then captured combined views and Slicer's native 3D display. All 18 individual slice captures, the four-up view, and the native 3D image were visually inspected. No obvious global shift, flip, or scale mismatch was seen. This is a technical sanity check, not expert anatomical review or clinical validation.
7. Rechecked all 117 original mask hashes and the CT hash after review. The original MONAI segmentation, overlay, and report also retained their previous hashes.

Review points are actual foreground voxels nearest each structure's centroid, so a point cannot fall in the gap between disconnected vessels. Slicer fits each view before setting its slice position, then asserts that the selected point lies in the captured plane. These checks address issues found during initial capture attempts; the final evidence directory below contains the corrected captures. Earlier captures under `results/slicer/PUBLIC-001-totalseg-B/` are superseded.

Slicer's own closed-surface representation was enabled solely for visual review, with smoothing factor zero. No HeartAI reconstruction algorithm, GLB/STL export, quantitative measurement pipeline, backend, or frontend was added. The saved segmentation is a binary-labelmap artifact.

## Evidence and reopening

Final output root: `results/slicer/PUBLIC-001-totalseg-B-final/`.

| Artifact | Contents |
| --- | --- |
| `cardiac_subset.json` | Full actual inventory/hashes, six selected masks, label IDs, colors, geometry, component checks, and review points |
| `review_summary.json` | Completed technical/visual review record, limitations, and hashes of the 20 inspected images |
| `slicer/verification.json` | Executed Slicer geometry/voxel/round-trip checks and actual review positions |
| `slicer/cardiac.seg.nrrd` | Six named cardiac segments, preserving original voxels |
| `slicer/review.mrb` | Saved Slicer session containing the source CT and cardiac segmentation |
| `slicer/four_up.png` | Axial/coronal/sagittal CT overlays plus native 3D display |
| `slicer/<structure>_<plane>.png` | Individual structure captures in three planes |
| `stdout.txt`, `stderr.txt` | Slicer process logs |

Open `slicer/review.mrb` with Slicer's **Add Data** in a new/empty session. Alternatively load the source CT and `cardiac.seg.nrrd` together. The six segment names use the original TotalSegmentator class names and retain label-ID tags. No licensed task is needed to inspect these existing results.

## Reproduce

From the repository root, using the Milestone A environment and an installed Slicer. Select a **new output directory**: both preparation and Slicer review refuse to overwrite their results.

```powershell
.\.venv-totalseg\Scripts\python.exe scripts/prepare_totalseg_review.py results/cases/PUBLIC-001-totalseg results/slicer/PUBLIC-001-totalseg-B-rerun
$env:HEARTAI_TOTALSEG_REVIEW = Join-Path (Get-Location) 'results/slicer/PUBLIC-001-totalseg-B-rerun/cardiac_subset.json'
$env:HEARTAI_SLICER_EXIT = '1'
$reviewScript = Join-Path (Get-Location) 'scripts/review_totalseg_in_slicer.py'
Start-Process -FilePath 'C:\Users\Ahmad Soboh\AppData\Local\slicer.org\3D Slicer 5.12.4\Slicer.exe' -ArgumentList @('--no-splash', '--ignore-slicerrc', '--python-script', ('"' + $reviewScript + '"')) -WindowStyle Hidden -Wait
```

Use the actual local Slicer installation path on another machine. Run `review_totalseg_in_slicer.py` only in Slicer's Python runtime; do not install the HeartAI environment into Slicer. `HEARTAI_SLICER_EXIT=1` closes only the newly launched review process after saving. An optional `HEARTAI_SLICER_REVIEW_OUTPUT` chooses a fresh capture directory; leave it unset for the default `slicer/` subdirectory.

The Slicer script's verification status deliberately remains `technical_checks_passed_visual_review_pending` because a successful automated import cannot certify a visual inspection. Inspect the newly captured images separately. This run's completed inspection is recorded in `review_summary.json`; rerunning does not automatically copy that sign-off.

The desktop-control helper could not initialize (`failed to write kernel assets`), so this check used the actual installed Slicer application and its [supported Python segmentation API](https://slicer.readthedocs.io/en/latest/developer_guide/script_repository/segmentations.html), launched as a separate process. The evidence images came from Slicer's Screen Capture module, not a substitute renderer. The final Slicer run completed without a traceback.

For later debugging: if Slicer shows correct alignment but HeartAI does not, investigate HeartAI's viewer/spatial conversion. If both display poor segmentation, investigate the model/input. Neither comparison establishes clinical accuracy.

**Ready for Milestone C** with the recorded boundary/component limitations. No later milestone has been started.
