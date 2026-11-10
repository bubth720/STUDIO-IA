"""CPU scene evidence and conservative guards; never generates or interpolates an image."""

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from studio_ia.analysis_io import capture_local
from studio_ia.core import Cancellation, StudioError, Tools
from studio_ia.media import sha256
from studio_ia.temporal import FrameTimeline, frame_records, probe_complete_timeline

SAMPLE_SIZE = 32
_HEADER = re.compile(r"frame:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:")


@dataclass(frozen=True)
class SceneBoundary:
    frame_index: int
    pts: int
    kind: str
    score_percent: str
    reason: str


@dataclass(frozen=True)
class SceneScan:
    source_sha256: str
    timeline: FrameTimeline
    scores: tuple[tuple[Decimal, Decimal], ...]
    boundaries: tuple[SceneBoundary, ...]
    frame_hashes: tuple[str, ...]
    means: tuple[str, ...]
    threshold: str
    ffmpeg_version: str
    ignored_boundaries: tuple[int, ...] = ()

    def to_dict(self) -> dict:
        indexes = tuple(sorted({b.frame_index for b in self.boundaries}))
        return {
            "schema_version": 1,
            "status": "PASS_READ_ONLY_SCENE_ANALYSIS",
            "scope": "CPU_ONLY_NOT_RIFE_QUALIFICATION",
            "source_sha256": self.source_sha256,
            "timeline": self.timeline.summary(),
            "threshold_percent": self.threshold,
            "score_definition": "FFmpeg scdet; score is not a calibrated semantic probability",
            "preprocessing": f"GRAY8_{SAMPLE_SIZE}x{SAMPLE_SIZE}_ASPECT_PADDED_FOR_ANALYSIS_ONLY",
            "ffmpeg_version": self.ffmpeg_version,
            "boundaries": [asdict(b) for b in self.boundaries],
            "manual_exclusions": list(self.ignored_boundaries),
            "records": [
                asdict(r) for r in frame_records(self.timeline, indexes, self.frame_hashes)
            ],
            "scores": [
                {"frame_index": i, "mafd_percent": str(a), "score_percent": str(b)}
                for i, (a, b) in enumerate(self.scores)
            ],
            "mean_luma": list(self.means),
            "neural_executed": False,
            "limitations": [
                "Flash and a one-frame scene insert can be indistinguishable.",
                "Cuts are conservative candidates. "
                "A pan or split-screen change can be a false positive.",
                "Threshold calibration and manual boundaries remain necessary for real footage.",
            ],
        }


def _threshold(value) -> Decimal:
    try:
        result = Decimal(str(value))
        if isinstance(value, bool) or not result.is_finite() or not 0 < result <= 100:
            raise ValueError
        return result
    except (InvalidOperation, ValueError) as exc:
        raise StudioError("Seuil de coupe attendu dans ]0,100].") from exc


def parse_scores(text: str, timeline: FrameTimeline) -> tuple[tuple[Decimal, Decimal], ...]:
    rows: list[dict] = []
    for line in text.splitlines():
        header = _HEADER.search(line)
        if header:
            index, pts = int(header[1]), int(header[2])
            if (
                index != len(rows)
                or index >= len(timeline.frames)
                or pts != timeline.frames[index].pts
            ):
                raise StudioError("Les scores de scènes ne correspondent pas aux PTS décodés.")
            rows.append({})
        elif line.startswith(("lavfi.scd.mafd=", "lavfi.scd.score=")):
            if not rows:
                raise StudioError("Score sans identité de frame.")
            key, value = line.split("=", 1)
            try:
                score = Decimal(value)
            except InvalidOperation as exc:
                raise StudioError("Score de scène invalide.") from exc
            if not score.is_finite() or not 0 <= score <= 100 or key in rows[-1]:
                raise StudioError("Score de scène hors limites ou dupliqué.")
            rows[-1][key] = score
    if len(rows) != len(timeline.frames) or any(len(r) != 2 for r in rows):
        raise StudioError("Couverture des scores de scènes incomplète.")
    return tuple((r["lavfi.scd.mafd"], r["lavfi.scd.score"]) for r in rows)


