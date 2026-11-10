"""CLI uses the same planner, runner and verification as Qt."""

import argparse
import json
import signal
import sys
import uuid
from pathlib import Path

from studio_ia import __version__
from studio_ia.core import Cancellation, StudioError, Tools, capabilities, state_dir
from studio_ia.files import write_json
from studio_ia.media import analyze
from studio_ia.pipeline import Request, build_plan, run_plan, verify_output


def emit(value: dict, output: str | None) -> None:
    # JSON escapes keep redirected Windows/ASCII consoles usable with Unicode paths.
    payload = json.dumps(value, ensure_ascii=True, indent=2)
    if output:
        write_json(Path(output).expanduser().absolute(), value, replace=False)
    else:
        print(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="STUDIO IA — restauration vidéo locale")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Diagnostic réel FFmpeg et moteurs locaux")
    doctor.add_argument("--json", dest="json_output")
    doctor.add_argument("scope", nargs="?", choices=["neural"])
    doctor.add_argument("--binary", help="Binaire NCNN local explicitement choisi")
    models = sub.add_parser(
        "model-check", help="Vérifier un manifeste local sans charger les poids"
    )
    models.add_argument("manifest")
    models.add_argument("root")
    models.add_argument("--register", metavar="REGISTRY_JSON")
    models.add_argument("--json", dest="json_output")
    neural_plan = sub.add_parser(
        "neural-plan", help="Figer le plan ×2 NCNN, sans exécuter de modèle"
    )
    neural_plan.add_argument("source")
    neural_plan.add_argument("destination")
    neural_plan.add_argument("--manifest", required=True)
    neural_plan.add_argument("--model-root", required=True)
    neural_plan.add_argument("--binary", required=True)
    neural_plan.add_argument("--tile", type=int, default=64)
    neural_plan.add_argument("--workspace-mib", type=int, default=2048)
    neural_plan.add_argument("--json", dest="json_output")
    neural_run = sub.add_parser("process-neural", help="Qualifier puis exécuter un plan v2 local")
    neural_run.add_argument("plan")
    neural_run.add_argument("--json", dest="json_output")
    neural_preview = sub.add_parser(
        "preview-neural", help="Vrai segment court, paramètres du plan v2"
    )
    neural_preview.add_argument("plan")
    neural_preview.add_argument("directory")
    neural_preview.add_argument("--seconds", type=float, default=0)
    neural_preview.add_argument("--duration", type=float, default=1)
    neural_preview.add_argument("--json", dest="json_output")
    temporal = sub.add_parser(
        "temporal-audit", help="Diagnostic CPU réel des coupes, PTS, mouvement et audio"
    )
    temporal.add_argument("source")
    temporal.add_argument("--threshold", default="10")
    temporal.add_argument("--cut", type=int, action="append", default=[])
    temporal.add_argument("--ignore-cut", type=int, action="append", default=[])
    temporal.add_argument("--max-frames", type=int, default=10000)
    temporal.add_argument("--motion", action="store_true")
    temporal.add_argument("--audio", action="store_true")
    temporal.add_argument("--json", dest="json_output")
    schedule = sub.add_parser(
        "interpolation-plan", help="Planning ×2 seulement ; aucun backend RIFE activé"
    )
    schedule.add_argument("source")
    schedule.add_argument("--x2", action="store_true", help="Consentement explicite au planning ×2")
    schedule.add_argument("--cut", type=int, action="append", default=[])
    schedule.add_argument("--json", dest="json_output")
    inspect = sub.add_parser("analyze", help="Analyser via ffprobe")
    inspect.add_argument("source")
    inspect.add_argument("--json", dest="json_output")
    process = sub.add_parser("process", help="Traiter et vérifier avant export")
    process.add_argument("source")
    process.add_argument("destination")
    process.add_argument("--denoise", choices=["off", "light", "moderate"], default="light")
    process.add_argument(
        "--deband",
        choices=["off", "light", "moderate"],
        default="off",
        help="Anti-banding CPU conservateur (désactivé par défaut)",
    )
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
    temporal_gui = sub.add_parser("temporal-preview", help="Inspection Qt source/référence par PTS")
    temporal_gui.add_argument("source", type=Path)
    temporal_gui.add_argument("--reference", type=Path)

    args = parser.parse_args()
    if args.command == "temporal-preview":
        from studio_ia.temporal_preview import main as temporal_main

        temporal_main(args.source, args.reference)
        return
    if args.command == "gui":
        from studio_ia.ui import main as gui_main

        gui_main()
        return
    try:
        if getattr(args, "json_output", None):
            report_path = Path(args.json_output).expanduser().absolute()
            if report_path.exists() or report_path.is_symlink():
                raise StudioError("Le rapport existe déjà ; choisir un nouveau fichier JSON.")
            protected = [
                Path(getattr(args, key)).expanduser().resolve()
                for key in ("source", "destination")
                if hasattr(args, key)
            ]
            if args.command in ("process-neural", "preview-neural"):
                from studio_ia.plans_v2 import load_plan

                frozen = load_plan(json.loads(Path(args.plan).read_text(encoding="utf-8")))
                protected += [Path(frozen.request.source), Path(frozen.request.destination)]
            for key in ("manifest", "plan", "register"):
                if getattr(args, key, None):
                    protected.append(Path(getattr(args, key)).expanduser().resolve())
            if report_path.resolve() in protected:
                raise StudioError("Le rapport JSON doit être distinct des médias source et sortie.")
        tools = Tools.discover()
        if args.command == "doctor":
            from studio_ia.engines import neural_status

            report = capabilities(tools)
            report["video2x"] = neural_status()
            if args.scope == "neural":
                from studio_ia.hardware import hardware_report
                from studio_ia.neural import probe

                report["neural"] = hardware_report()
                report["ncnn"] = (
                    probe(Path(args.binary))
                    if args.binary
                    else {"status": "NOT_CONFIGURED", "real_video_validated": False}
                )
            emit(report, args.json_output)
            if not report["cpu_ready"]:
                sys.exit(1)
        elif args.command in ("temporal-audit", "interpolation-plan"):
            from studio_ia.interpolate import plan_x2
            from studio_ia.motion import TranslationTracker
            from studio_ia.scene_detect import scan_scenes
            from studio_ia.temporal_audio import audit_audio

            if args.command == "interpolation-plan" and not args.x2:
                raise StudioError("Le planning exige --x2 ; aucune interpolation automatique.")
            cancel = Cancellation()
            signal.signal(signal.SIGINT, lambda *_: cancel.request())
            tracker = TranslationTracker() if getattr(args, "motion", False) else None
            scan = scan_scenes(
                Path(args.source),
                tools,
                cancel=cancel,
                threshold=getattr(args, "threshold", "10"),
                manual_boundaries=tuple(args.cut),
                ignored_boundaries=tuple(getattr(args, "ignore_cut", [])),
                max_frames=getattr(args, "max_frames", 10000),
                sample_observer=tracker.feed if tracker else None,
            )
            if args.command == "interpolation-plan":
                report = plan_x2(scan, explicit_opt_in=args.x2)
            else:
                report = scan.to_dict()
                if tracker:
                    report["motion"] = tracker.report(scan)
                if args.audio:
                    report["audio"] = audit_audio(
                        Path(args.source), tools, timeline=scan.timeline, cancel=cancel
                    )
            emit(report, args.json_output)
        elif args.command == "analyze":
            emit(analyze(Path(args.source), tools).to_dict(), args.json_output)
        elif args.command == "process":
            request = Request(
                args.source,
                args.destination,
                denoise=args.denoise,
                deband=args.deband,
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
            from studio_ia.plans_v2 import compare_timing, frame_table, load_plan

            data = json.loads(Path(args.plan).read_text(encoding="utf-8"))
            envelope = load_plan(data)
            report = verify_output(
                envelope.cpu_plan(),
                Path(args.output),
                tools,
                Cancellation(),
                state_dir() / "verify.log",
            )
            if envelope.data["kind"] == "neural-ncnn":
                compare_timing(envelope.data["timing"], frame_table(Path(args.output), tools))
            emit(report, None)
        elif args.command == "model-check":
            from studio_ia.models import inspect, read_manifest, register

            manifest = read_manifest(Path(args.manifest))
            record = inspect(Path(args.root), manifest)
            report = {
                "status": "VERIFIED_LOCAL_FILES",
                "manifest_sha256": record.identity,
                "real_video_validated": False,
                "hardware": "NOT_TESTED",
            }
            if args.register:
                registry = Path(args.register).expanduser().absolute()
                registry.parent.mkdir(parents=True, exist_ok=True)
                register(Path(args.root), manifest, registry)
            emit(report, args.json_output)
        elif args.command == "neural-plan":
            from studio_ia.models import inspect, read_manifest
            from studio_ia.neural import build_neural_plan

            model = inspect(Path(args.model_root), read_manifest(Path(args.manifest)))
            plan = build_neural_plan(
                Request(args.source, args.destination, scale=2, denoise="off"),
                tools,
                model,
                Path(args.binary),
                tile=args.tile,
                workspace_budget=args.workspace_mib * 1024**2,
            )
            emit(plan.to_dict(), args.json_output)
        elif args.command in ("process-neural", "preview-neural"):
            from studio_ia.neural import preview_neural, run_neural_plan
            from studio_ia.plans_v2 import load_plan

            plan = load_plan(json.loads(Path(args.plan).read_text(encoding="utf-8")))
            cancel = Cancellation()
            signal.signal(signal.SIGINT, lambda *_: cancel.request())
            if args.command == "preview-neural":
                report = preview_neural(
                    plan,
                    tools,
                    Path(args.directory),
                    seconds=args.seconds,
                    duration=args.duration,
                    cancel=cancel,
                )
            else:
                directory = state_dir() / "jobs" / str(uuid.uuid4())
                report = run_neural_plan(plan, tools, directory, cancel)
                report["job_directory"] = str(directory)
            emit(report, args.json_output)
    except (StudioError, OSError, ValueError) as exc:
        print(f"STUDIO IA : {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
