from dataclasses import dataclass
from pathlib import Path
import os

from heartai.assets import ROOT


@dataclass(frozen=True)
class Settings:
    cases_dir: Path = ROOT / "results/cases"
    uploads_dir: Path = ROOT / "data/uploads"
    jobs_dir: Path = ROOT / "results/jobs"
    demo_path: Path = ROOT / "data/demo/CTA-cardio.nii.gz"
    max_upload_bytes: int = 256 * 1024 * 1024
    max_voxels: int = 128_000_000
    max_pending: int = 4
    engine: str = os.environ.get("HEARTAI_ENGINE", "totalseg")
    device: str = os.environ.get("HEARTAI_DEVICE", "cpu")
    totalseg_python: str | None = os.environ.get("HEARTAI_TOTALSEG_PYTHON")
    threads: int = 4
    origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
