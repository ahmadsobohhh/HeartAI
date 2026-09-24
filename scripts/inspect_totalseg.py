"""Validate real Milestone A binary masks and render a CT overlay; no meshes."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import nibabel as nib
import numpy as np


# This is a display selection, not a claim that every task supplies these labels.
FOCUS = ["heart", "aorta", "pulmonary_vein", "atrial_appendage_left",
         "superior_vena_cava", "inferior_vena_cava"]
COLORS = ["#f26079", "#ffbd42", "#47c9ef", "#b38bf5", "#69d39d", "#f58945"]


def validate_mask(image, scan, name):
    if image.shape != scan.shape or not np.allclose(image.affine, scan.affine, rtol=0, atol=1e-4):
        raise ValueError(f"{name}: mask does not align with the original CT grid")
    data = np.asarray(image.dataobj)
    if not np.isin(data, [0, 1]).all():
        raise ValueError(f"{name}: expected finite binary values 0/1")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    case = args.case.resolve()
    run = json.loads((case / "run.json").read_text(encoding="utf-8"))
    if version("TotalSegmentator") != run["version"]:
        raise ValueError("Inspect using the same TotalSegmentator version that produced the masks")
    if run["status"] != "segmented_pending_validation":
        raise ValueError("Inference must complete successfully before inspection")
    upstream = json.loads((case / "upstream_report.json").read_text(encoding="utf-8"))
    if (upstream["task"] != "total" or upstream["fast"] or upstream["fastest"]
            or upstream["license_required"] or upstream["roi_subset"] is not None
            or upstream["totalsegmentator_version"] != run["version"]
            or upstream["device"] != run["device"]):
        raise ValueError("Upstream report does not match the requested standard total run")
    scan_path = Path(run["input"]["path"])
    with scan_path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != run["input"]["sha256"]:
            raise ValueError("Input changed since inference")
    scan = nib.load(scan_path)
    label_map = json.loads((case / "installed_label_map.json").read_text(encoding="utf-8"))
    expected = {name: int(label_id) for label_id, name in label_map.items()}
    files = {p.name.removesuffix(".nii.gz"): p for p in (case / "segmentations").glob("*.nii.gz")}
    if set(files) != set(expected):
        raise ValueError(f"Output class mismatch: missing={set(expected)-set(files)}, unexpected={set(files)-set(expected)}")
    records = []
    cardiac = {}
    for name, path in sorted(files.items()):
        image = nib.load(path)
        data = validate_mask(image, scan, name)
        count = int(np.count_nonzero(data))
        record = {"name": name, "label_id": expected[name], "file": str(path.relative_to(case)),
                  "foreground_voxels": count, "nonempty": count > 0,
                  "dtype": str(data.dtype), "shape_matches": True, "affine_matches": True,
                  "binary": True}
        if name in FOCUS and count:
            coordinates = np.where(data)
            record["bounds_voxel_inclusive"] = [[int(a.min()), int(a.max())] for a in coordinates]
            record["touches_scan_boundary"] = any(a.min() == 0 or a.max() == scan.shape[i]-1
                                                   for i, a in enumerate(coordinates))
            # Apply the same lossless axis permutation/flips to CT and masks. No
            # interpolation or independent centering: their shared affine stays aligned.
            cardiac[name] = np.asarray(nib.as_closest_canonical(image).dataobj)
            del coordinates
        records.append(record)
        del data, image
    if not all(name in cardiac for name in ("heart", "aorta")):
        raise ValueError("Heart/aorta foreground absent; Milestone A is not proven")
    canonical = nib.as_closest_canonical(scan)
    ct = canonical.get_fdata(dtype=np.float32)
    occupied = np.flatnonzero(cardiac["heart"].sum(axis=(0, 1)))
    slices = [int(np.quantile(occupied, q)) for q in (0.25, 0.50, 0.75)]
    names = [name for name in FOCUS if name in cardiac]
    colors = [COLORS[FOCUS.index(name)] for name in names]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(0.5, len(names)+1.5), cmap.N)
    dx, dy, _ = nib.affines.voxel_sizes(canonical.affine)
    extent = [0, ct.shape[0]*dx, 0, ct.shape[1]*dy]
    fig, axes = plt.subplots(3, 2, figsize=(10, 13), facecolor="white")
    for row, z in enumerate(slices):
        labels = np.zeros(ct.shape[:2], dtype=np.uint8)
        for label, name in enumerate(names, start=1):
            labels[cardiac[name][:, :, z] > 0] = label
        for col, ax in enumerate(axes[row]):
            ax.imshow(ct[:, :, z].T, origin="lower", cmap="gray", vmin=-160, vmax=240, extent=extent)
            if col:
                ax.imshow(np.ma.masked_equal(labels.T, 0), origin="lower", cmap=cmap,
                          norm=norm, alpha=0.5, interpolation="nearest", extent=extent)
            # Canonical RAS: increasing screen x points to patient right (R), y to anterior (A).
            ax.text(0.02, 0.5, "L", color="white", transform=ax.transAxes)
            ax.text(0.96, 0.5, "R", color="white", transform=ax.transAxes)
            ax.text(0.5, 0.97, "A", color="white", transform=ax.transAxes, va="top")
            ax.text(0.5, 0.02, "P", color="white", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"{'CT' if col == 0 else 'CT + real masks'} | axial RAS slice {z}")
    fig.suptitle(f"HeartAI | TotalSegmentator {run['version']} / total / standard / {run['device']}\n"
                 "Public CTACardio | Research prototype, not for clinical use", fontsize=13)
    fig.legend(handles=[Patch(color=c, label=n.replace('_', ' ')) for c, n in zip(colors, names)],
               loc="lower center", ncol=3, frameon=False)
    fig.tight_layout(rect=(0, 0.055, 1, 0.95))
    preview = case / "previews" / "cardiac_overlay.png"
    preview.parent.mkdir(exist_ok=True)
    fig.savefig(preview, dpi=120)
    plt.close(fig)
    report = {
        "status": "passed", "files_produced": len(files),
        "nonempty_structures": sum(r["nonempty"] for r in records),
        "empty_structures": [r["name"] for r in records if not r["nonempty"]],
        "cardiac_available": names,
        "not_in_total_task": [n for n in ["pulmonary_artery", "myocardium", "atrium_left",
                                "atrium_right", "ventricle_left", "ventricle_right"] if n not in expected],
        "checks": "Every mask is binary and matches original CT shape and affine (absolute tolerance 1e-4).",
        "structures": records, "overlay": str(preview.relative_to(case)),
        "overlay_slices_canonical_ras": slices, "display_window_hu": [-160, 240],
        "limitations": "No ground-truth accuracy assessment. Programmatic alignment is not clinical validation. Slicer review deferred to Milestone B.",
    }
    from totalsegmentator.map_tasks_config import TASK_CONFIGS
    report["model_configuration"] = TASK_CONFIGS["total"]["sub_modes"]["default"]
    weights = []
    for task_id in report["model_configuration"]["task_id"]:
        checkpoints = list(Path(run["weights_dir"]).glob(f"Dataset{task_id}_*/**/checkpoint_final.pth"))
        if not checkpoints:
            raise ValueError(f"Missing cached model checkpoint for task {task_id}")
        for checkpoint in checkpoints:
            with checkpoint.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            weights.append({"task_id": task_id, "path": str(checkpoint), "sha256": digest})
    report["model_checkpoints"] = weights
    (case / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "structures"}, indent=2))


if __name__ == "__main__":
    main()
