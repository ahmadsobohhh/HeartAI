"""Static, physically scaled axial checks of model-generated cardiac labels."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
import nibabel as nib
import numpy as np

CARDIAC = {
    7: "Aorta", 44: "Myocardium", 45: "Left atrium", 46: "Left ventricle",
    47: "Right atrium", 48: "Right ventricle", 49: "Pulmonary artery",
}


def create_overlay(scan_path, segmentation_path, output):
    scan = nib.as_closest_canonical(nib.load(scan_path))
    segmentation = nib.as_closest_canonical(nib.load(segmentation_path))
    if scan.shape != segmentation.shape or not np.allclose(scan.affine, segmentation.affine):
        raise ValueError("CT and segmentation grids differ")
    ct = scan.get_fdata(dtype=np.float32)
    labels = np.asarray(segmentation.dataobj)
    display = np.zeros(labels.shape, dtype=np.uint8)
    for color_id, class_id in enumerate(CARDIAC, start=1):
        display[labels == class_id] = color_id
    # Choose three slices within the predicted heart (excluding long aorta).
    heart = np.isin(labels, list(CARDIAC)[1:])
    occupied = np.flatnonzero(heart.sum(axis=(0, 1)))
    if not len(occupied):
        raise ValueError("No cardiac foreground predicted; inspect input/model")
    slices = [int(np.quantile(occupied, q)) for q in (0.25, 0.5, 0.75)]
    colors = ["#ffb000", "#e85873", "#5ac8fa", "#3977eb", "#72d38e", "#bc85ed", "#ff8552"]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(0.5, 8.5), cmap.N)
    dx, dy, _ = nib.affines.voxel_sizes(scan.affine)
    extent = [0, ct.shape[0] * dx, 0, ct.shape[1] * dy]
    fig, axes = plt.subplots(3, 3, figsize=(12, 11), facecolor="white")
    for row, z in enumerate(slices):
        mask = np.ma.masked_equal(display[:, :, z].T, 0)
        for col in range(3):
            ax = axes[row, col]
            ax.set_facecolor("#10141c")
            if col != 1:
                ax.imshow(ct[:, :, z].T, cmap="gray", vmin=-160, vmax=240, origin="lower", extent=extent)
            if col != 0:
                ax.imshow(mask, cmap=cmap, norm=norm, alpha=0.55 if col == 2 else 1,
                          origin="lower", extent=extent, interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            if row == 0:
                ax.set_title(["Original CT", "Predicted cardiac labels", "CT + prediction"][col])
        axes[row, 0].set_ylabel(f"RAS axial slice {z}")
    fig.legend(handles=[Patch(color=c, label=n) for c, n in zip(colors, CARDIAC.values())],
               loc="lower center", ncol=4, frameon=False)
    fig.suptitle("HeartAI | Pretrained MONAI inference | Research prototype", fontsize=15)
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return slices
