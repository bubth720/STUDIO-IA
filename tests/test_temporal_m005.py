"""M005 preparatory tests: no claim of RIFE qualification or M004 GPU closure."""

from fractions import Fraction

import pytest

from studio_ia.core import StudioError
from studio_ia.temporal import parse_frame_timeline, probe_frame_timeline


def payload(pts=(0, 40, 80), *, duration=40, count=None, base="1/1000"):
    return {
        "streams": [{"time_base": base, "nb_frames": str(len(pts)) if count is None else count}],
        "frames": [
            {"best_effort_timestamp": str(p), "duration": str(duration), "key_frame": int(i == 0)}
            for i, p in enumerate(pts)
        ],
    }


def test_exact_cfr_timing_and_duration():
    timeline = parse_frame_timeline(payload())
    assert timeline.complete
    assert timeline.duration == Fraction(3, 25)
    assert timeline.first_time == 0
    assert timeline.nonuniform_pts_deltas is False
    assert timeline.summary()["status"] == "PASS"


def test_nonzero_and_negative_origin_preserved():
    for pts in [(250, 290, 330), (-80, -40, 0)]:
        timeline = parse_frame_timeline(payload(pts))
        assert timeline.frames[0].pts == pts[0]
        assert timeline.duration == Fraction(3, 25)


def test_vfr_intervals_do_not_get_normalized():
    timeline = parse_frame_timeline(payload((0, 40, 100, 140)))
    assert [f.pts for f in timeline.frames] == [0, 40, 100, 140]
    assert [f.duration for f in timeline.frames] == [40, 60, 40, 40]
    assert timeline.nonuniform_pts_deltas
    assert timeline.differing_declared_durations == 1
    assert "does not prove VFR" in timeline.summary()["limitations"][0]


def test_unknown_last_duration_is_not_guessed():
    data = payload()
    del data["frames"][-1]["duration"]
    timeline = parse_frame_timeline(data)
    assert timeline.frames[-1].duration is None
    assert timeline.duration is None
    assert timeline.summary()["duration_from_first_frame_seconds"] is None


def test_partial_prefix_status_is_not_full_success():
    timeline = parse_frame_timeline(payload(count="120"))
    assert not timeline.complete
    assert timeline.summary()["status"] == "PARTIAL_PREFIX"


@pytest.mark.parametrize("pts", [(0, 0, 40), (80, 40, 120)])
def test_duplicate_and_nonmonotone_pts_rejected(pts):
    with pytest.raises(StudioError, match="monotones"):
        parse_frame_timeline(payload(pts))


def test_noninteger_pts_and_bad_timebase_are_rejected():
    data = payload()
    data["frames"][0]["best_effort_timestamp"] = "1.9"
    with pytest.raises(StudioError, match="entier"):
        parse_frame_timeline(data)
    with pytest.raises(StudioError, match="Timebase"):
        parse_frame_timeline(payload(base="0/0"))


def test_bad_frame_budgets_rejected():
    for value in (0, -1, 10001, True):
        with pytest.raises(StudioError, match="Budget"):
            parse_frame_timeline(payload(), max_frames=value)
    with pytest.raises(StudioError, match="limite"):
        parse_frame_timeline(payload(), max_frames=2)


def test_declared_frames_smaller_than_decoded_rejected():
    with pytest.raises(StudioError, match="incohérent"):
        parse_frame_timeline(payload(count="2"))


@pytest.mark.integration
def test_real_ffprobe_timeline_is_read_only(source, tools):
    from studio_ia.media import sha256

    before = sha256(source)
    timeline = probe_frame_timeline(source, tools, max_frames=300)
    assert len(timeline.frames) > 3
    assert timeline.time_base > 0
    assert timeline.frames[0].pts < timeline.frames[-1].pts
    assert sha256(source) == before
    assert timeline.summary()["mode"] == "READ_ONLY_PTS_INSPECTION_NOT_INTERPOLATION"
