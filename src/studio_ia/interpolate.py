"""Executable-independent x2 scheduling and scene guards. No RIFE engine is enabled."""

import argparse
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from studio_ia.core import StudioError, Tools
from studio_ia.scene_detect import SceneScan, scan_scenes


@dataclass(frozen=True)
class ScheduledFrame:
    output_index: int
    pts: str
    duration: str
    action: str
    left_source_index: int
    right_source_index: int | None
    reason: str


def plan_x2(scan: SceneScan, *, explicit_opt_in: bool = False) -> dict:
    if explicit_opt_in is not True:
        raise StudioError(
            "Plan ×2 uniquement sur demande explicite, jamais de conversion automatique."
        )
    timeline = scan.timeline
    if not timeline.complete or any(f.duration is None for f in timeline.frames):
        raise StudioError("Durées finales/couverture inconnues : plan d'interpolation refusé.")
    # VFR input is preserved by the inspector. An x2 CFR renderer is not silently imposed.
    durations = {f.duration for f in timeline.frames}
    if len(durations) != 1:
        raise StudioError("VFR : aucun rééchantillonnage CFR ou 60fps implicite n'est autorisé.")
    interval = timeline.frames[0].duration
    assert interval is not None
    boundaries = {b.frame_index: b for b in scan.boundaries}
    rows = []
    neutralized = []
    for index, source in enumerate(timeline.frames):
        assert source.duration is not None
        start = source.pts * timeline.time_base
        half = source.duration * timeline.time_base / 2
        rows.append(
            ScheduledFrame(
                2 * index,
                str(start),
                str(half),
                "SOURCE_ANCHOR",
                index,
                None,
                "PRESERVE_ORIGINAL_PTS",
            )
        )
        if index + 1 == len(timeline.frames):
            action, right, reason = "HOLD_LAST", None, "COVER_FINAL_INTERVAL_WITHOUT_FUTURE_IMAGE"
        elif index + 1 in boundaries:
            action, right, reason = "HOLD_SOURCE", None, boundaries[index + 1].kind
            neutralized.append(
                {
                    "left_index": index,
                    "right_index": index + 1,
                    "start": str(start),
                    "end": str(start + 2 * half),
                    "reason": reason,
                }
            )
        else:
            action, right, reason = (
                "RIFE_REQUEST_NOT_EXECUTED",
                index + 1,
                "M004_AND_RIFE_GATES_CLOSED",
            )
        rows.append(
            ScheduledFrame(
                2 * index + 1, str(start + half), str(half), action, index, right, reason
            )
        )
    if any(
        Fraction(b.pts) != Fraction(a.pts) + Fraction(a.duration)
        for a, b in zip(rows, rows[1:], strict=False)
    ):
        raise StudioError("Le planning ne conserve pas les intervalles source.")
    original_duration = timeline.duration
    assert original_duration is not None
    if sum((Fraction(r.duration) for r in rows), Fraction()) != original_duration:
        raise StudioError("Durée du planning modifiée.")
    return {
        "schema_version": 1,
        "status": "PREPARATION_PLAN_ONLY",
        "can_execute_neural": False,
        "source_sha256": scan.source_sha256,
        "source_frames": len(timeline.frames),
        "planned_frames": len(rows),
        "convention": "N_TO_2N_WITH_EXPLICIT_HOLD_LAST",
        "original_duration": str(original_duration),
        "planned_duration": str(original_duration),
        "source_frame_rate": str(1 / (interval * timeline.time_base)),
        "planned_frame_rate": str(2 / (interval * timeline.time_base)),
        "neutralized_intervals": neutralized,
        "frames": [asdict(r) for r in rows],
        "rife_executed": False,
        "m004_gate": "BLOCKED",
        "m005_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--explicit-x2-plan", action="store_true")
    parser.add_argument("--cut", type=int, action="append", default=[])
    args = parser.parse_args()
    try:
        scan = scan_scenes(args.source, Tools.discover(), manual_boundaries=tuple(args.cut))
        print(json.dumps(plan_x2(scan, explicit_opt_in=args.explicit_x2_plan), indent=2))
        return 0
    except (StudioError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
