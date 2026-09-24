"""Execute the official total CLI and retain real run evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scan", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    parser.add_argument("--timeout", type=float, default=14400)
    args = parser.parse_args()
    os.environ.setdefault("TOTALSEG_HOME_DIR", str(Path(__file__).resolve().parents[1] / "models" / "totalsegmentator"))
    Path(os.environ["TOTALSEG_HOME_DIR"]).mkdir(parents=True, exist_ok=True)
    import nibabel as nib
    import numpy as np
    from totalsegmentator.map_to_binary import class_map

    scan_path = args.scan.resolve(strict=True)
    scan = nib.load(scan_path)
    if (len(scan.shape) != 3 or min(scan.shape) <= 0 or not np.isfinite(scan.affine).all()
            or abs(np.linalg.det(scan.affine[:3, :3])) < 1e-12):
        raise ValueError("Expected a 3D CT with finite spatial metadata")
    if scan.header.get_xyzt_units()[0] != "mm":
        raise ValueError("Expected NIfTI spatial units in millimeters")
    data = np.asarray(scan.dataobj)
    if not np.isfinite(data).all() or data.min() == data.max():
        raise ValueError("Input must contain finite, nonconstant CT intensities")
    del data
    # Probe in a short-lived process. Importing upstream config also imports
    # torch; keeping that copy resident during inference wastes Windows commit.
    probe_code = """
import json, torch
from totalsegmentator.config import get_weights_dir, setup_totalseg, set_config_key
setup_totalseg()
set_config_key('send_usage_stats', False)
print(json.dumps({'torch_version': torch.__version__, 'cuda_available': torch.cuda.is_available(),
                  'weights_dir': str(get_weights_dir())}))
"""
    probe = subprocess.run([sys.executable, '-c', probe_code], check=True, capture_output=True,
                           text=True, timeout=120)
    environment = json.loads(probe.stdout.strip().splitlines()[-1])
    if args.device == "gpu" and not environment['cuda_available']:
        raise ValueError("CUDA was requested but is unavailable")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, "-u", "-m", "totalsegmentator.bin.TotalSegmentator",
               "-i", str(scan_path), "-o", str(output / "segmentations"),
               "--task", "total", "--device", args.device,
               "--nr_thr_resamp", "1", "--nr_thr_saving", "1",
               "--report", str(output / "upstream_report.json")]
    with scan_path.open("rb") as stream:
        scan_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {
        "status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
        "command": command, "engine": "TotalSegmentator", "version": version("TotalSegmentator"),
        "torch_version": environment['torch_version'], "nnunet_version": version("nnunetv2"),
        "task": "total", "device": args.device, "cuda_available": environment['cuda_available'],
        "fast_mode": False, "roi_subset": None, "weights_dir": environment['weights_dir'],
        "input": {"path": str(scan_path), "sha256": scan_hash,
                  "shape": list(scan.shape), "spacing_mm": list(map(float, nib.affines.voxel_sizes(scan.affine))),
                  "affine": scan.affine.tolist(), "orientation": list(nib.aff2axcodes(scan.affine))},
        "runtime_seconds": None,
    }
    report_path = output / "run.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "installed_label_map.json").write_text(json.dumps(class_map["total"], indent=2), encoding="utf-8")
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="6", MKL_NUM_THREADS="6", PYTHONUNBUFFERED="1")
    report["thread_environment"] = {key: env[key] for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS")}
    started = time.perf_counter()
    try:
        with (output / "logs.txt").open("w", encoding="utf-8") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env,
                           check=True, timeout=args.timeout)
        report["status"] = "segmented_pending_validation"
    except (subprocess.SubprocessError, OSError) as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        report["runtime_seconds"] = time.perf_counter() - started
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
