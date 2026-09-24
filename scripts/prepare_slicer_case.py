"""Run with HeartAI's Python environment, before opening Slicer."""
import argparse
from pathlib import Path
from heartai.slicer_package import prepare_case

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("output_dir", type=Path, help="New directory; existing packages are never overwritten")
    args = parser.parse_args()
    print(prepare_case(args.case_dir, args.output_dir))
