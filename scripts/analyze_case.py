"""Run the authorized V1 CLI milestone; no backend or frontend."""
import argparse
import json



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CT -> pretrained segmentation -> meshes -> measurements")
    parser.add_argument("scan")
    parser.add_argument("--case-id", help="Optional new case ID; never overwrites existing results")
    parser.add_argument("--engine", choices=["totalseg", "monai"], default="totalseg")
    parser.add_argument("--totalseg-python", help="Separate TotalSegmentator environment's Python executable")
    parser.add_argument("--cases-dir", default="results/cases")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "gpu"], default=None)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.engine == "monai":
        from heartai.pipeline.analyze import analyze_case
        if args.device == 'gpu':
            parser.error('Use --device cuda for legacy MONAI')
        result = analyze_case(args.scan, args.case_id, cases_dir=args.cases_dir,
                              device=args.device or 'auto', threads=args.threads)
    else:
        from heartai.pipeline.totalseg import analyze_case
        if args.device in ('auto', 'cuda'):
            parser.error('TotalSegmentator accepts --device cpu or gpu; default is cpu')
        result = analyze_case(args.scan, args.case_id, cases_dir=args.cases_dir,
                              device=args.device or 'cpu', totalseg_python=args.totalseg_python)
    print(json.dumps(result, indent=2))
