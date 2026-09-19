import argparse
import json
from heartai.preprocessing.loader import load_scan, scan_info

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scan")
    args = parser.parse_args()
    print(json.dumps(scan_info(load_scan(args.scan)), indent=2))
