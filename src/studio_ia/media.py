"""Real ffprobe analysis and conservative media policy."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from studio_ia.core import StudioError, Tools, capture


def number(value) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) and result > 0 else None
    except (ValueError, TypeError):
        return None


def rate(value: str) -> float | None:
    try:
        return float(Fraction(value)) or None
    except (ValueError, ZeroDivisionError):
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class MediaInfo:
    path: str
    size: int
    container: str
    duration: float | None
    video: dict
    audio: list[dict]
    streams: list[dict]
    hdr: bool
    rotation: float
    possible_vfr: bool
    warnings: list[str]
    raw: dict

    def to_dict(self) -> dict:
        return asdict(self)


def analyze(path: Path, tools: Tools) -> MediaInfo:
    path = path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise StudioError("La source doit être un fichier local existant.")
    data = json.loads(
        capture(
            [
                tools.ffprobe,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ]
        )
    )
    streams = data.get("streams", [])
    videos = [
        s
        for s in streams
        if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")
    ]
    if not videos:
        raise StudioError("Aucune piste vidéo décodable dans ce fichier.")
    video = videos[0]
    if not video.get("width") or not video.get("height"):
        raise StudioError("Dimensions vidéo inconnues.")
    transfer = video.get("color_transfer", "unknown")
    hdr = transfer in ("smpte2084", "arib-std-b67") or video.get("color_primaries") == "bt2020"
    rotation = float(video.get("tags", {}).get("rotate", 0))
    for side in video.get("side_data_list", []):
        rotation = float(side.get("rotation", rotation))
    avg, nominal = rate(video.get("avg_frame_rate", "0/0")), rate(video.get("r_frame_rate", "0/0"))
    vfr = bool(avg and nominal and abs(avg - nominal) > 0.01)
    warnings = []
    if vfr:
        warnings.append(
            "Cadences moyenne/nominale différentes ; timestamps conservés, progrès indéterminé."
        )
    if hdr:
        warnings.append(
            "HDR/BT.2020 détecté : export CPU 8 bits refusé, aucun tone mapping implicite."
        )
    if rotation:
        warnings.append(
            "Rotation détectée : export non qualifié, refusé pour préserver l'orientation."
        )
    secondary = [s for s in streams if s.get("codec_type") not in ("video", "audio")]
    if (
        secondary
        or len(videos) != 1
        or len(videos) != len([s for s in streams if s.get("codec_type") == "video"])
    ):
        warnings.append(
            "Flux secondaires/multi-vidéo : export MVP refusé pour éviter toute perte silencieuse."
        )
    fmt = data.get("format", {})
    return MediaInfo(
        str(path),
        path.stat().st_size,
        fmt.get("format_name", "unknown"),
        number(fmt.get("duration")) or number(video.get("duration")),
        video,
        [s for s in streams if s.get("codec_type") == "audio"],
        streams,
        hdr,
        rotation,
        vfr,
        warnings,
        data,
    )
