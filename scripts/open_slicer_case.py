"""Run ONLY in 3D Slicer's Python runtime, via start_slicer.ps1."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

import numpy as np
import slicer
import vtk


def file_hash(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def geometry(node):
    matrix = vtk.vtkMatrix4x4()
    node.GetIJKToRASMatrix(matrix)
    return np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])


def load_heartai_case(package_path):
    package = json.loads(Path(package_path).read_text(encoding="utf-8"))
    for key in ("ct", "prediction", "cardiac_labels"):
        with open(package[f"{key}_path"], "rb") as stream:
            hasher = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
            digest = hasher.hexdigest()
        if digest != package[f"{key}_sha256"]:
            raise ValueError(f"{key} changed after package preparation")
    created = []
    try:
        ct = slicer.util.loadVolume(package["ct_path"])
        created.append(ct)
        labels = slicer.util.loadLabelVolume(package["cardiac_labels_path"])
        created.append(labels)
        # Slicer arrays are KJI; both masks and reference volume use this convention.
        data = slicer.util.arrayFromVolume(labels)
        matrices = []
        for node in (ct, labels):
            matrix = vtk.vtkMatrix4x4()
            node.GetIJKToRASMatrix(matrix)
            matrices.append(np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)]))
        if ct.GetImageData().GetDimensions() != labels.GetImageData().GetDimensions() or not np.allclose(*matrices, atol=1e-4, rtol=0):
            raise ValueError("Imported CT and labels do not occupy the same physical grid")
        segmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", f"HeartAI {package['case_id']} — draft")
        created.append(segmentation)
        segmentation.CreateDefaultDisplayNodes()
        segmentation.SetReferenceImageGeometryParameterFromVolumeNode(ct)
        segmentation.SetAttribute("HeartAI.CaseId", package["case_id"])
        segmentation.SetAttribute("HeartAI.ReviewPackage", str(Path(package_path).resolve()))
        segmentation.SetAttribute("HeartAI.ReviewState", "draft")
        segmentation.SetNodeReferenceID("HeartAI.SourceVolume", ct.GetID())
        segmentation.SetAttribute("HeartAI.SourceGeometry", json.dumps(geometry(ct).tolist()))
        segmentation.SetAttribute("HeartAI.SourceArrayHash", hashlib.sha256(slicer.util.arrayFromVolume(ct).tobytes()).hexdigest())
        for spec in package["structures"]:
            if not spec["present"]:
                continue
            color = tuple(int(spec["color"][i:i+2], 16) / 255 for i in (1, 3, 5))
            segment_id = segmentation.GetSegmentation().AddEmptySegment(spec["name"], spec["label"], color)
            segment = segmentation.GetSegmentation().GetSegment(segment_id)
            segment.SetTag("HeartAI.LabelId", str(spec["label_id"]))
            segment.SetTag("HeartAI.Structure", spec["name"])
            slicer.util.updateSegmentBinaryLabelmapFromArray((data == spec["label_id"]).astype(np.uint8), segmentation, segment_id, ct)
        segmentation.GetSegmentation().SetConversionParameter("Smoothing factor", "0.0")
        segmentation.CreateClosedSurfaceRepresentation()
        segmentation.GetDisplayNode().SetOpacity2DFill(0.15)
        segmentation.GetDisplayNode().SetOpacity2DOutline(1.0)
        slicer.mrmlScene.RemoveNode(labels)
        created.remove(labels)
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        slicer.util.setSliceViewerLayers(background=ct)
        slicer.util.selectModule("SegmentEditor")
        editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
        editor.setSegmentationNode(segmentation)
        editor.setSourceVolumeNode(ct)
        slicer.util.resetSliceViews()
        center_kji = np.argwhere(slicer.util.arrayFromSegmentBinaryLabelmap(segmentation, "myocardium", ct)).mean(axis=0) if "myocardium" in [segmentation.GetSegmentation().GetNthSegmentID(i) for i in range(segmentation.GetSegmentation().GetNumberOfSegments())] else np.array(data.shape) / 2
        center_ras = geometry(ct) @ np.r_[center_kji[::-1], 1]
        for name in slicer.app.layoutManager().sliceViewNames():
            slicer.app.layoutManager().sliceWidget(name).mrmlSliceNode().JumpSliceByCentering(*center_ras[:3])
        slicer.util.resetThreeDViews()
        print(f"HeartAI case {package['case_id']} opened as a draft. Slicer {slicer.app.applicationVersion}, revision {slicer.app.repositoryRevision}")
        for warning in package["warnings"]:
            print(f"Prediction note: {warning}")
        return ct, segmentation
    except Exception:
        for node in reversed(created):
            slicer.mrmlScene.RemoveNode(node)
        raise


def export_heartai_review(segmentation, output_root, reviewer, purpose, notes=""):
    """Export a NEW draft revision; never mark a technical export reviewed."""
    if not reviewer.strip() or purpose not in ("test edit", "anatomical review", "no-edit round trip"):
        raise ValueError("Provide a reviewer and an explicit review purpose")
    package_path = segmentation.GetAttribute("HeartAI.ReviewPackage")
    package = json.loads(Path(package_path).read_text(encoding="utf-8"))
    ct = segmentation.GetNodeReference("HeartAI.SourceVolume")
    if ct is None or ct.GetParentTransformNode() or segmentation.GetParentTransformNode():
        raise ValueError("Missing source CT or unresolved parent transform")
    if not np.allclose(geometry(ct), json.loads(segmentation.GetAttribute("HeartAI.SourceGeometry")), atol=1e-4, rtol=0):
        raise ValueError("Source CT geometry changed")
    if hashlib.sha256(slicer.util.arrayFromVolume(ct).tobytes()).hexdigest() != segmentation.GetAttribute("HeartAI.SourceArrayHash"):
        raise ValueError("Source CT voxels changed")
    for key in ("ct", "prediction", "cardiac_labels"):
        if file_hash(package[f"{key}_path"]) != package[f"{key}_sha256"]:
            raise ValueError(f"Original {key} file changed")
    expected = {s["name"]: s for s in package["structures"] if s["present"]}
    segments = segmentation.GetSegmentation()
    ids = [segments.GetNthSegmentID(i) for i in range(segments.GetNumberOfSegments())]
    if set(ids) != set(expected):
        raise ValueError("Segment identities changed; keep empty segments instead of deleting them")
    combined = np.zeros(slicer.util.arrayFromVolume(ct).shape, dtype=np.uint8)
    for segment_id in ids:
        segment = segments.GetSegment(segment_id)
        tag = vtk.mutable("")
        if not segment.GetTag("HeartAI.LabelId", tag) or str(tag) != str(expected[segment_id]["label_id"]):
            raise ValueError("Segment label mapping changed")
        mask = slicer.util.arrayFromSegmentBinaryLabelmap(segmentation, segment_id, ct) != 0
        if np.any(mask & (combined != 0)):
            raise ValueError("Overlapping segments cannot be exported to a single labelmap")
        combined[mask] = expected[segment_id]["label_id"]
    if not combined.any():
        raise ValueError("At least one cardiac structure must remain")
    # Detect edits outside the reference extent instead of silently cropping them.
    for segment_id in ids:
        from vtk.util.numpy_support import vtk_to_numpy
        native = slicer.vtkOrientedImageData()
        segmentation.GetBinaryLabelmapRepresentation(segment_id, native)
        matrix = vtk.vtkMatrix4x4()
        native.GetImageToWorldMatrix(matrix)
        native_geometry = np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])
        relation = np.linalg.inv(geometry(ct)) @ native_geometry
        if not np.allclose(relation[:3, :3], np.eye(3), atol=1e-5, rtol=0) or not np.allclose(relation[:3, 3], np.rint(relation[:3, 3]), atol=1e-4, rtol=0):
            raise ValueError("Segmentation grid changed; implicit resampling is not allowed")
        scalars = native.GetPointData().GetScalars()
        native_count = 0 if scalars is None else int(np.count_nonzero(vtk_to_numpy(scalars)))
        exported_count = int(np.count_nonzero(combined == expected[segment_id]["label_id"]))
        if native_count != exported_count:
            raise ValueError("Segmentation grid/extent changed; export would resample or crop labels")
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    revision_id = uuid4().hex[:12]
    staging = output_root / (".tmp-" + revision_id)
    staging.mkdir(exist_ok=False)
    label_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    try:
        label_node.CopyOrientation(ct)
        slicer.util.updateVolumeFromArray(label_node, combined)
        if not slicer.util.saveNode(label_node, str(staging / "cardiac_labels.nii.gz")):
            raise RuntimeError("Could not save reviewed labels")
        if not slicer.util.saveNode(segmentation, str(staging / "review.seg.nrrd")):
            raise RuntimeError("Could not save editable segmentation")
        record = {
            "schema_version": 1, "case_id": package["case_id"], "revision_id": revision_id,
            "review_state": "draft", "processing_status": "exported", "reviewer": reviewer,
            "purpose": purpose, "notes": notes, "created_at": datetime.now(timezone.utc).isoformat(),
            "slicer_version": slicer.app.applicationVersion, "slicer_revision": slicer.app.repositoryRevision,
            "extensions": {"SlicerHeart": dict(slicer.app.extensionsManagerModel().extensionMetadata("SlicerHeart"))},
            "ct_sha256": package["ct_sha256"], "prediction_sha256": package["prediction_sha256"],
            "model": package["model"], "structures": package["structures"],
            "parent_revision": None,
            "source_warnings": package["warnings"], "reviewed_structures": [],
            "artifacts": {name: file_hash(staging / name) for name in ("cardiac_labels.nii.gz", "review.seg.nrrd")},
        }
        (staging / "review.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        destination = output_root / revision_id
        staging.rename(destination)
        # SaveNode assigned a temporary storage path; keep subsequent scene saves valid.
        segmentation.GetStorageNode().SetFileName(str(destination / "review.seg.nrrd"))
        print(f"Exported draft revision: {destination}")
        return destination
    finally:
        slicer.mrmlScene.RemoveNode(label_node)


def export_current_heartai_review(reviewer, purpose="anatomical review", notes=""):
    """Convenience entry point for the selected Segment Editor draft."""
    editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    segmentation = editor.segmentationNode()
    if segmentation is None or not segmentation.GetAttribute("HeartAI.ReviewPackage"):
        raise ValueError("Select a HeartAI draft in Segment Editor first")
    package = Path(segmentation.GetAttribute("HeartAI.ReviewPackage"))
    return export_heartai_review(segmentation, package.parent.parent / "exports", reviewer, purpose, notes)


if os.environ.get("HEARTAI_SLICER_PACKAGE"):
    load_heartai_case(os.environ["HEARTAI_SLICER_PACKAGE"])
