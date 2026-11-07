"""Verify the delivered ZIP itself, extract safely, then test its frozen executable."""

import argparse
import json
import os
import stat
import subprocess
import zipfile
from pathlib import Path

from studio_ia.media import sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive, output = args.archive.resolve(), args.output.resolve()
    if output.exists():
        raise RuntimeError("Use a new extraction directory to preserve previous evidence")
    expected = archive.with_suffix(archive.suffix + ".sha256").read_text().split()[0]
    if sha256(archive) != expected:
        raise ValueError("ZIP SHA-256 mismatch")
    output.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise ValueError("Corrupt ZIP member")
        for member in zipped.infolist():
            path = (output / member.filename).resolve()
            if not path.is_relative_to(output) or stat.S_ISLNK(member.external_attr >> 16):
                raise RuntimeError("Unsafe archive member")
        zipped.extractall(output)
    folder = output / "STUDIO-IA"
    files = json.loads((folder / "FILES_SHA256.json").read_text(encoding="utf-8"))
    for name, checksum in files.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder):
            raise ValueError("Unsafe inventory path")
        if sha256(path) != checksum:
            raise ValueError(f"File checksum mismatch: {name}")
    actual_files = {str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()}
    if actual_files != set(files) | {"FILES_SHA256.json"}:
        raise ValueError("Unlisted files in bundle")
    executable = folder / ("STUDIO-IA.exe" if os.name == "nt" else "STUDIO-IA")
    if os.name != "nt":
        executable.chmod(0o755)
        (folder / "Lancer-STUDIO-IA.sh").chmod(0o755)
    env = {
        key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "VIRTUAL_ENV")
    }
    env["STUDIO_IA_HOME"] = str(output / "state")
    subprocess.run(
        [str(executable), "--smoke", "--output", str(output / "gui")],
        cwd=output,
        env=env,
        check=True,
        timeout=180,
    )
    report = {
        "archive_sha256": expected,
        "file_hashes_verified": len(files),
        "zip_integrity": "PASS",
        "extracted_frozen_smoke": "PASS",
        "build": json.loads((folder / "BUILD_INFO.json").read_text(encoding="utf-8")),
    }
    (output / "archive-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
