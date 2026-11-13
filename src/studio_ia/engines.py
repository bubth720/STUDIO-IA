"""Optional discovery. No invented Video2X commands or download."""

import json
import shutil
from pathlib import Path
from typing import Protocol

from studio_ia.core import StudioError, capture
from studio_ia.media import sha256


class EngineAdapter(Protocol):
    def probe(self) -> dict: ...
    def validate(self, request: dict) -> None: ...
    def run(self, request: dict) -> dict: ...
    def cancel(self) -> None: ...


def neural_status() -> dict:
    binary = shutil.which("video2x")
    if not binary:
        return {
            "engine": "video2x",
            "status": "absent",
            "real_video_validated": False,
            "reason": "Video2X et modèles absents ; aucun moteur neuronal qualifié.",
        }
    try:
        version = capture([binary, "--version"], timeout=10)
        help_text = capture([binary, "--help"], timeout=10)
        return {
            "engine": "video2x",
            "status": "present_not_qualified",
            "version": version,
            "help": help_text,
            "real_video_validated": False,
            "reason": "GPU/API, modèle et traitement réel non validés.",
        }
    except StudioError as exc:
        return {
            "engine": "video2x",
            "status": "incompatible_or_unknown",
            "error": str(exc),
            "real_video_validated": False,
        }


def inspect_model(path: Path, manifest: dict) -> dict:
    """Only inspect a selected local file, never load/execute model code."""
    required = ("name", "version", "origin", "license", "engine", "expected_sha256")
    if any(not manifest.get(key) for key in required):
        raise StudioError("Modèle : provenance, licence, version, moteur et SHA-256 obligatoires.")
    path = path.resolve(strict=True)
    actual = sha256(path)
    if actual != manifest["expected_sha256"]:
        raise StudioError("Empreinte du modèle incorrecte.")
    return {
        **manifest,
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": actual,
        "integrity": "verified_against_supplied_hash",
        "real_video_validated": False,
    }


def save_model_record(path: Path, manifest: dict, registry: Path) -> dict:
    record = inspect_model(path, manifest)
    data = json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else []
    data.append(record)
    registry.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return record
