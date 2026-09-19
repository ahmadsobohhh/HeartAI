# Public demo scan

The successful demo uses **CTACardio**, distributed through 3D Slicer's built-in Sample Data module. This is a real public CTA scan with heart coverage, not a generated image or a ground-truth mask.

- [Official Sample Data registration](https://github.com/Slicer/Slicer/blob/main/Modules/Scripted/SampleData/SampleData.py) registers `CTACardio`, filename `CTA-cardio.nrrd`, and the checksum below.
- [Immutable SlicerTestingData download](https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/3b0d4eb1a7d8ebb0c5a89cc0504640f76a030b4e869e33ff34c564c3d3b88ad2).
- SHA-256: `3b0d4eb1a7d8ebb0c5a89cc0504640f76a030b4e869e33ff34c564c3d3b88ad2`.
- [Slicer maintainer guidance about reuse of distributed sample data](https://discourse.slicer.org/t/using-3d-slicer-sample-cts-for-a-publication/33260) points to the [Slicer license](https://github.com/Slicer/Slicer/blob/main/License.txt). [The CTACardio-specific provenance discussion](https://discourse.slicer.org/t/reference-of-cta-cardio-in-master-thesis/33366) directs users to this guidance. Cite 3D Slicer when reusing the sample.

This project uses the public sample as provided. We do not claim independently verified acquisition details, an ECG-gated protocol, original patient provenance, or a de-identification audit beyond its public Slicer distribution. No patient information is inferred.

## Conversion and geometry

`scripts/download_assets.py` stores the original NRRD in `data/raw/CTA-cardio.nrrd`, then uses SimpleITK 2.4.0 to write `data/demo/CTA-cardio.nii.gz`. Conversion changes file format only: no cropping, intensity changes, or resampling. A round-trip check compares every voxel and the physical grid. SimpleITK handles LPS/RAS conventions during NIfTI writing; the inference loader uses the resulting NIfTI affine.

Verified NIfTI geometry:

- Shape: 512 × 512 × 321.
- Spacing: 0.9335939884 × 0.9335939884 × 1.25 mm.
- Nibabel axis codes: L, P, S.
- Intensity range: -1024 to 3532.
- Affine diagonal: -0.9335939884, -0.9335939884, 1.25.
- Affine translation: 238.5332642, 238.5332642, -200 mm.

The converted NIfTI and all raw data are Git-ignored and reproducibly generated from the pinned source. Inference accepts only NIfTI; the NRRD converter is specific to demo preparation, not DICOM support.

## Initial input check

An initial trial used the [TotalSegmentator public test CT](https://github.com/wasserth/TotalSegmentator/blob/bf691a6b22acba1ee1d5a75585755023bec2c367/tests/reference_files/example_ct.nii.gz). It was predominantly abdominal, with inadequate heart coverage, so it was rejected for the cardiac milestone. The reproducible demo downloads CTACardio instead. No pre-existing labelmap was used as a prediction or model input.
