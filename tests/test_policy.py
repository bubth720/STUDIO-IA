import json
import socket

import pytest
from generate_fixtures import fixture

from studio_ia.core import StudioError, Tools, capture
from studio_ia.engines import inspect_model, neural_status
from studio_ia.media import analyze, sha256
from studio_ia.pipeline import Request, build_plan, run_plan


def test_missing_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_IA_FFPROBE", str(tmp_path / "missing-ffprobe"))
    with pytest.raises(StudioError, match="ffprobe absent"):
        Tools.discover()


def test_audio_only(tmp_path, tools):
    path = tmp_path / "sound.m4a"
    capture([tools.ffmpeg, "-v", "error", "-f", "lavfi", "-i", "sine=duration=1", str(path)])
    with pytest.raises(StudioError, match="Aucune piste vidéo"):
        analyze(path, tools)


def test_multiple_audio_kept(source, tmp_path, tools):
    source_multi = tmp_path / "F06_multi.mkv"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-i",
            str(source),
            "-map",
            "0:v",
            "-map",
            "0:a",
            "-map",
            "0:a",
            "-c",
            "copy",
            str(source_multi),
        ]
    )
    output = tmp_path / "multi.mp4"
    result = run_plan(
        build_plan(Request(str(source_multi), str(output)), tools), tools, tmp_path / "job"
    )
    assert len(analyze(output, tools).audio) == 2
    assert all(result["assertions"].values())


def test_subtitles_refused(source, tmp_path, tools):
    subtitle = tmp_path / "subtitle.srt"
    subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nSynthetic test\n")
    source_sub = tmp_path / "F06_sub.mkv"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-i",
            str(source),
            "-i",
            str(subtitle),
            "-map",
            "0",
            "-map",
            "1",
            "-c",
            "copy",
            str(source_sub),
        ]
    )
    with pytest.raises(StudioError, match="Sous-titres"):
        build_plan(Request(str(source_sub), str(tmp_path / "out.mp4")), tools)


def test_hdr_refused(tmp_path, tools):
    source = fixture(
        tools,
        tmp_path / "F08_hdr_metadata.mp4",
        duration=1,
        extra=["-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc"],
    )
    assert analyze(source, tools).hdr
    with pytest.raises(StudioError, match="HDR"):
        build_plan(Request(str(source), str(tmp_path / "out.mp4")), tools)


def test_vfr_timestamps(source, tmp_path, tools):
    vfr = tmp_path / "F07_vfr.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-i",
            str(source),
            "-vf",
            "select=if(lt(t\\,4)\\,not(mod(n\\,2))\\,1)",
            "-fps_mode",
            "vfr",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-c:a",
            "copy",
            str(vfr),
        ]
    )
    output = tmp_path / "vfr_out.mp4"
    result = run_plan(build_plan(Request(str(vfr), str(output)), tools), tools, tmp_path / "job")

    def timestamps(path):
        return json.loads(
            capture(
                [
                    tools.ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_frames",
                    "-show_entries",
                    "frame=best_effort_timestamp_time",
                    "-of",
                    "json",
                    str(path),
                ]
            )
        )["frames"]

    before, after = timestamps(vfr), timestamps(output)
    assert len(before) == len(after)
    assert all(
        abs(float(a["best_effort_timestamp_time"]) - float(b["best_effort_timestamp_time"])) < 0.001
        for a, b in zip(before, after, strict=True)
    )
    assert result["status"] == "PASS"


def test_audio_transcode_to_aac(source, tmp_path, tools):
    pcm = tmp_path / "pcm.mkv"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-i",
            str(source),
            "-c:v",
            "copy",
            "-c:a",
            "pcm_s16le",
            str(pcm),
        ]
    )
    output = tmp_path / "aac.mp4"
    plan = build_plan(Request(str(pcm), str(output)), tools)
    assert plan.audio_policy == "aac"
    result = run_plan(plan, tools, tmp_path / "job")
    assert all(result["assertions"].values())
    assert analyze(output, tools).audio[0]["codec_name"] == "aac"


def test_delayed_audio_offset_preserved(tmp_path, tools):
    source = tmp_path / "delayed.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=25:duration=3",
            "-itsoffset",
            "0.6",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=2:sample_rate=48000",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ]
    )
    result = run_plan(
        build_plan(Request(str(source), str(tmp_path / "out.mp4")), tools), tools, tmp_path / "job"
    )
    assert result["assertions"]["audio_0_sync"]


def test_no_network_python_and_real_cpu(source, tmp_path, tools, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden during CPU processing")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    result = run_plan(
        build_plan(Request(str(source), str(tmp_path / "offline.mp4")), tools),
        tools,
        tmp_path / "job",
    )
    assert result["status"] == "PASS"


def test_symlink_and_hardlink_sources(source, tmp_path, tools):
    import os

    linked = tmp_path / "linked.mp4"
    try:
        os.link(source, linked)
    except OSError:
        pytest.skip("Filesystem does not support test hard links")
    with pytest.raises(StudioError):
        build_plan(Request(str(source), str(linked)), tools)
    assert sha256(source) == sha256(linked)


def test_model_integrity(tmp_path):
    model = tmp_path / "model.bin"
    model.write_bytes(b"not a neural model; integrity test only")
    manifest = {
        "name": "integrity-test",
        "version": "1",
        "origin": "synthetic",
        "license": "test-only",
        "engine": "unqualified",
        "expected_sha256": sha256(model),
    }
    assert not inspect_model(model, manifest)["real_video_validated"]
    with pytest.raises(StudioError, match="Empreinte"):
        inspect_model(model, {**manifest, "expected_sha256": "0" * 64})


def test_neural_real_qualification():
    status = neural_status()
    if not status["real_video_validated"]:
        pytest.skip(status.get("reason", "No qualified model/GPU/video execution"))
    raise AssertionError("A real neural E2E must be implemented before claiming qualification")
