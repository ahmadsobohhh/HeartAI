"""Milestone C only; reconstruct existing reviewed masks without inference."""
import argparse
from heartai.reconstruction.totalseg_case import reconstruct_review

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    report = reconstruct_review(args.review_dir, args.output_dir)
    print(f"{report['status']} in {report['runtime_seconds']:.2f} seconds")
