"""RESTORE content profiles (LOT 03 step 3): « Animation » or « Vidéos réelles ».

Each profile is bound to exactly one catalogued NCNN model. A profile never changes
the model silently: an incompatible manifest is refused with a concrete fix. Pure
Python, no Qt, so the CLI, jobs and tests share the same rules.
"""

import json
from pathlib import Path

from studio_ia.core import StudioError
from studio_ia.files import write_json
from studio_ia.models import CATALOG

PROFILES: dict[str, dict[str, str]] = {
    "animation": {
        "label": "Animation",
        "model": "realesr-animevideov3",
        "manifest": "manifests/realesr-animevideov3-x2.json",
        "summary": (
            "Dessins animés : contours nets, aplats, couleurs stables. "
            "Modèle realesr-animevideov3, ×2 natif."
        ),
    },
    "live-action": {
        "label": "Vidéos réelles",
        "model": "realesrgan-x4plus",
        "manifest": "manifests/realesrgan-x4plus.json",
        "summary": (
            "Films et vidéos filmées : textures naturelles, grain. "
            "Modèle realesrgan-x4plus, ×4 natif réduit en Lanczos vers ×2. "
            "Aucun modèle spécialisé visages."
        ),
    },
}
DEFAULT_PROFILE = "animation"
SETTINGS_NAME = "restore-settings.json"

assert all(p["model"] in CATALOG for p in PROFILES.values())


def validate_profile(profile: str) -> str:
    if profile not in PROFILES:
        raise StudioError(f"Type de contenu inconnu : {profile!r} (animation ou live-action).")
    return profile


def profile_for_model(manifest: dict) -> str:
    for name, profile in PROFILES.items():
        if profile["model"] == manifest.get("name"):
            return name
    raise StudioError("Aucun type de contenu ne correspond à ce modèle.")


def check_model(profile: str, manifest: dict) -> None:
    """Refuse a manifest whose model is not the one bound to the profile."""
    expected = PROFILES[validate_profile(profile)]
    if manifest.get("name") != expected["model"]:
        raise StudioError(resolution(profile, found=manifest.get("name")))


def resolution(profile: str, *, found: str | None = None) -> str:
    expected = PROFILES[validate_profile(profile)]
    prefix = (
        f"Le modèle {found} ne convient pas au type « {expected['label']} ». "
        if found
        else f"Aucun modèle utilisable pour « {expected['label']} ». "
    )
    return (
        prefix + f"Placer le manifeste {expected['manifest']} à côté des fichiers "
        f"{CATALOG[expected['model']]['param']} et {CATALOG[expected['model']]['weights']} "
        "(archive officielle Real-ESRGAN v0.2.5.0), puis « Choisir et diagnostiquer un "
        "modèle NCNN… » sur une machine avec GPU Vulkan physique."
    )


def describe(profile: str) -> dict:
    data = PROFILES[validate_profile(profile)]
    return {"id": profile, "label": data["label"], "model": data["model"]}


def load_settings(root: Path) -> dict:
    """Never crash the UI on a missing or corrupt settings file: fall back to defaults."""
    defaults = {"schema_version": 1, "content_profile": DEFAULT_PROFILE}
    path = root / SETTINGS_NAME
    try:
        if path.is_symlink() or path.stat().st_size > 64 * 1024:
            return defaults
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            return defaults
        validate_profile(str(data.get("content_profile")))
        return {**defaults, "content_profile": data["content_profile"]}
    except (OSError, ValueError, StudioError):
        return defaults


def save_settings(root: Path, *, content_profile: str) -> None:
    validate_profile(content_profile)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / SETTINGS_NAME, {"schema_version": 1, "content_profile": content_profile})
