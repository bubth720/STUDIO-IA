"""Bounded CPU translation/luminance diagnostics, not a neural quality estimator."""

from fractions import Fraction
from pathlib import Path
from statistics import mean

from studio_ia.core import Cancellation, Tools
from studio_ia.scene_detect import SAMPLE_SIZE, SceneScan, scan_scenes


class TranslationTracker:
    """Keep two 16x16 luma planes; compare the same central 12x12 ROI at every offset."""

    def __init__(self):
        self.previous: bytes | None = None
        self.rows: list[dict] = []

    def feed(self, index: int, sample: bytes) -> None:
        small = bytes(sample[y * SAMPLE_SIZE + x] for y in range(0, 32, 2) for x in range(0, 32, 2))
        if self.previous is not None:
            previous = self.previous
            options = []
            positions = [y * 16 + x for y in range(2, 14) for x in range(2, 14)]
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    errors = [small[p] - previous[p - dy * 16 - dx] for p in positions]
                    options.append((sum(abs(e) for e in errors), dx, dy, sum(errors)))
            options.sort(key=lambda row: (row[0], abs(row[1]) + abs(row[2])))
            best, second = options[:2]
            unique = best[0] < second[0]
            original = next(row[0] for row in options if row[1:3] == (0, 0))
            self.rows.append(
                {
                    "frame_index": index,
                    "status": "MEASURED_TRANSLATION" if unique else "UNOBSERVABLE_OR_AMBIGUOUS",
                    "dx_sample_pixels": best[1] if unique else None,
                    "dy_sample_pixels": best[2] if unique else None,
                    "unaligned_mae_percent": str(Fraction(original * 100, 144 * 255)),
                    "aligned_mae_percent": str(Fraction(best[0] * 100, 144 * 255))
                    if unique
                    else None,
                    "aligned_luma_bias_percent": str(Fraction(abs(best[3]) * 100, 144 * 255))
                    if unique
                    else None,
                    "winner_margin_sad": second[0] - best[0],
                }
            )
        self.previous = small

    def report(self, scan: SceneScan) -> dict:
        boundaries = {b.frame_index for b in scan.boundaries}
        rows = []
        for row in self.rows:
            result = dict(row)
            if row["frame_index"] in boundaries:
                result.update(
                    status="EXCLUDED_SCENE_TRANSITION",
                    dx_sample_pixels=None,
                    dy_sample_pixels=None,
                    aligned_mae_percent=None,
                    aligned_luma_bias_percent=None,
                )
            rows.append(result)
        observed = [r for r in rows if r["status"] == "MEASURED_TRANSLATION"]

        def average(key):
            return str(mean(Fraction(r[key]) for r in observed)) if observed else None

        return {
            "schema_version": 1,
            "status": "PASS_CPU_DIAGNOSTIC" if observed else "NOT_APPLICABLE_UNOBSERVABLE_MOTION",
            "source_sha256": scan.source_sha256,
            "method": "GRAY8_32x32_PADDED_THEN_DECIMATED_16x16_TRANSLATION_SAD_FIXED_12x12_ROI",
            "search_radius_sample_pixels": 2,
            "sample_pixel_scale": "2 pixels of the 32x32 analysis plane",
            "measured_pairs": len(observed),
            "excluded_transitions": sum(r["status"] == "EXCLUDED_SCENE_TRANSITION" for r in rows),
            "mean_aligned_mae_percent": average("aligned_mae_percent"),
            "mean_aligned_luma_bias_percent": average("aligned_luma_bias_percent"),
            "pairs": rows,
            "neural_executed": False,
            "ghosting": "NOT_APPLICABLE_NO_ALIGNED_REFERENCE_OR_NEURAL_OUTPUT",
            "limitations": [
                "Translation only: neither dense optical flow nor an occlusion mask.",
                "Low resolution may miss fine edges; ambiguous matches stay unknown, not zero.",
                "Luma bias may be exposure/lighting/motion; it is not proof of perceptual flicker.",
                "No automatic smoothing, frame replacement or change of model/profile.",
            ],
        }


def analyze_motion(
    path: Path, tools: Tools, *, cancel: Cancellation | None = None, max_frames: int = 10000
) -> tuple[SceneScan, dict]:
    tracker = TranslationTracker()
    scan = scan_scenes(
        path, tools, cancel=cancel, max_frames=max_frames, sample_observer=tracker.feed
    )
    return scan, tracker.report(scan)
