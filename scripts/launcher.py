"""Frozen executable: desktop by default, CLI and real GUI smoke explicitly available."""

import argparse
import json
import sys
from pathlib import Path

if "--smoke" in sys.argv:
    from studio_ia.smoke import run_smoke

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_smoke(args.output), indent=2))
elif "--temporal-smoke" in sys.argv:
    from studio_ia.temporal_smoke import run_temporal_smoke

    parser = argparse.ArgumentParser()
    parser.add_argument("--temporal-smoke", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_temporal_smoke(args.output), indent=2))
elif "--machine" in sys.argv:
    from studio_ia.files import write_json
    from studio_ia.system_profile import profile

    parser = argparse.ArgumentParser()
    parser.add_argument("--machine", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = profile(args.output.parent)
    write_json(args.output, data)
    print(json.dumps(data["capabilities"], indent=2))
elif "--create" in sys.argv:
    from studio_create.cli import main as create_main

    sys.argv.remove("--create")
    raise SystemExit(create_main(sys.argv[1:]))
elif "--cli" in sys.argv:
    from studio_ia.cli import main

    sys.argv.remove("--cli")
    main()
else:
    from studio_ia.ui import main

    main()
