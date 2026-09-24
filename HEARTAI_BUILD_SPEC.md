# HeartAI — complete application build specification

Date: September 20, 2026. Status: implementation plan, not a claim that every feature below exists.

## 1. The product we are building

A technician imports a supported cardiac CT, confirms the correct scan series, and clicks **Create heart**. HeartAI runs verified pretrained segmentation models and opens a patient-specific 3D reconstruction beside the original CT. A qualified reviewer can inspect, correct, save, and export the result.

The intended experience is:

```text
Open HeartAI in 3D Slicer
    → Import CT
    → Confirm series and cardiac phase
    → Check scan suitability
    → Choose available anatomy profile
    → Create heart
    → View CT + editable segmentation + 3D surfaces
    → Inspect/correct and record review
    → Save case and export selected revision
    → Reopen the same result later
```

**This is feasible. Automatically reconstructing every artery, tiny branch, valve, and defect from any CT is not a defensible product promise.** Only display anatomy supported by the selected model and visible enough in the source scan. Never fill missing anatomy with a generic heart or invented vessel branches.

This document specifies the complete target application and its release gates. It does not authorize training, purchasing licenses, sending scans to cloud services, or releasing a clinical product. Implement it in independently testable milestones, preserving the existing working pipeline.

## 2. Decisions and non-negotiable constraints

