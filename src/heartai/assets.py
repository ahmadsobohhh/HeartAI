"""Pinned public assets; verify bytes before loading configs/checkpoints."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "models/wholeBody_ct_segmentation"
MANIFEST = ROOT / "assets.json"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_asset(path):
    path = Path(path).resolve()
    relative = path.relative_to(ROOT).as_posix()
    expected = json.loads(MANIFEST.read_text())[relative]["sha256"]
    if sha256(path) != expected:
        raise ValueError(f"Checksum mismatch: {path}. Run scripts/download_assets.py.")


def download_assets():
    for relative, asset in json.loads(MANIFEST.read_text()).items():
        path = ROOT / relative
        if path.exists() and sha256(path) == asset["sha256"]:
            print(f"Verified {relative}", flush=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".part")
        print(f"Downloading {relative}", flush=True)
        with urllib.request.urlopen(asset["url"], timeout=120) as source, temporary.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        if sha256(temporary) != asset["sha256"]:
            raise ValueError(f"Downloaded checksum mismatch: {relative}")
        temporary.replace(path)


def prepare_demo():
    """Convert Slicer's public NRRD to NIfTI without resampling or cropping."""
    import SimpleITK as sitk
    import numpy as np

    source = ROOT / "data/raw/CTA-cardio.nrrd"
    verify_asset(source)
    target = ROOT / "data/demo/CTA-cardio.nii.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = sitk.ReadImage(str(source))
    sitk.WriteImage(image, str(target))
    restored = sitk.ReadImage(str(target))
    assert restored.GetSize() == image.GetSize()
    np.testing.assert_allclose(restored.GetSpacing(), image.GetSpacing(), atol=1e-6)
    np.testing.assert_allclose(restored.GetOrigin(), image.GetOrigin(), atol=1e-4)
    np.testing.assert_allclose(restored.GetDirection(), image.GetDirection(), atol=1e-6)
    np.testing.assert_array_equal(sitk.GetArrayViewFromImage(restored), sitk.GetArrayViewFromImage(image))
    print(f"Converted and verified physical grid and voxel values: {target}", flush=True)
