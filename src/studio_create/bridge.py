"""Unreal Bridge V0: discovery, diagnostic, project creation, command files.

Rules: no single hard-coded path, no network port, no automatic install. The bridge
never claims that Unreal works: the best diagnostic status is
``READY_FOR_MANUAL_TEST`` until a real render has been verified on the target PC.
Commands for Unreal are built as argument lists and validated JSON command files;
launching them is an explicit user action (``launch=True``), never done by tests.
"""

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from studio_create import contracts

REQUIRED_PLUGINS = (
    "PythonScriptPlugin",
    "EditorScriptingUtilities",
    "SequencerScripting",
    "MovieRenderPipeline",
)
TARGET_VERSIONS = ((5, 6), (5, 7), (5, 8))  # targeted, NOT yet tested on hardware


def _template_dir() -> Path:
    """Source tree: <repo>/unreal-template ; frozen build: bundled data directory."""
    bundled = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and bundled:
        return Path(bundled) / "unreal-template"
    return Path(__file__).resolve().parents[2] / "unreal-template"


TEMPLATE = _template_dir()
ENV_ROOTS = "STUDIO_CREATE_UNREAL_ROOTS"


class BridgeError(RuntimeError):
    """Actionable bridge failure; never a partial success."""


def _platform_dir() -> str:
    return "Win64" if os.name == "nt" else ("Mac" if sys.platform == "darwin" else "Linux")


def candidate_roots(env: dict | None = None) -> list[Path]:
    """Search locations, most explicit first. Nothing here is assumed to exist."""
    env = dict(os.environ if env is None else env)
    roots: list[Path] = []
    for item in env.get(ENV_ROOTS, "").split(os.pathsep):
        if item.strip():
            roots.append(Path(item.strip()).expanduser())
    search_dirs: list[Path] = []
    if os.name == "nt":
        for key in ("ProgramFiles", "ProgramW6432"):
            if env.get(key):
                search_dirs.append(Path(env[key]) / "Epic Games")
    else:
        home = Path(env.get("HOME", "~")).expanduser()
        search_dirs += [home, home / "Epic Games", Path("/opt")]
    for directory in search_dirs:
        try:
            for child in sorted(directory.iterdir()):
                if child.is_dir() and child.name.startswith(("UE_", "UnrealEngine")):
                    roots.append(child)
        except OSError:
            continue
    unique, seen = [], set()
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def inspect_install(root: Path) -> dict:
    """Read version and executables of one installation without running anything."""
    report: dict = {"root": str(root), "status": "INVALID", "problems": []}
    build = root / "Engine" / "Build" / "Build.version"
    try:
        version = json.loads(build.read_text(encoding="utf-8-sig"))
        major, minor, patch = (
            int(version[k]) for k in ("MajorVersion", "MinorVersion", "PatchVersion")
        )
        report["version"] = f"{major}.{minor}.{patch}"
    except (OSError, ValueError, KeyError, TypeError):
        report["problems"].append("Engine/Build/Build.version absent ou illisible.")
        return report
    suffix = ".exe" if os.name == "nt" else ""
    binaries = root / "Engine" / "Binaries" / _platform_dir()
    editor = binaries / f"UnrealEditor{suffix}"
    command = binaries / f"UnrealEditor-Cmd{suffix}"
    report["editor"] = str(editor) if editor.is_file() else None
    report["editor_cmd"] = str(command) if command.is_file() else None
    if not report["editor"]:
        report["problems"].append(f"Éditeur absent : {editor}")
    if not report["editor_cmd"]:
        report["problems"].append(f"Exécutable en ligne de commande absent : {command}")
    plugins_root = root / "Engine" / "Plugins"
    found = {}
    for name in REQUIRED_PLUGINS:
        hits = sorted(plugins_root.rglob(f"{name}.uplugin")) if plugins_root.is_dir() else []
        found[name] = str(hits[0]) if hits else None
        if not hits:
            report["problems"].append(f"Plugin moteur introuvable : {name}")
    report["plugins"] = found
    if (major, minor) not in TARGET_VERSIONS:
        report["problems"].append(
            f"Version {major}.{minor} hors cible (5.6 à 5.8) ; le kit n'est pas prévu pour elle."
        )
    report["status"] = "INCOMPATIBLE" if report["problems"] else "COMPATIBLE_NOT_TESTED"
    return report


