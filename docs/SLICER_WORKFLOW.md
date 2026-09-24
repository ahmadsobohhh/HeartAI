# HeartAI: Slicer review and correction workflow

Status: technical round trip tested, September 20, 2026. Real import, no-edit export, deliberate one-voxel edit, rebuild, and saved-session reopening passed. The current workflow still uses scripts; a technician-facing Slicer module and structured review controls remain planned. See [setup](SLICER_SETUP.md), [validation evidence](SLICER_VALIDATION.md), and the [complete application build specification](../HEARTAI_BUILD_SPEC.md).

## 1. Architecture decision

Use **3D Slicer as the primary imaging workspace**. Install **SlicerHeart as an extension** for cardiac workflows that need it. Continue using HeartAI's Python pipeline for pretrained inference, reproducible reconstruction, and measurements.

| Component | Responsibility in this workflow |
| --- | --- |
| 3D Slicer | Load the original CT and segmentation; inspect image slices and 3D anatomy; edit labels; save the review session |
| SlicerHeart | Additional cardiac modules, such as valve analysis and device-planning tools, when their required inputs are available |
| HeartAI | Run the verified checkpoint; preserve model provenance; validate returned labels; regenerate measurements, meshes, and previews |
| Existing web application | Optional access to generated results; further cosmetic development is deferred |

SlicerHeart runs inside Slicer; it is not an alternative application or the segmentation model. Basic CT inspection and correction use Slicer's built-in tools. The first integration must work even without SlicerHeart installed. Installing either application does not establish clinical accuracy or provide missing valve labels.

## 2. Scope and first acceptance milestone

Complete one reproducible round trip using the existing public CTACardio case:

```text
Original CT + immutable AI prediction
                  |
                  v
Slicer: inspect axial / coronal / sagittal slices and 3D surfaces
                  |
                  v
Save a separately editable cardiac segmentation
                  |
                  v
Review and correct; save a named revision
                  |
                  v
HeartAI: validate labels and physical geometry
                  |
                  v
Rebuild revision-specific meshes, measurements, and overlay
```

No training or fine-tuning. Keep the verified 3 mm checkpoint for this first round trip. A 1.5 mm comparison is a separate inference experiment so that model changes are not confused with correction/export errors. DICOM ingestion, simulation, and specialized valve workflows are later milestones.

## 3. Existing inputs

Use case `788812d5bc03`, if still available under `results/cases/`, or another completed case manifest. That case was produced by a real browser upload of the public Slicer CTACardio scan.

Read artifact locations from the manifest rather than assuming every input has the same extension:

- Original volume: manifest `artifacts.input`, commonly `input/scan.nii.gz`.
- Original prediction: `segmentation/prediction.nii.gz`.
- Model name, version, checkpoint hash, input hash, geometry, and warnings: `manifest.json` and `inference_report.json`.

The prediction contains the whole-body model's labels. The review workspace will extract only these supported cardiac labels into a new editable segmentation:

| Original label ID | HeartAI name | Display name |
| --- | --- | --- |
| 7 | aorta | Aorta |
| 44 | myocardium | Myocardium |
| 45 | left_atrium | Left atrium |
| 46 | left_ventricle | Left ventricle |
| 47 | right_atrium | Right atrium |
| 48 | right_ventricle | Right ventricle |
| 49 | pulmonary_artery | Pulmonary artery |

Use `src/heartai/structures.py` as the implementation's source of label IDs, names, and colors. An absent prediction must be reported as absent. The untouched original full labelmap remains available for provenance.

## 4. Slicer setup and case loading

1. Install an official stable 3D Slicer release. Record the exact version and revision used for testing.
2. Optionally install SlicerHeart through Extension Manager with its dependencies, restart, and record its installed revision. It is needed only when testing a specific cardiac module.
3. Load the original CT as a scalar volume. Load the prediction explicitly as a labelmap and convert the selected cardiac labels into a Slicer segmentation; do not treat the prediction as a grayscale CT or as an editable surface mesh.
4. Assign stable segment identities, display names, colors, and original numeric label IDs through a mapping owned by the integration.
5. Set the original CT as the source/reference geometry and open a four-up layout: three orthogonal slice views plus a 3D view.
6. Check alignment and left/right orientation using the volume's physical coordinates before making edits. The CT and prediction must occupy the same physical space without a manual registration transform.

Start with a Slicer Python script that opens one case. Add a small Slicer module only after the scripted import/export path passes its checks. Avoid building a second inference environment inside Slicer: initially, inference runs in HeartAI's existing Python environment, and Slicer consumes its completed files.

## 5. Review procedure

The reviewer inspects the original CT beneath segmentation outlines/fills in all three planes. Use 3D surfaces as a supplementary view. Check structures individually, their boundaries, missing regions, disconnected regions, and scan-boundary clipping. The existing demo's clipped aorta and disconnected left-ventricle components must remain visible as review items.

Corrections occur in Segment Editor on a new segmentation. Save a baseline copy before editing. Record which structures were reviewed, what was changed, unresolved concerns, and whether this is a technical demonstration or a review by an appropriately qualified person.

