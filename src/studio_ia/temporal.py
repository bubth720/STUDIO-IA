"""M005 preflight: inspect decoded presentation timestamps without resampling video.

This read-only module does NOT interpolate frames or qualify RIFE. A bounded
ffprobe query supplies exact integer timestamps; no floating point arithmetic is
used for timing decisions.
"""

import argparse
import json
import re
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path

from studio_ia.analysis_io import capture_local
from studio_ia.core import Cancellation, StudioError, Tools, capture

_INTEGER = re.compile(r"-?\d+\Z")
_RATIONAL = re.compile(r"-?\d+/\d+\Z")


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not _INTEGER.fullmatch(str(value)):
        raise StudioError(f"Horodatage invalide : {label} doit être entier.")
    return int(str(value))


@dataclass(frozen=True)
class FrameStamp:
    index: int
    pts: int
    duration: int | None
    keyframe: bool
    duration_evidence: str


@dataclass(frozen=True)
class FrameRecord:
    """Serializable frame identity; hashes require an explicitly documented pixel domain."""

    frame_index: int
    pts_int: int
    time_base_num: int
    time_base_den: int
    duration_int: int | None
    keyframe: bool
    scene_id: int = 0
    frame_sha256: str | None = None

    def __post_init__(self):
        for name in ("frame_index", "pts_int", "time_base_num", "time_base_den", "scene_id"):
            if type(getattr(self, name)) is not int:
                raise StudioError("FrameRecord : champs temporels entiers requis.")
        if (
            self.frame_index < 0
            or self.scene_id < 0
            or min(self.time_base_num, self.time_base_den) <= 0
        ):
            raise StudioError("FrameRecord : index ou timebase invalide.")
        if self.duration_int is not None and (
            type(self.duration_int) is not int or self.duration_int <= 0
        ):
            raise StudioError("FrameRecord : durée positive ou inconnue requise.")
        if type(self.keyframe) is not bool:
            raise StudioError("FrameRecord : keyframe booléen requis.")
        if self.frame_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", self.frame_sha256):
            raise StudioError("FrameRecord : hash invalide.")

    @property
    def presentation_time(self) -> Fraction:
        return self.pts_int * Fraction(self.time_base_num, self.time_base_den)


@dataclass(frozen=True)
class FrameTimeline:
    time_base: Fraction
    frames: tuple[FrameStamp, ...]
    complete: bool
    declared_frame_count: int | None
    differing_declared_durations: int
    coverage_evidence: str = "DECLARED_FRAME_COUNT_OR_PREFIX"

    @property
    def first_time(self) -> Fraction:
        return self.frames[0].pts * self.time_base

    @property
    def last_time(self) -> Fraction:
        return self.frames[-1].pts * self.time_base

    @property
    def duration(self) -> Fraction | None:
        last = self.frames[-1]
        if last.duration is None:
            return None
        return (last.pts + last.duration - self.frames[0].pts) * self.time_base

    @property
    def nonuniform_pts_deltas(self) -> bool:
        gaps = [
            right.pts - left.pts for left, right in zip(self.frames, self.frames[1:], strict=False)
        ]
        return len(set(gaps)) > 1

    def summary(self) -> dict:
        return {
            "schema_version": 1,
            "mode": "READ_ONLY_PTS_INSPECTION_NOT_INTERPOLATION",
            "status": "PASS" if self.complete else "PARTIAL_PREFIX",
            "frame_count_observed": len(self.frames),
            "frame_count_declared": self.declared_frame_count,
            "time_base": str(self.time_base),
            "first_pts": self.frames[0].pts,
            "first_time_seconds": str(self.first_time),
            "last_pts": self.frames[-1].pts,
            "duration_from_first_frame_seconds": (
                str(self.duration) if self.duration is not None else None
            ),
            "nonuniform_pts_deltas": self.nonuniform_pts_deltas,
            "differing_declared_durations": self.differing_declared_durations,
            "complete": self.complete,
            "coverage_evidence": self.coverage_evidence,
            "limitations": [
                "PTS delta variation alone does not prove VFR; codec timebase rounding may differ.",
                "No interpolation, optical-flow estimation or RIFE inference performed.",
            ],
        }


