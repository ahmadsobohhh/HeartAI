"""Milestone B; execute in Slicer's Python runtime, not the HeartAI venv."""
import hashlib
import json
import os
from pathlib import Path
import traceback

import numpy as np
import qt
import slicer
import vtk
import ScreenCapture


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def geometry(node):
    matrix = vtk.vtkMatrix4x4()
    node.GetIJKToRASMatrix(matrix)
    return np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])


def run_review(package_path, output_dir=None):
    package_path = Path(package_path).resolve()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    output = Path(output_dir).resolve() if output_dir else package_path.parent / "slicer"
    output.mkdir(exist_ok=False)
    try:
        if digest(package["ct_path"]) != package["ct_sha256"]:
            raise ValueError("Source CT hash mismatch")
        ct = slicer.util.loadVolume(package["ct_path"], {"name": "PUBLIC-001 TotalSegmentator source CT"})
        expected_geometry = np.asarray(package["affine_ijk_to_ras"])
        if (list(ct.GetImageData().GetDimensions()) != package["shape_ijk"]
                or not np.allclose(geometry(ct), expected_geometry, atol=1e-4, rtol=0)):
            raise ValueError("Slicer CT geometry differs from NIfTI geometry")
        ct.GetDisplayNode().AutoWindowLevelOff()
        ct.GetDisplayNode().SetWindowLevel(400, 40)
        seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "TotalSegmentator cardiac focus - technical review")
        seg.CreateDefaultDisplayNodes()
        seg.SetReferenceImageGeometryParameterFromVolumeNode(ct)
        seg.SetAttribute("HeartAI.Engine", "TotalSegmentator")
        seg.SetAttribute("HeartAI.ReviewScope", "Milestone B technical sanity check; not clinical review")
        checks = []
        for spec in package["structures"]:
            if digest(spec["path"]) != spec["sha256"]:
                raise ValueError(f"Source mask changed: {spec['name']}")
            mask_node = slicer.util.loadLabelVolume(spec["path"])
            if (mask_node.GetImageData().GetDimensions() != ct.GetImageData().GetDimensions()
                    or not np.allclose(geometry(mask_node), geometry(ct), atol=1e-4, rtol=0)):
                raise ValueError(f"Slicer mask grid mismatch: {spec['name']}")
            data = slicer.util.arrayFromVolume(mask_node)
            if hashlib.sha256(data.astype(np.uint8).tobytes()).hexdigest() != spec["kji_uint8_sha256"]:
                raise ValueError(f"Voxel-order/import mismatch: {spec['name']}")
            color = tuple(int(spec["color"][i:i+2], 16)/255 for i in (1, 3, 5))
            segment_id = seg.GetSegmentation().AddEmptySegment(spec["name"], spec["name"], color)
            seg.GetSegmentation().GetSegment(segment_id).SetTag("TotalSegmentator.LabelId", str(spec["label_id"]))
            # Slicer uses KJI arrays. Supplying the source CT as reference preserves
            # the original physical grid instead of independently centering masks.
            slicer.util.updateSegmentBinaryLabelmapFromArray(data, seg, segment_id, ct)
            restored = slicer.util.arrayFromSegmentBinaryLabelmap(seg, segment_id, ct)
            if not np.array_equal(restored, data):
                raise ValueError(f"Segment import changed voxels: {spec['name']}")
            checks.append({"name": spec["name"], "foreground_voxels": int(np.count_nonzero(restored)),
                           "source_hash_matches": True, "grid_matches": True, "exact_voxel_match": True})
            slicer.mrmlScene.RemoveNode(mask_node)
            del data, restored
        # Slicer's native display representation is only for the sanity check.
        # This does not implement or export HeartAI reconstruction meshes.
        seg.GetSegmentation().SetConversionParameter("Smoothing factor", "0.0")
        seg.CreateClosedSurfaceRepresentation()
        display = seg.GetDisplayNode()
        display.SetOpacity2DFill(0.18)
        display.SetOpacity2DOutline(1.0)
        display.SetOpacity3D(0.7)
        layout = slicer.app.layoutManager()
        layout.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        slicer.util.setSliceViewerLayers(background=ct)
        slicer.util.resetSliceViews()
        slicer.util.selectModule("Segmentations")
        capture = ScreenCapture.ScreenCaptureLogic()

        def center(spec):
            for name in layout.sliceViewNames():
                widget = layout.sliceWidget(name)
                widget.sliceLogic().FitSliceToAll()
                # FitSliceToAll resets slice offsets; jump only after fitting.
                widget.mrmlSliceNode().JumpSliceByCentering(*spec["review_center_ras_mm"])
                matrix = widget.mrmlSliceNode().GetSliceToRAS()
                slice_to_ras = np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])
                position_in_slice = np.linalg.solve(slice_to_ras, np.r_[spec["review_center_ras_mm"], 1])
                if abs(position_in_slice[2]) > 1e-4:
                    raise ValueError(f"{name}: captured plane misses the selected review point")
                widget.sliceView().forceRender()
            slicer.app.processEvents()

        def capture_views(prefix):
            for label, plane in [("Red", "axial"), ("Yellow", "sagittal"), ("Green", "coronal")]:
                capture.captureImageFromView(layout.sliceWidget(label).sliceView(), str(output / f"{prefix}_{plane}.png"))

        review_positions = []
        for spec in package["structures"]:
            display.SetAllSegmentsVisibility(False)
            display.SetSegmentVisibility(spec["name"], True)
            center(spec)
            capture_views(spec["name"])
            review_positions.append({"name": spec["name"], "center_ras_mm": spec["review_center_ras_mm"],
                                     "slice_offsets_mm": {name: layout.sliceWidget(name).sliceLogic().GetSliceOffset()
                                                          for name in layout.sliceViewNames()}})
        display.SetAllSegmentsVisibility(True)
        heart = next(s for s in package["structures"] if s["name"] == "heart")
        center(heart)
        slicer.util.resetThreeDViews()
        layout.threeDWidget(0).threeDView().forceRender()
        capture_views("combined")
        capture.captureImageFromView(layout.threeDWidget(0).threeDView(), str(output / "native_3d.png"))
        capture.captureImageFromView(None, str(output / "four_up.png"))
        if not slicer.util.saveNode(seg, str(output / "cardiac.seg.nrrd")):
            raise RuntimeError("Could not save the Slicer segmentation")
        # Re-open the saved segmentation and compare every segment on the CT grid.
        reopened = slicer.util.loadSegmentation(str(output / "cardiac.seg.nrrd"))
        for spec in package["structures"]:
            sid = reopened.GetSegmentation().GetSegmentIdBySegmentName(spec["name"])
            data = slicer.util.arrayFromSegmentBinaryLabelmap(reopened, sid, ct)
            if hashlib.sha256(data.astype(np.uint8).tobytes()).hexdigest() != spec["kji_uint8_sha256"]:
                raise ValueError(f"Saved segmentation changed voxels: {spec['name']}")
        slicer.mrmlScene.RemoveNode(reopened)
        if not slicer.util.saveScene(str(output / "review.mrb")):
            raise RuntimeError("Could not save review scene")
        # Verify all originals, including unselected outputs, remain unchanged.
        for item in package["output_inventory"]:
            if digest(item["path"]) != item["sha256"]:
                raise ValueError(f"Original output changed: {item['name']}")
        report = {"status": "technical_checks_passed_visual_review_pending",
                  "slicer_version": slicer.app.applicationVersion, "slicer_revision": slicer.app.repositoryRevision,
                  "ct_grid_matches": True, "segments": checks, "saved_segmentation_round_trip_exact": True,
                  "original_masks_unchanged": len(package["output_inventory"]),
                  "review_positions": review_positions,
                  "captures": sorted(p.name for p in output.glob("*.png")),
                  "scene": "review.mrb", "segmentation": "cardiac.seg.nrrd",
                  "clinical_validation": False}
        (output / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        if os.environ.get("HEARTAI_SLICER_EXIT") == "1":
            slicer.app.exit(0)
        return ct, seg
    except Exception:
        (output / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        if os.environ.get("HEARTAI_SLICER_EXIT") == "1":
            slicer.app.exit(1)
        raise


if os.environ.get("HEARTAI_TOTALSEG_REVIEW"):
    qt.QTimer.singleShot(1000, lambda: run_review(os.environ["HEARTAI_TOTALSEG_REVIEW"],
                                                os.environ.get("HEARTAI_SLICER_REVIEW_OUTPUT")))
