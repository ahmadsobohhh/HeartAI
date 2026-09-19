# Verified pretrained model

Verified directly against the official MONAI bundle, including configuration, metadata, license, and actual checkpoint loading.

| Item | Verified value |
| --- | --- |
| Name | Whole Body CT Segmentation (`wholeBody_ct_segmentation`) |
| Bundle version | 0.2.7 |
| Publisher | MONAI team / MONAI Consortium |
| Architecture | 3-D SegResNet, one input channel, 105 output channels, 32 initial filters, down blocks [1,2,2,4], up blocks [1,1,1], dropout 0.2 |
| Selected checkpoint | Published low-resolution 3 mm `models/model_lowres.pt` |
| License | Apache License 2.0, supplied in the official bundle; training data retain their separate licenses |
| Modality / format | CT intensities in a scalar 3-D NIfTI volume |
| Scope | 104 whole-body structures plus background; trained upstream on TotalSegmentator |
| Local checkpoint | `models/wholeBody_ct_segmentation/models/model_lowres.pt` |
| SHA-256 | `c3ab55eb979785fdcb30690872c210bbeee73d79a170c32fdaa1eca117779f90` |

## Primary sources and immutable revision

- [Official MONAI Model Zoo entry](https://github.com/Project-MONAI/model-zoo/tree/dev/models/wholeBody_ct_segmentation)
- [Official hosted bundle at pinned revision](https://huggingface.co/MONAI/wholeBody_ct_segmentation/tree/13f6d33ae9de6664571d935ee647039f477c3fad)
- [Inference configuration](https://huggingface.co/MONAI/wholeBody_ct_segmentation/blob/13f6d33ae9de6664571d935ee647039f477c3fad/configs/inference.json)
- [Metadata and complete class map](https://huggingface.co/MONAI/wholeBody_ct_segmentation/blob/13f6d33ae9de6664571d935ee647039f477c3fad/configs/metadata.json)
- [Model documentation](https://huggingface.co/MONAI/wholeBody_ct_segmentation/blob/13f6d33ae9de6664571d935ee647039f477c3fad/docs/README.md)
- [License](https://huggingface.co/MONAI/wholeBody_ct_segmentation/blob/13f6d33ae9de6664571d935ee647039f477c3fad/LICENSE)
- [Checkpoint download](https://huggingface.co/MONAI/wholeBody_ct_segmentation/resolve/13f6d33ae9de6664571d935ee647039f477c3fad/models/model_lowres.pt)

The downloader preserves these upstream documents alongside the weights. `assets.json` pins every downloaded file by URL and SHA-256. Model loading verifies the checkpoint and configuration bytes, uses `torch.load(weights_only=True)`, and requires an exact state-dictionary match. We do not run upstream training scripts or instantiate optimizers.

## Cardiac classes

| Original class ID | Official name |
| --- | --- |
| 7 | aorta |
| 44 | heart_myocardium |
| 45 | heart_atrium_left |
| 46 | heart_ventricle_left |
| 47 | heart_atrium_right |
| 48 | heart_ventricle_right |
| 49 | pulmonary_artery |

The complete 0–104 mapping is copied unchanged into [labels.json](labels.json). These seven classes are supported directly; no missing class was fabricated. They do not imply support for valves, coronary arteries, congenital defects, or separate pulmonary branches.

## Exact preprocessing and inference

HeartAI parses the verified upstream `configs/inference.json` with MONAI's `ConfigParser` and selects `highres=false`. The actual transform objects come from that configuration:

1. `LoadImaged`: load image and metadata.
2. `EnsureTyped`: tracked tensor.
3. `EnsureChannelFirstd`: one image channel.
4. `Orientationd(axcodes="RAS")`.
5. `Spacingd(pixdim=[3,3,3], mode="bilinear")`: trilinear interpolation for a 3-D image.
6. `NormalizeIntensityd(nonzero=True)`: normalize nonzero voxels.
7. `ScaleIntensityd(minv=-1, maxv=1)`.

There is no custom HU clipping, foreground cropping, or augmentation. **The metadata describes a [0,1] range, but the executable inference configuration explicitly scales to [-1,1]. We follow the executable configuration.** Upstream documentation also contains a foreground-range typo (“1-105”); metadata and the network establish 104 foreground labels, IDs 1–104, with background 0.

Inference uses the original SegResNet in `eval()` mode, disabled gradients, unchanged weights, and the official sliding-window settings: 96³ patches, batch size 1, 0.25 overlap, Gaussian blending, replicate padding. CPU uses float32; CUDA uses automatic mixed precision as in the upstream evaluator. Full-volume logits accumulate on CPU to reduce GPU memory pressure. The selected device executes patch inference.

The official postprocessing applies softmax, argmax, and `Invertd` with nearest-neighbor interpolation, undoing resampling and orientation. HeartAI verifies native shape and affine, then saves uint8 labels with the input spacing, qform, sform, codes, and units. The only postprocessing replacement is the file writer, so we can enforce these checks and use stable output paths. No smoothing, class remapping, or connected-component cleanup is applied.

## Selection rationale and limits

This satisfies the preference for an official MONAI model and verifies all seven desired cardiac structures. The published 3 mm variant keeps the first CPU run small without substituting arbitrary downsampling for the model's expected spacing. The 1.5 mm checkpoint exists upstream but is not part of this milestone's tested path.

This is a general CT model, not a specialized validated cardiac or congenital model. Published upstream metrics are not measurements of HeartAI or this case. No training, fine-tuning, or accuracy claim is made. Framework versions are pinned in `requirements.txt`; MONAI matches the bundle's 1.4.0 requirement, while PyTorch uses the 2.4.1 patch release and NumPy 1.26.4 for Python 3.12 compatibility. Unused training/evaluator dependencies are omitted.
