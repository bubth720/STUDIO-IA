"""Validated CPU plans, complete verification and no-clobber atomic export."""

import math
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable

from studio_ia import __version__
from studio_ia.core import Cancellation, StudioError, Tools, build_identity, capabilities, execute
from studio_ia.files import publish_no_replace, write_json
from studio_ia.media import MediaInfo, analyze, number, rate, sha256, timestamp


@dataclass(frozen=True)
class Request:
    source: str
    destination: str
    profile: str = "preservation"
    denoise: str = "light"
    scale: float = 1.0
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    crf: int = 18
    schema_version: int = 1
    deband: str = "off"  # Explicit opt-in; backward compatible with CPU v1 plans.


@dataclass
class Plan:
    request: Request
    media: MediaInfo
    width: int
    height: int
    filters: list[str]
    audio_policy: str
    warnings: list[str]
    engine_version: str

    def to_dict(self) -> dict:
        return asdict(self)


def build_plan(request: Request, tools: Tools, caps: dict | None = None) -> Plan:
    if request.schema_version != 1 or request.profile not in ("preservation", "custom", "control"):
        raise StudioError("Profil ou version du schéma inconnu.")
    if request.denoise not in ("off", "light", "moderate"):
        raise StudioError("Débruitage inconnu.")
    if request.deband not in ("off", "light", "moderate"):
        raise StudioError("Anti-banding inconnu.")
    for value, low, high, label in (
        (request.scale, 0.25, 4, "Échelle"),
        (request.brightness, -0.1, 0.1, "Luminosité"),
        (request.contrast, 0.8, 1.2, "Contraste"),
        (request.saturation, 0.8, 1.2, "Saturation"),
        (request.crf, 12, 28, "CRF"),
    ):
        if not math.isfinite(value) or not low <= value <= high:
            raise StudioError(f"{label} hors limites ({low}–{high}).")
    if int(request.crf) != request.crf:
        raise StudioError("CRF doit être entier.")
    try:
        source = Path(request.source).expanduser().resolve(strict=True)
        entered_destination = Path(request.destination).expanduser().absolute()
        destination = entered_destination.parent.resolve() / entered_destination.name
        if destination.is_symlink() or destination.exists():
            raise StudioError(
                "La destination existe déjà : choisir un nouveau nom. Aucun écrasement."
            )
        if source == destination:
            raise StudioError("Source et destination identiques.")
        if not destination.parent.is_dir():
            raise StudioError("Le dossier de destination doit exister.")
        if destination.suffix.lower() not in (".mp4", ".mkv"):
            raise StudioError("Export MVP : choisir .mp4 ou .mkv.")
        info = analyze(source, tools)
        if shutil.disk_usage(destination.parent).free < max(64 * 1024**2, info.size * 2):
            raise StudioError("Espace disque insuffisant (minimum 64 Mio et deux fois la source).")
    except OSError as exc:
        raise StudioError(f"Chemin inaccessible : {exc}") from exc
    if info.hdr or info.rotation:
        raise StudioError("HDR/BT.2020 ou rotation : export non qualifié dans ce MVP.")
    if info.video.get("sample_aspect_ratio", "1:1") not in ("1:1", "N/A", "0:1"):
        raise StudioError("Pixels non carrés : export non qualifié.")
    if info.video.get("field_order", "progressive") not in ("progressive", "unknown"):
        raise StudioError("Vidéo entrelacée : désentrelacement non qualifié.")
    if (
        any(s.get("codec_type") not in ("video", "audio") for s in info.streams)
        or sum(s.get("codec_type") == "video" for s in info.streams) != 1
    ):
        raise StudioError(
            "Sous-titres/données/multi-vidéo : export refusé pour éviter leur suppression."
        )
    pix = info.video.get("pix_fmt", "unknown")
    if any(depth in pix for depth in ("10", "12", "14", "16", "f32")):
        raise StudioError("Source supérieure à 8 bits : conversion non qualifiée.")
    width = max(2, round(info.video["width"] * request.scale / 2) * 2)
    height = max(2, round(info.video["height"] * request.scale / 2) * 2)
    if max(width, height) > 7680 or width * height > 3840 * 2160:
        raise StudioError("Limite CPU : 8,3 millions de pixels et dimension maximale 7680.")
    filters = []
    if request.denoise != "off":
        filters.append("hqdn3d=" + ("1.5:1.5:6:6" if request.denoise == "light" else "3:3:6:6"))
    # CPU gradient debanding only, not neural detail restoration. Keep OFF by default.
    if request.deband != "off":
        threshold, radius = ("0.012", 8) if request.deband == "light" else ("0.020", 12)
        filters.append(
            f"deband=1thr={threshold}:2thr={threshold}:3thr={threshold}:"
            f"4thr={threshold}:range={radius}:blur=1"
        )
    if (request.brightness, request.contrast, request.saturation) != (0, 1, 1):
        filters.append(
            f"eq=brightness={request.brightness}:contrast={request.contrast}"
            f":saturation={request.saturation}"
        )
    if (width, height) != (info.video["width"], info.video["height"]):
        filters.extend([f"scale={width}:{height}:flags=lanczos", "setsar=1"])
    caps = caps or capabilities(tools)
    if not caps.get("supports_fps_mode"):
        raise StudioError("FFmpeg ne fournit pas fps_mode ; utiliser FFmpeg 5.1 ou plus récent.")
    for encoder in ("libx264", "aac"):
        if encoder not in caps["encoders"]:
            raise StudioError(f"Encodeur requis absent : {encoder}. Utiliser un FFmpeg compatible.")
    for item in filters:
        if item.split("=", 1)[0] not in caps["filters"]:
            raise StudioError(f"Filtre absent : {item.split('=', 1)[0]}.")
    copy_audio = destination.suffix.lower() == ".mkv" or all(
        stream.get("codec_name") == "aac" for stream in info.audio
    )
    warnings = list(info.warnings)
    if request.deband != "off":
        warnings.append("Anti-banding CPU activé : peut lisser certains dégradés ou détails fins.")
    if info.audio and not copy_audio:
        warnings.append("Audio réencodé en AAC 192 kbit/s par piste pour compatibilité MP4.")
    warnings.append("CPU classique : aucun nouveau détail neuronal garanti.")
    return Plan(
        replace(request, source=str(source), destination=str(destination)),
        info,
        width,
        height,
        filters,
        "copy" if copy_audio else "aac",
        warnings,
        caps["ffmpeg_version"],
    )


