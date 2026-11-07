"""Actual CPU E2E: generates F01, processes, asserts and emits evidence."""

import argparse
import json
import platform
import subprocess
from dataclasses import asdict
from pathlib import Path

from generate_fixtures import fixture

from studio_ia.core import Tools, capabilities
from studio_ia.media import analyze, sha256
from studio_ia.pipeline import Request, build_plan, run_plan


def e2e(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    tools = Tools.discover()
    source = fixture(tools, root / "F01_with_audio.mp4")
    before_hash = sha256(source)
    request = Request(str(source), str(root / "result_cpu.mp4"), scale=2)
    plan = build_plan(request, tools)
    result = run_plan(plan, tools, root / "job")
    after = analyze(Path(request.destination), tools)
    assert (after.video["width"], after.video["height"]) == (640, 360)
    assert len(after.audio) == 1 and after.duration and abs(after.duration - 8) <= 0.25
    assert sha256(source) == before_hash
    assert all(result["assertions"].values())
    try:
        source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        source_commit = "unknown"
    summary = {
        "status": "PASS",
        "machine": platform.platform(),
        "source_commit": source_commit,
        "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "request": asdict(request),
        "assertions": result["assertions"],
        "source_sha256": before_hash,
        "output_sha256": result["output_sha256"],
        "elapsed_seconds": result["elapsed_seconds"],
        "engine_version": plan.engine_version,
    }
    for name, content in (
        ("e2e-summary.json", summary),
        ("doctor-report.json", capabilities(tools)),
        ("ffprobe-before.json", plan.media.raw),
        ("ffprobe-after.json", result["ffprobe_after"]),
    ):
        (root / name).write_text(
            json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/e2e"))
    args = parser.parse_args()
    e2e(args.output.resolve())
