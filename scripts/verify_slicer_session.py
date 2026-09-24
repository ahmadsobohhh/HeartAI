"""Run in Slicer: verify a saved real scene, rejection guards, and leave it open."""
from pathlib import Path
import json
import runpy
import traceback
import numpy as np
import qt
import slicer

root = Path(__file__).resolve().parents[1]
output = root / "results/slicer/runtime-validation"
try:
    bridge = runpy.run_path(str(root / "scripts/open_slicer_case.py"))
    if not slicer.util.loadScene(str(output / "baseline.mrb")):
        raise RuntimeError("Could not reopen saved session")
    seg = next(n for n in slicer.util.getNodesByClass("vtkMRMLSegmentationNode") if n.GetAttribute("HeartAI.CaseId") == "788812d5bc03")
    ct = seg.GetNodeReference("HeartAI.SourceVolume")
    assert ct is not None
    assert seg.GetSegmentation().GetNumberOfSegments() == 7
    export = bridge["export_heartai_review"]
    checks = []

    def rejected(expected):
        try:
            export(seg, output, "automated guard test", "test edit")
        except ValueError as error:
            assert expected in str(error), str(error)
            checks.append(expected)
        else:
            raise AssertionError(f"Did not reject {expected}")

    transform = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode")
    seg.SetAndObserveTransformNodeID(transform.GetID())
    rejected("transform")
    seg.SetAndObserveTransformNodeID(None)
    slicer.mrmlScene.RemoveNode(transform)
    unknown = seg.GetSegmentation().AddEmptySegment("unknown")
    rejected("identities")
    seg.GetSegmentation().RemoveSegment(unknown)
    myocardium = seg.GetSegmentation().GetSegment("myocardium")
    myocardium.SetTag("HeartAI.LabelId", "99")
    rejected("mapping")
    myocardium.SetTag("HeartAI.LabelId", "44")
    original = slicer.util.arrayFromSegmentBinaryLabelmap(seg, "myocardium", ct).copy()
    overlap = original.copy()
    lv = slicer.util.arrayFromSegmentBinaryLabelmap(seg, "left_ventricle", ct)
    overlap[tuple(np.argwhere(lv)[0])] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(overlap, seg, "myocardium", ct)
    rejected("Overlapping")
    slicer.util.updateSegmentBinaryLabelmapFromArray(original, seg, "myocardium", ct)
    seg.CreateClosedSurfaceRepresentation()
    slicer.util.selectModule("SegmentEditor")
    editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    editor.setSegmentationNode(seg)
    editor.setSourceVolumeNode(ct)
    center = bridge["geometry"](ct) @ np.r_[np.argwhere(original).mean(axis=0)[::-1], 1]
    for name in slicer.app.layoutManager().sliceViewNames():
        slicer.app.layoutManager().sliceWidget(name).mrmlSliceNode().JumpSliceByCentering(*center[:3])
    # Expose the helper in Slicer's Python console for the user's later edits.
    import __main__
    __main__.export_current_heartai_review = bridge["export_current_heartai_review"]
    __main__.load_heartai_case = bridge["load_heartai_case"]
    metadata = dict(slicer.app.extensionsManagerModel().extensionMetadata("SlicerHeart"))
    (output / "session-verification.json").write_text(json.dumps({"reopened": True, "guards_rejected": checks, "slicerheart": metadata}, indent=2, default=str), encoding="utf-8")
    slicer.util.mainWindow().showMaximized()
    qt.QTimer.singleShot(2500, lambda: slicer.util.mainWindow().grab().save(str(output / "slicer-session.png")))
except Exception:
    (output / "session-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    traceback.print_exc()
