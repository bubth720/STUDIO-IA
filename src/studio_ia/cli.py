"""CLI uses the same planner, runner and verification as Qt."""

import argparse
import json
import signal
import sys
import uuid
from pathlib import Path

from studio_ia import __version__
from studio_ia.core import Cancellation, StudioError, Tools, capabilities, state_dir
from studio_ia.media import MediaInfo, analyze
from studio_ia.pipeline import Plan, Request, build_plan, run_plan, verify_output


def emit(value: dict, output: str | None) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(payload, encoding="utf-8")
    else:
        print(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="STUDIO IA — restauration vidéo locale")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Diagnostic réel FFmpeg et moteurs locaux")
    doctor.add_argument("--json", dest="json_output")
    inspect = sub.add_parser("analyze", help="Analyser via ffprobe")
    inspect.add_argument("source")
    inspect.add_argument("--json", dest="json_output")
    process = sub.add_parser("process", help="Traiter et vérifier avant export")
    process.add_argument("source")
    process.add_argument("destination")
    process.add_argument("--denoise", choices=["off", "light", "moderate"], default="light")
    process.add_argument("--scale", type=float, default=1)
    process.add_argument("--brightness", type=float, default=0)
    process.add_argument("--contrast", type=float, default=1)
    process.add_argument("--saturation", type=float, default=1)
    process.add_argument("--crf", type=int, default=18)
    process.add_argument("--json", dest="json_output")
    verify = sub.add_parser("verify", help="Vérifier avec un plan figé")
    verify.add_argument("plan")
    verify.add_argument("output")
    sub.add_parser("gui", help="Ouvrir l'application de bureau")
    args = parser.parse_args()
    if args.command == "gui":
        from studio_ia.ui import main as gui_main

        gui_main()
        return
    try:
        tools = Tools.discover()
        if args.command == "doctor":
            from studio_ia.engines import neural_status

            report = capabilities(tools)
            report["video2x"] = neural_status()
            emit(report, args.json_output)
            if not report["cpu_ready"]:
                sys.exit(1)
        elif args.command == "analyze":
            emit(analyze(Path(args.source), tools).to_dict(), args.json_output)
        elif args.command == "process":
            request = Request(
                args.source,
                args.destination,
                denoise=args.denoise,
                scale=args.scale,
                brightness=args.brightness,
                contrast=args.contrast,
                saturation=args.saturation,
                crf=args.crf,
            )
            directory = state_dir() / "jobs" / str(uuid.uuid4())
            plan = build_plan(request, tools)
            cancel = Cancellation()
            signal.signal(signal.SIGINT, lambda *_: cancel.request())
            report = run_plan(plan, tools, directory, cancel)
            report["job_directory"] = str(directory)
            emit(report, args.json_output)
        elif args.command == "verify":
            data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            data["request"] = Request(**data["request"])
            data["media"] = MediaInfo(**data["media"])
            report = verify_output(
                Plan(**data), Path(args.output), tools, Cancellation(), state_dir() / "verify.log"
            )
            emit(report, None)
    except (StudioError, OSError, ValueError) as exc:
        print(f"STUDIO IA : {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
