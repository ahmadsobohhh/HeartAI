"""Rebuild a Slicer draft export in a new case revision; never run AI inference."""
import argparse
from pathlib import Path
from heartai.pipeline.review import accept_review

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("export_dir", type=Path)
    args = parser.parse_args()
    result = accept_review(args.case_dir, args.export_dir)
    print(f"Draft rebuilt: {result['directory']}\nChanged voxels: {result['changed_voxels']}")
