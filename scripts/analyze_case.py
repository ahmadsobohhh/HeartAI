"""Run the authorized V1 CLI milestone; no backend or frontend."""
import argparse
import json

from heartai.pipeline.analyze import analyze_case


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CT -> pretrained segmentation -> meshes -> measurements")
    parser.add_argument("scan")
    parser.add_argument("--case-id", help="Optional new ID: 8–32 lowercase hexadecimal characters")
    parser.add_argument("--cases-dir", default="results/cases")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    result = analyze_case(args.scan, args.case_id, cases_dir=args.cases_dir,
                          device=args.device, threads=args.threads)
    print(json.dumps(result, indent=2))
