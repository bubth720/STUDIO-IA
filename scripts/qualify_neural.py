"""Opt-in real GPU qualification; never downloads engines/models or provisions a GPU."""

import argparse
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from studio_ia.core import Cancellation, StudioError, Tools, capture
from studio_ia.files import write_json
from studio_ia.hardware import hardware_report
from studio_ia.media import sha256
from studio_ia.models import inspect, read_manifest
from studio_ia.neural import build_neural_plan, run_neural_plan
from studio_ia.pipeline import Request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--run", action="store_true", help="Explicit local inference, needs all three paths"
    )
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--models", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    hardware = hardware_report()
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    report = {
        "mission": "M004",
        "task_id": "NN01",
        "status": "BLOCKED",
        "tested_commit_sha": sha,
        "tested_source_dirty": dirty,
        "os_arch": platform.platform(),
        "hardware": {"cpu": hardware["cpu"], "gpu": hardware["vulkan"]},
        "engine": {"name": "Real-ESRGAN NCNN Vulkan", "version": None, "model_sha256": None},
        "source_sha256": None,
        "output_sha256": None,
        "tests": {"passed": 0, "failed": 0, "skipped": 1},
        "evidence_paths": [],
        "limitations": [],
        "ci_run_url": None,
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "m005_allowed": False,
    }
    try:
        if hardware["vulkan"]["status"] != "COMPATIBLE":
            raise StudioError("NO_COMPATIBLE_PHYSICAL_GPU: " + hardware["vulkan"]["reason"])
        if not args.run or not all([args.binary, args.manifest, args.models]):
            raise StudioError(
                "Explicit --run with trusted binary and reviewed local model manifest required"
            )
        if dirty:
            raise StudioError("A clean committed source is required for a qualification claim")
        tools = Tools.discover()
        record = inspect(args.models, read_manifest(args.manifest))
        source = args.output / "NN01-source-8s-two-audio.mp4"
        capture(
            [
                tools.ffmpeg,
                "-v",
                "error",
                "-n",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=64x48:rate=8:duration=8",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=8:sample_rate=48000",
                "-itsoffset",
                "0.25",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:duration=7:sample_rate=48000",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-map",
                "2:a",
                "-c:v",
                "libx264",
                "-threads",
                "2",
                "-pix_fmt",
                "yuv420p",
                "-x264-params",
                "colorprim=bt709:transfer=bt709:colormatrix=bt709",
                "-color_range",
                "tv",
                "-c:a",
                "aac",
                str(source),
            ]
        )
        plan = build_neural_plan(
            Request(str(source), str(args.output / "NN01-neural.mp4"), scale=2, denoise="off"),
            tools,
            record,
            args.binary,
        )
        result = run_neural_plan(plan, tools, args.output / "job", Cancellation())
        report.update(
            status="PASS",
            source_sha256=sha256(source),
            output_sha256=result["output_sha256"],
            tests={"passed": 1, "failed": 0, "skipped": 0},
            engine={
                "name": "Real-ESRGAN NCNN Vulkan",
                "version": plan.data["engine"]["version_source"],
                "model_sha256": record.identity,
            },
            evidence_paths=["job/result.json", "job/frames.json", "job/qualification.json"],
            limitations=[
                "Single synthetic sequence; NN02 and visual review remain required; "
                "GPU fault campaign is separate"
            ],
        )
    except (StudioError, OSError, ValueError) as exc:
        report["limitations"].append(str(exc))
    write_json(args.output / "nn-e2e-001.json", report, replace=False)
    print(json.dumps(report, indent=2))
    # Even a real NN01 PASS does not automatically accept all M004 gates.
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
