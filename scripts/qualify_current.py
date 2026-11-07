"""Repeatable CPU/Qt/frozen-package qualification; requires preinstalled dependencies."""

import os
import subprocess
import sys
from pathlib import Path

from studio_ia import __version__

root = Path(__file__).resolve().parents[1]
artifacts = root / "artifacts"
artifacts.mkdir(exist_ok=True)
env = dict(os.environ)
env.setdefault("STUDIO_IA_GUI_EVIDENCE", str(artifacts / "gui"))
commands = [
    ["-m", "ruff", "check", "src", "tests", "scripts"],
    ["-m", "ruff", "format", "--check", "src", "tests", "scripts"],
    [
        "-m",
        "mypy",
        *[f"src/studio_ia/{name}.py" for name in ("core", "media", "pipeline", "jobs", "files")],
    ],
    ["-m", "pytest", "-q", "-ra", "--junitxml=artifacts/pytest.xml"],
    ["scripts/run_e2e.py", "--output", "artifacts/e2e"],
    ["scripts/package.py"],
]
for args in commands:
    subprocess.run([sys.executable, *args], cwd=root, env=env, check=True)
archives = list((root / "dist").glob(f"STUDIO-IA-{__version__}-*.zip"))
if len(archives) != 1:
    raise RuntimeError("Expected exactly one package of the current version")
subprocess.run(
    [
        sys.executable,
        "scripts/check_archive.py",
        str(archives[0]),
        "--output",
        "artifacts/extracted-package",
    ],
    cwd=root,
    env=env,
    check=True,
)
