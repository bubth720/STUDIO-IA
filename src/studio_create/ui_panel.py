"""« CREATE » tab: prepare a city scene and its cameras; Unreal is optional.

Without Unreal the tab is fully usable for scene preparation (2D plan, cameras,
sequence, create_scene.json, Unreal project kit). Launching Unreal is an explicit
click, enabled only when an installation is detected, and is labelled untested:
no Unreal render is ever claimed by this panel.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from studio_create import bridge, city, contracts

CAMERAS = [
    ("Avenue", "travelling", "Travelling au-dessus de l'avenue", True),
    ("Orbite", "orbit", "Orbite autour de la ville", True),
    ("Large", "wide", "Plan large fixe", False),
    ("Grue", "crane", "Mouvement de grue", False),
]
TIMES = {"dawn": "Aube", "day": "Jour", "dusk": "Crépuscule", "night": "Nuit"}
DENSITIES = {"low": "Faible", "medium": "Moyenne", "high": "Forte"}


class _Bridge(QObject):
    done = Signal(str, object, str)


class CityMap(QWidget):
    """Top view of the layout: roads, buildings (shade = height), lamps, camera paths."""

    def __init__(self):
        super().__init__()
        self.scene: dict | None = None
        self.setMinimumSize(420, 300)
        self.setAccessibleName("Plan de la ville vu de dessus avec trajectoires des caméras")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#10161d"))
        if not self.scene:
            painter.setPen(QColor("#9faab5"))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, "Générez une scène pour afficher le plan"
            )
            return
        layout = self.scene["layout"]
        city_bounds = layout["bounds"]
        # View = city + every camera keyframe, so orbit/wide shots stay visible.
        xs = [city_bounds["min"][0], city_bounds["max"][0]]
        ys = [city_bounds["min"][1], city_bounds["max"][1]]
        for camera in self.scene["cameras"]:
            for key in camera["keyframes"]:
                xs.append(key["location"][0])
                ys.append(key["location"][1])
        b = {"min": [min(xs), min(ys)], "max": [max(xs), max(ys)]}
        width, depth = b["max"][0] - b["min"][0], b["max"][1] - b["min"][1]
        margin = 16
        scale = min((self.width() - 2 * margin) / width, (self.height() - 2 * margin) / depth)
        ox = (self.width() - width * scale) / 2
        oy = (self.height() - depth * scale) / 2

        def point(x, y):
            # Unreal X forward -> screen right; Unreal Y right -> screen down.
            return QPointF(ox + (x - b["min"][0]) * scale, oy + (y - b["min"][1]) * scale)

        def rect(r):
            return QRectF(point(*r["min"]), point(*r["max"]))

        painter.fillRect(rect(city_bounds), QColor("#1d2a24"))
        for road in layout["roads"]:
            shade = "#4a4f57" if road["id"] == layout["avenue"] else "#363b42"
            painter.fillRect(rect(road["rect"]), QColor(shade))
        heights = [x["height_cm"] for x in layout["buildings"]] or [1]
        low, high = min(heights), max(heights)
        for building in layout["buildings"]:
            level = (building["height_cm"] - low) / ((high - low) or 1)
            painter.fillRect(
                rect(building["footprint"]), QColor.fromHsvF(0.08, 0.35, 0.45 + 0.5 * level)
            )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffd27a"))
        for lamp in layout["props"]["lamps"]:
            painter.drawEllipse(point(lamp["location"][0], lamp["location"][1]), 2, 2)
        palette = ["#4fc3f7", "#ff8a65", "#aed581", "#ba68c8"]
        for index, camera in enumerate(self.scene["cameras"]):
            colour = QColor(palette[index % len(palette)])
            painter.setPen(QPen(colour, 2))
            keys = [point(k["location"][0], k["location"][1]) for k in camera["keyframes"]]
            for start, end in zip(keys, keys[1:], strict=False):
                painter.drawLine(start, end)
            painter.setBrush(colour)
            painter.drawEllipse(keys[0], 5, 5)
            painter.drawText(keys[0] + QPointF(8, -6), camera["name"])
            painter.setBrush(Qt.BrushStyle.NoBrush)


class CreatePanel(QWidget):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root
        self.scene: dict | None = None
        self.project: Path | None = None
        self.doctor: dict | None = None
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="studio-create")
        self.bridge = _Bridge()
        self.bridge.done.connect(self.receive)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 18)
        title = QLabel("STUDIO IA  /  CREATE · CONSTRUCTION DE SCÈNES")
        title.setStyleSheet("font-size:22px; font-weight:700; color:#ffc477")
        outer.addWidget(title)
        self.unreal_label = QLabel("Recherche d'Unreal Engine…")
        self.unreal_label.setWordWrap(True)
        outer.addWidget(self.unreal_label)
        body = QHBoxLayout()
        outer.addLayout(body, 1)
        settings = QGroupBox("Ville procédurale (générateur city-v0)")
        form = QFormLayout(settings)
        self.seed = QSpinBox()
        self.seed.setRange(0, 2**31 - 1)
        self.seed.setValue(2048)
        form.addRow("Graine (seed)", self.seed)
        self.blocks_x = QSpinBox()
        self.blocks_x.setRange(1, 20)
        self.blocks_x.setValue(6)
        form.addRow("Îlots en longueur", self.blocks_x)
        self.blocks_y = QSpinBox()
        self.blocks_y.setRange(1, 20)
        self.blocks_y.setValue(1)
        form.addRow("Îlots en largeur", self.blocks_y)
        self.density = QComboBox()
        for key, label in DENSITIES.items():
            self.density.addItem(label, key)
        self.density.setCurrentIndex(1)
        form.addRow("Densité", self.density)
        self.time = QComboBox()
        for key, label in TIMES.items():
            self.time.addItem(label, key)
        self.time.setCurrentIndex(2)
        form.addRow("Heure", self.time)
        self.fps = QComboBox()
        self.fps.addItems(["24", "25", "30"])
        form.addRow("Images/s", self.fps)
        self.camera_boxes = {}
        for name, preset, label, checked in CAMERAS:
            box = QCheckBox(f"{label} (12 s)")
            box.setChecked(checked)
            self.camera_boxes[(name, preset)] = box
            form.addRow(box)
        self.generate_button = QPushButton("Générer la scène")
        self.generate_button.clicked.connect(self.generate)
        form.addRow(self.generate_button)
        self.save_button = QPushButton("Enregistrer create_scene.json…")
        self.save_button.clicked.connect(self.save_scene)
        form.addRow(self.save_button)
        self.project_button = QPushButton("Créer un projet Unreal (dossier neuf)…")
        self.project_button.clicked.connect(self.create_project)
        form.addRow(self.project_button)
        self.command_button = QPushButton("Préparer la construction dans le projet")
        self.command_button.clicked.connect(self.prepare_command)
        form.addRow(self.command_button)
        self.launch_button = QPushButton("Construire dans Unreal (expérimental, non testé)")
        self.launch_button.clicked.connect(self.launch_unreal)
        form.addRow(self.launch_button)
        self.detect_button = QPushButton("Détecter Unreal à nouveau")
        self.detect_button.clicked.connect(self.detect)
        form.addRow(self.detect_button)
        body.addWidget(settings)
        right = QVBoxLayout()
        self.map = CityMap()
        right.addWidget(self.map, 1)
        self.info = QLabel("Aucune scène générée.")
        self.info.setWordWrap(True)
        right.addWidget(self.info)
        body.addLayout(right, 1)
        self.update_buttons()
        self.detect()

    def run(self, name, function):
        future = self.pool.submit(function)

        def complete(done):
            try:
                self.bridge.done.emit(name, done.result(), "")
            except Exception as exc:  # report every failure in the panel
                self.bridge.done.emit(name, None, str(exc))

        future.add_done_callback(complete)

    def update_buttons(self):
        has_scene = self.scene is not None
        self.save_button.setEnabled(has_scene)
        self.command_button.setEnabled(has_scene and self.project is not None)
        ready = bool(self.doctor and self.doctor["status"] == "READY_FOR_MANUAL_TEST")
        self.launch_button.setEnabled(has_scene and self.project is not None and ready)

    def detect(self):
        self.unreal_label.setText("Recherche d'Unreal Engine…")
        self.run("doctor", bridge.doctor)

    def params(self) -> city.CityParams:
        return city.CityParams(
            seed=self.seed.value(),
            blocks_x=self.blocks_x.value(),
            blocks_y=self.blocks_y.value(),
            density=self.density.currentData(),
            time_of_day=self.time.currentData(),
        )

    def generate(self):
        shots = [key for key, box in self.camera_boxes.items() if box.isChecked()]
        if not shots:
            self.info.setText("Choisir au moins une caméra.")
            return
        params, fps = self.params(), self.fps.currentText()
        self.generate_button.setEnabled(False)
        self.run("scene", lambda: contracts.build_scene(params, shots, fps=fps))

    def save_scene(self):
        if not self.scene:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la scène",
            str(self.root / f"{self.scene['level_id']}.create_scene.json"),
            "JSON (*.json)",
        )
        if path:
            contracts.write_json(Path(path), self.scene)
            self.info.setText(self.info.text() + f"\nScène enregistrée : {path}")

    def create_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Dossier parent du projet Unreal")
        if not directory:
            return
        destination = Path(directory) / "STUDIO CREATE projet"
        self.run("project", lambda: bridge.create_project(destination))

    def prepare_command(self):
        if self.scene and self.project:
            scene, project = self.scene, self.project
            self.run("command", lambda: bridge.write_command(project, "build_city", scene))

    def launch_unreal(self):
        if not (self.scene and self.project and self.doctor):
            return
        install = next(
            i for i in self.doctor["installations"] if i["status"] == "COMPATIBLE_NOT_TESTED"
        )
        scene, project = self.scene, self.project

        def work():
            info = bridge.inspect_project(project)
            command = bridge.write_command(project, "build_city", scene)
            script = project / "Content" / "Python" / "studio_create_unreal" / "build_city.py"
            argv = bridge.script_argv(install, Path(info["uproject"]), str(script), command)
            log = project / "Saved" / "StudioCreate" / "build_city.log"
            return {"exit_code": bridge.launch(argv, log), "log": str(log)}

        self.launch_button.setEnabled(False)
        self.unreal_label.setText("Unreal travaille (fenêtre de commande en arrière-plan)…")
        self.run("launch", work)

    def receive(self, name, value, error):
        self.generate_button.setEnabled(True)
        if error:
            self.info.setText(f"Erreur ({name}) : {error}")
            self.update_buttons()
            return
        if name == "doctor":
            self.doctor = value
            installs = value["installations"]
            if value["status"] == "NOT_FOUND":
                text = (
                    "Unreal Engine non détecté : CREATE fonctionne en mode préparation de scène "
                    "(plan, caméras, séquence, projet). " + value["actions"][0]
                )
            elif value["status"] == "INCOMPATIBLE":
                problems = "; ".join(p for i in installs for p in i["problems"])
                text = f"Unreal détecté mais incompatible : {problems}"
            else:
                versions = ", ".join(
                    i["version"] for i in installs if i["status"] == "COMPATIBLE_NOT_TESTED"
                )
                text = (
                    f"Unreal Engine {versions} détecté (compatible, non testé). "
                    "Aucun rendu Unreal n'est encore vérifié."
                )
            self.unreal_label.setText(text)
        elif name == "scene":
            self.scene = value
            self.map.scene = value
            self.map.update()
            seq = value["sequence"]
            seconds = seq["total_frames"] / float(eval_fraction(seq["fps"]))
            self.info.setText(
                f"{value['level_id']} · {len(value['layout']['buildings'])} bâtiments · "
                f"{len(value['layout']['roads'])} rues · {len(value['cameras'])} caméra(s) · "
                f"{seq['total_frames']} images à {seq['fps']} i/s ({seconds:.0f} s)\n"
                f"Empreinte {value['layout']['layout_sha256'][:16]}… (même graine = même ville). "
                "Rendu Unreal : non effectué."
            )
        elif name == "project":
            self.project = Path(value["path"])
            self.info.setText(self.info.text() + f"\nProjet Unreal créé : {value['path']}")
        elif name == "command":
            self.info.setText(self.info.text() + f"\nCommande prête pour Unreal : {value}")
        elif name == "launch":
            self.unreal_label.setText(
                f"Unreal a terminé avec le code {value['exit_code']}. "
                f"Vérifier le journal : {value['log']} (résultat non vérifié automatiquement)."
            )
        self.update_buttons()

    def shutdown(self):
        self.pool.shutdown(wait=True)


def eval_fraction(text: str):
    from fractions import Fraction

    return Fraction(text)


def scene_json(scene: dict) -> str:
    return json.dumps(scene, ensure_ascii=False, indent=2)
