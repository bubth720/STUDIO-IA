"""Opt-in CPU temporal inspection. Reuses the existing Qt Comparison widget."""

import argparse
import bisect
import re
import sys
import tempfile
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from studio_ia.analysis_io import capture_local
from studio_ia.core import Cancellation, StudioError, Tools
from studio_ia.media import sha256
from studio_ia.scene_detect import scan_scenes
from studio_ia.temporal import FrameTimeline, probe_complete_timeline
from studio_ia.ui import Comparison, configure_app


@dataclass(frozen=True)
class PreviewSource:
    path: Path
    source_sha256: str
    fingerprint: tuple[int, int]
    timeline: FrameTimeline


def fingerprint(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def load_source(path: Path, tools: Tools, cancel: Cancellation) -> PreviewSource:
    path = path.expanduser().resolve(strict=True)
    identity = fingerprint(path)
    before = sha256(path, cancel)
    timeline = probe_complete_timeline(path, tools, cancel=cancel)
    if not timeline.complete or identity != fingerprint(path) or before != sha256(path, cancel):
        raise StudioError("Aperçu : source modifiée ou chronologie incomplète.")
    return PreviewSource(path, before, identity, timeline)


def presented_index(timeline: FrameTimeline, requested: Fraction) -> int:
    times = [f.pts * timeline.time_base for f in timeline.frames]
    index = bisect.bisect_right(times, requested) - 1
    end = timeline.first_time + timeline.duration if timeline.duration is not None else None
    if (
        index < 0
        or (end is not None and requested >= end)
        or (end is None and requested > times[-1])
    ):
        raise StudioError("Les deux médias ne couvrent pas cet instant PTS commun.")
    return index


def decode_frame(source: PreviewSource, index: int, tools: Tools, cancel: Cancellation) -> dict:
    cancel.check()
    if fingerprint(source.path) != source.fingerprint:
        raise StudioError("La source a changé depuis son chargement.")
    stamp = source.timeline.frames[index]
    tb = source.timeline.time_base
    with tempfile.TemporaryDirectory(prefix="studio-temporal-preview-") as temp:
        image = Path(temp) / "owned.png"
        graph = (
            f"settb=expr={tb.numerator}/{tb.denominator},select=eq(n\\,{index}),"
            "scdet=threshold=100,metadata=mode=print:file='pipe\\:1',"
            "scale=640:360:force_original_aspect_ratio=decrease"
        )
        metadata = capture_local(
            [
                tools.ffmpeg,
                "-v",
                "error",
                "-xerror",
                "-n",
                "-threads",
                "2",
                "-filter_threads",
                "1",
                "-protocol_whitelist",
                "file,pipe",
                "-copyts",
                "-i",
                str(source.path),
                "-map",
                "0:v:0",
                "-an",
                "-vf",
                graph,
                "-frames:v",
                "1",
                "-fps_mode",
                "passthrough",
                "-c:v",
                "png",
                "-threads",
                "1",
                str(image),
            ],
            cancel,
            timeout=30,
            max_bytes=1024**2,
        )
        matches = re.findall(r"frame:\s*\d+\s+pts:\s*(-?\d+)\s+pts_time:", metadata)
        if (
            matches != [str(stamp.pts)]
            or not image.is_file()
            or not 0 < image.stat().st_size <= 3 * 1024**2
        ):
            raise StudioError("Aperçu : image absente ou PTS extrait différent du PTS demandé.")
        data = image.read_bytes()
    if fingerprint(source.path) != source.fingerprint:
        raise StudioError("La source a changé pendant le décodage.")
    cancel.check()
    return {"frame_index": index, "pts": str(stamp.pts * tb), "png": data}


class PreviewBridge(QObject):
    result = Signal(str, int, object, str)


class TemporalPreview(QWidget):
    """One active task + one coalesced request; bounded cache; pixmaps on GUI thread."""

    def __init__(self, source: Path, reference: Path | None = None, tools: Tools | None = None):
        super().__init__()
        self.tools = tools or Tools.discover()
        self.source_path, self.reference_path = source, reference or source
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="studio-temporal")
        self.bridge = PreviewBridge()
        self.bridge.result.connect(self.receive)
        self.active = False
        self.closing = False
        self.epoch = 0
        self.pending: int | None = None
        self.cancel = Cancellation()
        self.cache: OrderedDict[int, dict] = OrderedDict()
        self.loaded = None
        self.rendered_index = None
        self.rendered_pair = None
        self.submitted_decodes = 0
        self.coalesced_requests = 0
        self.peak_active_tasks = 0
        self.setWindowTitle("STUDIO IA · inspection temporelle CPU · aucun RIFE activé")
        self.resize(840, 600)
        layout = QVBoxLayout(self)
        self.status = QLabel("Lecture bornée des PTS et des transitions…")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.comparison = Comparison()
        self.comparison.setFixedSize(640, 360)
        viewport = QScrollArea()
        viewport.setWidget(self.comparison)
        viewport.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(viewport)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.request)
        layout.addWidget(self.slider)
        row = QHBoxLayout()
        self.target = QSpinBox()
        self.target.setPrefix("Image à inspecter : ")
        self.target.setEnabled(False)
        jump = QPushButton("Aller à cette image")
        jump.clicked.connect(lambda: self.slider.setValue(self.target.value()))
        self.next_cut = QPushButton("Transition suivante")
        self.next_cut.clicked.connect(self.jump_next_cut)
        self.next_cut.setEnabled(False)
        zoom = QSpinBox()
        zoom.setRange(1, 4)
        zoom.setPrefix("Loupe ×")
        zoom.valueChanged.connect(
            lambda value: self.comparison.setFixedSize(640 * value, 360 * value)
        )
        for widget in (self.target, jump, self.next_cut, zoom):
            row.addWidget(widget)
        layout.addLayout(row)
        split = QSlider(Qt.Orientation.Horizontal)
        split.setRange(0, 100)
        split.setValue(50)
        split.setToolTip("Séparation source/référence")
        split.valueChanged.connect(self.set_split)
        layout.addWidget(split)
        self.cuts: tuple[int, ...] = ()
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(60)
        self.debounce.timeout.connect(self.start_pending)
        self.submit("load", self.load)

    def set_split(self, value):
        self.comparison.fraction = value / 100
        self.comparison.update()

    def load(self):
        left = load_source(self.source_path, self.tools, self.cancel)
        right = (
            left
            if self.reference_path.resolve() == left.path
            else load_source(self.reference_path, self.tools, self.cancel)
        )
        scan = scan_scenes(left.path, self.tools, cancel=self.cancel)
        if scan.source_sha256 != left.source_sha256:
            raise StudioError("La source a changé entre chronologie et analyse de scènes.")
        return left, right, tuple(b.frame_index for b in scan.boundaries)

    def submit(self, kind, function):
        self.active = True
        self.peak_active_tasks = max(self.peak_active_tasks, 1)
        epoch = self.epoch
        future = self.pool.submit(function)

        def done(task):
            try:
                value, error = task.result(), ""
            except Exception as exc:
                value, error = None, str(exc)
            self.bridge.result.emit(kind, epoch, value, error)

        future.add_done_callback(done)

    def request(self, index):
        if self.closing or self.loaded is None:
            return
        self.epoch += 1
        if self.pending is not None or self.active:
            self.coalesced_requests += 1
        self.pending = index
        self.target.setValue(index)
        if self.active:
            self.cancel.request()
        self.debounce.start()

    def start_pending(self):
        if self.active or self.pending is None or self.closing:
            return
        index, self.pending = self.pending, None
        try:
            changed = any(fingerprint(s.path) != s.fingerprint for s in self.loaded)
        except OSError:
            changed = True
        if changed:
            self.cache.clear()
            self.status.setText("Une source a changé : recharger l'inspection.")
            return
        if index in self.cache:
            self.cache.move_to_end(index)
            self.display(index, self.cache[index])
            return
        left, right = self.loaded
        requested = left.timeline.frames[index].pts * left.timeline.time_base
        self.cancel = Cancellation()
        token = self.cancel
        self.submitted_decodes += 1

        def work():
            first = decode_frame(left, index, self.tools, token)
            second = (
                first
                if left is right
                else decode_frame(
                    right, presented_index(right.timeline, requested), self.tools, token
                )
            )
            return {"index": index, "requested_pts": str(requested), "left": first, "right": second}

        self.submit("frame", work)

    def receive(self, kind, epoch, value, error):
        self.active = False
        if self.closing:
            self.close()
            return
        if kind == "load":
            if error:
                self.status.setText(error)
                return
            left, right, self.cuts = value
            self.loaded = left, right
            count = len(left.timeline.frames)
            self.slider.setRange(0, count - 1)
            self.target.setRange(0, count - 1)
            self.slider.setEnabled(True)
            self.target.setEnabled(True)
            self.next_cut.setEnabled(bool(self.cuts))
            self.request(0)
            return
        if epoch == self.epoch:
            if error:
                self.status.setText(error)
            else:
                self.cache[value["index"]] = value
                while len(self.cache) > 6:
                    self.cache.popitem(last=False)
                self.display(value["index"], value)
        if self.pending is not None:
            self.debounce.start()

    def display(self, index, pair):
        before, after = QPixmap(), QPixmap()
        if not before.loadFromData(pair["left"]["png"]) or not after.loadFromData(
            pair["right"]["png"]
        ):
            self.status.setText("Image décodée illisible par Qt.")
            return
        self.comparison.before, self.comparison.after = before, after
        self.comparison.update()
        self.rendered_index, self.rendered_pair = index, pair
        self.status.setText(
            f"PTS demandé {pair['requested_pts']} s · source {pair['left']['pts']} s · "
            f"référence {pair['right']['pts']} s · CPU, aucune inférence"
        )

    def jump_next_cut(self):
        next_index = next(
            (i for i in self.cuts if i > self.slider.value()), self.cuts[0] if self.cuts else 0
        )
        self.slider.setValue(next_index)

    def closeEvent(self, event):
        self.closing = True
        self.debounce.stop()
        self.pending = None
        self.cancel.request()
        if self.active:
            event.ignore()
            return
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.cache.clear()
        self.comparison.before = QPixmap()
        self.comparison.after = QPixmap()
        event.accept()


def main(source: Path | None = None, reference: Path | None = None):
    if source is None:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("source", type=Path)
        parser.add_argument("--reference", type=Path)
        args = parser.parse_args()
        source, reference = args.source, args.reference
    app = QApplication.instance() or QApplication(sys.argv)
    configure_app(app)
    window = TemporalPreview(source, reference)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