def doctor(env: dict | None = None, project: Path | None = None) -> dict:
    installs = [inspect_install(root) for root in candidate_roots(env)]
    compatible = [i for i in installs if i["status"] == "COMPATIBLE_NOT_TESTED"]
    actions: list[str] = []
    if not installs:
        status = "NOT_FOUND"
        actions.append(
            "Installer Unreal Engine 5.8 avec Epic Games Launcher (compte Epic, licence Epic), "
            f"ou indiquer son dossier dans la variable {ENV_ROOTS}."
        )
    elif not compatible:
        status = "INCOMPATIBLE"
        actions.append("Corriger les problèmes listés pour au moins une installation.")
    else:
        status = "READY_FOR_MANUAL_TEST"
        actions.append(
            "Créer un projet (« Créer projet »), l'ouvrir dans Unreal, puis lancer la "
            "construction de la ville : aucun rendu n'est encore vérifié."
        )
    report = {
        "schema_version": 1,
        "status": status,
        "render_verified": False,
        "installations": installs,
        "actions": actions,
        "network": "NO_PORT_OPENED",
    }
    if project is not None:
        report["project"] = inspect_project(project)
    return report


def inspect_project(directory: Path) -> dict:
    uprojects = sorted(directory.glob("*.uproject")) if directory.is_dir() else []
    writable = os.access(directory, os.W_OK) if directory.is_dir() else False
    return {
        "path": str(directory),
        "uproject": str(uprojects[0]) if len(uprojects) == 1 else None,
        "writable": writable,
        "status": "OK" if len(uprojects) == 1 and writable else "INVALID",
    }


def create_project(
    destination: Path, project_id: str = "StudioCreate", template: Path = TEMPLATE
) -> dict:
    """Copy the versioned template into a NEW directory; never merge into an existing one."""
    contracts._ident(project_id, "project_id")
    if not (template / "StudioCreate.uproject").is_file():
        raise BridgeError(f"Modèle de projet introuvable : {template}")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise BridgeError(
            f"Le dossier existe déjà et n'est pas vide : {destination}. Aucun écrasement."
        )
    staging = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.partial")
    try:
        shutil.copytree(template, staging, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (staging / "StudioCreate.uproject").rename(staging / f"{project_id}.uproject")
        contracts.write_json(staging / "project.json", contracts.new_project(project_id, "create"))
        if destination.exists():
            destination.rmdir()
        staging.rename(destination)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise BridgeError(f"Création du projet impossible : {exc}") from exc
    return inspect_project(destination)


def write_command(project: Path, command: str, payload: dict) -> Path:
    """Validated JSON command file read by the Unreal-side script (local IPC, no port)."""
    if command not in ("build_city", "render"):
        raise BridgeError(f"Commande inconnue : {command}")
    if command == "build_city":
        payload = {"scene": payload, "actions": contracts.scene_actions(payload)}
    directory = project / "Saved" / "StudioCreate" / "commands"
    path = directory / f"{command}-{uuid.uuid4().hex}.json"
    contracts.write_json(path, {"schema_version": 1, "command": command, **payload})
    return path


def render_payload(scene: dict, project: Path) -> dict:
    """Movie Render Queue command (PNG sequence) for a validated scene."""
    contracts.validate_scene(scene)
    level, sequence = scene["level_id"], scene["sequence"]["name"]
    return {
        "map": f"/Game/Maps/{level}.{level}",
        "sequence": f"/Game/Sequences/{sequence}_{level}.{sequence}_{level}",
        "job_name": f"{sequence}_{level}",
        "output_directory": str(
            project / "Saved" / "StudioCreate" / "renders" / f"{sequence}_{level}"
        ),
        "resolution": scene["render"]["resolution"],
        "anti_aliasing": scene["render"]["anti_aliasing"],
        "fps": scene["sequence"]["fps"],
        "expected_frames": scene["sequence"]["total_frames"],
    }


def editor_argv(install: dict, uproject: Path) -> list[str]:
    if not install.get("editor"):
        raise BridgeError("Éditeur Unreal introuvable pour cette installation.")
    return [install["editor"], str(uproject)]


def script_argv(install: dict, uproject: Path, script: str, command_file: Path) -> list[str]:
    """Headless editor run of a template script with the command file as argument."""
    if not install.get("editor_cmd"):
        raise BridgeError("UnrealEditor-Cmd introuvable pour cette installation.")
    return [
        install["editor_cmd"],
        str(uproject),
        "-run=pythonscript",
        f"-script={script} {command_file}",
        "-unattended",
        "-nosplash",
        "-stdout",
    ]


def launch(argv: list[str], log: Path) -> int:
    """Explicit user action only. Returns the exit code; success still needs evidence."""
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as handle:
        return subprocess.run(argv, stdout=handle, stderr=subprocess.STDOUT, check=False).returncode
