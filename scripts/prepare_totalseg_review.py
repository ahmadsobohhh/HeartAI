"""Milestone B: select and validate existing TotalSegmentator cardiac masks."""
import argparse
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage

from inspect_totalseg import COLORS, FOCUS, validate_mask


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(case, output):
    case, output = Path(case).resolve(), Path(output).resolve()
    run = json.loads((case / "run.json").read_text())
    validation = json.loads((case / "validation.json").read_text())
    mapping = json.loads((case / "installed_label_map.json").read_text())
    if validation["status"] != "passed" or run["task"] != "total":
        raise ValueError("A validated total run is required")
    ct_path = Path(run["input"]["path"])
    if digest(ct_path) != run["input"]["sha256"]:
        raise ValueError("CT changed since inference")
    ct = nib.load(ct_path)
    inventory = {p.name.removesuffix(".nii.gz"): p for p in (case / "segmentations").glob("*.nii.gz")}
    if set(inventory) != set(mapping.values()):
        raise ValueError("Output filenames do not match the saved installed task map")
    ids = {name: int(idx) for idx, name in mapping.items()}
    original = {r["name"]: r for r in validation["structures"]}
    occupied = np.zeros(ct.shape, dtype=bool)
    structures, unavailable = [], []
    for name, color in zip(FOCUS, COLORS):
        if name not in inventory:
            unavailable.append({"name": name, "reason": "not in task output"})
            continue
        data = validate_mask(nib.load(inventory[name]), ct, name)
        count = int(np.count_nonzero(data))
        if count != original[name]["foreground_voxels"]:
            raise ValueError(f"{name}: foreground count changed since Milestone A")
        if not count:
            unavailable.append({"name": name, "reason": "empty prediction"})
            continue
        if np.any(occupied & (data != 0)):
            raise ValueError(f"{name}: cardiac masks overlap")
        occupied |= data != 0
        coords = np.where(data)
        lower = [int(a.min()) for a in coords]
        upper = [int(a.max()) for a in coords]
        center = [float(a.mean()) for a in coords]
        # A centroid can fall between disconnected vessels. Choose the nearest
        # actual foreground voxel so all three review planes intersect the mask.
        nearest = int(np.argmin(sum((a-c)**2 for a, c in zip(coords, center))))
        review_ijk = [int(a[nearest]) for a in coords]
        # Use the foreground bounding box to avoid labeling the whole CT volume.
        crop = tuple(slice(a, b+1) for a, b in zip(lower, upper))
        components, number = ndimage.label(data[crop], structure=np.ones((3, 3, 3)))
        sizes = sorted(np.bincount(components.ravel())[1:].tolist(), reverse=True)
        structures.append({"name": name, "label_id": ids[name], "color": color,
                           "path": str(inventory[name]), "sha256": digest(inventory[name]),
                           "foreground_voxels": count, "bounds_ijk_inclusive": [lower, upper],
                           "review_voxel_ijk": review_ijk,
                           "review_center_ras_mm": (ct.affine @ np.r_[review_ijk, 1])[:3].tolist(),
                           "boundary_contact": any(a == 0 or b == ct.shape[i]-1 for i, (a, b) in enumerate(zip(lower, upper))),
                           "components_26_connected": number, "component_sizes_voxels": sizes,
                           # Slicer arrays are KJI; Nibabel arrays are IJK. Hash the
                           # same uint8 KJI byte order to verify import without resampling.
                           "kji_uint8_sha256": hashlib.sha256(data.transpose(2, 1, 0).astype(np.uint8).tobytes()).hexdigest()})
    if not {"heart", "aorta"} <= {s["name"] for s in structures}:
        raise ValueError("Heart and aorta are required for this review")
    report = {"milestone": "B", "status": "prepared_pending_slicer_review", "case": str(case),
              "engine": run["engine"], "version": run["version"], "task": run["task"],
              "ct_path": str(ct_path), "ct_sha256": run["input"]["sha256"],
              "shape_ijk": list(ct.shape), "affine_ijk_to_ras": ct.affine.tolist(),
              "output_inventory": [{"name": name, "label_id": ids[name], "path": str(path),
                                     "sha256": digest(path), "foreground_voxels": original[name]["foreground_voxels"]}
                                    for name, path in sorted(inventory.items())],
              "structures": structures, "unavailable_focus": unavailable,
              "absent_task_labels": validation["not_in_total_task"], "overlap_voxels": 0,
              "postprocessing": "none; all predicted components preserved"}
    output.mkdir(parents=True, exist_ok=False)
    target = output / "cardiac_subset.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(target)
    for spec in structures:
        print(spec["name"], spec["foreground_voxels"], "voxels; components:", spec["component_sizes_voxels"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.case, args.output)
