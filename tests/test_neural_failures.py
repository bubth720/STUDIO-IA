"""Transport/fault contracts with an explicitly NON-NEURAL FFmpeg test double.

These tests cannot qualify Real-ESRGAN or a GPU. Public NN reports never invoke them
as inference evidence. Real FFmpeg still extracts, assembles, maps audio and decodes.
"""

import threading
import time
from pathlib import Path

import pytest
from test_models import model as model

from studio_ia import neural
from studio_ia.core import Cancellation, Cancelled, StudioError, capture
from studio_ia.media import sha256
from studio_ia.models import BACKEND, inspect
from studio_ia.pipeline import Request
from studio_ia.plans_v2 import compare_timing, frame_table


@pytest.fixture
def neural_transport(request, tmp_path, tools, monkeypatch):
    root, manifest = request.getfixturevalue("model")
    source = tmp_path / "NN01 synthetic audio 日本語.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x48:rate=8:duration=8",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=8:sample_rate=48000",
            "-itsoffset",
            "0.25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=7:sample_rate=48000",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "2:a",
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
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-color_range",
            "tv",
            str(source),
        ]
    )
    binary = tmp_path / "NOT_A_NEURAL_BINARY"
    binary.write_bytes(b"Synthetic executable identity only; never executed")

    def fake_probe(path):
        return {
            "backend": BACKEND,
            "path": str(path.resolve()),
            "sha256": sha256(path),
            "help": "TEST DOUBLE ONLY",
            "status": "DETECTED",
            "test_double": True,
        }

    monkeypatch.setattr(neural, "probe", fake_probe)
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
        lambda engine, record, root, source, output, **k: [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-threads",
            "1",
            "-filter_threads",
            "1",
            "-i",
            str(source),
            "-vf",
            "scale=iw*2:ih*2:flags=neighbor",
            "-threads",
            "1",
            str(output),
        ],
    )
    record = inspect(root, manifest)
    request = Request(str(source), str(tmp_path / "transport-output.mp4"), scale=2, denoise="off")
    plan = neural.build_neural_plan(request, tools, record, binary)
    return plan, source, root, manifest, binary


def test_transport_double_8_seconds_two_audio_exact_pts_offline(
    neural_transport, tools, tmp_path, monkeypatch
):
    import socket

    plan, source, *_ = neural_transport
    before = sha256(source)
    monkeypatch.setattr(
        socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Network forbidden"))
    )
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    result = neural.run_neural_plan(plan, tools, tmp_path / "job")
    assert result["qualification"]["test_double"] is True
    assert result["status"] == "PASS" and all(result["assertions"].values())
    assert result["assertions"]["audio_count"] and len(result["ffprobe_after"]["streams"]) == 3
    assert result["assertions"]["audio_1_sync"]
    assert sha256(source) == before
    compare_timing(frame_table(source, tools), frame_table(Path(plan.request.destination), tools))
    assert not list(tmp_path.glob(".studio-ia-nn-*"))


def test_registered_model_swap_is_refused_before_export(neural_transport, tools, tmp_path):
    plan, source, root, manifest, _ = neural_transport
    before = sha256(source)
    (root / manifest["files"][1]["path"]).write_bytes(b"swapped")
    with pytest.raises(StudioError, match="modifié"):
        neural.run_neural_plan(plan, tools, tmp_path / "job")
    assert sha256(source) == before and not Path(plan.request.destination).exists()


def test_binary_swap_or_loss_does_not_requalify_silently(neural_transport, tools, tmp_path):
    plan, _, _, _, binary = neural_transport
    binary.write_bytes(b"replaced")
    with pytest.raises(StudioError, match="modifié"):
        neural.run_neural_plan(plan, tools, tmp_path / "job")
    binary.unlink()
    with pytest.raises((OSError, StudioError)):
        neural.run_neural_plan(plan, tools, tmp_path / "another-job")
    assert not Path(plan.request.destination).exists()


