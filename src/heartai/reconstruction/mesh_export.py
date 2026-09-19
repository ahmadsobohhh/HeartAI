from pathlib import Path

import numpy as np
import trimesh

from heartai.reconstruction.marching_cubes import validate_mesh

# RAS millimeters -> right-handed Y-up meters: (R, S, -A) / 1000.
# Keep the same patient origin in every file; never center structures separately.
RAS_MM_TO_GLB = np.array([
    [0.001, 0, 0, 0], [0, 0, 0.001, 0], [0, -0.001, 0, 0], [0, 0, 0, 1.]
])


def glb_mesh(mesh: trimesh.Trimesh, color: str) -> trimesh.Trimesh:
    result = mesh.copy()
    result.apply_transform(RAS_MM_TO_GLB)
    result.units = "meters"
    result.visual.face_colors = [int(color[i:i+2], 16) for i in (1, 3, 5)] + [255]
    return result


def export_structure(mesh: trimesh.Trimesh, output_dir: Path, name: str, color: str) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {"glb": output_dir / f"{name}.glb", "stl": output_dir / f"{name}.stl"}
    converted = glb_mesh(mesh, color)
    scene = trimesh.Scene()
    scene.add_geometry(converted, node_name=name, geom_name=name)
    scene.export(paths["glb"], file_type="glb")
    mesh.export(paths["stl"], file_type="stl")  # STL is unitless; documented as RAS mm.
    loaded = trimesh.load(paths["glb"], force="scene")
    if len(loaded.geometry) != 1:
        raise ValueError("Export lost structure geometry")
    exported = next(iter(loaded.geometry.values()))
    validate_mesh(exported)
    np.testing.assert_allclose(loaded.bounds, converted.bounds, atol=1e-7, rtol=1e-6)
    if len(exported.faces) != len(mesh.faces):
        raise ValueError("GLB face count changed during export")
    stl = trimesh.load(paths["stl"], force="mesh")
    np.testing.assert_allclose(stl.bounds, mesh.bounds, atol=1e-4, rtol=1e-6)
    return paths


def export_combined(meshes: dict[str, trimesh.Trimesh], colors: dict[str, str], path: Path) -> Path:
    scene = trimesh.Scene()
    for name, mesh in meshes.items():
        scene.add_geometry(glb_mesh(mesh, colors[name]), geom_name=name, node_name=name)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.export(path, file_type="glb")
    loaded = trimesh.load(path, force="scene")
    if set(loaded.geometry) != set(meshes):
        raise ValueError("Combined GLB did not retain separate named structures")
    np.testing.assert_allclose(loaded.bounds, scene.bounds, atol=1e-7, rtol=1e-6)
    return path
