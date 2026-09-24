"""Milestone C reconstruction of the real, reviewed TotalSegmentator subset."""
import hashlib
import json
from pathlib import Path
import time

import nibabel as nib
import numpy as np
from scipy.spatial import cKDTree
import trimesh

from heartai.measurements.geometry import measure_structure
from heartai.reconstruction.marching_cubes import mask_to_mesh, nifti_affine_mm, validate_affine, validate_mesh
from heartai.reconstruction.mesh_export import export_structure, export_combined, RAS_MM_TO_GLB


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def crop_binary_mask(mask, affine):
    """Keep every component; translate crop indices back into the original RAS grid."""
    affine = validate_affine(affine)
    if mask.ndim != 3 or not np.isin(mask, [0, 1]).all() or not np.any(mask):
        raise ValueError("Expected a nonempty binary 3D mask")
    coords = np.where(mask)
    low = np.array([a.min() for a in coords])
    high = np.array([a.max() for a in coords]) + 1
    translation = np.eye(4)
    translation[:3, 3] = low
    edge = bool(np.any(low == 0) or np.any(high == mask.shape))
    return mask[tuple(slice(a, b) for a, b in zip(low, high))].copy(), affine @ translation, edge


def mesh_measurements(mesh, mask_measurements, tolerance=0.05):
    """Five percent is an engineering check, not a clinical accuracy threshold."""
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("Mesh must be closed, consistently wound and have positive volume")
    difference = abs(float(mesh.volume)-mask_measurements["volume_mm3"]) / mask_measurements["volume_mm3"]
    return {"surface_area_mm2": float(mesh.area), "surface_area_cm2": float(mesh.area)/100,
            "mesh_volume_mm3": float(mesh.volume), "mesh_volume_ml": float(mesh.volume)/1000,
            "mesh_voxel_volume_relative_difference": difference,
            "mesh_voxel_volume_tolerance": tolerance, "mesh_voxel_volume_check_passed": difference <= tolerance}


def reconstruct_review(review_dir, output_dir):
    review_dir, output_dir = Path(review_dir).resolve(), Path(output_dir).resolve()
    package = json.loads((review_dir / "cardiac_subset.json").read_text())
    summary = json.loads((review_dir / "review_summary.json").read_text())
    if summary["status"] != "complete" or summary["milestone"] != "B":
        raise ValueError("Milestone B must be complete")
    return reconstruct_package(package, output_dir, review_dir=str(review_dir))


def reconstruct_package(package, output_dir, *, review_dir=None):
    """Reconstruct validated masks; automated cases do not claim Slicer review."""
    output_dir = Path(output_dir).resolve()
    if package.get("status") != "prepared_pending_slicer_review" or not package["structures"]:
        raise ValueError("A validated nonempty cardiac package is required")
    ct = nib.load(package["ct_path"])
    affine = nifti_affine_mm(ct)
    if file_hash(package["ct_path"]) != package["ct_sha256"]:
        raise ValueError("CT changed since review")
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {"milestone": "C", "status": "running", "review_dir": review_dir,
              "source_ct": package["ct_path"], "source_ct_sha256": package["ct_sha256"],
              "source_engine": package["engine"], "source_version": package["version"],
              "coordinates": {"stl": "RAS millimeters (explicitly select RAS when importing)",
                              "glb": "right-handed Y-up meters: (R,S,-A)/1000",
                              "ras_mm_to_glb": RAS_MM_TO_GLB.tolist()},
              "postprocessing": "no smoothing, decimation, or component removal; padding caps boundaries",
              "structures": [], "measurements": {}, "warnings": []}
    started = time.perf_counter()
    try:
        meshes, colors = {}, {}
        for spec in package["structures"]:
            name = spec["name"]
            if file_hash(spec["path"]) != spec["sha256"]:
                raise ValueError(f"{name}: source mask hash changed")
            image = nib.load(spec["path"])
            if image.shape != ct.shape or not np.allclose(nifti_affine_mm(image), affine, atol=1e-4, rtol=0):
                raise ValueError(f"{name}: source mask grid differs from CT")
            mask, cropped_affine, edge = crop_binary_mask(np.asarray(image.dataobj), affine)
            measurement = measure_structure(mask, cropped_affine)
            if measurement["voxel_count"] != spec["foreground_voxels"]:
                raise ValueError(f"{name}: foreground count changed")
            mesh = mask_to_mesh(mask, cropped_affine)
            if not np.isfinite(mesh.vertex_normals).all():
                raise ValueError(f"{name}: nonfinite normals")
            measurement.update(mesh_measurements(mesh, measurement))
            if not measurement["mesh_voxel_volume_check_passed"]:
                raise ValueError(f"{name}: mesh/voxel volume differs by more than 5 percent")
            paths = export_structure(mesh, output_dir / "meshes", name, spec["color"])
            # Reopen GLB and undo its axis/unit transform. Check every exported
            # vertex, not just a bounding box that could hide axis/reflection bugs.
            loaded = trimesh.load(paths["glb"], force="scene").to_geometry()
            restored = nib.affines.apply_affine(np.linalg.inv(RAS_MM_TO_GLB), loaded.vertices)
            tree = cKDTree(mesh.vertices)
            max_error = float(tree.query(restored)[0].max())
            reverse_error = float(cKDTree(restored).query(mesh.vertices)[0].max())
            if max(max_error, reverse_error) > 0.001:
                raise ValueError(f"{name}: GLB round trip moved vertices by more than 0.001 mm")
            stl = trimesh.load(paths["stl"], force="mesh")
            stl_error = float(tree.query(stl.vertices)[0].max())
            if stl_error > 0.001:
                raise ValueError(f"{name}: STL round trip changed coordinates")
            report["structures"].append({**{k: spec[k] for k in ("name", "label_id", "color", "path", "sha256", "review_center_ras_mm")},
                                          "mesh": validate_mesh(mesh), "boundary_capped": edge,
                                          "glb_vertex_round_trip_max_mm": max(max_error, reverse_error),
                                          "stl_vertex_round_trip_max_mm": stl_error,
                                          "artifacts": {kind: str(path.relative_to(output_dir)) for kind, path in paths.items()}})
            report["measurements"][name] = measurement
            meshes[name], colors[name] = mesh, spec["color"]
            if edge:
                report["warnings"].append(f"{name}: capped at truncated CT field of view; not complete anatomy")
            if measurement["connected_components"] > 1:
                report["warnings"].append(f"{name}: all {measurement['connected_components']} disconnected components retained")
            print(f"{name}: {measurement['volume_ml']:.3f} mL; {len(mesh.faces)} triangles", flush=True)
        export_combined(meshes, colors, output_dir / "meshes/cardiac.glb")
        for item in package["output_inventory"]:
            if file_hash(item["path"]) != item["sha256"]:
                raise ValueError("Source outputs changed during reconstruction")
        (output_dir / "measurements.json").write_text(json.dumps(report["measurements"], indent=2), encoding="utf-8")
        report["status"] = "reconstructed_pending_slicer_alignment"
    except Exception as exc:
        report["status"], report["error"] = "failed", str(exc)
        raise
    finally:
        report["runtime_seconds"] = time.perf_counter()-started
        (output_dir / "reconstruction.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