def test_second_neural_task_and_stale_lock_are_refused(tmp_path):
    with neural.intensive_job(), pytest.raises(StudioError, match="déjà active"):
        with neural.intensive_job():
            pass
    lock = neural.state_dir() / "neural-active.lock"
    lock.write_text("old-process-not-auto-recovered")
    with pytest.raises(StudioError, match="arrêt précédent"):
        with neural.intensive_job():
            pass
    assert lock.read_text() == "old-process-not-auto-recovered"


def test_cancellation_stops_real_child_without_final_output(
    neural_transport, tools, tmp_path, monkeypatch
):
    import sys

    plan, source, *_ = neural_transport
    before = sha256(source)
    cancel = Cancellation()
    entered = threading.Event()

    def sleep_command(*a, **k):
        entered.set()
        return [sys.executable, "-c", "import time; time.sleep(60)"]

    monkeypatch.setattr(neural, "image_command", sleep_command)

    def stop():
        assert entered.wait(10)
        time.sleep(0.1)
        cancel.request()

    thread = threading.Thread(target=stop)
    thread.start()
    try:
        with pytest.raises(Cancelled):
            neural.run_neural_plan(plan, tools, tmp_path / "cancel-job", cancel)
    finally:
        thread.join(timeout=12)
    assert not Path(plan.request.destination).exists() and sha256(source) == before
    assert not list(tmp_path.glob(".studio-ia-nn-*"))


def test_injected_oom_exit_is_not_a_real_gpu_oom_or_success(
    neural_transport, tools, tmp_path, monkeypatch
):
    import sys

    plan, source, *_ = neural_transport
    before = sha256(source)
    monkeypatch.setattr(
        neural, "image_command", lambda *a, **k: [sys.executable, "-c", "raise SystemExit(137)"]
    )
    with pytest.raises(StudioError):
        neural.run_neural_plan(plan, tools, tmp_path / "oom-job")
    assert not Path(plan.request.destination).exists() and sha256(source) == before
    assert not (tmp_path / "oom-job/result.json").exists()


def test_disk_shortage_refused_before_processing(neural_transport, tools, tmp_path, monkeypatch):
    from collections import namedtuple

    plan, *_ = neural_transport
    usage = namedtuple("Usage", "total used free")
    monkeypatch.setattr(neural.shutil, "disk_usage", lambda p: usage(100, 99, 1))
    with pytest.raises(StudioError, match="disque|espace"):
        neural.run_neural_plan(plan, tools, tmp_path / "full-job")
    assert not Path(plan.request.destination).exists()


def test_destination_race_does_not_overwrite(neural_transport, tools, tmp_path, monkeypatch):
    plan, *_ = neural_transport
    destination = Path(plan.request.destination)
    original = neural.publish_no_replace

    def race(source, target):
        target.write_bytes(b"COMPETING FILE")
        return original(source, target)

    monkeypatch.setattr(neural, "publish_no_replace", race)
    with pytest.raises(OSError):
        neural.run_neural_plan(plan, tools, tmp_path / "race-job")
    assert destination.read_bytes() == b"COMPETING FILE"
    assert not (tmp_path / "race-job/result.json").exists()


def test_gpu_absence_never_exports_or_invents_preview(
    neural_transport, tools, tmp_path, monkeypatch
):
    plan, *_ = neural_transport
    monkeypatch.setattr(
        neural, "qualify", lambda *a, **k: {"status": "BLOCKED", "reason": "NO_PHYSICAL_VULKAN_GPU"}
    )
    with pytest.raises(StudioError, match="BLOCKED"):
        neural.run_neural_plan(plan, tools, tmp_path / "blocked-job")
    with pytest.raises(StudioError, match="BLOCKED"):
        neural.preview_neural(plan, tools, tmp_path / "blocked-preview")
    assert not Path(plan.request.destination).exists()
    assert not list((tmp_path / "blocked-preview").glob("*.png"))
