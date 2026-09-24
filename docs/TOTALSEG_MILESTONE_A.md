# Milestone A — real TotalSegmentator proof

Completed on 2026-09-20. Stopped at Milestone A: official pretrained inference, output inspection, and a real CT overlay. No model training/fine-tuning, meshes, frontend, backend, or licensed cardiac task were implemented for this checkpoint.

## Executed run

| Item | Observed value |
| --- | --- |
| Engine | TotalSegmentator 2.18.0 |
| Supporting runtime | Python 3.12.5, PyTorch 2.14.0+cpu, nnUNetv2 2.8.1 |
| Task | `total`, standard 1.5 mm model, `fast=false`, no ROI subset |
| Models | Pretrained datasets 291, 292, 293, 294, 295; fold 0; `nnUNetTrainerNoMirroring` |
| Device | CPU; CUDA unavailable |
| Public input | `data/demo/CTA-cardio.nii.gz`, Slicer CTACardio |
| Input SHA-256 | `d8b3846d2784d9bc8d2611b820183c7edee0c338fb7634b2e5eac89645120709` |
| Original/output grid | 512 × 512 × 321; 0.9335939884 × 0.9335939884 × 1.25 mm; LPS voxel-axis orientation |
| CLI process elapsed | **501.8101535 seconds**, including first-use downloads, startup, inference, and saving; excludes the separate inspection/overlay command |
| Upstream API elapsed | 499.34 seconds, measured inside TotalSegmentator |
| Prediction stage | 378.10 seconds, as printed by TotalSegmentator |
| Saving stage | 35.23 seconds, as printed by TotalSegmentator |
| Output files | **117 binary NIfTI masks; 88 nonempty, 29 empty** |
| Output directory | `results/cases/PUBLIC-001-totalseg/` |
| Weight cache | `models/totalsegmentator/nnunet/results/` |

Model/task configuration was read from the installed package, not inferred from older TotalSegmentator versions. `validation.json` records the actual checkpoint paths and SHA-256 hashes. The checkpoint trainer name describes the upstream pretrained artifact; no training ran locally. CPU inference uses the installed upstream implementation, which sets PyTorch threads to the logical CPU count (12 here); the runner records its OMP/MKL environment separately.

Exact reproducible wrapper commands, from the repository root:

```powershell
.\.venv-totalseg\Scripts\python.exe scripts/run_totalseg.py data/demo/CTA-cardio.nii.gz --output-dir results/cases/PUBLIC-001-totalseg --device cpu
.\.venv-totalseg\Scripts\python.exe scripts/inspect_totalseg.py results/cases/PUBLIC-001-totalseg
```

The recorded directory already exists. Choose a fresh directory for another inference run; overwrite protection deliberately refuses the command above against the existing proof. Re-inspection of the existing directory is supported. Installation and optional pre-download instructions are in [README](../README.md#reproduce-milestone-a).

The wrapper executed the following official CLI module with absolute paths (the complete argument list is retained in `run.json`):

```powershell
.\.venv-totalseg\Scripts\python.exe -u -m totalsegmentator.bin.TotalSegmentator -i data/demo/CTA-cardio.nii.gz -o results/cases/PUBLIC-001-totalseg/segmentations --task total --device cpu --nr_thr_resamp 1 --nr_thr_saving 1 --report results/cases/PUBLIC-001-totalseg/upstream_report.json
```

The wrapper sets `TOTALSEG_HOME_DIR` to the repository's `models/totalsegmentator` unless overridden, and sets `OMP_NUM_THREADS=6` and `MKL_NUM_THREADS=6` for the child environment. For identical cache selection when calling the module directly, set `TOTALSEG_HOME_DIR` as shown in README. The official run report confirms `license_required=false`, `device=cpu`, `fast=false`, `fastest=false`, and `roi_subset=null`.

## Real cardiac output

These are actual nonempty masks, using IDs from this installation's `total` map:

| ID | Filename under `segmentations/` | Foreground voxels | Reaches CT boundary |
| --- | --- | ---: | --- |
| 51 | `heart.nii.gz` | 454,365 | No |
| 52 | `aorta.nii.gz` | 122,460 | Yes, inferior slice 0 |
| 53 | `pulmonary_vein.nii.gz` | 18,584 | No |
| 61 | `atrial_appendage_left.nii.gz` | 4,501 | No |
| 62 | `superior_vena_cava.nii.gz` | 15,118 | No |
| 63 | `inferior_vena_cava.nii.gz` | 23,403 | No |

The entire installed map is in `installed_label_map.json`; `validation.json` lists every output class and its foreground count, including the empty masks. Additional vascular and thoracic classes remain in the full output inventory. The six names above form the small inspection selection, not a replacement for the original 117 masks.

**Unavailable as separate labels in this task:** pulmonary artery, myocardium, left/right atria, left/right ventricles. Do not substitute the legacy MONAI chamber masks into this result or relabel pulmonary veins as pulmonary artery. `heartchambers_highres` was not downloaded or executed.

## Validation and preview

- The CLI exited successfully; official help and class-list commands worked; `pip check` found no broken requirements.
- All 117 masks were opened and checked against the CT: identical shape, matching affine with absolute tolerance 0.0001, finite binary 0/1 data. Every mask is uint8.
- Heart and aorta foreground were required for validation success. All six selected cardiac masks were also checked for foreground bounds and boundary contact.
- Real-data guard checks accepted the real heart mask, rejected an intentionally shifted header (1 mm), rejected CT intensities as a binary mask, and verified an exact lossless canonical-orientation round trip. These checks wrote no altered anatomical outputs. Results are in `validation_checks.json`.
- The preview displays actual CT alongside actual masks at canonical RAS axial slices **169, 194, 218**, selected from the heart's occupied slice range. Reorientation only permutes/flips axes; it does not resample or move anatomy independently. Physical in-plane spacing is respected, with left/right/anterior/posterior markers. Window [-160, 240] HU is for display only.
- `previews/cardiac_overlay.png` was opened and visually inspected. Visible heart/aorta/pulmonary-vein masks show gross alignment with the underlying CT. This is a spatial sanity check, not expert anatomical review or ground-truth accuracy validation.

The original MONAI environment remains PyTorch 2.4.1+cpu / MONAI 1.4.0. Its loading/inference tests passed (**8 passed, 2 integration tests deselected**). The original `results/segmentations/CTA-cardio.nii.gz`, `results/overlays/CTA-cardio.png`, and `results/reports/CTA-cardio.json` retained their SHA-256 hashes. Existing source, case outputs, meshes, and application work were preserved.

## Warnings and next checkpoint

The TotalSegmentator log contains a PyTorch `torch.jit.interface` deprecation warning; it did not prevent execution. Legacy MONAI tests emitted existing Matplotlib/Pyparsing deprecation warnings. No inference error occurred.

The aorta is incomplete at the inferior field-of-view boundary. The 29 empty class files do not represent detected anatomy, and the 88 nonempty predictions do not establish anatomical accuracy. No ground-truth scores or clinical measurements are claimed. There is no clinical validation.

**Milestone A is proven working.** The real CT, masks, label inventory, logs, checkpoint hashes, and inspected overlay are ready for Milestone B's independent cardiac sanity check in 3D Slicer. That TotalSegmentator Slicer review has not been performed here; prior MONAI Slicer work is not evidence for this new result. No later milestone was started.

Attribution: [TotalSegmentator](https://github.com/wasserth/TotalSegmentator), [TotalSegmentator paper](https://pubs.rsna.org/doi/10.1148/ryai.230024), and [public Slicer CTACardio provenance](DATA.md).
