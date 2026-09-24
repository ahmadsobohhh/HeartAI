"""Integration test: run in Slicer using --python-script. No AI inference."""
from pathlib import Path
import json
import runpy
import traceback

import numpy as np
import slicer

root = Path(__file__).resolve().parents[1]
output = root / "results/slicer/runtime-validation"
output.mkdir(parents=True, exist_ok=True)
try:
    bridge = runpy.run_path(str(root / "scripts/open_slicer_case.py"))
    ct, seg = bridge["load_heartai_case"](root / "results/slicer/788812d5bc03-initial/review_package.json")
    baseline = bridge["export_heartai_review"](seg, output, "automated integration test", "no-edit round trip")
    # Save a reopenable session with the untouched draft and the CT.
    if not slicer.util.saveScene(str(output / "baseline.mrb")):
        raise RuntimeError("Scene save failed")
    mask = slicer.util.arrayFromSegmentBinaryLabelmap(seg, "myocardium", ct)
    index = tuple(np.argwhere(mask != 0)[len(np.argwhere(mask != 0)) // 2])
    mask[index] = 0
    slicer.util.updateSegmentBinaryLabelmapFromArray(mask, seg, "myocardium", ct)
    edited = bridge["export_heartai_review"](seg, output, "automated integration test", "test edit", "Removed one myocardium voxel; not an anatomical correction")
    result = {"slicer_version": slicer.app.applicationVersion, "slicer_revision": slicer.app.repositoryRevision,
              "baseline": str(baseline), "edited": str(edited), "removed_voxel_kji": [int(v) for v in index],
              "segment_ids": [seg.GetSegmentation().GetNthSegmentID(i) for i in range(seg.GetSegmentation().GetNumberOfSegments())]}
    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    slicer.app.exit(0)
except Exception:
    (output / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    traceback.print_exc()
    slicer.app.exit(1)