def command(plan: Plan, tools: Tools, temporary: Path) -> list[str]:
    args = [
        tools.ffmpeg,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-n",
        "-threads",
        "2",
        "-filter_threads",
        "2",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        plan.media.path,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-map_metadata",
        "0",
        "-map_chapters",
        "0",
    ]
    if plan.filters:
        args += ["-vf", ",".join(plan.filters)]
    args += [
        "-c:v",
        "libx264",
        "-threads",
        "2",
        "-preset",
        "medium",
        "-crf",
        str(plan.request.crf),
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "passthrough",
        "-c:a",
        plan.audio_policy,
    ]
    if plan.audio_policy == "aac":
        args += ["-b:a", "192k"]
    for key, flag in (
        ("color_primaries", "-color_primaries"),
        ("color_transfer", "-color_trc"),
        ("color_space", "-colorspace"),
        ("color_range", "-color_range"),
    ):
        value = plan.media.video.get(key)
        if value and value not in ("unknown", "unspecified", "reserved"):
            args += [flag, value]
    if temporary.suffix.lower() == ".mp4":
        args += ["-movflags", "+faststart"]
    return args + ["-progress", "pipe:1", "-nostats", str(temporary)]


def verify_output(plan: Plan, output: Path, tools: Tools, cancel: Cancellation, log: Path) -> dict:
    cancel.check()
    after = analyze(output, tools)
    if output.stat().st_size == 0:
        raise StudioError("Export vide.")
    assertions = {
        "resolution": (after.video["width"], after.video["height"]) == (plan.width, plan.height),
        "video_codec": after.video.get("codec_name") == "h264",
        "pixel_format": after.video.get("pix_fmt") == "yuv420p",
        "audio_count": len(after.audio) == len(plan.media.audio),
        "duration": after.duration is not None
        and (
            not plan.media.duration
            or abs(after.duration - plan.media.duration)
            <= max(0.25, 2 / (rate(plan.media.video.get("avg_frame_rate", "0/0")) or 25))
        ),
    }
    for key in ("color_primaries", "color_transfer", "color_space", "color_range"):
        original = plan.media.video.get(key)
        if original and original not in ("unknown", "unspecified", "reserved"):
            assertions[key] = original == after.video.get(key)
    for index, (before_audio, after_audio) in enumerate(
        zip(plan.media.audio, after.audio, strict=False)
    ):
        assertions[f"audio_{index}_channels"] = before_audio.get("channels") == after_audio.get(
            "channels"
        )
        expected_codec = before_audio.get("codec_name") if plan.audio_policy == "copy" else "aac"
        assertions[f"audio_{index}_codec"] = expected_codec == after_audio.get("codec_name")
        assertions[f"audio_{index}_sample_rate"] = before_audio.get(
            "sample_rate"
        ) == after_audio.get("sample_rate")
        starts = [
            timestamp(stream.get("start_time"))
            for stream in (before_audio, plan.media.video, after_audio, after.video)
        ]
        known_starts = [value for value in starts if value is not None]
        if len(known_starts) == 4:
            before_a, before_v, after_a, after_v = known_starts
            assertions[f"audio_{index}_sync"] = (
                abs((before_a - before_v) - (after_a - after_v)) <= 0.1
            )
        for field in ("duration", "start_time"):
            before_value, after_value = (
                number(before_audio.get(field)),
                number(after_audio.get(field)),
            )
            if before_value and after_value:
                assertions[f"audio_{index}_{field}"] = abs(before_value - after_value) <= 0.25
    before_rate, after_rate = (
        rate(plan.media.video.get("avg_frame_rate", "0/0")),
        rate(after.video.get("avg_frame_rate", "0/0")),
    )
    if before_rate and after_rate and not plan.media.possible_vfr:
        assertions["cadence"] = abs(before_rate - after_rate) < 0.05
    if not all(assertions.values()):
        raise StudioError(f"Vérification export refusée : {assertions}")
    execute(
        [
            tools.ffmpeg,
            "-hide_banner",
            "-v",
            "error",
            "-xerror",
            "-threads",
            "2",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(output),
            "-map",
            "0:v",
            "-map",
            "0:a?",
            "-f",
            "null",
            "-",
        ],
        log,
        cancel,
    )
    assertions["full_decode"] = True
    return {"assertions": assertions, "ffprobe_after": after.raw}


