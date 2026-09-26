# Milestone F — CT volume viewer

Completed on 2026-09-26. This milestone loads the **original CT** into a VTK.js GPU volume renderer. It stops before segmentation overlays (G) and clipping (H). No inference, training, or fine-tuning was performed for F.

![HeartAI CT volume viewer](images/ct-volume-browser.png)

## What works

- `/volume` is a separate Next.js client route; the existing MONAI page and pipeline are preserved.
- A completed TotalSegmentator case is fetched from the Milestone E API. The downloaded NIfTI SHA-256 must match the manifest before rendering.
- `nifti-reader-js` decodes the actual full-resolution scan. Scalar endianness, slope/intercept, dimensions, millimetre units, and affine are checked. Affine disagreements and sheared grids are rejected explicitly.
- VTK.js image origin, spacing, and column-major direction preserve NIfTI RAS millimetres. No resampling, axis reversal, invented anatomy, or mesh substitution is used.
- WebGL 2 volume ray casting supports drag rotation, Shift-drag pan, scroll zoom, pan buttons, and anterior reset. Contrast CT, Bone, and Soft tissue are intensity transfer functions, not anatomical classifications.
- Resize observation, cancellation, renderer disposal, missing-case errors, and same-case retry are implemented. The source/geometry disclosure reports the hash, geometry, GPU adapter, and current camera.

Implementation: [`VolumeViewer.tsx`](../frontend/components/VolumeViewer.tsx), [`ct-volume.ts`](../frontend/lib/ct-volume.ts), and [`app/volume/page.tsx`](../frontend/app/volume/page.tsx). Dependencies are pinned to VTK.js 37.3.1 and nifti-reader-js 0.8.0.

## Real scan and independent checks

Case: `PUBLIC-001-D-final`, from the previously completed pipeline. Source SHA-256:

```text
d8b3846d2784d9bc8d2611b820183c7edee0c338fb7634b2e5eac89645120709
```

| Check | Result |
| --- | --- |
| Dimensions | 512 × 512 × 321; 84,148,224 voxels |
| Spacing | 0.9335939884 × 0.9335939884 × 1.25 mm |
| Voxel (0,0,0), RAS | (238.5332642, 238.5332642, −200) mm |
| Voxel (511,511,320), RAS | (−238.5332639, −238.5332639, 200) mm |
| Intensity range | −1024 to 3532 |
| Decoded float32 voxel SHA-256 | `45280303bb3e15809b835deb78d6fd71a236c06f431c54b59e5cd70bd31829f4` |
| Browser adapter | ANGLE / AMD Radeon RX 7800 XT / Direct3D 11 |
| Slicer | 5.12.4, GPU ray-cast volume rendering |
| Spatial comparison | All eight voxel-centre corners agree within 0.00001 mm |
| Scalar comparison | Hash of every decoded float32 voxel exactly matches Slicer |

Slicer independently loads the same NIfTI, compares its IJK-to-RAS matrix and scalar array, and renders all three browser transfer functions. Visual inspection confirms the same anterior orientation, extent, ribs, spine, arm, and scan equipment. Rendering engines have different lighting and sampling; pixel equality is neither expected nor claimed. Patient right is on the left in the reset anterior view, with superior up. VTK image bounds include the outer half-voxel extent; the table above reports voxel centres.

Browser interaction evidence records an actual drag changing camera position and view-up, a pan translating position and focal point together by 25 mm, scroll zoom reducing camera distance, and reset restoring the original camera. All three presets were exercised. A nonexistent case returned a visible 404 error; reopening the real case recovered successfully. Desktop and narrow layouts were inspected.

## Reproduce

Start the backend using the [Milestone E instructions](TOTALSEG_MILESTONE_E.md). In another terminal:

```powershell
cd frontend
npm ci
# Only needed if the backend uses a different port:
# $env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:8765'
npm run dev
```

Open `http://127.0.0.1:3000/volume`. Enter your completed case ID and click **Open CT**. The prefilled `PUBLIC-001-D-final` is the local evidence case, not a bundled result. The verified session used backend port 8765 and frontend port 3000.

Numerical checks and real-data export, from `frontend` (Node 22.18+ with TypeScript stripping, tested on Node 26.7):

```powershell
npm run typecheck
npm run lint
npm run build
node scripts/verify-ct.mjs ../results/cases/PUBLIC-001-D-final/manifest.json
```

Nine geometry/scaling/endian/compression combinations passed. The real-data check additionally verifies the file hash and every physical corner, and writes `results/milestone-f-volume.json`. Build, lint, and type checking passed. A Node module-type warning in this standalone numerical script is harmless.

For the independent Slicer check, set `HEARTAI_ROOT` to the repository root and launch Slicer with `--no-splash --ignore-slicerrc --python-script scripts/verify_ct_volume_in_slicer.py` (use an absolute script path). This runs in a separate Slicer process and exits after writing evidence; it does not modify an existing user scene.

Local evidence (large outputs remain Git-ignored):

- `results/milestone-f-volume.json`: decoded scalar hash, geometry, eight corners, exact preset points.
- `results/milestone-f-browser.json`: observed adapter and camera states from browser interactions.
- `results/milestone-f-slicer/verification.json`: independent scalar and geometry comparison.
- `results/milestone-f-slicer/{contrast,bone,tissue}.png`: actual Slicer volume captures.
- `results/milestone-f-{bone,tissue}-browser.png`: browser preset captures.
- `docs/images/ct-volume-browser.png`: repository screenshot for GitHub.

## Limits

This is a technical rendering verification on one public scan, not clinical validation. The presets also reveal bones, skin, wires, and equipment present in the CT. They do not isolate coronary arteries or cardiac chambers. Full-resolution decoding uses substantial host and GPU memory (the float32 voxel array alone is about 321 MiB); unsupported WebGL 2 environments receive an error. Segmentation still uses the previously tested CPU path—AMD browser rendering does not imply AMD inference support.

VTK references: [ImageData](https://kitware.github.io/vtk-js/api/Common_DataModel_ImageData.html), [VolumeMapper](https://kitware.github.io/vtk-js/api/Rendering_Core_VolumeMapper.html), [GenericRenderWindow](https://kitware.github.io/vtk-js/api/Rendering_Misc_GenericRenderWindow.html).
