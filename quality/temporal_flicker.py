"""Source-tree compatibility entry point for the bounded CPU temporal metric."""

import argparse
import json
from pathlib import Path

from studio_ia.core import Tools
from studio_ia.motion import analyze_motion

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    _, report = analyze_motion(args.source, Tools.discover())
    print(json.dumps(report, indent=2, ensure_ascii=True))
