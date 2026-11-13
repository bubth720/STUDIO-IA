"""Build, launch in a distinct directory, then archive a tested onedir application."""

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

from studio_ia import __version__
from studio_ia.media import sha256

ROOT = Path(__file__).resolve().parents[1]


def package():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--name",
            "STUDIO-IA",
            "--distpath",
            str(output),
            "--workpath",
            str(ROOT / "build"),
            "--specpath",
            str(ROOT / "build"),
            "--hidden-import",
            "studio_ia.cli",
            "--hidden-import",
            "studio_ia.smoke",
            "--hidden-import",
            "PySide6.QtTest",
            "--hidden-import",
            "studio_create.ui_panel",
            "--hidden-import",
            "studio_create.cli",
            "--hidden-import",
            "studio_ia.hardware_panel",
            "--add-data",
            f"{ROOT / 'unreal-template'}{os.pathsep}unreal-template",
            str(ROOT / "scripts/launcher.py"),
        ],
        check=True,
        cwd=ROOT,
    )
    folder = output / "STUDIO-IA"
    for name in ("INSTALLER.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "requirements-runtime.lock"):
        shutil.copy2(ROOT / name, folder / name)
    shutil.copytree(ROOT / "licenses", folder / "licenses", dirs_exist_ok=True)
    for extra in ("Lancer-STUDIO-IA.sh", "Lancer-STUDIO-IA.cmd", "PREMIER-LANCEMENT.txt"):
        shutil.copy2(ROOT / "packaging" / extra, folder / extra)
    if os.name != "nt":
        (folder / "Lancer-STUDIO-IA.sh").chmod(0o755)
    if platform.system() == "Linux":
        from collect_binary_licenses import collect

        collect(ROOT / "build/STUDIO-IA/Analysis-00.toc", folder)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))
    manifest = {
        "application": "STUDIO IA",
        "version": __version__,
        "label": "ALPHA / EXPERIMENTAL",
        "source_commit": commit,
        "source_dirty": dirty,
        "platform": platform.platform(),
        "glibc": platform.libc_ver() if platform.system() == "Linux" else None,
        "python": platform.python_version(),
        "packager": "PyInstaller " + importlib.metadata.version("pyinstaller"),
        "qt_binding": importlib.metadata.version("PySide6-Essentials"),
        "ffmpeg_bundled": False,
        "neural_models_bundled": False,
    }
    (folder / "BUILD_INFO.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    executable = folder / ("STUDIO-IA.exe" if os.name == "nt" else "STUDIO-IA")
    smoke = (
        ROOT
        / "artifacts"
        / (f"frozen-smoke-{platform.system().lower()}-{commit[:8]}-{uuid.uuid4().hex[:8]}")
    )
    if smoke.exists():
        raise RuntimeError(f"Test output already exists: {smoke}; use a fresh worktree/output.")
    smoke.mkdir(parents=True)
    # No PYTHONPATH, no source working directory, no venv executable to launch the application.
    env = {
        key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "VIRTUAL_ENV")
    }
    env["STUDIO_IA_HOME"] = str(smoke / "state")
    completed = subprocess.run(
        [str(executable), "--cli", "doctor", "--json", str(smoke / "doctor.json")],
        cwd=smoke,
        env=env,
        timeout=60,
        check=False,
        capture_output=True,
        text=True,
    )
    (smoke / "doctor-launch.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    completed.check_returncode()
    completed = subprocess.run(
        [str(executable), "--smoke", "--output", str(smoke / "gui")],
        cwd=smoke,
        env=env,
        timeout=180,
        check=False,
        capture_output=True,
        text=True,
    )
    (smoke / "gui-launch.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    completed.check_returncode()
    smoke_report = json.loads((smoke / "gui/gui-smoke.json").read_text(encoding="utf-8"))
    if smoke_report["status"] != "PASS" or not smoke_report["frozen"]:
        raise RuntimeError("A real successful frozen application smoke is required")
    shutil.copy2(smoke / "gui/gui-smoke.json", folder / "BUILD_SMOKE.json")
    temporal = smoke / "temporal"
    subprocess.run(
        [str(executable), "--temporal-smoke", "--output", str(temporal)],
        cwd=smoke,
        env=env,
        timeout=120,
        check=True,
    )
    subprocess.run(
        [
            str(executable),
            "--cli",
            "temporal-audit",
            str(temporal / "synthetic-source.mp4"),
            "--audio",
            "--motion",
            "--json",
            str(temporal / "audit.json"),
        ],
        cwd=smoke,
        env=env,
        timeout=120,
        check=True,
    )
    subprocess.run(
        [
            str(executable),
            "--cli",
            "interpolation-plan",
            str(temporal / "synthetic-source.mp4"),
            "--x2",
            "--json",
            str(temporal / "x2-plan.json"),
        ],
        cwd=smoke,
        env=env,
        timeout=120,
        check=True,
    )
    shutil.copy2(temporal / "temporal-smoke.json", folder / "BUILD_TEMPORAL_SMOKE.json")
    # Inventory every distributed binary/data file; archive checksum is emitted separately.
    files = {
        str(path.relative_to(folder)): sha256(path)
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }
    (folder / "FILES_SHA256.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
    archive = (
        output
        / f"STUDIO-IA-{__version__}-{platform.system().lower()}-{platform.machine()}-ALPHA.zip"
    )
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zipped.write(path, str(Path(folder.name) / path.relative_to(folder)))
    checksum = sha256(archive)
    archive.with_suffix(archive.suffix + ".sha256").write_text(f"{checksum}  {archive.name}\n")
    print(
        json.dumps({"archive": str(archive), "sha256": checksum, "smoke": smoke_report}, indent=2)
    )


if __name__ == "__main__":
    package()