Surface-display smoothing and edits to the voxel segmentation are different operations. A display setting must not silently alter the measured labelmap. Any operation that changes labels, including segmentation smoothing or component removal, creates a new revision and requires remeasurement.

For the technical round-trip test, make a small deliberate edit on a copy of the public scan's prediction. Label it **test edit**, not an anatomical correction or expert-validated result.

## 6. Export contract and spatial checks

Save two complementary artifacts:

- `review.seg.nrrd`: Slicer-native editable segmentation, preserving segment metadata.
- `cardiac_labels.nii.gz`: a single-channel cardiac-only labelmap for HeartAI, using original IDs 7 and 44–49, with background 0, on the original CT grid.

Do not rely on Slicer's segment order to determine exported numeric labels. The integration must explicitly map stable segment identities to the original label IDs. Renaming a segment in the UI must not change its meaning. Unknown or duplicated mappings must stop the export.

Slicer can represent overlapping segments, whereas this V1 labelmap cannot. Detect overlap before conversion and require it to be resolved. Do not silently discard overlapping voxels based on segment order. Export using the complete reference CT extent rather than a cropped extent.

Before accepting a revision, HeartAI must check:

- Parent case and original CT hash match the review package.
- Shape, orientation, voxel spacing, affine, and millimeter units match the original CT; geometry differences must produce an explicit error.
- Values are finite integers and belong to the declared cardiac mapping plus background.
- No label was silently renumbered or lost during conversion.
- At least one supported structure remains; empty/removed structures are explicitly recorded.
- No unresolved parent transform changes the relationship between the CT and segmentation.

Account explicitly for RAS/LPS representation differences when reading/writing formats. Compare physical coordinates using the image libraries, not raw header strings. A segmentation NIfTI is the input to measurements; GLB coordinates in Y-up meters are not a source for medical-image geometry.

## 7. Revision storage and provenance

Proposed additions under each existing case; none replace the original artifacts:

```text
results/cases/<case_id>/
  manifest.json                         existing AI result
  segmentation/prediction.nii.gz        immutable original prediction
  reviews/<revision_id>/
    review.json
    review.seg.nrrd
    cardiac_labels.nii.gz
    measurements.json
    meshes/
    previews/overlay.png
```

The revision record must include its parent case/revision, original input and prediction hashes, output hashes, UTC timestamps, Slicer and extension versions, label mapping, reviewer identifier, review scope, purpose, notes, changed-voxel counts per structure, unresolved warnings, and processing status.

Keep technical processing status separate from human review state. A revision can be `draft`, `reviewed`, or `rejected`; `reviewed` records a human action and is not a claim of clinical validation. A successful export or mesh build must never automatically mark a result reviewed.

Stage incomplete writes in a temporary revision directory and publish only after successful validation. Retrying must not overwrite an existing revision. Failed revisions must not appear as completed results.

## 8. Implementation sequence and verification gates

| Step | Deliverable | Required evidence before continuing |
| --- | --- | --- |
| A | Slicer installation/version check and case-loading script | Real CT and correctly named cardiac labels visibly align in all three slice views |
| B | Explicit export mapping and revision writer | No-edit round trip preserves every cardiac voxel and the original physical geometry |
| C | HeartAI entry point for rebuilding from a supplied segmentation | Reconstruction and measurements run without invoking inference; original case hashes remain unchanged |
| D | Edited round trip | Deliberate test edit changes exactly the intended label voxels and the corresponding measurement/export |
| E | Human review record and repeatable instructions | Saved session/revision reopens with correct labels; warnings, provenance, and review state persist |

For C, extract reusable reconstruction/measurement code from `analyze_case()` without changing `segment_scan()`. The original CLI and API behavior must continue to pass their existing tests.

Meaningful automated tests should cover label-ID preservation, affine/axis mistakes, nontrivial spacing/orientation, overlap detection before export, altered reference CT, missing segments, unexpected labels, revision overwrite prevention, no-edit equality, and the known-volume change from a synthetic edit. Run Slicer-specific checks in its Python runtime and the existing numerical checks in HeartAI's environment.

## 9. Completion criteria and subsequent decisions

This milestone is complete when a real case can be opened, inspected, saved without changes, deliberately edited, returned, rebuilt, and reopened with correct geometry and traceable versions. Record observed results and remaining limitations in a validation report. Do not describe this design document as a working integration.

Afterward, choose the first specialized cardiac task with a domain expert. Determine whether an existing SlicerHeart module fits it and what additional labels/landmarks it requires. Do not infer valve anatomy or congenital-defect support from the current seven classes. Clinical deployment, regulatory assessment, and comparative model evaluation remain separate workstreams.

## Official references

- [3D Slicer Segment Editor](https://slicer.readthedocs.io/en/latest/user_guide/modules/segmenteditor.html): editing workflow and segmentation geometry.
- [3D Slicer Segmentations](https://slicer.readthedocs.io/en/latest/user_guide/modules/segmentations.html): segmentation representations and import/export.
- [SlicerHeart](https://slicerheart.org/): installation and cardiac scope.
- [SlicerHeart source and modules](https://github.com/SlicerHeart/SlicerHeart).
- [HeartAI model verification](MODEL.md): actual supported labels, preprocessing, and resolution limitations.
