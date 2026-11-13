"""French Qt desktop. All media work runs outside the GUI thread."""

import json
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRect, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from studio_ia import __version__, content_profiles
from studio_ia.core import Cancellation, StudioError, Tools, capabilities, sibling_probe, state_dir
from studio_ia.files import write_json
from studio_ia.jobs import TERMINAL, Manager
from studio_ia.media import MediaInfo, analyze, sha256
from studio_ia.pipeline import Request, build_plan
from studio_ia.preview import snapshot


class Bridge(QObject):
    result = Signal(str, int, object, str)


class Comparison(QWidget):
    """Before/after wipe with synchronised zoom and pan (LOT 04).

    Zoom and pan are expressed in normalised image coordinates, so both images show
    exactly the same region even when the result has a higher resolution.
    """

    def __init__(self):
        super().__init__()
        self.before = QPixmap()
        self.after = QPixmap()
        self.fraction = 0.5
        self.zoom = 1.0
        self.center = QPointF(0.5, 0.5)
        self._drag: QPointF | None = None
        self.setMinimumSize(450, 240)
        self.setAccessibleName("Comparaison avant après à l'instant sélectionné")

    def set_zoom(self, value: float, anchor: QPointF | None = None):
        self.zoom = max(1.0, min(8.0, value))
        if anchor is not None:
            self.center = anchor
        self._clamp()
        self.update()

    def _clamp(self):
        half = 0.5 / self.zoom
        self.center = QPointF(
            min(1 - half, max(half, self.center.x())), min(1 - half, max(half, self.center.y()))
        )

    def _source(self, pixmap: QPixmap) -> QRectF:
        w, h = pixmap.width() / self.zoom, pixmap.height() / self.zoom
        return QRectF(
            self.center.x() * pixmap.width() - w / 2,
            self.center.y() * pixmap.height() - h / 2,
            w,
            h,
        )

    def _target(self) -> QRect:
        aspect = self.before.width() / max(1, self.before.height())
        width = min(self.width(), round(self.height() * aspect))
        height = round(width / aspect)
        return QRect((self.width() - width) // 2, (self.height() - height) // 2, width, height)

    def wheelEvent(self, event):
        if self.before.isNull():
            return
        target = self._target()
        position = event.position()
        if target.contains(position.toPoint()):
            # Keep the point under the cursor where it is while zooming.
            source = self._source(self.before)
            anchor = QPointF(
                (source.x() + (position.x() - target.x()) / target.width() * source.width())
                / self.before.width(),
                (source.y() + (position.y() - target.y()) / target.height() * source.height())
                / self.before.height(),
            )
        else:
            anchor = None
        step = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.set_zoom(self.zoom * step, anchor)

    def mousePressEvent(self, event):
        self._drag = event.position()

    def mouseMoveEvent(self, event):
        if self._drag is None or self.zoom == 1.0 or self.before.isNull():
            return
        target = self._target()
        delta = event.position() - self._drag
        self._drag = event.position()
        self.center = QPointF(
            self.center.x() - delta.x() / target.width() / self.zoom,
            self.center.y() - delta.y() / target.height() / self.zoom,
        )
        self._clamp()
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag = None

    def info(self) -> str:
        parts = []
        if not self.before.isNull():
            parts.append(f"Avant {self.before.width()}×{self.before.height()}")
        if not self.after.isNull():
            parts.append(f"Après {self.after.width()}×{self.after.height()}")
        parts.append(f"zoom ×{self.zoom:.2f}".rstrip("0").rstrip("."))
        return " · ".join(parts)

    def composite(self) -> QImage:
        """Side-by-side export of the current region, both at the result's resolution."""
        if self.before.isNull():
            return QImage()
        reference = self.after if not self.after.isNull() else self.before
        region_b, region_a = self._source(self.before), self._source(reference)
        width, height = round(region_a.width()), round(region_a.height())
        image = QImage(width * 2 + 8, height + 28, QImage.Format.Format_RGB32)
        image.fill(QColor("#10161d"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(QRectF(0, 28, width, height), self.before, region_b)
        painter.drawPixmap(QRectF(width + 8, 28, width, height), reference, region_a)
        painter.setPen(QColor("#ffc477"))
        painter.drawText(6, 19, f"AVANT · {self.before.width()}×{self.before.height()}")
        painter.drawText(
            width + 14, 19, f"APRÈS · {reference.width()}×{reference.height()} · {self.info()}"
        )
        painter.end()
        return image

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#10161d"))
        if self.before.isNull():
            painter.setPen(QColor("#9faab5"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Importez une vidéo pour afficher son image réelle",
            )
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        target = self._target()
        painter.drawPixmap(QRectF(target), self.before, self._source(self.before))
        if not self.after.isNull():
            split = target.x() + round(target.width() * self.fraction)
            painter.save()
            painter.setClipRect(
                QRect(split, target.y(), target.right() - split + 1, target.height())
            )
            painter.drawPixmap(QRectF(target), self.after, self._source(self.after))
            painter.restore()
            painter.setPen(QColor("#ffc477"))
            painter.drawLine(split, target.y(), split, target.bottom())
        painter.setPen(QColor("#e8edf2"))
        painter.drawText(target.adjusted(8, 6, -8, -6), Qt.AlignmentFlag.AlignTop, self.info())


class Window(QMainWindow):
    def __init__(self, root: Path | None = None):
        super().__init__()
        configure_app(QApplication.instance())
        self.root = root or state_dir()
        self.manager = Manager(self.root)
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="studio-ui")
        self.bridge = Bridge()
        self.bridge.result.connect(self.receive)
        self.versions: dict[str, int] = {}
        self.futures = []
        self.source = None
        self.plan = None
        self.current_job = None
        self.last_result = None
        self.neural_configuration = None
        self.neural_cancel = Cancellation()
        self.last_neural_preview = None
        self.closing = False
        self.temporal_windows = []
        self.preview_temp = tempfile.TemporaryDirectory(prefix="preview-", dir=self.root)
        self.setWindowTitle(f"STUDIO IA · {__version__} · ALPHA")
        self.resize(1180, 850)
        self.setMinimumSize(920, 720)
        self.build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(200)
        self.refresh()
        self.background("doctor", lambda: capabilities(Tools.discover()))

    def background(self, name, function):
        version = self.versions.get(name, 0) + 1
        self.versions[name] = version
        future = self.pool.submit(function)
        self.futures = [pending for pending in self.futures if not pending.done()]
        self.futures.append(future)

        def complete(done):
            try:
                value, error = done.result(), ""
            except Exception as exc:
                value, error = None, str(exc)
            self.bridge.result.emit(name, version, value, error)

        future.add_done_callback(complete)

    def build_ui(self):
        base = QWidget()
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(base, "RESTORE · Restauration vidéo")
        self.extra_panels = []
        try:
            from studio_create.ui_panel import CreatePanel

            create = CreatePanel(self.root)
            self.extra_panels.append(create)
            self.tabs.addTab(create, "CREATE · Scènes et caméras")
        except Exception as exc:  # CREATE must never break RESTORE
            self.tabs.addTab(QLabel(f"CREATE indisponible : {exc}"), "CREATE · indisponible")
        from studio_ia.hardware_panel import HardwarePanel

        hardware = HardwarePanel(self.root)
        self.extra_panels.append(hardware)
        self.tabs.addTab(hardware, "Matériel et diagnostic")
        self.setCentralWidget(self.tabs)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(24, 20, 24, 18)
        header = QHBoxLayout()
        title = QLabel("STUDIO IA  /  RESTAURATION VIDÉO")
        title.setStyleSheet("font-size:22px; font-weight:700; color:#ffc477")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("ALPHA  •  LOCAL  •  CPU"))
        layout.addLayout(header)
        self.engine_label = QLabel("Vérification des moteurs locaux…")
        layout.addWidget(self.engine_label)
        actions = QHBoxLayout()
        self.import_button = QPushButton("Importer une vidéo…")
        self.import_button.clicked.connect(self.choose_source)
        actions.addWidget(self.import_button)
        diagnostic = QPushButton("Diagnostic")
        diagnostic.clicked.connect(
            lambda: self.background("doctor", lambda: capabilities(Tools.discover()))
        )
        actions.addWidget(diagnostic)
        configure = QPushButton("Chemins FFmpeg…")
        configure.clicked.connect(self.configure_tools)
        actions.addWidget(configure)
        export_diagnostic = QPushButton("Exporter un diagnostic…")
        export_diagnostic.clicked.connect(self.export_diagnostic)
        actions.addWidget(export_diagnostic)
        actions.addStretch()
        layout.addLayout(actions)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.metadata = QLabel("Aucune source. MP4, MKV et formats décodables localement.")
        self.metadata.setWordWrap(True)
        self.metadata.setTextFormat(Qt.TextFormat.PlainText)
        left_layout.addWidget(self.metadata)
        self.comparison = Comparison()
        left_layout.addWidget(self.comparison, 1)
        self.comparison_label = QLabel("Source  |  Résultat après validation")
        left_layout.addWidget(self.comparison_label)
        self.wipe = QSlider(Qt.Orientation.Horizontal)
        self.wipe.setRange(0, 100)
        self.wipe.setValue(50)
        self.wipe.setAccessibleName("Répartition avant après")
        self.wipe.valueChanged.connect(self.set_wipe)
        left_layout.addWidget(self.wipe)
        zoom_row = QHBoxLayout()
        for label, callback in (
            ("Zoom +", lambda: self.comparison.set_zoom(self.comparison.zoom * 1.5)),
            ("Zoom −", lambda: self.comparison.set_zoom(self.comparison.zoom / 1.5)),
            ("Vue entière", lambda: self.comparison.set_zoom(1.0, QPointF(0.5, 0.5))),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            zoom_row.addWidget(button)
        self.export_comparison_button = QPushButton("Exporter la comparaison…")
        self.export_comparison_button.clicked.connect(self.export_comparison)
        zoom_row.addWidget(self.export_comparison_button)
        left_layout.addLayout(zoom_row)
        preview_row = QHBoxLayout()
        self.timestamp = QDoubleSpinBox()
        self.timestamp.setRange(0, 86400)
        self.timestamp.setDecimals(3)
        self.timestamp.setSuffix(" s")
        preview_row.addWidget(QLabel("Instant commun"))
        preview_row.addWidget(self.timestamp)
        self.preview_button = QPushButton("Comparer les images")
        self.preview_button.clicked.connect(self.preview)
        preview_row.addWidget(self.preview_button)
        self.temporal_button = QPushButton("Inspection temporelle")
        self.temporal_button.clicked.connect(self.open_temporal_preview)
        left_layout.addLayout(preview_row)
        left_layout.addWidget(self.temporal_button)
        splitter.addWidget(left)
        settings = QGroupBox("Traitement proposé")
        form = QFormLayout(settings)
        form.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        settings.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.engine = QComboBox()
        self.engine.addItems(
            [
                "CPU classique · disponible",
                "Real-ESRGAN NCNN ×2 · non qualifié",
                "Anime4K · aucun shader qualifié",
                "RIFE · mission M005, non activé",
            ]
        )
        for index in (1, 2, 3):
            self.engine.model().item(index).setEnabled(False)
        form.addRow("Moteur", self.engine)
        self.model_label = QLabel("Aucun modèle neuronal sélectionné ou validé.")
        self.model_label.setWordWrap(True)
        form.addRow("Modèle local", self.model_label)
        content_row = QVBoxLayout()
        self.content_group = QButtonGroup(self)
        self.content_buttons = {}
        for profile_id, data in content_profiles.PROFILES.items():
            button = QRadioButton(data["label"])
            button.setAccessibleName(f"Type de contenu : {data['label']}")
            self.content_group.addButton(button)
            self.content_buttons[profile_id] = button
            content_row.addWidget(button)
        form.addRow("Contenu (IA)", content_row)
        self.content_summary = QLabel()
        self.content_summary.setWordWrap(True)
        self.content_summary.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        form.addRow(self.content_summary)
        self.content_resolution = QLabel()
        self.content_resolution.setWordWrap(True)
        self.content_resolution.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        self.content_resolution.setStyleSheet("color: #ffc477;")
        form.addRow(self.content_resolution)
        self.configure_neural_button = QPushButton("Choisir et diagnostiquer un modèle NCNN…")
        self.configure_neural_button.clicked.connect(self.configure_neural)
        form.addRow(self.configure_neural_button)
        self.neural_preview_button = QPushButton("Aperçu neuronal réel · 1 s")
        self.neural_preview_button.setEnabled(False)
        self.neural_preview_button.clicked.connect(self.neural_preview)
        form.addRow(self.neural_preview_button)
        self.cancel_neural_button = QPushButton("Annuler diagnostic / aperçu neuronal")
        self.cancel_neural_button.clicked.connect(lambda: self.neural_cancel.request())
        form.addRow(self.cancel_neural_button)
        self.compare_neural_cpu = QPushButton("Comparaison CPU / neuronal du dernier aperçu")
        self.compare_neural_cpu.setCheckable(True)
        self.compare_neural_cpu.setEnabled(False)
        self.compare_neural_cpu.clicked.connect(self.show_neural_comparison)
        form.addRow(self.compare_neural_cpu)
        self.profile = QComboBox()
        self.profile.addItems(
            ["AUTO · Préservation", "AVANCÉ · Personnalisé", "Témoin · Réencodage seul"]
        )
        form.addRow("Profil", self.profile)
        self.reason = QLabel("Préservation : débruitage léger, taille native, couleurs inchangées.")
        self.reason.setWordWrap(True)
        form.addRow(self.reason)
        self.denoise = QComboBox()
        self.denoise.addItems(["Désactivé", "Léger", "Modéré"])
        self.denoise.setCurrentIndex(1)
        form.addRow("Débruitage", self.denoise)
        self.deband = QComboBox()
        self.deband.addItems(["Désactivé", "Léger", "Modéré"])
        self.deband.setToolTip(
            "Atténue les bandes dans les dégradés compressés. "
            "Peut lisser les détails ; ce n’est pas un traitement neuronal."
        )
        form.addRow("Anti-banding CPU", self.deband)
        self.scale = QComboBox()
        self.scale.addItems(["× 0,5", "× 1 · Taille native", "× 2 · Lanczos", "× 4 · Lanczos"])
        self.scale.setCurrentIndex(1)
        form.addRow("Résolution classique", self.scale)
        self.brightness = self.spin(-0.1, 0.1, 0)
        self.contrast = self.spin(0.8, 1.2, 1)
        self.saturation = self.spin(0.8, 1.2, 1)
        form.addRow("Luminosité", self.brightness)
        form.addRow("Contraste", self.contrast)
        form.addRow("Saturation", self.saturation)
        self.crf = QSpinBox()
        self.crf.setRange(12, 28)
        self.crf.setValue(18)
        form.addRow("CRF H.264 (12–28)", self.crf)
        self.destination = QLineEdit()
        self.destination.setPlaceholderText("Destination .mp4 ou .mkv, nouveau fichier")
        form.addRow("Export", self.destination)
        self.destination_button = QPushButton("Choisir la destination…")
        self.destination_button.clicked.connect(self.choose_destination)
        form.addRow(self.destination_button)
        self.plan_button = QPushButton("1. Vérifier le plan")
        self.plan_button.clicked.connect(self.validate_plan)
        form.addRow(self.plan_button)
        self.start_button = QPushButton("2. Démarrer le traitement")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_job)
        form.addRow(self.start_button)
        limitation = QLabel(
            "CPU classique par défaut ; neuronal après qualification réelle.\n"
            "HDR/rotation/sous-titres : export refusé.\nL'original reste intact."
        )
        limitation.setWordWrap(True)
        form.addRow(limitation)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setMinimumWidth(350)
        self.settings_scroll.setWidget(settings)
        self.settings_scroll.setAccessibleName("Réglages du traitement, défilement vertical")
        splitter.addWidget(self.settings_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        self.status = QLabel("Prêt à importer une vidéo.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        row.addWidget(self.progress, 1)
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(
            lambda: self.manager.cancel(self.current_job) if self.current_job else None
        )
        row.addWidget(self.cancel_button)
        self.open_button = QPushButton("Ouvrir l'export")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_output)
        row.addWidget(self.open_button)
        layout.addLayout(row)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(85)
        layout.addWidget(self.details)
        history_row = QHBoxLayout()
        self.history = QListWidget()
        self.history.setMaximumHeight(95)
        self.history.setAccessibleName("Historique local des traitements")
        self.history.setToolTip("Double-clic ou Entrée : charger un résultat validé et le comparer")
        self.history.itemActivated.connect(self.load_history)
        history_row.addWidget(self.history, 1)
        history_actions = QVBoxLayout()
        for label, callback in (
            ("Relancer…", self.retry),
            ("Journal", self.open_log),
            ("Retirer de l'historique", self.remove_history),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            history_actions.addWidget(button)
        history_row.addLayout(history_actions)
        layout.addLayout(history_row)
        self.profile.currentIndexChanged.connect(self.apply_profile)
        self.engine.currentIndexChanged.connect(self.apply_engine)
        saved = content_profiles.load_settings(self.root)["content_profile"]
        self.content_buttons[saved].setChecked(True)
        self.content_group.buttonToggled.connect(self.apply_content_profile)
        self.show_content_profile()
        for control in (self.denoise, self.deband, self.scale):
            control.currentIndexChanged.connect(self.invalidate)
        for control in (self.brightness, self.contrast, self.saturation, self.crf):
            control.valueChanged.connect(self.invalidate)
        self.destination.textChanged.connect(self.invalidate)
        self.apply_profile()

    @staticmethod
    def spin(low, high, value):
        control = QDoubleSpinBox()
        control.setRange(low, high)
        control.setSingleStep(0.01)
        control.setValue(value)
        return control

    def export_comparison(self):
        image = self.comparison.composite()
        if image.isNull():
            self.status.setText("Aucune image à comparer : importer une vidéo et comparer d'abord.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la comparaison avant/après",
            str(Path.home() / "studio-ia-comparaison.png"),
            "PNG (*.png)",
        )
        if path:
            if image.save(path, "PNG"):
                self.status.setText(f"Comparaison exportée : {path} ({self.comparison.info()})")
            else:
                self.status.setText(f"Export impossible : {path}")

    def set_wipe(self, value):
        self.comparison.fraction = value / 100
        self.comparison.update()

    def invalidate(self, *_):
        self.plan = None
        self.versions["plan"] = self.versions.get("plan", 0) + 1
        self.start_button.setEnabled(False)
        self.neural_preview_button.setEnabled(False)
        self.compare_neural_cpu.setEnabled(False)
        self.last_neural_preview = None
        self.versions["neural_preview"] = self.versions.get("neural_preview", 0) + 1
        self.neural_cancel.request()

    def content_profile(self) -> str:
        for profile_id, button in self.content_buttons.items():
            if button.isChecked():
                return profile_id
        return content_profiles.DEFAULT_PROFILE

    def show_content_profile(self):
        profile = self.content_profile()
        self.content_summary.setText(content_profiles.PROFILES[profile]["summary"])
        missing = self.neural_configuration is None
        self.content_resolution.setText(content_profiles.resolution(profile) if missing else "")
        self.content_resolution.setVisible(missing)
        # Wrapped labels change height with their text: re-layout the scrolled form.
        self.content_summary.updateGeometry()
        self.content_resolution.updateGeometry()
        self.settings_scroll.widget().adjustSize()

    def apply_content_profile(self, button, checked):
        if not checked:
            return
        profile = self.content_profile()
        try:
            content_profiles.save_settings(self.root, content_profile=profile)
        except (OSError, StudioError) as exc:
            self.status.setText(f"Préférence non enregistrée : {exc}")
        config = self.neural_configuration
        if config is not None:
            try:
                content_profiles.check_model(profile, config["model"].manifest)
            except StudioError as exc:
                # Never keep a model that does not belong to the chosen profile.
                self.neural_configuration = None
                self.engine.setCurrentIndex(0)
                self.engine.model().item(1).setEnabled(False)
                self.model_label.setText("Modèle précédent incompatible avec ce type de contenu.")
                self.status.setText(str(exc))
        self.show_content_profile()
        self.invalidate()

    def apply_engine(self, *_):
        if self.engine.currentIndex() == 1:
            self.profile.setCurrentIndex(1)
            self.denoise.setCurrentIndex(0)
            self.deband.setCurrentIndex(0)
            self.scale.setCurrentIndex(2)
            self.brightness.setValue(0)
            self.contrast.setValue(1)
            self.saturation.setValue(1)
        self.invalidate()

    def configure_neural(self):
        manifest_path, _ = QFileDialog.getOpenFileName(
            self, "Manifeste local model-manifest-v2", filter="JSON (*.json)"
        )
        if not manifest_path:
            return
        binary_path, _ = QFileDialog.getOpenFileName(
            self, "Binaire officiel Real-ESRGAN NCNN local"
        )
        if not binary_path:
            return
        # Invalidate readiness immediately, including a previous successful configuration.
        self.engine.setCurrentIndex(0)
        self.engine.model().item(1).setEnabled(False)
        self.neural_configuration = None
        self.invalidate()
        self.neural_cancel.request()
        self.neural_cancel = Cancellation()
        cancel = self.neural_cancel
        directory = self.root / "neural-qualification" / str(uuid.uuid4())
        profile = self.content_profile()

        def check():
            from studio_ia.models import inspect, read_manifest
            from studio_ia.neural import probe, qualify

            manifest = Path(manifest_path)
            model = inspect(manifest.parent, read_manifest(manifest))
            content_profiles.check_model(profile, model.manifest)
            engine = probe(Path(binary_path))
            receipt = qualify(engine, model, Tools.discover(), directory, cancel)
            return {"model": model, "engine": engine, "receipt": receipt}

        self.background("neural_configuration", check)

    def neural_preview(self):
        from studio_ia.plans_v2 import PlanV2

        if not isinstance(self.plan, PlanV2):
            return
        frozen, seconds = self.plan, self.timestamp.value()
        self.neural_cancel.request()
        self.neural_cancel = Cancellation()
        cancel = self.neural_cancel
        directory = self.root / "neural-previews" / str(uuid.uuid4())
        from studio_ia.neural import preview_neural

        self.background(
            "neural_preview",
            lambda: preview_neural(
                frozen, Tools.discover(), directory, seconds=seconds, duration=1, cancel=cancel
            ),
        )

    def show_neural_comparison(self, *_):
        value = self.last_neural_preview
        if value is None:
            return
        reference = "cpu" if self.compare_neural_cpu.isChecked() else "source"
        self.comparison.before = QPixmap(value["frames"][reference])
        self.comparison.after = QPixmap(value["frames"]["neural"])
        self.comparison_label.setText(
            f"{reference.upper()} / NEURONAL · aperçu réel à "
            f"{value['actual_sample_source_seconds_rational']} s de la source"
        )
        self.comparison.update()

    def apply_profile(self, *_):
        custom = self.profile.currentIndex() == 1
        for control in (
            self.denoise,
            self.deband,
            self.scale,
            self.brightness,
            self.contrast,
            self.saturation,
            self.crf,
        ):
            control.setEnabled(custom)
        if not custom:
            self.denoise.setCurrentIndex(1 if self.profile.currentIndex() == 0 else 0)
            self.deband.setCurrentIndex(0)
            self.scale.setCurrentIndex(1)
            self.brightness.setValue(0)
            self.contrast.setValue(1)
            self.saturation.setValue(1)
            self.crf.setValue(18)
        self.reason.setText(
            "Réglages explicites ; vérifier le plan avant de démarrer."
            if custom
            else "Taille native, couleurs inchangées ; débruitage léger en Préservation."
        )
        self.invalidate()

    def choose_source(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importer une vidéo locale")
        if path:
            self.import_source(path)

    def import_source(self, path):
        self.invalidate()
        self.source = None
        self.last_result = None
        self.open_button.setEnabled(False)
        self.comparison.before = QPixmap()
        self.comparison.after = QPixmap()
        self.comparison.update()
        self.versions["preview"] = self.versions.get("preview", 0) + 1
        self.versions["history_result"] = self.versions.get("history_result", 0) + 1
        self.status.setText("Analyse réelle de la source…")
        self.background("source", lambda: analyze(Path(path), Tools.discover()))

    def choose_destination(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Nouvel export (aucun écrasement)",
            self.destination.text(),
            "MP4 (*.mp4);;Matroska (*.mkv)",
        )
        if path:
            self.destination.setText(path)

    def request(self):
        if self.source is None:
            raise StudioError("Importer une vidéo et attendre son analyse.")
        if self.engine.currentIndex() not in (0, 1) or (
            self.engine.currentIndex() == 1 and self.neural_configuration is None
        ):
            raise StudioError("Ce moteur n'est pas qualifié ; choisir CPU ou vérifier le modèle.")
        return Request(
            self.source.path,
            self.destination.text(),
            profile=("preservation", "custom", "control")[self.profile.currentIndex()],
            denoise=("off", "light", "moderate")[self.denoise.currentIndex()],
            deband=("off", "light", "moderate")[self.deband.currentIndex()],
            scale=(0.5, 1, 2, 4)[self.scale.currentIndex()],
            brightness=self.brightness.value(),
            contrast=self.contrast.value(),
            saturation=self.saturation.value(),
            crf=self.crf.value(),
        )

    def validate_plan(self):
        try:
            request = self.request()
            self.status.setText("Vérification des chemins, capacités et espace disque…")
            if self.engine.currentIndex() == 1:
                from studio_ia.neural import build_neural_plan

                config = self.neural_configuration
                if config is None:
                    raise StudioError("Modèle neuronal non qualifié.")
                profile = self.content_profile()
                content_profiles.check_model(profile, config["model"].manifest)
                # Tile from the detected GPU memory (estimate); 64 when unknown.
                machine = next(
                    (
                        p.data
                        for p in self.extra_panels
                        if getattr(p, "data", None) and "gpu" in p.data
                    ),
                    None,
                )
                tile = (machine or {}).get("recommendations", {}).get("ncnn_tile") or 64
                self.background(
                    "plan",
                    lambda: build_neural_plan(
                        request,
                        Tools.discover(),
                        config["model"],
                        Path(config["engine"]["path"]),
                        content_profile=profile,
                        tile=tile,
                    ),
                )
            else:
                self.background("plan", lambda: build_plan(request, Tools.discover()))
        except StudioError as exc:
            self.status.setText(str(exc))

    def start_job(self):
        if not self.plan:
            return
        try:
            from studio_ia.plans_v2 import PlanV2

            self.current_job = self.manager.submit(
                self.plan.request,
                neural_plan=(self.plan.to_dict() if isinstance(self.plan, PlanV2) else None),
            )
            self.last_result = None
            self.comparison.after = QPixmap()
            self.comparison.update()
            self.versions["preview"] = self.versions.get("preview", 0) + 1
            self.versions["history_result"] = self.versions.get("history_result", 0) + 1
            self.open_button.setEnabled(False)
            self.invalidate()
        except StudioError as exc:
            self.status.setText(str(exc))

    def open_temporal_preview(self):
        if not self.source:
            self.status.setText("Importer une vidéo avant l'inspection temporelle.")
            return
        from studio_ia.temporal_preview import TemporalPreview

        reference = (
            Path(self.last_result["plan"]["request"]["destination"]) if self.last_result else None
        )
        self.temporal_windows = [w for w in self.temporal_windows if not w.closing]
        window = TemporalPreview(Path(self.source.path), reference)
        self.temporal_windows.append(window)
        window.show()

    def preview(self):
        if not self.source:
            return
        source = Path(self.source.path)
        output = (
            Path(self.last_result["plan"]["request"]["destination"]) if self.last_result else None
        )
        seconds = self.timestamp.value()
        directory = Path(self.preview_temp.name)

        def extract():
            tools = Tools.discover()
            before = snapshot(source, seconds, directory / f"{uuid.uuid4()}.png", tools)
            after = (
                snapshot(output, seconds, directory / f"{uuid.uuid4()}.png", tools)
                if output
                else None
            )
            return (str(before), str(after) if after else None, seconds)

        self.background("preview", extract)

    def receive(self, name, version, value, error):
        if self.closing or self.versions.get(name) != version:
            return
        if error:
            self.status.setText(error)
            if name == "doctor":
                self.engine_label.setText("Moteurs indisponibles : configurer FFmpeg et ffprobe.")
            return
        if name == "source":
            self.source = value
            video = value.video
            self.metadata.setText(
                f"{Path(value.path).name}\n{video['width']} × {video['height']} · "
                f"{value.duration or '?'} s · {video.get('avg_frame_rate')} fps · "
                f"{video.get('codec_name')} · {len(value.audio)} piste(s) audio\n"
                + "\n".join(value.warnings)
            )
            source = Path(value.path)
            self.destination.setText(str(source.with_name(source.stem + "_restaure.mp4")))
            self.timestamp.setMaximum(max(0, (value.duration or 1) - 0.1))
            self.timestamp.setValue(0)
            self.status.setText("Source analysée. Vérifier le plan proposé avant de démarrer.")
            self.preview()
        elif name == "plan":
            self.plan = value
            from studio_ia.plans_v2 import PlanV2

            if isinstance(value, PlanV2):
                cpu = value.cpu_plan()
                estimate_mib = value.data["budgets"]["estimated_bytes"] / 1024**2
                self.details.setPlainText(
                    f"Real-ESRGAN ×2 · {cpu.width}×{cpu.height}, audio {cpu.audio_policy}\n"
                    f"Modèle : {value.data['model']['manifest']['id']}\n"
                    f"Frames : {len(value.data['timing']['frames'])}, PTS exacts\n"
                    f"Stockage estimé : {estimate_mib:.1f} Mio\n"
                    "VRAM non garantie ; détails plausibles et scintillement possibles."
                )
                self.start_button.setEnabled(True)
                self.neural_preview_button.setEnabled(True)
                self.status.setText("Plan neuronal expérimental prêt ; aperçu court conseillé.")
                return
            self.details.setPlainText(
                f"{value.width}×{value.height}, H.264, audio {value.audio_policy}\n"
                f"Filtres : {', '.join(value.filters) or 'aucun'}\n" + "\n".join(value.warnings)
            )
            self.status.setText("Plan vérifié. Le bouton Démarrer lance le traitement complet.")
            self.start_button.setEnabled(True)
        elif name == "preview":
            before, after, seconds = value
            self.comparison.before = QPixmap(before)
            self.comparison.after = QPixmap(after) if after else QPixmap()
            self.comparison_label.setText(
                f"SOURCE  ←  {seconds:.3f} s demandées  →  "
                + ("EXPORT VÉRIFIÉ" if after else "SOURCE SEULE")
            )
            self.comparison.update()
        elif name == "doctor":
            self.engine_label.setText(
                value["ffmpeg_version"].split(" Copyright")[0]
                + (" · CPU disponible" if value["cpu_ready"] else " · Capacités CPU incomplètes")
                + " · IA neuronale non qualifiée"
            )
            self.details.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
        elif name == "neural_configuration":
            receipt = value["receipt"]
            manifest = value["model"].manifest
            self.model_label.setText(
                f"{content_profiles.PROFILES[self.content_profile()]['label']} · "
                f"{manifest['id']} · {manifest['version']} · "
                f"{sum(f['bytes'] for f in manifest['files']) / 1024**2:.1f} Mio\n"
                f"{receipt['status']} : {receipt.get('reason', 'inférence courte réussie')}"
            )
            self.details.setPlainText(json.dumps(receipt, ensure_ascii=False, indent=2))
            ready = receipt["status"] == "PASS_SHORT_INFERENCE"
            self.engine.model().item(1).setEnabled(ready)
            if ready:
                self.neural_configuration = value
                self.engine.setItemText(1, "Real-ESRGAN NCNN ×2 · essai court PASS, expérimental")
            self.status.setText(
                "Inférence courte validée ; vidéo complète encore non qualifiée."
                if ready
                else "BLOCKED : GPU/modèle non qualifié. CPU conservé."
            )
            self.show_content_profile()
        elif name == "neural_preview":
            self.last_neural_preview = value
            self.compare_neural_cpu.setEnabled(True)
            self.compare_neural_cpu.setChecked(False)
            self.show_neural_comparison()
            self.details.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
            self.status.setText(
                "Aperçu et comparaison issus du segment courant ; voir le dossier local."
            )
        elif name == "history_result":
            self.invalidate()
            self.last_result = value
            self.source = MediaInfo(**value["plan"]["media"])
            self.metadata.setText(
                f"{Path(self.source.path).name} · résultat chargé depuis l'historique"
            )
            self.open_button.setEnabled(True)
            self.timestamp.setMaximum(max(0, (self.source.duration or 1) - 0.1))
            self.preview()
        elif name == "configured_tools":
            tools, report = value
            if not report["cpu_ready"]:
                self.status.setText(
                    "Capacités FFmpeg incomplètes ; configuration précédente conservée."
                )
                return
            try:
                write_json(
                    state_dir() / "config.json", {"ffmpeg": tools.ffmpeg, "ffprobe": tools.ffprobe}
                )
            except OSError as exc:
                self.status.setText(f"Enregistrement de la configuration impossible : {exc}")
                return
            self.invalidate()
            self.background("doctor", lambda: capabilities(Tools.discover()))

    def refresh(self):
        rows = self.manager.store.list()
        selected = self.selected_job()
        self.history.clear()
        for row in rows:
            self.history.addItem(
                f"{row.get('created_at', '')[:19]}  ·  {row['state']}  ·  "
                + Path(row.get("request", {}).get("source", "?")).name
            )
            item = self.history.item(self.history.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            if row["id"] == selected:
                self.history.setCurrentItem(item)
        busy = False
        if self.current_job:
            row = self.manager.store.get(self.current_job)
            busy = row["state"] not in TERMINAL
            self.cancel_button.setEnabled(busy)
            value = row.get("progress")
            if busy:
                self.progress.setRange(0, 0 if value is None else 100)
                if value is not None:
                    self.progress.setValue(round(value * 100))
                self.status.setText(
                    f"{row['state']} · {row.get('elapsed_seconds', 0):.1f} s écoulées"
                    + (" · vérification complète…" if row["state"] == "VERIFYING" else "")
                )
            else:
                self.progress.setRange(0, 100)
                self.progress.setValue(100 if row["state"] == "SUCCEEDED" else 0)
                self.status.setText(
                    "Export validé : décodage complet, audio, dimensions et source vérifiés."
                    if row["state"] == "SUCCEEDED"
                    else row.get("error") or row["state"]
                )
                if row["state"] == "SUCCEEDED":
                    self.last_result = row["result"]
                    self.source = MediaInfo(**row["result"]["plan"]["media"])
                    self.metadata.setText(
                        f"{Path(self.source.path).name} · "
                        f"{self.source.video['width']}×{self.source.video['height']} · "
                        f"{self.source.duration or '?'} s"
                    )
                    self.open_button.setEnabled(True)
                    if row["result"].get("warnings"):
                        self.status.setText("Export validé. " + " ".join(row["result"]["warnings"]))
                    self.preview()
                self.current_job = None
        for control in (
            self.import_button,
            self.plan_button,
            self.preview_button,
            self.destination_button,
            self.profile,
            self.destination,
            self.engine,
            self.configure_neural_button,
            *self.content_buttons.values(),
        ):
            control.setEnabled(not busy)
        for control in (
            self.denoise,
            self.deband,
            self.scale,
            self.brightness,
            self.contrast,
            self.saturation,
            self.crf,
        ):
            control.setEnabled(
                not busy
                and self.profile.currentIndex() == 1
                and (self.engine.currentIndex() == 0 or control is self.crf)
            )
        self.profile.setEnabled(not busy and self.engine.currentIndex() == 0)

    def selected_job(self):
        item = self.history.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def open_output(self):
        if self.last_result:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(self.last_result["plan"]["request"]["destination"])
            )

    def open_log(self):
        job_id = self.selected_job()
        if job_id:
            path = self.root / "jobs" / job_id / "pipeline.log"
            self.details.setPlainText(
                path.read_text(encoding="utf-8", errors="replace")
                if path.exists()
                else "Pas de journal pour cette tâche."
            )

    def retry(self):
        if any(row["state"] not in TERMINAL for row in self.manager.store.list()):
            self.status.setText("Attendre la tâche active avant de relancer depuis l'historique.")
            return
        job_id = self.selected_job()
        if not job_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Nouvelle destination pour relancer", "", "MP4 (*.mp4);;MKV (*.mkv)"
        )
        if path:
            try:
                self.current_job = self.manager.retry(job_id, path)
            except StudioError as exc:
                self.status.setText(str(exc))

    def remove_history(self):
        job_id = self.selected_job()
        if job_id:
            try:
                self.manager.store.remove(job_id)
                if job_id == self.current_job:
                    self.current_job = None
            except StudioError as exc:
                self.status.setText(str(exc))

    def load_history(self, *_):
        job_id = self.selected_job()
        if not job_id or self.current_job:
            return
        row = self.manager.store.get(job_id)
        if row["state"] != "SUCCEEDED":
            self.status.setText("Cette tâche n'a pas de résultat validé ; utiliser Relancer.")
            return
        result = row["result"]
        self.invalidate()
        self.versions["source"] = self.versions.get("source", 0) + 1
        self.versions["preview"] = self.versions.get("preview", 0) + 1

        def confirm_files():
            request = result["plan"]["request"]
            if (
                sha256(Path(request["source"])) != result["source_sha256"]
                or sha256(Path(request["destination"])) != result["output_sha256"]
            ):
                raise StudioError("Un média a changé depuis la validation ; comparaison refusée.")
            return result

        self.background("history_result", confirm_files)

    def export_diagnostic(self):
        from studio_ia.privacy import public_job_report

        job_id = self.selected_job()
        if not job_id:
            self.status.setText("Sélectionner une tâche à diagnostiquer dans l'historique.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Diagnostic sans chemins privés", "diagnostic.json", "JSON (*.json)"
        )
        if path:
            try:
                data = public_job_report(self.manager.store.get(job_id))
                Path(path).write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                self.status.setText(
                    "Diagnostic exporté ; relire les noms de fichiers avant partage."
                )
            except OSError as exc:
                self.status.setText(f"Export du diagnostic impossible : {exc}")

    def configure_tools(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir FFmpeg local (ffprobe sera détecté à côté)"
        )
        if not path:
            return
        probe = sibling_probe(path)
        if not probe:
            probe, _ = QFileDialog.getOpenFileName(self, "Choisir ffprobe local")
        if not probe:
            return
        tools = Tools(str(Path(path).resolve()), str(Path(probe).resolve()))
        self.background("configured_tools", lambda: (tools, capabilities(tools)))

    def closeEvent(self, event):
        for window in self.temporal_windows:
            window.close()
        self.neural_cancel.request()
        active = [row for row in self.manager.store.list() if row["state"] not in TERMINAL]
        if active:
            answer = QMessageBox.question(
                self, "Traitement actif", "Annuler les tâches et fermer ?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            for row in active:
                self.manager.cancel(row["id"])
            self.closing = True
            self.status.setText("Annulation en cours avant fermeture…")
            QTimer.singleShot(200, self.close_when_idle)
            event.ignore()
            return
        if any(not future.done() for future in self.futures):
            self.closing = True
            self.status.setText("Fermeture après l'analyse ou l'aperçu en cours…")
            QTimer.singleShot(200, self.close_when_idle)
            event.ignore()
            return
        self.closing = True
        self.timer.stop()
        self.manager.close()
        self.pool.shutdown(wait=True)
        for panel in self.extra_panels:
            panel.shutdown()
        self.preview_temp.cleanup()
        event.accept()

    def close_when_idle(self):
        if all(row["state"] in TERMINAL for row in self.manager.store.list()) and all(
            future.done() for future in self.futures
        ):
            self.close()
        else:
            QTimer.singleShot(200, self.close_when_idle)


def configure_app(app):
    app.setApplicationName("STUDIO IA")
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background:#17212b; color:#edf1f5; font-size:12px; }
        QPushButton { background:#2d3d4c; border:1px solid #526473;
                      padding:8px; border-radius:4px; }
        QPushButton:hover { background:#40566a; } QPushButton:disabled { color:#7a8690; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget {
            background:#101921; padding:5px; border:1px solid #526473; }
        QGroupBox { border:1px solid #526473; border-radius:6px;
                    margin-top:16px; padding-top:16px; }
        QGroupBox::title { color:#ffc477; subcontrol-origin:margin; left:12px; }
        QProgressBar { border:1px solid #526473; text-align:center; min-height:20px; }
        QProgressBar::chunk { background:#426b69; }
    """)


def main():
    app = QApplication.instance() or QApplication(sys.argv[:1])
    configure_app(app)
    try:
        window = Window()
    except (StudioError, OSError) as exc:
        QMessageBox.critical(None, "STUDIO IA", str(exc))
        sys.exit(1)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
