import json
from pathlib import Path
import platform
import time

import monai
import numpy as np
import torch

from heartai.assets import BUNDLE, ROOT, sha256
from heartai.inference.model import load_model
from heartai.preprocessing.loader import load_scan, scan_info, save_segmentation
from heartai.preprocessing.transforms import inference_config
from heartai.visualization import CARDIAC, create_overlay


def segment_scan(path, output_dir=None, device="auto", threads=4):
    """Run the unchanged published 3-mm checkpoint and restore the native grid."""
    started = time.perf_counter()
    path = Path(path).resolve()
    output_dir = Path(output_dir or ROOT / "results")
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device not in ("cpu", "cuda"):
        raise ValueError("Device must be auto, cpu, or cuda")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if threads < 1:
        raise ValueError("threads must be positive")
    torch.set_num_threads(threads)
    print(f"Loading {path.name}; device={device}", flush=True)
    scan = load_scan(path)
    info = scan_info(scan)
    print(json.dumps(info), flush=True)
    parser = inference_config(device)
    preprocessing = parser.get_parsed_content("preprocessing")
    network = load_model(parser, device)
    print("Applying official RAS / 3-mm / intensity preprocessing", flush=True)
    batch = preprocessing({"image": str(path)})
    image = batch["image"]
    inferer = parser.get_parsed_content("inferer")
    inference_started = time.perf_counter()
    print(f"Running pretrained model: input tensor {tuple(image.shape)}", flush=True)
    with torch.inference_mode(), torch.autocast("cuda", enabled=device == "cuda"):
        logits = inferer(image.unsqueeze(0), network)
    if device == "cuda":
        torch.cuda.synchronize()
    inference_seconds = time.perf_counter() - inference_started
    expected = (1, 105, *image.shape[1:])
    if tuple(logits.shape) != expected or not torch.isfinite(logits).all():
        raise RuntimeError("Invalid network output shape or values")
    batch["pred"] = logits[0]
    result = parser.get_parsed_content("postprocessing")(batch)
    restored = result["pred"]
    if not np.allclose(restored.affine.cpu().numpy(), scan.affine, atol=1e-4):
        raise RuntimeError("Inverse transforms did not restore the input affine")
    labels = restored[0].cpu().numpy()
    case = path.name.removesuffix(".gz").removesuffix(".nii")
    segmentation_path = save_segmentation(labels, scan, output_dir / "segmentations" / f"{case}.nii.gz")
    overlay_path = output_dir / "overlays" / f"{case}.png"
    slices = create_overlay(path, segmentation_path, overlay_path)
    report = {
        "model": "MONAI wholeBody_ct_segmentation 0.2.7 / model_lowres.pt",
        "checkpoint_sha256": sha256(BUNDLE / "models/model_lowres.pt"),
        "input_path": str(path), "input_sha256": sha256(path), "input": info,
        "device": device, "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "python": platform.python_version(), "torch": torch.__version__, "monai": monai.__version__,
        "threads": threads, "preprocessed_shape": list(image.shape),
        "logits_shape": list(logits.shape), "output_shape": list(labels.shape),
        "predicted_labels": [int(v) for v in np.unique(labels)],
        "cardiac_labels_present": {str(k): v for k, v in CARDIAC.items() if np.any(labels == k)},
        "inference_seconds": inference_seconds,
        "total_seconds": time.perf_counter() - started,
        "segmentation_path": str(segmentation_path.resolve()),
        "overlay_path": str(overlay_path.resolve()), "overlay_ras_slices": slices,
    }
    report_path = output_dir / "reports" / f"{case}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    return report