def run_plan(
    plan: Plan,
    tools: Tools,
    job_dir: Path,
    cancel: Cancellation | None = None,
    on_progress: Callable[[float | None], None] | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> dict:
    cancel = cancel or Cancellation()
    job_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    log = job_dir / "pipeline.log"
    source, destination = (
        Path(plan.media.path),
        Path(plan.request.destination),
    )
    started = time.monotonic()
    original_hash = sha256(source, cancel)
    cancel.check()
    # Same filesystem: atomic hard-link finalization without replacing existing files.
    temporary_dir = Path(tempfile.mkdtemp(prefix=".studio-ia-", dir=destination.parent))
    temporary = temporary_dir / ("export" + destination.suffix.lower())
    result = None
    try:
        args = command(plan, tools, temporary)
        write_json(job_dir / "plan.json", plan.to_dict())
        write_json(job_dir / "command.json", args)
        if on_stage:
            on_stage("RUNNING")
        execute(
            args, log, cancel, on_progress, None if plan.media.possible_vfr else plan.media.duration
        )
        if on_stage:
            on_stage("VERIFYING")
        verification = verify_output(plan, temporary, tools, cancel, log)
        if sha256(source, cancel) != original_hash:
            raise StudioError("La source a changé pendant le traitement ; export non finalisé.")
        verification["assertions"]["source_unchanged"] = True
        result = {
            "schema_version": 1,
            "status": "PASS",
            "application_version": __version__,
            "application": build_identity(),
            "engine_version": plan.engine_version,
            "plan": plan.to_dict(),
            "source_sha256": original_hash,
            "output_sha256": sha256(temporary, cancel),
            "elapsed_seconds": time.monotonic() - started,
            "warnings": [],
            **verification,
        }
        write_json(job_dir / "verification.json", {**result, "status": "VERIFIED_NOT_COMMITTED"})
        with cancel.lock:
            cancel.check()
            result["finalization"] = publish_no_replace(temporary, destination)
            cancel.committed = True
        try:
            write_json(job_dir / "result.json", result)
        except OSError:
            result["warnings"].append("Export validé ; écriture du rapport local impossible.")
        return result
    except OSError as exc:
        raise StudioError(f"Stockage/finalisation impossible (aucun écrasement) : {exc}") from exc
    finally:
        try:
            shutil.rmtree(temporary_dir)
        except OSError:
            if result is not None and cancel.committed:
                result["warnings"].append(
                    "Export validé ; nettoyage du dossier temporaire impossible."
                )
                try:
                    write_json(job_dir / "result.json", result)
                except OSError:
                    pass