1. Use **3D Slicer as the primary technician and reviewer workspace**. Build a focused HeartAI module inside it.
2. Use SlicerHeart modules only for defined cardiac tasks with the required images, labels, and landmarks. Installing SlicerHeart does not supply missing segmentation classes. [Official SlicerHeart scope](https://slicerheart.org/).
3. Keep pretrained inference in HeartAI's separate Python environment. Do not install its ML dependency stack into Slicer's Python.
4. Reuse the existing inference, geometry, reconstruction, and measurements code. Keep the browser application as an optional results viewer; do not build a competing medical editor in React for this release.
5. No training, fine-tuning, modified weights, physics simulation, Newton, or Warp in this build.
6. Preserve original CTs and original predictions. All edits create traceable revisions.
7. Distinguish software success, human review, and clinical validation. None implies either of the others.
8. Use public/de-identified data during development. Do not add real patient data to Git, screenshots, logs, fixtures, or external services.
9. Use actual model outputs and measured timings. Do not fabricate accuracy, confidence, progress percentages, labels, or successful completion.

## 3. Current implementation: reuse this foundation

The repository already contains:

| Capability | Current evidence / limitation |
| --- | --- |
| CT inference | Official MONAI wholeBody_ct_segmentation 0.2.7, unchanged 3 mm checkpoint |
| Cardiac anatomy | Aorta, myocardium, left/right atria, left/right ventricles, pulmonary artery |
| Geometry | NIfTI spatial metadata preserved; physical meshes and voxel measurements |
| Application | CLI, local FastAPI service, Next.js/Three.js browser viewer |
| Slicer bridge | Real CT and seven editable masks load in Slicer; revision exports rebuild without inference |
| Tests | Forty non-integration Python tests passed at this checkpoint; real no-edit and one-voxel Slicer round trips verified |
| Installed workstation | Slicer 5.12.4 with SlicerHeart; current inference uses CPU |

Read `CODEX.md`, `CODEX2.md`, `README.md`, `docs/MODEL.md`, and the Slicer documentation before implementation. Follow the user's current instructions when older documents describe a superseded order or interface. Inspect actual code and rerun relevant checks rather than assuming the table remains current.

Existing entry points include `src/heartai/pipeline/analyze.py`, `src/heartai/pipeline/review.py`, `src/heartai/slicer_package.py`, and `scripts/open_slicer_case.py`. Actual Slicer evidence is in [docs/SLICER_VALIDATION.md](docs/SLICER_VALIDATION.md).

## 4. Define what “the heart and all the arteries” means

| Anatomy | First product commitment | Additional work |
| --- | --- | --- |
| Four chambers and myocardium | Supported predicted structures with review/correction | Evaluate finer pretrained models |
| Aorta and main pulmonary artery | Supported within the scan's field of view | Flag truncation; do not imply whole-vessel coverage |
| Coronary artery tree | Required for an eventual **Heart + coronaries** profile | Dedicated pretrained model, suitable scans, license verification, and evaluation |
| Named RCA, left main, LAD, LCx | Not implied by a single coronary-tree mask | Separately validated labeling method or explicit human labeling |
| Tiny distal branches | No completeness guarantee | Define a supported vessel size/territory and measure coverage |
| Pulmonary veins, venae cavae, separate pulmonary branches | Optional future profile | Verify each class and evaluate the corresponding model |
| Valve leaflets, chordae, septal defects, congenital anatomy | Outside the initial automatic claim | Separate imaging/annotation/model and expert validation workstream |
| Coronary stenosis, plaque, flow, treatment planning | Outside this build | Separate intended use and evidence requirements |

The interface must distinguish **not supported**, **not requested**, **not detected**, **failed**, and **reviewed**. An empty mask must not be described as proof that anatomy is absent. A named vascular structure must retain the identity supplied by its model or human annotation; proximity alone is insufficient to name a branch.

## 5. Scan quality and resolution

The initial product target is supported adult cardiac CT/CTA for research reconstruction. Pediatric and congenital performance are separate evaluation populations; do not assume adult-model performance transfers.

For coronary development, use an appropriately acquired cardiac CTA selected with an imaging specialist. Admission criteria must address cardiac motion, contrast, reconstruction spacing, field of view, and artifacts. This software specification is not a CT acquisition prescription.

Keep these three values distinct in both manifests and the UI:

- **Source resolution:** information present in the acquired/reconstructed CT.
- **Model inference spacing:** the model's required grid.
- **Display/export spacing:** the grid or mesh used to show results.

A 1.5 mm model can be evaluated for chamber boundaries, but that spacing alone does not establish coronary capability. Resampling a coarse prediction to 0.5 mm or smoothing its surface cannot recover unpredicted arteries. Never substitute prettier surfaces for accuracy evidence.

The official MONAI bundle offers separate 3 mm and 1.5 mm pretrained configurations/checkpoints. Evaluate the matching high-resolution weights and preprocessing together; changing only the spacing is invalid. See [upstream bundle documentation](https://github.com/Project-MONAI/model-zoo/blob/dev/models/wholeBody_ct_segmentation/docs/README.md) and [local verification](docs/MODEL.md).

The existing CTACardio case is a pipeline regression scan, not ground truth for coronary completeness or model accuracy.

## 6. Pretrained model selection and licenses

Keep the tested MONAI profile as the reproducible baseline. Compare alternatives in isolated environments before changing the application default.

As checked on September 20, 2026, the official TotalSegmentator repository lists `heartchambers_highres` for seven cardiac structures and `coronary_arteries` for a single coronary-artery class. Both appear under license-gated tasks, with non-commercial and commercial licensing paths. They are candidates, not models already tested in HeartAI. The coronary task does not establish separate named-branch labels. Verify the exact selected release, weights, and permitted use before integration. [Official task and license listing](https://github.com/wasserth/TotalSegmentator#subtasks).

For every candidate, create a model record containing:

```text
provider, task, version, immutable source revision
checkpoint URL or approved acquisition procedure and SHA-256
code license, weight license, commercial/redistribution conditions
modality, intended population, input requirements
exact class map and absent capabilities
official preprocessing, inference, and postprocessing
model grid, native output grid, coordinate conventions
runtime/dependency lock, device, measured RAM/VRAM/time
evaluation evidence, known failure modes, deployment eligibility
```

Do not infer weight rights from a code repository's license. Do not store license keys in manifests or source control. If a desired model requires a license the owner has not provided, finish the independent baseline work and report that specific blocker. Do not bypass restrictions or silently replace the task with a less capable model.

No model becomes the default merely because its grid is finer or its demonstration looks better. Use the evaluation gate in section 13.

## 7. Architecture

```text
3D Slicer + HeartAI module
  Import / series selection / Create heart / review / save
                 |
                 v
Local HeartAI job service → persistent job/case store
                 |
                 v
Isolated pretrained inference worker(s)
                 |
                 v
Native-grid masks + model provenance + quality findings
                 |
                 v
Shared reconstruction / measurements / revision validation
                 |
        +--------+--------+
        v                 v
Slicer workspace    Optional browser results viewer
```

The local service owns jobs and immutable artifacts; Slicer owns interactive image review. Reuse existing FastAPI contracts when practical. Keep dependency-incompatible model families in separate worker environments with versioned input/output contracts. Exchange artifact paths and structured manifests, not Python objects across environments.

Bind local services to loopback. Use a per-install/session authentication mechanism for new desktop integration endpoints, restrict file access to the configured case store, and validate all requests. Never construct shell commands from scan names or UI text; use structured argument lists. A network deployment is a separate deployment profile requiring authentication, authorization, transport protection, and operational review.

Start with a durable local job store such as SQLite and a bounded worker queue. Do not introduce a distributed queue or Kubernetes for the single-workstation build.

## 8. Technician interface requirements

Build `slicer/HeartAI/` as a scripted Slicer module, with a concise task-oriented panel:

1. **New case:** choose DICOM folder/series or NIfTI; show scan preview and identity summary appropriate to the deployment.
2. **Confirm scan:** show dimensions, spacing, selected series, phase if available, and suitability findings. Never silently choose among ambiguous series.
3. **Anatomy:** select an available, validated profile. Initially Basic heart; enable Heart + coronaries only after its gates pass. Explain unavailable profiles in plain language.
4. **Create heart:** submit a background job. Show actual stage, elapsed time, cancel/retry, and actionable errors. Keep Slicer responsive.
5. **Inspect:** automatically open aligned axial/coronal/sagittal CT views, colored masks, and 3D anatomy. Provide window/level, crosshair, structure visibility, opacity, isolate, reset, and source-slice navigation.
6. **Correct:** use core Segment Editor. Preserve structure identities and link every change to a revision.
7. **Review:** record reviewer, scope, unresolved findings, and decision. Do not precheck all structures as reviewed.
8. **Save/export:** choose a revision and export format. Show draft/review status. Reopen from the case list without terminal commands.

The 3D viewer must support seeing coronary vessels without the myocardium obscuring them, through hide/isolate/opacity controls. Provide clipping when useful. Display vessel surfaces from actual masks; do not create decorative tube branches.

The regular workflow must not require a Python console, manual path copying, multiple terminals, or hand-started servers. Those remain developer diagnostics only.

## 9. Ingestion and scan validation

Reuse Slicer's DICOM import and series selection rather than writing a slice sorter from filenames. Slicer represents DICOM's patient/study/series hierarchy and exposes geometry-related import findings. [Official DICOM documentation](https://slicer.readthedocs.io/en/latest/user_guide/modules/dicom.html).

Implement:

- NIfTI support retained for existing tests and reproducibility.
- Supported CT DICOM series selected explicitly; preserve provenance and required source references securely.
- Reject mixed patients/series, incomplete or inconsistent geometry, unsupported pixel types, and malformed data.
- Detect temporal/multiphase inputs. Select one phase explicitly; do not stack phases into the spatial axis. Unsupported enhanced/multiframe cases must fail clearly until tested.
- Verify physical orientation, spacing, affine, intensity conversion, and frame references. Record any intentional conversion/resampling.
- Use an admission result of `eligible`, `needs_review`, or `unsupported`, with reasons. Do not invent a model confidence score from simple image checks.
- Define required coverage and quality thresholds with an imaging expert before claiming automatic scan suitability.
- Import into a managed case store; copying/normalizing data must not modify the original files.

Privacy handling must include local DICOM caches, scene bundles, logs, previews, exports, backups, and crash reports, not just the uploaded file.

## 10. Jobs, model outputs, and anatomy composition

Processing states:

```text
queued → validating → preprocessing → segmenting
       → validating_outputs → reconstructing → ready_for_review
Any active state → failed or cancelled
```

Human review state is separate: `draft`, `reviewed`, or `rejected`. Require an explicit recorded human action for review status. Editing a reviewed revision creates a new draft.

Each anatomy profile declares its required model tasks. A coronary failure must leave the profile visibly partial/failed even if the chambers succeeded. Optional outputs can fail independently, but a required missing output cannot produce a complete-profile success message.

Adapters must restore outputs to a verified common source grid and retain their native provenance. A new model's numeric label IDs must not overwrite existing IDs by accident. Use a versioned semantic structure registry with explicit provider-to-structure mapping.

Keep chamber and coronary outputs separately traceable. The current single-label seven-structure export assumes mutually exclusive labels; do not force multiple model outputs into that format when anatomy overlaps. Introduce separate masks or Slicer segmentation layers with a documented overlap policy. Retain strict overlap rejection for formats that cannot represent it losslessly.

Retries create new run IDs. Never combine cached masks from different CTs, phases, model versions, or preprocessing settings. Validate cache keys against hashes and configuration. On restart, detect interrupted jobs and offer an explicit retry; do not show them as complete.

## 11. Reconstruction, measurements, and exports

Treat the accepted voxel masks as authoritative. Generate surfaces in physical coordinates; validate scale, orientation, finite vertices, and topology findings. A watertight mesh is not proof of correct anatomy.

Preserve unsmoothed source masks. Any display smoothing/decimation must be documented, reversible, and excluded from voxel volume calculations. Report scan-boundary truncation and disconnected components. Do not automatically delete small components that might be real vessels.

Initial measurements: segmented volume, centroid, and physical bounds with method and units. Do not label segmented blood-pool volume as cardiac function or produce ejection fraction from a single phase. Centerlines, vessel diameters, and branch lengths require separate validated implementations; no stenosis or flow claims.

Required export package:

```text
case_manifest.json
revision_manifest.json
segmentation/*.nii.gz        native CT grid, explicit labels
review.seg.nrrd              editable segmentation
session.mrb                 complete review workspace
meshes/*.glb and *.stl       declared transforms and units
measurements.json
previews/*.png
review_record.json
```

The manifest must identify every output's source run/revision and hash. Restore a portable package on another configured workstation without relying on this developer's absolute paths. Preserve original predictions alongside revisions. Never silently downgrade a reviewed export to a different revision.

DICOM SEG interoperability is a later export gate within the hospital-ready product; test reference UIDs, terminology, geometry, and round trips with the receiving system. Mesh exports alone do not substitute for image-linked segmentation.

## 12. Proposed repository additions

These are planned paths, not claims of existing modules:

```text
slicer/HeartAI/                 technician module and Slicer tests
src/heartai/ingestion/          scan admission and conversion records
src/heartai/models/             provider adapters and capability registry
src/heartai/jobs/               durable execution, cancellation, recovery
src/heartai/review/             portable revisions and review records
configs/profiles/              pinned Basic / Heart + coronaries profiles
tests/fixtures/                small synthetic and permitted test inputs
tests/acceptance/               real application workflow tests
docs/evaluation/               model comparison and failure reports
packaging/                     workstation setup and release checks
```

Avoid moving stable code merely to match the diagram. Extract shared functions when required, preserve current CLI/API behavior, and migrate manifests explicitly when schemas change.

## 13. Implementation milestones and acceptance gates

Complete and report one milestone at a time. Do not start a new major milestone when the current one has unresolved acceptance failures. Do not use long inference runs when a focused unit test answers the question.

### M0 — Preserve and inventory the working application

Read repository instructions, identify user changes, run existing relevant tests, and record the working demo and dependencies. Deliver a status checklist distinguishing implemented, tested, partial, and planned capabilities. Do not replace the functioning inference path.

**Pass:** existing demo artifacts remain intact; baseline test results and known limitations documented.

### M1 — Make the current Slicer workflow usable without a terminal

Build the HeartAI Slicer module, case list, NIfTI selection, Create heart action, background service/worker startup, progress, cancellation, and automatic result loading. Integrate draft save/rebuild controls. Start with the verified seven-structure profile.

**Pass:** a technician can import a real permitted CT, generate its segmentation, view aligned slices/3D, edit a mask, save a revision, close, and reopen it using only the UI. Test failure, cancel, retry, and service restart. No frozen Slicer UI or overwritten original.

### M2 — Add supported DICOM CT intake

Integrate explicit series/phase selection, geometry checks, admission findings, and conversion provenance. Include malformed, mixed-series, reversed orientation, and multiphase cases in tests.

**Pass:** at least one real permitted supported DICOM CT follows the same UI workflow with preserved physical alignment. Unsupported inputs fail clearly. This is an ingestion milestone, not proof of clinical suitability.

### M3 — Evaluate higher-detail cardiac and coronary candidates

Verify model rights and immutable artifacts. Benchmark the baseline, matching MONAI high-resolution option, and eligible dedicated candidates. Use identical source scans where appropriate. Measure runtime, peak memory, failures, and reviewer correction burden.

Create an evaluation plan before selecting a winner: target population/protocols, independent reference annotations, held-out cases, per-structure overlap and surface-distance metrics, and vascular continuity/coverage where applicable. Define acceptable thresholds with the intended users; do not choose them after inspecting results. Report all failures and subgroup limitations. A single attractive demo is insufficient.

**Pass:** written model-selection report, reproducible artifacts, license eligibility, and an approved capability profile. If evidence or permission is missing, keep the corresponding profile disabled and report the blocker. No training to bypass the gate.

### M4 — Integrate Heart + coronaries

Add the selected coronary adapter, common-grid checks, multi-model provenance, suitable mask representation, combined viewing, and clear partial-output states. Show unnamed coronary-tree output honestly if that is all the model supplies.

**Pass:** real suitable permitted CT generates both cardiac structures and predicted coronary vessels; both are aligned to source images and inspectable/editable. Test missing/fragmented vessel predictions and task failures. No claim that every branch is present.

### M5 — Complete review, portability, and export

Implement revision chaining, per-structure review scope, unresolved findings, explicit review decisions, review invalidation after edits, portable cases, and UI export. Complete deferred Slicer off-grid/out-of-extent rejection tests. Add DICOM SEG only after the receiving workflow is specified.

**Pass:** no-edit round trip preserves masks and geometry; known edits produce expected measurement changes; another workstation reopens the chosen revision; metadata/hashes identify the exact input, models, reviewer, and outputs. Clinical sign-off is not inferred from these tests.

### M6 — Package a dependable research application

Create one supported installation/start procedure with pinned dependencies, model/license preflight, health checks, bounded resource use, actionable logs, update/rollback, uninstall behavior, and backup/restore. Disable unnecessary model telemetry or document and explicitly configure approved behavior. Keep scans local by default.

Benchmark on the actual target hardware before publishing requirements. Define maximum supported scan sizes and expected performance ranges from measurements, not guesses. Verify low-memory, low-disk, interrupted job, unavailable model, expired/missing license, and corrupt-output behavior.

**Pass:** clean-workstation installation plus a technician usability test completes the full workflow without developer intervention. Research scope and unsupported anatomy remain visible. No silent network transfers.

### M7 — Commercial/clinical release preparation

Treat this as a separate release gate. Decide intended use, population, jurisdiction, purchasers, and claims with clinical and regulatory specialists. Medical-purpose software may fall within medical-device frameworks; the route depends on the actual intended use. [FDA SaMD overview](https://www.fda.gov/medical-devices/digital-health-center-excellence/software-medical-device-samd).

Establish the applicable quality/risk process, traceability from requirements to tests, independent clinical evaluation, human-factors evidence, cybersecurity review, controlled releases, support, incident response, and change management. Confirm licenses for redistributed code, weights, data, and dependencies. Add role-based access, audit integrity, retention, and institutional integration for the agreed deployment.

**Pass:** the responsible specialists approve the evidence and applicable market-access path. A research disclaimer, open-source dependency, or passing software tests is not a shortcut to this gate. Do not claim regulatory clearance or production clinical readiness without evidence.

## 14. Test strategy

Maintain three explicitly separate evidence levels:

| Level | Required evidence |
| --- | --- |
| Software correctness | Loading, coordinate transforms, output labels, masks, revision rules, numerical measurements, errors, security boundaries, restart/cancel |
| Anatomical performance | Independent expert/reference comparison on the defined population and acquisition protocols, including failures and artery coverage |
| User/deployment suitability | Technician workflow, review usability, install/recovery, controlled access, approved clinical/research use |

Synthetic tests are appropriate for geometry and numerical invariants. They cannot establish anatomical accuracy. Real-inference tests must use real checkpoints and permitted scans; mocks remain isolated unit tests only.

Every milestone report must include changed files, actual commands, observed outputs, checks passed/failed, limitations, and the next smallest useful step. Do not report a planned interface as implemented.

## 15. Definition of finished research application

The initial complete product is ready for research use when:

- A technician can import a supported scan, select the correct series, and create the model without programming.
- All requested supported tasks run with traceable versions, or missing results are explicitly identified.
- The generated heart is patient-specific, physically aligned, and inspectable against the original images.
- Coronaries appear only in a profile that has passed its model and integration gates.
- Reviewers can correct masks, preserve originals, save revisions, and reopen/export the chosen result.
- Errors, cancellation, restart, resource limits, and installation have been tested.
- Model limitations, review state, and research status are clear.

“Entire coronary tree guaranteed,” “all anatomy,” “diagnostic accuracy,” and “medical grade” are not acceptance labels for this research milestone.

## 16. Owner inputs needed at the relevant gates

Work can begin on M0/M1 using the current public scan and installed Slicer. Before dependent later work, obtain:

| Decision/resource | Needed for |
| --- | --- |
| First intended user and use: research, education, planning, diagnosis | Evaluation and release scope |
| Adult routine CTA versus pediatric/congenital focus | Dataset and capability boundaries |
| De-identified representative scans plus expert/reference annotations and usage rights | Model selection and performance assessment |
| Coronary model license access and eventual commercial rights if required | Enabling the coronary profile |
| Imaging specialist/reviewer | Scan admission, anatomical corrections, evaluation criteria |
| Target workstation specifications and acceptable waiting time | Measured hardware/performance requirements |
| Deployment country and local/network requirements | Commercial and institutional release planning |

Do not block independent development on every future business decision. Ask only when the next dependent milestone needs an answer.

## 17. Instruction for the next implementation session

> Read this specification and the repository instructions completely. Inspect the current implementation and preserve its working pretrained inference. Implement M0, then M1 only: a HeartAI module inside 3D Slicer that lets a technician select a supported CT, click Create heart, inspect the actual result, save a draft revision, and reopen it without terminal commands. Reuse the existing backend and numerical pipeline where appropriate. Do not train, fine-tune, purchase licenses, or enable unverified anatomy. Run meaningful tests and a real permitted CT workflow. Report the completed milestone, remaining limitations, and any specific blocker before moving to the next milestone.

This is the first implementation slice of the complete plan, not permission to skip the coronary, evaluation, or release gates.
