"""Exact source timing, real multi-track remux and explicitly unknown codec delay."""

from dataclasses import replace
from fractions import Fraction

import pytest
from generate_temporal_fixtures import audio_fixture

from studio_ia.core import StudioError, capture
from studio_ia.interpolate import plan_x2
from studio_ia.media import sha256
from studio_ia.scene_detect import scan_scenes
from studio_ia.temporal import probe_complete_timeline
from studio_ia.temporal_audio import audit_audio, compare_audio


@pytest.mark.parametrize("vfr", [False, True])
def test_real_multitrack_copy_preserves_offsets_languages_and_packets(tmp_path, tools, vfr):
    source = audio_fixture(tools, tmp_path / "source.mkv", vfr=vfr)
    before_hash = sha256(source)
    before = audit_audio(source, tools)
    assert before["audio_track_count"] == 2
    assert [r["language"] for r in before["tracks"]] == ["fra", "eng"]
    assert [r["codec"] for r in before["tracks"]] == ["aac", "pcm_s16le"]
    assert [r["sample_rate"] for r in before["tracks"]] == ["48000", "44100"]
    assert Fraction(before["tracks"][1]["initial_offset_from_video"]) == Fraction(1, 5)
    # AAC encoder priming is reported rather than rounded to the requested 200ms.
    assert (
        Fraction(17, 100)
        < Fraction(before["tracks"][0]["initial_offset_from_video"])
        <= Fraction(1, 5)
    )
    output = tmp_path / "copy.mkv"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-copyts",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a",
            "-c",
            "copy",
            "-avoid_negative_ts",
            "disabled",
            str(output),
        ]
    )
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-i",
            str(output),
            "-map",
            "0:v:0",
            "-map",
            "0:a",
            "-f",
            "null",
            "-",
        ]
    )
    after = audit_audio(output, tools)
    comparison = compare_audio(before, after)
    # Equal track counts/endpoints must not hide a layout, priming or internal cadence change.
    import copy

    for field, changed in [
        ("channel_layout", "5.1"),
        ("codec_delay_metadata", [{"skip_samples": 1024}]),
        ("relative_packet_timing_sha256", "0" * 64),
    ]:
        invalid = copy.deepcopy(after)
        invalid["tracks"][0][field] = changed
        with pytest.raises(StudioError, match="Piste audio modifiée"):
            compare_audio(before, invalid)
    assert all(Fraction(r["initial_offset_drift_seconds"]) == 0 for r in comparison["tracks"])
    assert sha256(source) == before_hash
    if vfr:
        timeline = probe_complete_timeline(source, tools)
        assert timeline.nonuniform_pts_deltas
        scan = scan_scenes(source, tools)
        # A complete VFR timeline remains observable but cannot silently become CFR.
        with pytest.raises(StudioError, match="VFR"):
            plan_x2(scan, explicit_opt_in=True)
        assert all(
            a.pts < b.pts for a, b in zip(timeline.frames, timeline.frames[1:], strict=False)
        )
    with pytest.raises(StudioError, match="Piste perdue"):
        compare_audio(before, {**after, "tracks": after["tracks"][:1]})
    with pytest.raises(StudioError, match="budget"):
        audit_audio(source, tools, max_packets=1)


def test_actual_nonzero_origin_is_not_rebased(tmp_path, tools):
    from test_scene_guard import make_clip

    source = make_clip(tools, tmp_path / "zero.mp4", kind="split", duration=1)
    offset = tmp_path / "offset.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-i",
            str(source),
            "-c",
            "copy",
            "-output_ts_offset",
            "2",
            str(offset),
        ]
    )
    scan = scan_scenes(offset, tools)
    assert scan.timeline.first_time == 2
    schedule = plan_x2(scan, explicit_opt_in=True)
    assert schedule["frames"][0]["pts"] == "2"
    assert schedule["planned_duration"] == "1"
    assert replace(scan.timeline, complete=False).summary()["status"] == "PARTIAL_PREFIX"
