# Screenshot provenance

These repository images are unmodified copies of real HeartAI outputs from the public CTACardio demo. No anatomical geometry, model result, or display was generated for illustration. The PNGs are included here so the main README renders on GitHub without the Git-ignored `results/` directory.

| Repository image | Original local artifact | What it shows |
| --- | --- | --- |
| `ct-and-meshes-slicer.png` | `results/cases/PUBLIC-001-D-final/slicer-check/four_up.png` | Source CT with exported STL contours and surfaces, captured in 3D Slicer 5.12.4 |
| `cardiac-meshes-slicer.png` | `results/cases/PUBLIC-001-D-final/slicer-check/exported_meshes.png` | Actual six-structure cardiac reconstruction in Slicer |
| `axial-overlay.png` | `results/cases/PUBLIC-001-D-final/previews/axial_overlay.png` | Real CT with TotalSegmentator masks, rendered by the pipeline |
| `ct-volume-browser.png` | Direct browser screenshot of `/volume`, case `PUBLIC-001-D-final` | Original CT rendered by VTK.js on AMD RX 7800 XT, Contrast CT preset, anterior view |
| `ct-segmentation-browser.png` | Direct Milestone G browser screenshot of `/volume`, case `PUBLIC-001-D-final` | Six real cardiac surfaces over the original CT, CT opacity 15%, surface opacity 85%, heart selected |

The case uses TotalSegmentator 2.18.0, standard `total`, CPU inference. Slicer is the independent inspection application. The new Milestone F browser screenshot shows CT intensity rendering only; its visible wires and equipment come from the original scan. The mesh images contain the limitations documented in [Milestone D](../TOTALSEG_MILESTONE_D.md), including scan truncation and retained disconnected components.

CTACardio is distributed through 3D Slicer Sample Data. See [source, checksum, and reuse references](../DATA.md). Screenshots are research illustrations, not ground truth or clinical validation. Source-to-copy hashes are recorded in `provenance.json`.
