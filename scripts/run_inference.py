import argparse
from heartai.inference.predictor import segment_scan

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pretrained CT inference only")
    parser.add_argument("scan")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    segment_scan(args.scan, args.output_dir, args.device, args.threads)
