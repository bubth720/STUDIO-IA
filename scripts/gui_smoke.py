import argparse
import json
from pathlib import Path

from studio_ia.smoke import run_smoke

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=Path("artifacts/gui"))
args = parser.parse_args()
print(json.dumps(run_smoke(args.output), indent=2))
