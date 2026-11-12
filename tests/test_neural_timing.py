"""LOT 03 timing contracts T02/T03 with an explicitly NON-NEURAL FFmpeg test double.

Real FFmpeg encodes the sources, extracts frames, assembles video/audio and decodes the
result; the "engine" is a nearest-neighbour FFmpeg resize. These tests check exact PTS,
origin, container and audio mapping only. They never qualify Real-ESRGAN or a GPU.
"""

from fractions import Fraction
from pathlib import Path

import pytest
from test_models import model as model  # noqa: F401  (fixture)

from studio_ia import neural
from studio_ia.core import StudioError, capture
from studio_ia.media import analyze, sha256
from studio_ia.models import BACKEND, inspect, native_scale
from studio_ia.pipeline import Request
from studio_ia.plans_v2 import compare_timing, frame_table

BT709 = [
    "-colorspace",
    "bt709",
    "-color_primaries",
    "bt709",
    "-color_trc",
    "bt709",
    "-color_range",
    "tv",
]


@pytest.fixture
def fake_ncnn(request, tools, tmp_path, monkeypatch):
    root, manifest = request.getfixturevalue("model")
    binary = tmp_path / "NOT_A_NEURAL_BINARY"
    binary.write_bytes(b"Synthetic executable identity only; never executed")
    monkeypatch.setattr(
        neural,
        "probe",
        lambda path: {
            "backend": BACKEND,
            "path": str(path.resolve()),
            "sha256": sha256(path),
            "help": "TEST DOUBLE ONLY",
            "status": "DETECTED",
            "test_double": True,
        },
    )
    monkeypatch.setattr(
        neural,
        "qualify",
        lambda *a, **k: {
            "status": "PASS_SHORT_INFERENCE",
            "gpu_index": 0,
            "test_double": True,
            "scope": "NO_NEURAL_INFERENCE_NO_GPU_QUALIFICATION",
        },
    )
    monkeypatch.setattr(
        neural,
        "image_command",
        lambda engine, record, r, source, output, **k: [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-threads",
            "1",
            "-i",
            str(source),
            "-vf",
            f"scale=iw*{native_scale(record.manifest)}:ih*{native_scale(record.manifest)}"
            ":flags=neighbor",
            str(output),
        ],
    )
    return inspect(root, manifest), binary


def make_source(tools, path: Path, *, rate: str, video_offset: int | None, global_offset=None):
    """4 s video + two AAC tracks (fra, eng +0.2 s); video_offset delays video by N frames."""
    args = [tools.ffmpeg, "-v", "error"]
    args += [
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size=64x48:rate={rate}:duration=4",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=4:sample_rate=48000",
        "-itsoffset",
        "0.2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=3:sample_rate=48000",
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-map",
        "2:a",
        *(
            ["-vf", f"setpts=PTS+{video_offset}", "-fps_mode", "passthrough"]
            if video_offset
            else []
        ),
        *(["-avoid_negative_ts", "disabled"] if video_offset else []),
        "-c:v",
        "libx264",
        "-threads",
        "2",
        "-pix_fmt",
        "yuv420p",
        "-x264-params",
        "colorprim=bt709:transfer=bt709:colormatrix=bt709",
        "-c:a",
        "aac",
        "-metadata:s:a:0",
        "language=fra",
        "-metadata:s:a:1",
        "language=eng",
        *BT709,
    ]
    if global_offset:
        args += ["-output_ts_offset", global_offset]
    capture([*args, str(path)])
    return path


def run_case(fake_ncnn, tools, tmp_path, source: Path, destination: Path):
    record, binary = fake_ncnn
    before = sha256(source)
    plan = neural.build_neural_plan(
        Request(str(source), str(destination), scale=2, denoise="off"), tools, record, binary
    )
    result = neural.run_neural_plan(plan, tools, tmp_path / "job")
    assert result["qualification"]["test_double"] is True
    assert result["status"] == "PASS" and all(result["assertions"].values())
    assert sha256(source) == before
    assert not list(tmp_path.glob(".studio-ia-nn-*"))
    return plan, result


def test_t03_ntsc_rational_rate_with_nonzero_video_origin_is_exact(fake_ncnn, tools, tmp_path):
    source = make_source(
        tools, tmp_path / "T03 ntsc origine 0,5 s.mp4", rate="30000/1001", video_offset=15
    )
    table = frame_table(source, tools)
    assert table["origin_pts"] > 0
    assert Fraction(table["frame_rate"]) == Fraction(30000, 1001)
    destination = tmp_path / "T03 sortie.mp4"
    plan, result = run_case(fake_ncnn, tools, tmp_path, source, destination)
    after = frame_table(destination, tools)
    compare_timing(plan.data["timing"], after)
    origin = Fraction(after["origin_pts"]) * Fraction(after["time_base"])
    assert origin == Fraction(table["origin_pts"]) * Fraction(table["time_base"])
    assert len(result["ffprobe_after"]["streams"]) == 3


def test_t03_whole_file_offset_keeps_absolute_timestamps(fake_ncnn, tools, tmp_path):
    source = make_source(
        tools,
        tmp_path / "T03b decalage global.mp4",
        rate="25",
        video_offset=None,
        global_offset="1",
    )
    assert frame_table(source, tools)["origin_pts"] > 0
    destination = tmp_path / "T03b sortie.mp4"
    plan, _ = run_case(fake_ncnn, tools, tmp_path, source, destination)
    compare_timing(plan.data["timing"], frame_table(destination, tools))


def test_t02_mkv_two_audio_tracks_languages_and_offset(fake_ncnn, tools, tmp_path):
    source = make_source(tools, tmp_path / "T02 deux pistes.mkv", rate="25", video_offset=None)
    destination = tmp_path / "T02 sortie.mkv"
    plan, result = run_case(fake_ncnn, tools, tmp_path, source, destination)
    compare_timing(plan.data["timing"], frame_table(destination, tools))
    info = analyze(destination, tools)
    assert (info.video["width"], info.video["height"]) == (128, 96)
    languages = [a.get("tags", {}).get("language") for a in info.audio]
    assert languages == ["fra", "eng"]
    assert result["assertions"]["audio_1_sync"]


def test_mkv_cannot_hold_ntsc_exactly_and_is_refused_not_resampled(fake_ncnn, tools, tmp_path):
    record, binary = fake_ncnn
    source = make_source(tools, tmp_path / "ntsc.mkv", rate="30000/1001", video_offset=None)
    with pytest.raises(StudioError, match="VFR|contigus"):
        neural.build_neural_plan(
            Request(str(source), str(tmp_path / "out.mp4"), scale=2, denoise="off"),
            tools,
            record,
            binary,
        )
    assert not (tmp_path / "out.mp4").exists()


def test_other_destination_containers_are_refused(fake_ncnn, tools, tmp_path):
    record, binary = fake_ncnn
    source = make_source(tools, tmp_path / "src.mp4", rate="25", video_offset=None)
    with pytest.raises(StudioError, match="MP4 ou MKV|mp4|mkv"):
        neural.build_neural_plan(
            Request(str(source), str(tmp_path / "out.avi"), scale=2, denoise="off"),
            tools,
            record,
            binary,
        )
