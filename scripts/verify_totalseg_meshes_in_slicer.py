"""Run with Slicer --python-script; independently rasterize exported STL files."""
import hashlib
import json
import os
from pathlib import Path
import traceback

import numpy as np
import qt
import slicer
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import ScreenCapture


def run():
    root = Path(os.environ["HEARTAI_MESH_CASE"]).resolve()
    output = root / os.environ.get("HEARTAI_MESH_REVIEW_FOLDER", "slicer-check")
    output.mkdir(exist_ok=False)
    try:
        report = json.loads((root / os.environ.get(
            "HEARTAI_MESH_RECONSTRUCTION_REPORT", "reconstruction.json")).read_text())
        ct = slicer.util.loadVolume(report["source_ct"])
        ct.GetDisplayNode().AutoWindowLevelOff()
        ct.GetDisplayNode().SetWindowLevel(400, 40)
        ras_to_ijk = vtk.vtkMatrix4x4()
        ct.GetRASToIJKMatrix(ras_to_ijk)
        transform = vtk.vtkTransform()
        transform.SetMatrix(ras_to_ijk)
        layout = slicer.app.layoutManager()
        layout.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        slicer.util.setSliceViewerLayers(background=ct)
        slicer.util.resetSliceViews()
        capture = ScreenCapture.ScreenCaptureLogic()
        checks, models = [], []
        for spec in report["structures"]:
            # STL is unitless. Read raw points explicitly as RAS millimeters,
            # avoiding Slicer's default LPS model-file convention.
            reader = vtk.vtkSTLReader()
            reader.SetFileName(str(root / spec["artifacts"]["stl"]))
            reader.Update()
            poly = reader.GetOutput()
            bounds = np.asarray(poly.GetBounds()).reshape(3, 2).T
            if not np.allclose(bounds, spec["mesh"]["bounds_mm"], atol=0.001, rtol=0):
                raise ValueError(f"{spec['name']}: exported bounds mismatch")
            model = slicer.modules.models.logic().AddModel(poly)
            model.SetName(spec["name"] + " exported STL")
            models.append(model)
            display = model.GetDisplayNode()
            display.SetColor(*(int(spec["color"][i:i+2], 16)/255 for i in (1, 3, 5)))
            display.SetOpacity(0.7)
            display.SetVisibility2D(True)
            display.SetSliceIntersectionThickness(2)
            # Classify every original CT voxel center using VTK, independently
            # of the scikit-image/trimesh reconstruction implementation.
            transformed = vtk.vtkTransformPolyDataFilter()
            transformed.SetInputData(poly)
            transformed.SetTransform(transform)
            stencil = vtk.vtkPolyDataToImageStencil()
            stencil.SetInputConnection(transformed.GetOutputPort())
            stencil.SetOutputOrigin(0, 0, 0)
            stencil.SetOutputSpacing(1, 1, 1)
            stencil.SetOutputWholeExtent(ct.GetImageData().GetExtent())
            raster = vtk.vtkImageStencilToImage()
            raster.SetInputConnection(stencil.GetOutputPort())
            raster.SetInsideValue(1)
            raster.SetOutsideValue(0)
            raster.SetOutputScalarTypeToUnsignedChar()
            raster.Update()
            data = vtk_to_numpy(raster.GetOutput().GetPointData().GetScalars()).reshape(
                tuple(reversed(ct.GetImageData().GetDimensions())))
            source = slicer.util.loadLabelVolume(spec["path"])
            original = slicer.util.arrayFromVolume(source)
            mismatch = int(np.count_nonzero(data != original))
            if mismatch:
                raise ValueError(f"{spec['name']}: {mismatch} voxel centers differ")
            checks.append({"name": spec["name"], "bounds_match_mm": True,
                           "rasterized_foreground_voxels": int(np.count_nonzero(data)),
                           "voxel_center_mismatches": mismatch})
            slicer.mrmlScene.RemoveNode(source)
            del data, original
            print(f"{spec['name']}: exact exported-mesh voxel-center agreement", flush=True)

        def center(spec):
            for name in layout.sliceViewNames():
                widget = layout.sliceWidget(name)
                widget.sliceLogic().FitSliceToAll()
                widget.mrmlSliceNode().JumpSliceByCentering(*spec["review_center_ras_mm"])
                matrix = widget.mrmlSliceNode().GetSliceToRAS()
                array = np.array([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])
                if abs(np.linalg.solve(array, np.r_[spec["review_center_ras_mm"], 1])[2]) > 1e-4:
                    raise ValueError("Capture plane misses selected review point")
                widget.sliceView().forceRender()
            slicer.app.processEvents()

        for spec, model in zip(report["structures"], models):
            for other in models:
                other.GetDisplayNode().SetVisibility(other == model)
            center(spec)
            for name, plane in [("Red", "axial"), ("Green", "coronal"), ("Yellow", "sagittal")]:
                capture.captureImageFromView(layout.sliceWidget(name).sliceView(),
                                             str(output / f"{spec['name']}_{plane}.png"))
        for model in models:
            model.GetDisplayNode().SetVisibility(True)
        center(report["structures"][0])
        slicer.util.resetThreeDViews()
        camera = slicer.modules.cameras.logic().GetViewActiveCameraNode(
            layout.threeDWidget(0).mrmlViewNode()).GetCamera()
        camera.Zoom(2.0)
        layout.threeDWidget(0).threeDView().forceRender()
        capture.captureImageFromView(None, str(output / "four_up.png"))
        capture.captureImageFromView(layout.threeDWidget(0).threeDView(), str(output / "exported_meshes.png"))
        if not slicer.util.saveScene(str(output / "meshes-on-ct.mrb")):
            raise RuntimeError("Cannot save Slicer scene")
        verification = {"status": "technical_checks_passed_visual_review_pending",
                        "slicer_version": slicer.app.applicationVersion,
                        "coordinate_system": "STL raw RAS mm; no implicit LPS conversion",
                        "checks": checks, "clinical_validation": False,
                        "meaning": "Mesh serialization and spatial fidelity, not segmentation accuracy",
                        "captures": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in output.glob("*.png")}}
        (output / "verification.json").write_text(json.dumps(verification, indent=2))
        slicer.app.exit(0)
    except Exception:
        (output / "error.txt").write_text(traceback.format_exc())
        traceback.print_exc()
        slicer.app.exit(1)


qt.QTimer.singleShot(1000, run)
