"""Actual CPU temporal smoke for a frozen/extracted application (synthetic media only)."""

import json
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from studio_ia.core import StudioError, Tools, build_identity, capture
from studio_ia.files import write_json
from studio_ia.media import sha256
from studio_ia.temporal_preview import TemporalPreview
from studio_ia.ui import configure_app


def run_temporal_smoke(root: Path) -> dict:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    tools = Tools.discover()
    source = root / "synthetic-source.mp4"
    capture(
        [
            tools.ffmpeg,
            "-v",
            "error",
            "-n",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=64x48:rate=25:duration=2",
            "-vf",
            "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable=gte(n\\,25)",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-crf",
            "0",
            str(source),
        ]
    )
    before = sha256(source)
    app = QApplication.instance() or QApplication([])
    configure_app(app)
    window = TemporalPreview(source, tools=tools)
    beats = []
    timer = QTimer()
    timer.timeout.connect(lambda: beats.append(time.monotonic()))
    timer.start(5)

    def wait(condition):
        start = time.monotonic()
        while not condition():
            if time.monotonic() - start > 45:
                raise StudioError(f"Aperçu temporel non abouti : {window.status.text()}")
            QTest.qWait(10)
            app.processEvents()

    try:
        window.show()
        wait(lambda: window.rendered_index == 0)
        for index in range(30):
            window.slider.setValue((index * 7) % 49)
            QTest.qWait(2)
        window.slider.setValue(40)
        wait(lambda: window.rendered_index == 40 and not window.active)
        if window.rendered_pair["left"]["pts"] != "8/5" or len(beats) < 10:
            raise StudioError("PTS/activité Qt incorrect pendant le smoke réel.")
        if not window.grab().save(str(root / "temporal-preview.png")):
            raise StudioError("Capture temporelle impossible.")
        report = {
            "status": "PASS_REAL_CPU_TEMPORAL_SMOKE",
            "application": build_identity(),
            "source_sha256": before,
            "source_unchanged": sha256(source) == before,
            "rapid_requests": 31,
            "last_frame": 40,
            "observed_pts_seconds": "8/5",
            "qt_heartbeat_events": len(beats),
            "cache_entries": len(window.cache),
            "coalesced_requests": window.coalesced_requests,
            "neural_executed": False,
        }
        if not report["source_unchanged"] or len(window.cache) > 6:
            raise StudioError("Source modifiée ou cache hors budget.")
        write_json(root / "temporal-smoke.json", report, replace=False)
        return report
    finally:
        timer.stop()
        window.close()
        wait(lambda: not window.active)
        window.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_temporal_smoke(args.output), indent=2))