def classify(
    timeline: FrameTimeline,
    scores: tuple[tuple[Decimal, Decimal], ...],
    hashes: tuple[str, ...],
    means: tuple[Decimal, ...],
    threshold: Decimal,
    manual: tuple[int, ...] = (),
) -> tuple[SceneBoundary, ...]:
    frame_records(
        timeline, manual, hashes
    )  # shared validation, including duplicate manual boundaries.
    decisions: dict[int, SceneBoundary] = {}
    for i in range(1, len(scores)):
        if scores[i][1] >= threshold:
            decisions[i] = SceneBoundary(
                i,
                timeline.frames[i].pts,
                "CUT_CANDIDATE",
                str(scores[i][1]),
                "SCDET_THRESHOLD_CROSSED",
            )
    for i in range(1, len(scores) - 1):
        if (
            hashes[i - 1] == hashes[i + 1] != hashes[i]
            and scores[i][0] >= threshold
            and scores[i + 1][0] >= threshold
        ):
            for edge in (i, i + 1):
                decisions[edge] = SceneBoundary(
                    edge,
                    timeline.frames[edge].pts,
                    "FLASH_OR_SINGLE_FRAME_INSERT",
                    str(scores[edge][0]),
                    "RETURN_TO_IDENTICAL_ANALYSIS_FRAME",
                )
    # A smooth global-luminance ramp is reported conservatively, not called a hard cut.
    for i in range(2, len(scores) - 1):
        diffs = [means[k] - means[k - 1] for k in range(i - 1, i + 2)]
        if (all(d > 0 for d in diffs) or all(d < 0 for d in diffs)) and sum(
            abs(d) for d in diffs
        ) >= 12:
            decisions.setdefault(
                i,
                SceneBoundary(
                    i,
                    timeline.frames[i].pts,
                    "GRADUAL_CHANGE_CANDIDATE",
                    str(scores[i][0]),
                    "MONOTONE_LUMINANCE_CHANGE_NOT_PROOF_OF_A_DISSOLVE",
                ),
            )
    for i in manual:
        decisions[i] = SceneBoundary(
            i, timeline.frames[i].pts, "MANUAL_BOUNDARY", "100", "EXPLICIT_OPERATOR_BOUNDARY"
        )
    return tuple(decisions[i] for i in sorted(decisions))


def scan_scenes(
    path: Path,
    tools: Tools,
    *,
    threshold=10,
    manual_boundaries: tuple[int, ...] = (),
    ignored_boundaries: tuple[int, ...] = (),
    max_frames: int = 10000,
    cancel: Cancellation | None = None,
) -> SceneScan:
    cancel = cancel or Cancellation()
    cancel.check()
    limit = _threshold(threshold)
    source = path.expanduser().resolve(strict=True)
    before = sha256(source, cancel)
    timeline = probe_complete_timeline(source, tools, max_frames=max_frames, cancel=cancel)
    cancel.check()
    if not timeline.complete:
        raise StudioError("Analyse des coupes refusée : vidéo complète non couverte par le budget.")
    frame_records(timeline, manual_boundaries)
    frame_records(timeline, ignored_boundaries)
    if set(manual_boundaries) & set(ignored_boundaries):
        raise StudioError("Une coupe ne peut être imposée et exclue simultanément.")
    count = len(timeline.frames)
    required = count * SAMPLE_SIZE**2
    if shutil.disk_usage(tempfile.gettempdir()).free < required + 32 * 1024**2:
        raise StudioError("Espace insuffisant pour l'analyse bornée.")
    tb = timeline.time_base
    graph = (
        f"settb=expr={tb.numerator}/{tb.denominator},"
        f"scale={SAMPLE_SIZE}:{SAMPLE_SIZE}:force_original_aspect_ratio=decrease,"
        f"pad={SAMPLE_SIZE}:{SAMPLE_SIZE}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"scdet=threshold={limit},metadata=mode=print:file='pipe\\:1',format=gray"
    )
    with tempfile.TemporaryDirectory(prefix="studio-scene-analysis-") as temp:
        raw = Path(temp) / "owned.gray"
        text = capture_local(
            [
                tools.ffmpeg,
                "-v",
                "error",
                "-xerror",
                "-n",
                "-threads",
                "2",
                "-filter_threads",
                "1",
                "-protocol_whitelist",
                "file,pipe",
                "-copyts",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-an",
                "-frames:v",
                str(count + 1),
                "-vf",
                graph,
                "-fps_mode",
                "passthrough",
                "-c:v",
                "rawvideo",
                "-threads",
                "1",
                "-pix_fmt",
                "gray",
                "-f",
                "rawvideo",
                str(raw),
            ],
            cancel,
        )
        scores = parse_scores(text, timeline)
        if raw.stat().st_size != required:
            raise StudioError("Décodage d'analyse incomplet ou nombre de frames modifié.")
        hashes, means = [], []
        with raw.open("rb") as stream:
            for _ in timeline.frames:
                cancel.check()
                frame = stream.read(SAMPLE_SIZE**2)
                hashes.append(hashlib.sha256(frame).hexdigest())
                means.append(Decimal(sum(frame)) / Decimal(len(frame)))
    if sha256(source, cancel) != before:
        raise StudioError("La source a changé pendant l'analyse des coupes.")
    boundaries = classify(timeline, scores, tuple(hashes), tuple(means), limit, manual_boundaries)
    boundaries = tuple(b for b in boundaries if b.frame_index not in ignored_boundaries)
    version = capture_local([tools.ffmpeg, "-version"], cancel).splitlines()[0]
    return SceneScan(
        before,
        timeline,
        scores,
        boundaries,
        tuple(hashes),
        tuple(str(m) for m in means),
        str(limit),
        version,
        ignored_boundaries,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--threshold", default="10")
    parser.add_argument("--cut", type=int, action="append", default=[])
    parser.add_argument("--ignore-cut", type=int, action="append", default=[])
    parser.add_argument("--max-frames", type=int, default=10000)
    args = parser.parse_args()
    try:
        result = scan_scenes(
            args.source,
            Tools.discover(),
            threshold=args.threshold,
            manual_boundaries=tuple(args.cut),
            ignored_boundaries=tuple(args.ignore_cut),
            max_frames=args.max_frames,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
        return 0
    except (StudioError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
