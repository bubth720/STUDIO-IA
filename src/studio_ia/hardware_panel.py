"""« Matériel et diagnostic » tab: what this PC can do, in plain French."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from studio_ia.files import write_json
from studio_ia.system_profile import human, profile

STATUS_TEXT = {
    "READY": "prêt",
    "FFMPEG_MISSING": "FFmpeg introuvable (onglet RESTORE → « Chemins FFmpeg… »)",
    "BLOCKED": "indisponible sur ce PC",
    "POSSIBLE_NOT_QUALIFIED": "possible, non qualifié (faire le premier test IA)",
    "NOT_TESTED_RECOMMENDED_HARDWARE": "matériel conforme, rendu non testé",
    "BELOW_RECOMMENDED_HARDWARE": "matériel sous la recommandation Epic",
}


class _Bridge(QObject):
    done = Signal(object, str)


def summary(data: dict) -> str:
    gpu = data["gpu"]["selected"]
    caps = data["capabilities"]
    lines = [
        f"Système : {data['os']}",
        f"Processeur : {data['cpu']['name']} · {data['cpu']['logical_cores']} cœurs logiques",
        f"Mémoire vive : {human(data['ram']['total_bytes'])} "
        f"(disponible {human(data['ram']['available_bytes'])})",
        f"Disque de travail : {human(data['disk']['free_bytes'])} libres",
        "Carte graphique retenue : "
        + (
            f"{gpu['name']} · {gpu.get('device_type_name', '?')} · "
            f"{human(gpu.get('device_local_bytes'))} de mémoire locale"
            if gpu
            else f"aucune ({data['gpu']['vulkan_reason']})"
        ),
        "",
        f"RESTORE classique (CPU) : {STATUS_TEXT.get(caps['restore_cpu'], caps['restore_cpu'])}",
        f"RESTORE IA (GPU Vulkan) : {STATUS_TEXT.get(caps['restore_ai'], caps['restore_ai'])}",
        "CREATE préparation de scène : prêt",
        "CREATE rendu Unreal : "
        + STATUS_TEXT.get(caps["create_unreal_render"], caps["create_unreal_render"]),
    ]
    tile = data["recommendations"]["ncnn_tile"]
    if tile:
        lines.append(
            f"Réglage IA proposé : tuiles de {tile} px (estimation, à confirmer par mesure)"
        )
    if data["limits"]:
        lines += ["", "Limites détectées :"] + [f"• {item}" for item in data["limits"]]
    return "\n".join(lines)


class HardwarePanel(QWidget):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        self.data: dict | None = None
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="studio-hw")
        self.bridge = _Bridge()
        self.bridge.done.connect(self.receive)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        title = QLabel("STUDIO IA  /  MATÉRIEL ET DIAGNOSTIC")
        title.setStyleSheet("font-size:22px; font-weight:700; color:#ffc477")
        layout.addWidget(title)
        self.status = QLabel("Analyse du PC en cours…")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.refresh_button = QPushButton("Analyser à nouveau")
        self.refresh_button.clicked.connect(self.refresh)
        self.export_button = QPushButton("Exporter le diagnostic matériel…")
        self.export_button.clicked.connect(self.export)
        self.export_button.setEnabled(False)
        self.logs_button = QPushButton("Ouvrir le dossier des journaux et projets")
        self.logs_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root)))
        )
        for button in (self.refresh_button, self.export_button, self.logs_button):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setAccessibleName("Résumé matériel et capacités de STUDIO IA")
        layout.addWidget(self.text, 1)
        self.refresh()

    def refresh(self):
        self.refresh_button.setEnabled(False)
        self.status.setText("Analyse du PC en cours (processeur, mémoire, disque, GPU Vulkan)…")
        future = self.pool.submit(profile, self.root)

        def complete(done):
            try:
                self.bridge.done.emit(done.result(), "")
            except Exception as exc:  # report, never crash the window
                self.bridge.done.emit(None, str(exc))

        future.add_done_callback(complete)

    def receive(self, data, error):
        self.refresh_button.setEnabled(True)
        if error:
            self.status.setText(f"Analyse impossible : {error}")
            return
        self.data = data
        self.export_button.setEnabled(True)
        self.status.setText("Analyse terminée. Aucune donnée n'est envoyée hors de ce PC.")
        self.text.setPlainText(
            summary(data)
            + "\n\nDétails techniques :\n"
            + json.dumps(data, ensure_ascii=False, indent=2)
        )

    def export(self):
        if not self.data:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le diagnostic matériel",
            str(Path(os.path.expanduser("~")) / "studio-ia-materiel.json"),
            "JSON (*.json)",
        )
        if path:
            write_json(Path(path), self.data)
            self.status.setText(f"Diagnostic exporté : {path}")

    def shutdown(self):
        self.pool.shutdown(wait=True)
