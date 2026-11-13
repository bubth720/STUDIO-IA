"""studio-create CLI (versioned, schema 1). Never launches Unreal unless --launch is given."""

import argparse
import json
import sys
from pathlib import Path

from studio_create import __version__, bridge, city, contracts


def emit(data, path: str | None) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        contracts.write_json(Path(path), data)
    print(text)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="studio-create", description="STUDIO CREATE V0 (Unreal Bridge)"
    )
    p.add_argument("--version", action="version", version=f"studio-create {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="Détecter Unreal et diagnostiquer (aucun lancement)")
    d.add_argument("--project")
    d.add_argument("--json", dest="json_output")
    n = sub.add_parser("new-project", help="Créer un projet depuis le modèle versionné")
    n.add_argument("destination")
    n.add_argument("--id", default="StudioCreate")
    s = sub.add_parser("scene", help="Générer create_scene.json (ville + caméras + séquence)")
    s.add_argument("output")
    s.add_argument("--seed", type=int, default=2048)
    s.add_argument("--blocks-x", type=int, default=3)
    s.add_argument("--blocks-y", type=int, default=2)
    s.add_argument("--density", default="medium", choices=sorted(city.DENSITY_LOTS))
    s.add_argument("--time-of-day", default="dusk", choices=city.TIMES_OF_DAY)
    s.add_argument("--fps", default="24")
    s.add_argument("--render", default="preview-720p", choices=sorted(contracts.RENDER_PRESETS))
    s.add_argument(
        "--camera",
        action="append",
        metavar="NOM:PRESET",
        help="Caméra (répétable), ex. Avenue:travelling ; défaut : Avenue:travelling, Orbite:orbit",
    )
    c = sub.add_parser("build-city", help="Écrire la commande build_city pour Unreal")
    c.add_argument("project")
    c.add_argument("scene")
    c.add_argument("--launch", action="store_true", help="Lancer réellement UnrealEditor-Cmd")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            report = bridge.doctor(project=Path(args.project) if args.project else None)
            emit(report, args.json_output)
            return 0 if report["status"] == "READY_FOR_MANUAL_TEST" else 2
        if args.command == "new-project":
            emit(bridge.create_project(Path(args.destination), args.id), None)
            return 0
        if args.command == "scene":
            specs = [
                tuple(item.split(":", 1))
                for item in (args.camera or ["Avenue:travelling", "Orbite:orbit"])
            ]
            if any(len(spec) != 2 for spec in specs):
                raise contracts.ContractError("--camera attend NOM:PRESET.")
            params = city.CityParams(
                seed=args.seed,
                blocks_x=args.blocks_x,
                blocks_y=args.blocks_y,
                density=args.density,
                time_of_day=args.time_of_day,
            )
            scene = contracts.build_scene(params, specs, fps=args.fps, render_preset=args.render)
            contracts.write_json(Path(args.output), scene)
            print(
                json.dumps(
                    {
                        "output": args.output,
                        "layout_sha256": scene["layout"]["layout_sha256"],
                        "buildings": len(scene["layout"]["buildings"]),
                        "total_frames": scene["sequence"]["total_frames"],
                        "render_verified": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "build-city":
            project = Path(args.project)
            scene = contracts.validate_scene(
                json.loads(Path(args.scene).read_text(encoding="utf-8"))
            )
            command_file = bridge.write_command(project, "build_city", scene)
            info = bridge.inspect_project(project)
            result = {
                "command_file": str(command_file),
                "launched": False,
                "render_verified": False,
            }
            if args.launch:
                report = bridge.doctor(project=project)
                ready = [
                    i for i in report["installations"] if i["status"] == "COMPATIBLE_NOT_TESTED"
                ]
                if not ready or info["status"] != "OK":
                    raise bridge.BridgeError(
                        "Unreal ou projet non prêt : voir studio-create doctor."
                    )
                script = str(
                    project / "Content" / "Python" / "studio_create_unreal" / "build_city.py"
                )
                argv_ = bridge.script_argv(ready[0], Path(info["uproject"]), script, command_file)
                result["exit_code"] = bridge.launch(
                    argv_, project / "Saved" / "StudioCreate" / "build_city.log"
                )
                result["launched"] = True
            emit(result, None)
            return 0
    except (bridge.BridgeError, contracts.ContractError, city.CityError, ValueError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
