# Screenshot provenance

These repository images are unmodified copies of real HeartAI outputs from the public CTACardio demo. No anatomical geometry, model result, or display was generated for illustration. The PNGs are included here so the main README renders on GitHub without the Git-ignored `results/` directory.

| Repository image | Original local artifact | What it shows |
| --- | --- | --- |
| `ct-and-meshes-slicer.png` | `results/cases/PUBLIC-001-D-final/slicer-check/four_up.png` | Source CT with exported STL contours and surfaces, captured in 3D Slicer 5.12.4 |
| `cardiac-meshes-slicer.png` | `results/cases/PUBLIC-001-D-final/slicer-check/exported_meshes.png` | Actual six-structure cardiac reconstruction in Slicer |
| `axial-overlay.png` | `results/cases/PUBLIC-001-D-final/previews/axial_overlay.png` | Real CT with TotalSegmentator masks, rendered by the pipeline |

The case uses TotalSegmentator 2.18.0, standard `total`, CPU inference. Slicer is the independent inspection application; its interface is not HeartAI's planned browser viewer. The anatomy contains the limitations documented in [Milestone D](../TOTALSEG_MILESTONE_D.md), including scan truncation and retained disconnected components.

CTACardio is distributed through 3D Slicer Sample Data. See [source, checksum, and reuse references](../DATA.md). Screenshots are research illustrations, not ground truth or clinical validation. Source-to-copy hashes are recorded in `provenance.json`.
