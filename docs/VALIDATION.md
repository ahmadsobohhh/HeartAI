# Milestone 1 execution record

Executed on Windows with Python 3.12.5, MONAI 1.4.0, PyTorch 2.4.1+cpu, four CPU threads, and approximately 32 GB installed RAM. AMD Radeon graphics were detected; CUDA was unavailable. No GPU acceleration is claimed.

## Successful real inference

- Model: unchanged official MONAI `model_lowres.pt`; verified SHA-256 recorded in the run report.
- Input: public Slicer CTACardio, converted without resampling to NIfTI.
- Original and saved output shapes: **512 × 512 × 321**.
- Preprocessed tensor: **1 × 160 × 160 × 134**.
- Network logits: **1 × 105 × 160 × 160 × 134**.
- First successful CTACardio inference: **11.6237 s**; complete load-to-overlay pipeline: **25.6142 s**.
- Output labels include all seven requested cardiac structures, retaining official class IDs.
- Output is uint8 NIfTI with the original grid, spacing, affine, qform and sform.
- Inspected RAS axial slices **164, 190, 216** in the generated three-column figure. Predictions occupy the corresponding heart and vessel regions without a gross orientation or translation mismatch. Boundaries are coarse, especially at vessels; this is visual alignment inspection, not expert annotation or an accuracy evaluation.
- A second real CPU inference in the integration test matched the saved labelmap voxel-for-voxel.

## Checks

- Eight synthetic loading/saving tests: pass.
- Official preprocessing/inversion on a non-RAS anisotropic synthetic volume: pass.
- Real pretrained inference/output-shape integration test: pass.
- `pip check`: no broken requirements.
- Asset download script: verified all cached source hashes and checked lossless NRRD-to-NIfTI conversion.

The first attempt exposed a missing optional progress-bar dependency; `tqdm` is now explicitly pinned. A test initially passed a Torch affine to a NumPy-only spacing helper; the test now explicitly converts it to NumPy. Neither issue required changing model weights or upstream preprocessing. Matplotlib emits deprecation warnings through the installed PyParsing version; these do not affect output.

## Limits

No ground-truth score, clinical validation, congenital cardiac validation, high-resolution checkpoint run, or GPU run was performed. Restoring the native output grid does not restore detail lost at the model's 3 mm inference resolution. The project stops at segmentation and visual inspection. No training, meshes, measurements, APIs, or web UI were added.
