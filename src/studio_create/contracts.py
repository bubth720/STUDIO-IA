"""Versioned exchange contracts shared by RESTORE and CREATE (schema_version 1).

- project.json      : project identity, relative paths, mode, settings, run journal.
- restore_job.json  : one RESTORE job (source, content profile, model fingerprint, state).
- create_scene.json : one CREATE scene (level, seed, layout digest, cameras, sequence, render).

Validators are strict and dependency-free and are the single reference for these
contracts (see docs/create/ARCHITECTURE.md). ``scene_actions`` turns a scene into the flat list of
primitive actions that the thin Unreal-side script executes.
"""

import json
import re
from fractions import Fraction
from pathlib import Path, PurePosixPath

from studio_create import GENERATOR_VERSION, cameras, city


class ContractError(ValueError):
    """Contract refused; nothing is written or executed."""


IDENT = re.compile(r"[A-Za-z0-9._-]{1,80}")
JOB_STATES = ("pending", "running", "failed", "completed")
PROFILES = ("animation", "live-action")
RENDER_PRESETS = {
    "preview-720p": {"resolution": [1280, 720], "output": "png-sequence", "anti_aliasing": 1},
    "final-1080p": {"resolution": [1920, 1080], "output": "png-sequence", "anti_aliasing": 8},
}


