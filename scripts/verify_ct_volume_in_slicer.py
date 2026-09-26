"""Independent Milestone F reference; run with Slicer --python-script."""
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


def run():
    root = Path(os.environ['HEARTAI_ROOT'])
    output = root / 'results' / 'milestone-f-slicer'
    output.mkdir(exist_ok=True)
    try:
        expected = json.loads((root / 'results/milestone-f-volume.json').read_text())
        ct = slicer.util.loadVolume(expected['source'])
        data = slicer.util.arrayFromVolume(ct)
        digest = hashlib.sha256(np.asarray(data, dtype='<f4').tobytes()).hexdigest()
        assert digest == expected['float32VoxelSHA256'], 'Decoded intensities differ'
        matrix = vtk.vtkMatrix4x4()
        ct.GetIJKToRASMatrix(matrix)
        affine = [[matrix.GetElement(r, c) for c in range(4)] for r in range(4)]
        assert np.allclose(affine, expected['affine'], atol=1e-5, rtol=0)
        for corner in expected['corners']:
            assert np.allclose(matrix.MultiplyPoint([*corner['ijk'], 1])[:3], corner['ras'], atol=1e-5, rtol=0)
        layout = slicer.app.layoutManager()
        layout.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
        logic = slicer.modules.volumerendering.logic()
        logic.SetDefaultRenderingMethod('vtkMRMLGPURayCastVolumeRenderingDisplayNode')
        display = logic.CreateDefaultVolumeRenderingNodes(ct)
        display.SetVisibility(True)
        prop = display.GetVolumePropertyNode().GetVolumeProperty()
        prop.SetInterpolationTypeToLinear()
        prop.SetShade(True)
        prop.SetAmbient(.25)
        prop.SetDiffuse(.7)
        prop.SetSpecular(.15)
        prop.SetScalarOpacityUnitDistance(0, 1)
        view = layout.threeDWidget(0).threeDView()
        camera = slicer.modules.cameras.logic().GetViewActiveCameraNode(layout.threeDWidget(0).mrmlViewNode()).GetCamera()
        center = np.mean(np.array([v['ras'] for v in expected['corners']]), axis=0)
        camera.SetFocalPoint(*center)
        camera.SetPosition(center[0], center[1] + 1000, center[2])
        camera.SetViewUp(0, 0, 1)
        slicer.util.resetThreeDViews()
        capture = ScreenCapture.ScreenCaptureLogic()
        for name, preset in expected['presets'].items():
            color, opacity = vtk.vtkColorTransferFunction(), vtk.vtkPiecewiseFunction()
            for hu, r, g, b, alpha in preset['points']:
                color.AddRGBPoint(hu, r, g, b)
                opacity.AddPoint(hu, alpha)
            prop.SetColor(color)
            prop.SetScalarOpacity(opacity)
            slicer.app.processEvents()
            view.forceRender()
            capture.captureImageFromView(view, str(output / f'{name}.png'))
        report = {'status': 'technical_checks_passed', 'slicer_version': slicer.app.applicationVersion, 'voxel_sha256': digest, 'all_voxels_equal': True, 'eight_corners_equal': True, 'affine': affine, 'rendering_class': display.GetClassName(), 'clinical_validation': False}
        (output / 'verification.json').write_text(json.dumps(report, indent=2))
        slicer.app.exit(0)
    except Exception:
        (output / 'error.txt').write_text(traceback.format_exc())
        traceback.print_exc()
        slicer.app.exit(1)


qt.QTimer.singleShot(1000, run)
