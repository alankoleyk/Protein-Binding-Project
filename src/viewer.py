"""A Qt widget that owns the entire 3Dmol.js communication boundary."""

import json
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from contracts import ResidueKey, Structure, ViewState

PAGE = Path(__file__).with_name("viewer_web") / "index.html"


class _Bridge(QObject):
    scene_changed = Signal(str)
    style_changed = Signal(str)
    camera_command = Signal(str)
    initialized = Signal()
    loaded = Signal()
    selected = Signal(object)
    failed = Signal(str)

    @Slot()
    def ready(self):
        self.initialized.emit()

    @Slot()
    def scene_loaded(self):
        self.loaded.emit()

    @Slot(str, int, str)
    def residue_picked(self, chain, number, insertion):
        self.selected.emit(ResidueKey(chain, number, insertion))

    @Slot(str)
    def load_failed(self, message):
        self.failed.emit(message)


class MoleculeView(QWebEngineView):
    residue_selected = Signal(object)
    ready = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.page().setBackgroundColor(QColor("#000000"))
        self._bridge = _Bridge(self)
        self._channel = QWebChannel(self.page())
        self._channel.registerObject("bridge", self._bridge)
        self.page().setWebChannel(self._channel)
        self._bridge.selected.connect(self.residue_selected)
        self._bridge.failed.connect(self.failed)
        self._bridge.initialized.connect(self._initialize)
        self._bridge.loaded.connect(self._scene_loaded)
        self._initialized = False
        self._scene_ready = False
        self._scene = None
        self._style = None
        self.load(QUrl.fromLocalFile(str(PAGE)))

    def load_structure(self, structure: Structure):
        self._scene_ready = False
        self._scene = json.dumps(
            {
                "code": structure.code,
                "pdb": structure.path.read_text(),
                "chains": [asdict(chain) for chain in structure.chains],
                "residues": [asdict(residue.key) for residue in structure.residues],
            }
        )
        if self._initialized:
            self._bridge.scene_changed.emit(self._scene)

    def show_state(self, state: ViewState):
        payload = json.dumps(
            {
                "selected": asdict(state.selected),
                "interface": [asdict(key) for key in state.interface],
                "highlight": state.highlight,
                "representation": state.representation,
            }
        )
        if payload != self._style:
            self._style = payload
            if self._scene_ready:
                self._bridge.style_changed.emit(payload)

    def command(self, command: str):
        self._bridge.camera_command.emit(command)

    def _initialize(self):
        self._initialized = True
        if self._scene is not None:
            self._bridge.scene_changed.emit(self._scene)

    def _scene_loaded(self):
        self._scene_ready = True
        if self._style is not None:
            self._bridge.style_changed.emit(self._style)
        self.ready.emit()
