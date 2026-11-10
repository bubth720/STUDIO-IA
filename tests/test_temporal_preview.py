"""Real ffmpeg seeks with QTest and a live GUI heartbeat; no fake preview worker."""

import json
import os
import time
from fractions import Fraction
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest

from studio_ia.core import StudioError, capture
from studio_ia.media import sha256
from studio_ia.temporal_preview import TemporalPreview, presented_index


def wait_for(qapp, condition, timeout=30):
    started = time.monotonic()
    while not condition():
        if time.monotonic() - started > timeout:
            raise AssertionError("Timed out waiting for an actual temporal preview")
        QTest.qWait(20)
        qapp.processEvents()


@pytest.mark.gui
@pytest.mark.integration
def test_actual_temporal_scrubbing_is_bounded_and_uses_observed_pts(tmp_path, tools, qapp):
    from test_scene_guard import make_clip

    source = make_clip(tools, tmp_path / "source.mp4")
    reference = tmp_path / "NON_NEURAL_REPEAT_REFERENCE.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-i",
            str(source),
            "-vf",
            "fps=50",
            "-c:v",
            "libx264",
            "-crf",
            "0",
            "-threads",
            "1",
            str(reference),
        ]
    )
    before = sha256(source)
    window = TemporalPreview(source, reference, tools)
    beats = []
    timer = QTimer()
    timer.timeout.connect(lambda: beats.append(time.monotonic()))
    timer.start(5)
    try:
        window.show()
        wait_for(qapp, lambda: window.rendered_index == 0)
        assert window.cuts == (100,)
        started = time.monotonic()
        for n in range(30):
            window.slider.setValue(n * 5 + 1)
            QTest.qWait(2)
        window.slider.setValue(150)
        wait_for(qapp, lambda: window.rendered_index == 150 and not window.active)
        assert window.rendered_pair["left"]["pts"] == window.rendered_pair["right"]["pts"] == "6"
        assert window.rendered_pair["right"]["frame_index"] == 300
        assert window.coalesced_requests > 0 and window.peak_active_tasks == 1
        assert len(window.cache) <= 6 and len(beats) > 10
        assert window.submitted_decodes < 15
        for index in range(7):
            window.slider.setValue(index)
            wait_for(qapp, lambda index=index: window.rendered_index == index and not window.active)
        window.slider.setValue(150)
        wait_for(qapp, lambda: window.rendered_index == 150 and not window.active)
        assert len(window.cache) == 6
        root = Path(os.environ.get("STUDIO_IA_TEMPORAL_GUI_EVIDENCE", tmp_path / "evidence"))
        root.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(root / "temporal-preview.png"))
        report = {
            "status": "PASS_REAL_CPU_QTEST",
            "requests": 31,
            "last_source_frame": 150,
            "last_reference_frame": 300,
            "observed_pts_seconds": "6",
            "elapsed_seconds": time.monotonic() - started,
            "qt_heartbeat_events": len(beats),
            "coalesced_requests": window.coalesced_requests,
            "submitted_decodes": window.submitted_decodes,
            "cache_entries": len(window.cache),
            "source_unchanged": sha256(source) == before,
            "rife_executed": False,
        }
        (root / "temporal-preview.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        assert report["source_unchanged"]
        with pytest.raises(StudioError, match="instant"):
            presented_index(window.loaded[0].timeline, Fraction(-1))
    finally:
        timer.stop()
        window.close()
        wait_for(qapp, lambda: not window.active)
        window.close()


@pytest.mark.gui
def test_close_during_real_probe_is_event_driven(tmp_path, tools, qapp):
    from test_scene_guard import make_clip

    source = make_clip(tools, tmp_path / "source.mp4", duration=2)
    window = TemporalPreview(source, tools=tools)
    window.show()
    window.close()
    wait_for(qapp, lambda: not window.active)
    assert window.closing and not window.isVisible()