def parse_frame_timeline(payload: dict, *, max_frames: int = 3000) -> FrameTimeline:
    """Validate exact decoded frame PTS, allowing VFR and nonzero/negative starts.

    Unlike the M004 neural path, this diagnostic never requires consecutive
    equidistant timestamps. The final frame duration remains unknown if ffprobe
    does not report it. It never invents a last-frame interval.
    """
    if (
        isinstance(max_frames, bool)
        or not isinstance(max_frames, int)
        or not 1 <= max_frames <= 10000
    ):
        raise StudioError("Budget de frames invalide (1 à 10000).")
    if not isinstance(payload, dict):
        raise StudioError("Rapport ffprobe invalide.")
    streams = payload.get("streams")
    rows = payload.get("frames")
    if not isinstance(streams, list) or len(streams) != 1 or not isinstance(rows, list):
        raise StudioError("Flux vidéo ou liste de frames indisponibles.")
    if not rows or len(rows) > max_frames:
        raise StudioError("Frames vides ou limite de lecture dépassée.")
    try:
        raw_time_base = streams[0]["time_base"]
        if not isinstance(raw_time_base, str) or not _RATIONAL.fullmatch(raw_time_base):
            raise ValueError("A rational string is required; binary floats are not timestamps")
        time_base = Fraction(raw_time_base)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise StudioError("Timebase rationnelle invalide.") from exc
    if time_base <= 0:
        raise StudioError("Timebase non positive.")

    declared = streams[0].get("nb_frames")
    if declared in (None, "N/A"):
        declared_count = None
    else:
        declared_count = _integer(declared, "nb_frames")
        if declared_count <= 0:
            raise StudioError("Nombre déclaré de frames invalide.")

    pts_list: list[int] = []
    raw_durations: list[int | None] = []
    keyflags: list[bool] = []
    for row in rows:
        if not isinstance(row, dict) or "best_effort_timestamp" not in row:
            raise StudioError("Timestamp décodé manquant.")
        pts_list.append(_integer(row["best_effort_timestamp"], "PTS"))
        raw = row.get("duration", row.get("pkt_duration"))
        duration = None if raw in (None, "N/A") else _integer(raw, "durée")
        if duration is not None and duration <= 0:
            raise StudioError("Durée de frame non positive.")
        raw_durations.append(duration)
        keyflags.append(row.get("key_frame") in (1, "1"))
    if any(b <= a for a, b in zip(pts_list, pts_list[1:], strict=False)):
        raise StudioError("PTS dupliqués ou non monotones : analyse refusée.")

    frames = []
    mismatches = 0
    for index, pts in enumerate(pts_list):
        raw_duration = raw_durations[index]
        if index + 1 < len(pts_list):
            duration = pts_list[index + 1] - pts
            evidence = "NEXT_DECODED_PTS"
            if raw_duration is not None and raw_duration != duration:
                mismatches += 1
        else:
            duration = raw_duration
            evidence = "LAST_DECLARED_DURATION" if duration is not None else "UNKNOWN_LAST_DURATION"
        frames.append(FrameStamp(index, pts, duration, keyflags[index], evidence))

    # Frame count is complete only if ffprobe provided a matching, explicit total.
    # Otherwise this is a prefix sample, never proof of complete coverage.
    complete = declared_count is not None and declared_count == len(frames)
    if declared_count is not None and declared_count < len(frames):
        raise StudioError("Nombre de frames incohérent entre flux et images décodées.")
    return FrameTimeline(time_base, tuple(frames), complete, declared_count, mismatches)


def probe_frame_timeline(
    path: Path, tools: Tools, *, max_frames: int = 3000, cancel: Cancellation | None = None
) -> FrameTimeline:
    if (
        isinstance(max_frames, bool)
        or not isinstance(max_frames, int)
        or not 1 <= max_frames <= 10000
    ):
        raise StudioError("Budget de frames invalide (1 à 10000).")
    source = path.expanduser().resolve(strict=True)
    if not source.is_file():
        raise StudioError("La source doit être une vidéo locale existante.")
    run = (
        capture if cancel is None else lambda args, **kwargs: capture_local(args, cancel, **kwargs)
    )
    output = run(
        [
            tools.ffprobe,
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-select_streams",
            "v:0",
            "-read_intervals",
            f"%+#{max_frames + 1}",
            "-show_frames",
            "-show_streams",
            "-show_entries",
            "frame=best_effort_timestamp,duration,pkt_duration,key_frame:"
            "stream=time_base,nb_frames",
            "-of",
            "json",
            str(source),
        ],
        timeout=120,
    )
    try:
        data = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise StudioError("Réponse ffprobe illisible.") from exc
    # The extra decoded frame is a sentinel, not permission to exceed the returned budget.
    rows = data.get("frames", []) if isinstance(data, dict) else []
    extra = isinstance(rows, list) and len(rows) > max_frames
    if extra:
        data["frames"] = rows[:max_frames]
    timeline = parse_frame_timeline(data, max_frames=max_frames)
    if extra:
        if timeline.complete:
            raise StudioError(
                "Frames supplémentaires malgré le total déclaré : source incohérente."
            )
        next_pts = _integer(rows[max_frames]["best_effort_timestamp"], "PTS sentinelle")
        last = timeline.frames[-1]
        if next_pts <= last.pts:
            raise StudioError("PTS sentinelle non monotone.")
        last = replace(
            last, duration=next_pts - last.pts, duration_evidence="NEXT_PTS_OUTSIDE_PREFIX"
        )
        timeline = replace(
            timeline,
            frames=(*timeline.frames[:-1], last),
            coverage_evidence="BOUNDED_PREFIX_WITH_SENTINEL",
        )
    return timeline


