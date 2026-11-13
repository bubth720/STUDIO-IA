"""Actual FFmpeg fixtures and scheduling contracts; no mocked NN result is qualified."""

from dataclasses import replace
from fractions import Fraction

import pytest

from studio_ia.core import StudioError, capture
from studio_ia.interpolate import plan_x2
from studio_ia.media import sha256
from studio_ia.scene_detect import scan_scenes
from studio_ia.temporal import frame_records, probe_complete_timeline, probe_frame_timeline


def make_clip(tools, path, *, kind="cut", duration=8, fps="25", container=None):
    if kind == "cut":
        filters = "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable=gte(n\\,100)"
    elif kind == "flash":
        filters = "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable=eq(n\\,20)"
    elif kind == "split":
        filters = "drawbox=x=0:y=0:w=iw/2:h=ih:color=white:t=fill"
    elif kind == "fade":
        filters = "fade=t=in:st=0:d=2"
    else:
        filters = "null"
    color = "white" if kind == "fade" else "black"
    args = [
        tools.ffmpeg,
        "-v",
        "error",
        "-n",
        "-f",
        "lavfi",
        "-i",
        f"color={color}:size=64x48:rate={fps}:duration={duration}",
        "-vf",
        filters,
        "-c:v",
        "libx264",
        "-threads",
        "1",
        "-crf",
        "0",
        "-pix_fmt",
        "yuv420p",
    ]
    if container:
        args += ["-f", container]
    capture(args + [str(path)])
    return path


def test_actual_cut_at_100_has_no_midpoint_request_across_scenes(tmp_path, tools):
    source = make_clip(tools, tmp_path / "cut.mp4")
    before = sha256(source)
    scan = scan_scenes(source, tools)
    assert scan.timeline.complete and len(scan.timeline.frames) == 200
    assert [b.frame_index for b in scan.boundaries] == [100]
    schedule = plan_x2(scan, explicit_opt_in=True)
    assert schedule["source_frame_rate"] == "25" and schedule["planned_frame_rate"] == "50"
    assert schedule["planned_frames"] == 400 and schedule["planned_duration"] == "8"
    assert schedule["frames"][199]["action"] == "HOLD_SOURCE"
    assert schedule["frames"][-1]["action"] == "HOLD_LAST"
    assert schedule["can_execute_neural"] is False and schedule["rife_executed"] is False
    records = frame_records(scan.timeline, (100,), scan.frame_hashes)
    assert records[99].scene_id == 0 and records[100].scene_id == 1
    assert records[100].presentation_time == 4 and records[100].frame_sha256
    assert sha256(source) == before


def test_flash_and_return_are_both_neutralized(tmp_path, tools):
    source = make_clip(tools, tmp_path / "flash.mp4", kind="flash", duration=2)
    scan = scan_scenes(source, tools)
    flashes = [b for b in scan.boundaries if b.kind == "FLASH_OR_SINGLE_FRAME_INSERT"]
    assert [b.frame_index for b in flashes] == [20, 21]
    schedule = plan_x2(scan, explicit_opt_in=True)
    assert schedule["frames"][39]["action"] == schedule["frames"][41]["action"] == "HOLD_SOURCE"


def test_stable_split_screen_has_no_false_cut(tmp_path, tools):
    source = make_clip(tools, tmp_path / "split.mp4", kind="split", duration=2)
    scan = scan_scenes(source, tools)
    assert scan.boundaries == ()
    with pytest.raises(StudioError, match="explicite"):
        plan_x2(scan)


def test_fade_is_conservative_and_manual_boundaries_are_logged(tmp_path, tools):
    source = make_clip(tools, tmp_path / "fade.mp4", kind="fade", duration=3)
    scan = scan_scenes(source, tools, manual_boundaries=(10,))
    assert any(b.frame_index == 10 and b.kind == "MANUAL_BOUNDARY" for b in scan.boundaries)
    assert not any(b.kind == "CUT_CANDIDATE" for b in scan.boundaries)
    assert any(b.kind == "GRADUAL_CHANGE_CANDIDATE" for b in scan.boundaries)
    with pytest.raises(StudioError, match="Limites"):
        frame_records(scan.timeline, (10, 10))


def test_prefix_is_not_complete_and_mkv_eof_is_proven(tmp_path, tools):
    source = make_clip(tools, tmp_path / "prefix.mkv", kind="split", duration=1)
    prefix = probe_frame_timeline(source, tools, max_frames=3)
    assert len(prefix.frames) == 3 and not prefix.complete
    assert prefix.summary()["status"] == "PARTIAL_PREFIX"
    complete = probe_complete_timeline(source, tools, max_frames=30)
    assert complete.complete and len(complete.frames) == 25
    assert complete.coverage_evidence == "BOUNDED_EOF_AND_DECODE_COUNTERS"
    assert complete.first_time == 0 and complete.frames[-1].pts > 0


@pytest.mark.parametrize("fps", ["24000/1001", "24", "25", "30000/1001", "60000/1001"])
def test_actual_fractional_cfr_keeps_exact_anchors(tmp_path, tools, fps):
    source = make_clip(tools, tmp_path / "rate.mp4", kind="split", duration=1, fps=fps)
    scan = scan_scenes(source, tools)
    schedule = plan_x2(scan, explicit_opt_in=True)
    assert Fraction(schedule["planned_frame_rate"]) == 2 * Fraction(fps)
    for original, planned in zip(scan.timeline.frames, schedule["frames"][::2], strict=True):
        assert original.pts * scan.timeline.time_base == Fraction(planned["pts"])
    assert Fraction(schedule["planned_duration"]) == scan.timeline.duration


@pytest.mark.parametrize("threshold", [0, -1, 101, "nan", "inf", True])
def test_bad_threshold_is_refused_before_decode(tmp_path, tools, threshold):
    with pytest.raises(StudioError, match="Seuil"):
        scan_scenes(tmp_path / "absent.mp4", tools, threshold=threshold)


def test_unknown_final_duration_cannot_become_a_renderable_plan(tmp_path, tools):
    scan = scan_scenes(make_clip(tools, tmp_path / "one.mp4", kind="split", duration=1), tools)
    incomplete = replace(
        scan.timeline,
        frames=(*scan.timeline.frames[:-1], replace(scan.timeline.frames[-1], duration=None)),
    )
    with pytest.raises(StudioError, match="inconnues"):
        plan_x2(replace(scan, timeline=incomplete), explicit_opt_in=True)


def test_manual_exclusion_is_explicit_and_auditable(tmp_path, tools):
    source = make_clip(tools, tmp_path / "manual.mp4")
    scan = scan_scenes(source, tools, ignored_boundaries=(100,))
    assert not scan.boundaries
    assert scan.to_dict()["manual_exclusions"] == [100]
    with pytest.raises(StudioError, match="simultanément"):
        scan_scenes(source, tools, manual_boundaries=(100,), ignored_boundaries=(100,))


def test_actual_analysis_cancellation_after_40_percent_leaves_no_result(tmp_path, tools):
    from studio_ia.core import Cancellation, Cancelled

    cancel = Cancellation()
    source = make_clip(tools, tmp_path / "cancel.mp4")
    before = sha256(source)
    observed = []

    def observe(index, sample):
        observed.append(index)
        if index == 79:
            cancel.request()

    with pytest.raises(Cancelled):
        scan_scenes(source, tools, cancel=cancel, sample_observer=observe)
    assert len(observed) == 80
    assert sha256(source) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["cancel.mp4"]
