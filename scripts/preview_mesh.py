"""Inspect an exported GLB independently using a Python visualization."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh


def render_mesh(path: Path, output: Path) -> None:
    # Load the exported file, not the pre-export in-memory marching-cubes result.
    scene = trimesh.load(path, force="scene")
    mesh = scene.to_geometry()
    points = np.asarray(mesh.vertices)
    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(projection="3d")
    ax.add_collection3d(Poly3DCollection(points[mesh.faces], facecolors="#e85873", linewidth=0, shade=True))
    low, high = points.min(axis=0), points.max(axis=0)
    center, radius = (low + high) / 2, max(high-low) * .6
    ax.set_xlim(center[0]-radius, center[0]+radius)
    ax.set_ylim(center[1]-radius, center[1]+radius)
    ax.set_zlim(center[2]-radius, center[2]+radius)
    ax.set_box_aspect((1, 1, 1))
    ax.set(xlabel="R (m)", ylabel="S (m)", zlabel="-A (m)",
           title=f"Exported GLB inspection: {path.stem}\n{len(mesh.vertices):,} vertices / {len(mesh.faces):,} triangles")
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mesh", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/mesh-inspection.png"))
    args = parser.parse_args()
    render_mesh(args.mesh, args.output)