def probe_complete_timeline(
    path: Path, tools: Tools, *, max_frames: int = 10000, cancel: Cancellation | None = None
) -> FrameTimeline:
    """Prove bounded EOF with packet/decode counters, including containers without nb_frames.

    Legacy probe_frame_timeline keeps its conservative header/prefix contract.
    A complete result here requires EOF before the packet limit, agreement with
    the decoder counter and an unchanged source hash across both observations.
    """
    from studio_ia.media import sha256

    source = path.expanduser().resolve(strict=True)
    before = sha256(source, cancel)
    timeline = probe_frame_timeline(source, tools, max_frames=max_frames, cancel=cancel)
    run = (
        capture if cancel is None else lambda args, **kwargs: capture_local(args, cancel, **kwargs)
    )
    raw = run(
        [
            tools.ffprobe,
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-select_streams",
            "v:0",
            "-read_intervals",
            f"%+#{max_frames + 1}",
            "-count_frames",
            "-count_packets",
            "-show_entries",
            "stream=nb_read_frames,nb_read_packets",
            "-of",
            "json",
            str(source),
        ],
        timeout=120,
    )
    try:
        data = json.loads(raw)
        stream = data["streams"][0]
        packets = _integer(stream["nb_read_packets"], "paquets décodés")
        decoded = _integer(stream["nb_read_frames"], "frames décodées")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise StudioError("Compteurs EOF indisponibles, couverture non démontrée.") from exc
    if sha256(source, cancel) != before:
        raise StudioError("La source a changé pendant l'analyse temporelle.")
    eof = 0 < packets < max_frames + 1 and decoded == len(timeline.frames)
    if not eof:
        return replace(timeline, complete=False, coverage_evidence="PARTIAL_NO_EOF_PROOF")
    if timeline.declared_frame_count is not None and timeline.declared_frame_count != decoded:
        raise StudioError("Total déclaré différent du décodage à EOF.")
    return replace(timeline, complete=True, coverage_evidence="BOUNDED_EOF_AND_DECODE_COUNTERS")


def frame_records(
    timeline: FrameTimeline, boundaries: tuple[int, ...] = (), hashes: tuple[str, ...] | None = None
) -> tuple[FrameRecord, ...]:
    if len(set(boundaries)) != len(boundaries) or any(
        type(i) is not int or not 0 < i < len(timeline.frames) for i in boundaries
    ):
        raise StudioError("Limites de scènes invalides.")
    if hashes is not None and len(hashes) != len(timeline.frames):
        raise StudioError("Nombre de hashes différent des frames.")
    scene = 0
    records = []
    for frame in timeline.frames:
        if frame.index in boundaries:
            scene += 1
        records.append(
            FrameRecord(
                frame.index,
                frame.pts,
                timeline.time_base.numerator,
                timeline.time_base.denominator,
                frame.duration,
                frame.keyframe,
                scene,
                hashes[frame.index] if hashes is not None else None,
            )
        )
    return tuple(records)


def main() -> int:
    parser = argparse.ArgumentParser(description="STUDIO IA M005 - diagnostic PTS en lecture seule")
    parser.add_argument("source", type=Path, help="Vidéo locale à inspecter")
    parser.add_argument("--max-frames", type=int, default=3000)
    args = parser.parse_args()
    try:
        result = probe_frame_timeline(args.source, Tools.discover(), max_frames=args.max_frames)
    except (StudioError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result.summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