def _relative(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ContractError(f"{field} : chemin relatif POSIX requis.")
    path = PurePosixPath(value)
    if path.is_absolute() or ":" in value or any(p in ("..", "") for p in value.split("/")):
        raise ContractError(f"{field} : chemin hors projet interdit.")
    return value


def _ident(value, field: str) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise ContractError(f"{field} : identifiant [A-Za-z0-9._-]{{1,80}} requis.")
    return value


def validate_project(data: dict) -> dict:
    try:
        if data["schema_version"] != 1:
            raise ContractError("project.json : schema_version 1 attendu.")
        _ident(data["id"], "id")
        if data["mode"] not in ("restore", "create"):
            raise ContractError("mode : restore ou create.")
        for key, value in data["paths"].items():
            _relative(value, f"paths.{key}")
        if not isinstance(data["settings"], dict) or not isinstance(data["runs"], list):
            raise ContractError("settings (objet) et runs (liste) requis.")
        for run in data["runs"]:
            _ident(run["id"], "runs.id")
            if run["status"] not in JOB_STATES:
                raise ContractError("runs.status invalide.")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ContractError("project.json incomplet ou mal typé.") from exc
    return data


def new_project(project_id: str, mode: str) -> dict:
    return validate_project(
        {
            "schema_version": 1,
            "id": project_id,
            "mode": mode,
            "paths": {"media": "media", "exports": "exports", "logs": "logs", "scenes": "scenes"},
            "settings": {},
            "runs": [],
        }
    )


def validate_restore_job(data: dict) -> dict:
    try:
        if data["schema_version"] != 1:
            raise ContractError("restore_job.json : schema_version 1 attendu.")
        _relative(data["source"], "source")
        if data["profile"] not in PROFILES:
            raise ContractError("profile : animation ou live-action.")
        if not re.fullmatch("[0-9a-f]{64}", data["model"]["manifest_sha256"]):
            raise ContractError("model.manifest_sha256 : SHA-256 requis.")
        _ident(data["model"]["name"], "model.name")
        if data["state"] not in JOB_STATES:
            raise ContractError("state : pending, running, failed ou completed.")
        for output in data["outputs"]:
            _relative(output, "outputs")
        if not isinstance(data["params"], dict):
            raise ContractError("params : objet requis.")
    except (KeyError, TypeError, AttributeError) as exc:
        raise ContractError("restore_job.json incomplet ou mal typé.") from exc
    return data


def build_scene(
    params: city.CityParams,
    shot_specs: list[tuple[str, str]],
    *,
    fps: str = "24",
    render_preset: str = "preview-720p",
    level_id: str | None = None,
) -> dict:
    """create_scene.json from city parameters and (camera name, preset) pairs."""
    layout = city.generate(params)
    shots = [cameras.shot(layout, preset, name=name) for name, preset in shot_specs]
    if render_preset not in RENDER_PRESETS:
        raise ContractError(f"Preset de rendu : {sorted(RENDER_PRESETS)}.")
    scene = {
        "schema_version": 1,
        "level_id": level_id or f"City_{params.seed}",
        "generator": GENERATOR_VERSION,
        "seed": params.seed,
        "layout": layout,
        "dimensions_cm": [
            layout["bounds"]["max"][0] - layout["bounds"]["min"][0],
            layout["bounds"]["max"][1] - layout["bounds"]["min"][1],
        ],
        "zones": [b["id"] for b in layout["blocks"]],
        "cameras": shots,
        "sequence": cameras.sequence(shots, fps=fps),
        "render": {"preset": render_preset, **RENDER_PRESETS[render_preset], "fps": fps},
    }
    return validate_scene(scene)


def validate_scene(data: dict) -> dict:
    try:
        if data["schema_version"] != 1 or data["generator"] != GENERATOR_VERSION:
            raise ContractError("create_scene.json : version ou générateur non pris en charge.")
        _ident(data["level_id"], "level_id")
        layout = data["layout"]
        if layout["layout_sha256"] != city.layout_sha256(layout):
            raise ContractError("Disposition modifiée : empreinte layout_sha256 incorrecte.")
        city.validate_layout(layout)
        regenerated = city.generate(city.CityParams(**layout["params"]))
        if (
            regenerated["layout_sha256"] != layout["layout_sha256"]
            or data["seed"] != layout["params"]["seed"]
        ):
            raise ContractError("Disposition non reproductible depuis la seed et les paramètres.")
        names = {c["name"] for c in data["cameras"]}
        if {cut["camera"] for cut in data["sequence"]["cuts"]} - names:
            raise ContractError("La séquence référence une caméra absente.")
        Fraction(data["sequence"]["fps"])
        if data["render"]["preset"] not in RENDER_PRESETS:
            raise ContractError("Preset de rendu inconnu.")
    except (KeyError, TypeError, AttributeError, ValueError, city.CityError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError(f"create_scene.json invalide : {exc}") from exc
    return data


def scene_actions(scene: dict) -> list[dict]:
    """Flat, deterministic list of primitive actions for the Unreal-side script.

    Shapes are /Engine/BasicShapes assets (100 cm cubes/cylinders), so the kit ships no
    third-party asset. Scale = size / 100.
    """
    validate_scene(scene)
    layout = scene["layout"]
    actions: list[dict] = [{"op": "new_level", "level_id": scene["level_id"]}]
    bounds = layout["bounds"]
    width = bounds["max"][0] - bounds["min"][0]
    depth = bounds["max"][1] - bounds["min"][1]
    actions.append(
        {
            "op": "box",
            "id": "ground",
            "center": [0, 0, -5],
            "size": [width, depth, 10],
            "material": "ground",
        }
    )
    for road in layout["roads"]:
        r = road["rect"]
        actions.append(
            {
                "op": "box",
                "id": road["id"],
                "center": [(r["min"][0] + r["max"][0]) / 2, (r["min"][1] + r["max"][1]) / 2, 1],
                "size": [r["max"][0] - r["min"][0], r["max"][1] - r["min"][1], 2],
                "material": "road",
            }
        )
    for building in layout["buildings"]:
        f = building["footprint"]
        sx, sy, h = f["max"][0] - f["min"][0], f["max"][1] - f["min"][1], building["height_cm"]
        cx, cy = (f["min"][0] + f["max"][0]) / 2, (f["min"][1] + f["max"][1]) / 2
        actions.append(
            {
                "op": "box",
                "id": building["id"],
                "center": [cx, cy, h / 2],
                "size": [sx, sy, h],
                "material": building["style"],
            }
        )
        if building["style"] == "stepped":
            actions.append(
                {
                    "op": "box",
                    "id": building["id"] + "-top",
                    "center": [cx, cy, h + h / 8],
                    "size": [sx * 0.6, sy * 0.6, h / 4],
                    "material": "stepped",
                }
            )
    for lamp in layout["props"]["lamps"]:
        x, y, _ = lamp["location"]
        actions.append({"op": "lamp", "id": lamp["id"], "location": [x, y, 0], "height": 500})
    actions.append({"op": "lighting", "time_of_day": layout["lighting"]["time_of_day"]})
    for camera in scene["cameras"]:
        actions.append({"op": "camera", **camera})
    actions.append({"op": "sequence", **scene["sequence"]})
    actions.append({"op": "save_level", "level_id": scene["level_id"]})
    return actions


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
