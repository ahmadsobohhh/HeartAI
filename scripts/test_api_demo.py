"""Run against a live local API: real multipart upload, polling, artifact checks."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import httpx

from heartai.assets import ROOT


def run(base_url: str) -> None:
    started = time.perf_counter()
    with httpx.Client(base_url=base_url, timeout=120) as client:
        client.get("/health").raise_for_status()
        with (ROOT / "data/demo/CTA-cardio.nii.gz").open("rb") as source:
            response = client.post("/api/cases", files={"file": ("CTA-cardio.nii.gz", source)})
        response.raise_for_status()
        assert response.status_code == 202
        case_id = response.json()["case_id"]
        accepted_seconds = time.perf_counter() - started
        print(f"Accepted {case_id} after {accepted_seconds:.2f}s", flush=True)
        previous = None
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            response = client.get(f"/api/cases/{case_id}/status")
            response.raise_for_status()
            state = response.json()
            if state["status"] != previous:
                print(state["status"], flush=True)
                previous = state["status"]
            if state["status"] == "failed":
                raise RuntimeError(state["error"])
            if state["status"] == "complete":
                break
            client.get("/health").raise_for_status()
            time.sleep(1)
        else:
            raise TimeoutError("Case did not complete within 10 minutes")
        result = client.get(f"/api/cases/{case_id}").json()
        assert len(result["structures"]) == 7
        artifacts = {}
        targets = {"segmentation": b"\x1f\x8b", "overlay": b"\x89PNG", "meshes/heart": b"glTF"}
        targets.update({f"meshes/{s['name']}": b"glTF" for s in result["structures"]})
        for endpoint, signature in targets.items():
            response = client.get(f"/api/cases/{case_id}/{endpoint}")
            response.raise_for_status()
            assert response.content.startswith(signature)
            artifacts[endpoint] = {"bytes": len(response.content), "sha256": hashlib.sha256(response.content).hexdigest()}
        measurements = client.get(f"/api/cases/{case_id}/measurements")
        measurements.raise_for_status()
        assert measurements.json()["structures"] == result["measurements"]
        response = client.get(f"/api/cases/{case_id}/meshes/aorta?format=stl")
        response.raise_for_status()
        assert len(response.content) > 84
        summary = {"case_id": case_id, "accepted_seconds": accepted_seconds,
                   "total_test_seconds": time.perf_counter()-started, "pipeline_timing": result["timing"],
                   "download_checks": artifacts, "result": "passed"}
        output = ROOT / "results/api-validation.json"
        output.write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    run(parser.parse_args().base_url)
