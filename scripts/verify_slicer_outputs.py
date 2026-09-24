"""Independently check the actual Slicer round trip with nibabel and measurements."""
import json
from pathlib import Path
import nibabel as nib
import numpy as np

from heartai.assets import sha256

root = Path(__file__).resolve().parents[1]
output = root / "results/slicer/runtime-validation"
runtime = json.loads((output / "result.json").read_text())
package = json.loads((root / "results/slicer/788812d5bc03-initial/review_package.json").read_text())
case = root / "results/cases/788812d5bc03"
source = nib.load(package["cardiac_labels_path"])
expected = np.asarray(source.dataobj)
records = {}
for kind in ("baseline", "edited"):
    exported = Path(runtime[kind])
    revision = case / "reviews" / exported.name
    record = json.loads((revision / "review.json").read_text())
    image = nib.load(revision / "cardiac_labels.nii.gz")
    assert image.shape == source.shape
    np.testing.assert_allclose(image.affine, source.affine, atol=1e-6, rtol=0)
    assert image.header.get_xyzt_units()[0] == "mm"
    for form in ("qform", "sform"):
        np.testing.assert_allclose(getattr(image, f"get_{form}")(), getattr(source, f"get_{form}")(), atol=1e-6, rtol=0)
        assert image.header[form + "_code"] == source.header[form + "_code"]
    actual = np.asarray(image.dataobj)
    if kind == "baseline":
        np.testing.assert_array_equal(actual, expected)
    else:
        index = tuple(runtime["removed_voxel_kji"][::-1])
        changed = np.argwhere(actual != expected)
        np.testing.assert_array_equal(changed, [index])
        assert expected[index] == 44 and actual[index] == 0
    for path, digest in record["artifacts"].items():
        assert sha256(revision / path) == digest
    records[kind] = record
for key in ("ct", "prediction", "cardiac_labels"):
    assert sha256(package[key + "_path"]) == package[key + "_sha256"]
parent = json.loads((case / "manifest.json").read_text())
assert parent["measurements"] == records["baseline"]["measurements"]
delta = records["baseline"]["measurements"]["myocardium"]["volume_ml"] - records["edited"]["measurements"]["myocardium"]["volume_ml"]
voxel_ml = abs(np.linalg.det(source.affine[:3, :3])) / 1000
np.testing.assert_allclose(delta, voxel_ml, atol=1e-10, rtol=0)
report = {"baseline_changed_voxels": 0, "edited_changed_voxels": 1,
          "myocardium_volume_decrease_ml": delta, "expected_voxel_volume_ml": voxel_ml,
          "original_hashes_unchanged": True, "original_measurements_equal_baseline": True,
          "geometry_and_coded_forms_preserved": True, "all_revision_artifact_hashes_match": True}
(output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
