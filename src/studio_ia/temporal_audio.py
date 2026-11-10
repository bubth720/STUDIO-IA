"""Read-only exact multi-track timing and packet identity for CPU remux qualification."""

import hashlib
import json
from fractions import Fraction
from pathlib import Path

from studio_ia.analysis_io import capture_local
from studio_ia.core import Cancellation, StudioError, Tools
from studio_ia.media import sha256
from studio_ia.temporal import FrameTimeline, _integer, probe_complete_timeline


def _rational(value) -> Fraction:
    if not isinstance(value, str) or "/" not in value:
        raise StudioError("Timebase audio rationnelle requise.")
    try:
        result = Fraction(value)
        if result <= 0:
            raise ValueError
        return result
    except (ValueError, ZeroDivisionError) as exc:
        raise StudioError("Timebase audio invalide.") from exc


def _optional_time(stream: dict, key: str, tb: Fraction) -> str | None:
    value = stream.get(key)
    return None if value in (None, "N/A") else str(_integer(value, key) * tb)


def audit_audio(
    path: Path,
    tools: Tools,
    *,
    timeline: FrameTimeline | None = None,
    cancel: Cancellation | None = None,
    max_packets: int = 40000,
) -> dict:
    if type(max_packets) is not int or not 1 <= max_packets <= 40000:
        raise StudioError("Budget de paquets audio invalide.")
    source = path.expanduser().resolve(strict=True)
    before = sha256(source, cancel)
    timeline = timeline or probe_complete_timeline(source, tools, cancel=cancel)
    if not timeline.complete:
        raise StudioError("Audit audio/vidéo complet impossible : couverture vidéo partielle.")
    text = capture_local(
        [
            tools.ffprobe,
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-read_intervals",
            f"%+#{max_packets + 1}",
            "-show_packets",
            "-show_streams",
            "-show_data_hash",
            "sha256",
            "-show_entries",
            "packet=stream_index,pts,duration,data_hash:packet_side_data=side_data_type,skip_samples,discard_padding:"
            "stream=index,codec_type,codec_name,time_base,start_pts,duration_ts,sample_rate,channels,channel_layout:"
            "stream_tags=language,title",
            "-of",
            "json",
            str(source),
        ],
        cancel,
        timeout=120,
        max_bytes=32 * 1024**2,
    )
    try:
        data = json.loads(text)
        packets = data["packets"]
        streams = data["streams"]
        if not isinstance(packets, list) or not isinstance(streams, list):
            raise TypeError
    except (ValueError, KeyError, TypeError) as exc:
        raise StudioError("Rapport de paquets illisible.") from exc
    if len(packets) > max_packets:
        raise StudioError("EOF audio non démontré : budget de paquets atteint.")
    tracks = []
    for stream in streams:
        if stream.get("codec_type") != "audio":
            continue
        index = _integer(stream["index"], "stream_index")
        tb = _rational(stream["time_base"])
        rows = [p for p in packets if p.get("stream_index") == index]
        if not rows:
            raise StudioError("Piste audio sans paquets observés.")
        pts = [_integer(p["pts"], "audio PTS") for p in rows if p.get("pts") not in (None, "N/A")]
        if len(pts) != len(rows):
            raise StudioError("PTS audio manquant, synchronisation inconnue.")
        ends = [
            pts[i] + _integer(p["duration"], "audio duration")
            for i, p in enumerate(rows)
            if p.get("duration") not in (None, "N/A")
        ]
        if any(
            _integer(p["duration"], "audio duration") <= 0
            for p in rows
            if p.get("duration") not in (None, "N/A")
        ):
            raise StudioError("Durée de paquet audio non positive.")
        start = _optional_time(stream, "start_pts", tb)
        end = str(max(ends) * tb) if len(ends) == len(rows) else None
        payloads = [p.get("data_hash") for p in rows]
        if any(not isinstance(h, str) or not h.startswith("SHA256:") for h in payloads):
            raise StudioError("Hash de paquet audio manquant.")
        tracks.append(
            {
                "stream_index": index,
                "codec": stream.get("codec_name"),
                "time_base": str(tb),
                "sample_rate": stream.get("sample_rate"),
                "channels": stream.get("channels"),
                "channel_layout": stream.get("channel_layout"),
                "language": stream.get("tags", {}).get("language"),
                "title": stream.get("tags", {}).get("title"),
                "declared_start": start,
                "declared_duration": _optional_time(stream, "duration_ts", tb),
                "first_packet_time": str(min(pts) * tb),
                "last_packet_end": end,
                "effective_start_evidence": "DECLARED_START_PTS"
                if start is not None
                else "FIRST_PACKET_PTS",
                "initial_offset_from_video": str(Fraction(start) - timeline.first_time)
                if start is not None
                else str(min(pts) * tb - timeline.first_time),
                "packet_count": len(rows),
                "packet_payload_sequence_sha256": hashlib.sha256(
                    "\n".join(payloads).encode("ascii")
                ).hexdigest(),
                "codec_delay_metadata": [s for p in rows for s in p.get("side_data_list", [])],
            }
        )
    if sha256(source, cancel) != before:
        raise StudioError("Source modifiée pendant le contrôle audio.")
    return {
        "schema_version": 1,
        "status": "PASS_READ_ONLY_AUDIO_AUDIT",
        "source_sha256": before,
        "video_first_time": str(timeline.first_time),
        "video_duration": str(timeline.duration) if timeline.duration is not None else None,
        "video_pts_seconds": [str(f.pts * timeline.time_base) for f in timeline.frames],
        "tracks": tracks,
        "audio_track_count": len(tracks),
        "observed_packet_count": len(packets),
        "complete_packet_eof": True,
        "audio_reencoded": False,
        "limitations": [
            "Packet extent is distinct from perceptual end and codec priming/discard padding.",
            "An audit alone makes no synchronization or remux quality claim.",
        ],
    }


