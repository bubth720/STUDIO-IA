"""Frames extracted from actual source/output at the same requested time."""

import math
from pathlib import Path

from studio_ia.core import StudioError, Tools, capture


def snapshot(path: Path, seconds: float, destination: Path, tools: Tools) -> Path:
    if not math.isfinite(seconds) or seconds < 0:
        raise StudioError("Instant d'aperçu invalide.")
    capture(
        [
            tools.ffmpeg,
            "-hide_banner",
            "-v",
            "error",
            "-n",
            "-threads",
            "2",
            "-filter_threads",
            "2",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(path.resolve()),
            "-ss",
            str(seconds),
            "-frames:v",
            "1",
            "-vf",
            "scale=640:-2:flags=lanczos",
            "-threads",
            "1",
            str(destination),
        ],
        timeout=120,
    )
    if not destination.is_file() or not destination.stat().st_size:
        raise StudioError("Aucune image à cet instant ; choisir un instant plus tôt.")
    return destination
