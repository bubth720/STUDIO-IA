"""Qt test driven by real widget clicks and real FFmpeg, also used by frozen builds."""

import json
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from studio_ia.core import Tools, capture
from studio_ia.jobs import TERMINAL
from studio_ia.media import sha256
from studio_ia.ui import Window


def run_smoke(root: Path) -> dict:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    tools = Tools.discover()
    source = root / "synthetic_gui_source.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=25:duration=8",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=8",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ]
    )
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = Window(root / "state")
    window.show()
    heartbeats = []
    timer = QTimer()
    timer.timeout.connect(lambda: heartbeats.append(time.monotonic()))
    timer.start(25)

    def wait_for(predicate, timeout=90):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise AssertionError(f"Qt timeout: {window.status.text()}")
            QTest.qWait(20)

    try:
        original = sha256(source)
        window.import_source(str(source))
        wait_for(lambda: window.source is not None)
        window.profile.setCurrentIndex(1)
        window.scale.setCurrentIndex(2)
        destination = root / "gui_verified_export.mp4"
        window.destination.setText(str(destination))
        QTest.mouseClick(window.plan_button, Qt.MouseButton.LeftButton)
        wait_for(lambda: window.plan is not None)
        QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
        job_id = window.current_job
        assert job_id
        ticks_before = len(heartbeats)
        wait_for(lambda: window.manager.store.get(job_id)["state"] in TERMINAL)
        row = window.manager.store.get(job_id)
        assert row["state"] == "SUCCEEDED", row
        assert all(row["result"]["assertions"].values())
        assert len(heartbeats) - ticks_before >= 3, "UI timer blocked during encode"
        wait_for(lambda: window.last_result is not None and not window.comparison.after.isNull())
        assert sha256(source) == original
        window.grab().save(str(root / "gui-success.png"))

        # A second job is really started, then stopped through the Cancel widget.
        window.scale.setCurrentIndex(3)
        cancelled_output = root / "must_not_exist.mp4"
        window.destination.setText(str(cancelled_output))
        QTest.mouseClick(window.plan_button, Qt.MouseButton.LeftButton)
        wait_for(lambda: window.plan is not None)
        QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
        cancel_id = window.current_job
        assert cancel_id
        wait_for(lambda: window.manager.store.get(cancel_id)["state"] == "RUNNING")
        wait_for(lambda: window.cancel_button.isEnabled())
        QTest.qWait(100)
        QTest.mouseClick(window.cancel_button, Qt.MouseButton.LeftButton)
        wait_for(lambda: window.manager.store.get(cancel_id)["state"] in TERMINAL)
        cancelled = window.manager.store.get(cancel_id)
        assert cancelled["state"] == "CANCELLED", cancelled
        assert not cancelled_output.exists()
        QTest.qWait(250)
        report = {
            "status": "PASS",
            "qt_platform": app.platformName(),
            "source_sha256": original,
            "output_sha256": sha256(destination),
            "success_job": job_id,
            "cancel_job": cancel_id,
            "assertions": row["result"]["assertions"],
            "widget_clicks": ["verify_plan", "start", "cancel"],
            "gui_timer_ticks": len(heartbeats),
            "cancel_state": cancelled["state"],
            "no_cancelled_output": not cancelled_output.exists(),
        }
        (root / "gui-smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    finally:
        timer.stop()
        window.manager.close()
        window.close()
        app.processEvents()