def compare_audio(before: dict, after: dict, *, tolerance: Fraction = Fraction(1, 20)) -> dict:
    """Strict bitstream-copy contract: no track loss, offset drift or hidden reencoding."""
    if tolerance < 0 or len(before["tracks"]) != len(after["tracks"]):
        raise StudioError("Piste perdue ou tolérance invalide.")
    if before["video_pts_seconds"] != after["video_pts_seconds"]:
        raise StudioError("PTS vidéo modifiés pendant le contrôle de remux.")
    drifts = []
    for left, right in zip(before["tracks"], after["tracks"], strict=True):
        for key in (
            "codec",
            "sample_rate",
            "channels",
            "language",
            "title",
            "packet_count",
            "packet_payload_sequence_sha256",
        ):
            if left[key] != right[key]:
                raise StudioError(f"Piste audio modifiée : {key}.")
        drift = abs(
            Fraction(left["initial_offset_from_video"])
            - Fraction(right["initial_offset_from_video"])
        )
        ends = (left["last_packet_end"], right["last_packet_end"])
        end_drift = (
            abs(Fraction(ends[0]) - Fraction(ends[1])) if all(x is not None for x in ends) else None
        )
        if end_drift is None:
            raise StudioError("Fin audio inconnue : drift non qualifiable.")
        if max(drift, end_drift) > tolerance:
            raise StudioError("Drift audio hors tolérance.")
        drifts.append(
            {
                "stream_index": left["stream_index"],
                "initial_offset_drift_seconds": str(drift),
                "end_drift_seconds": str(end_drift),
            }
        )
    if before["video_duration"] is None or before["video_duration"] != after["video_duration"]:
        raise StudioError("Durée vidéo inconnue ou modifiée.")
    return {
        "status": "PASS_STRICT_CPU_REMUX_COMPARISON",
        "audio_reencoded": False,
        "tolerance_seconds": str(tolerance),
        "tracks": drifts,
        "neural_executed": False,
    }
