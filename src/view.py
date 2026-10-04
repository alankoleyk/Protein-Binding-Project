"""Single-page Qt view. All application decisions belong to the presenter."""

from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from contracts import ViewState

AMINO_ACIDS = {
    "A": "Alanine",
    "R": "Arginine",
    "N": "Asparagine",
    "D": "Aspartate",
    "C": "Cysteine",
    "Q": "Glutamine",
    "E": "Glutamate",
    "G": "Glycine",
    "H": "Histidine",
    "I": "Isoleucine",
    "L": "Leucine",
    "K": "Lysine",
    "M": "Methionine",
    "F": "Phenylalanine",
    "P": "Proline",
    "S": "Serine",
    "T": "Threonine",
    "W": "Tryptophan",
    "Y": "Tyrosine",
    "V": "Valine",
}


def label(text="", name="", wrap=False):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def row(*widgets):
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def card(name="card"):
    widget = QFrame()
    widget.setObjectName(name)
    widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(7)
    return widget, layout


def section_header(title, *details):
    widget = QWidget()
    widget.setObjectName("sectionHeader")
    widget.setFixedHeight(26)
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(title)
    layout.addStretch()
    for detail in details:
        layout.addWidget(detail, 0, Qt.AlignmentFlag.AlignVCenter)
    return widget


def badge(width, text="", name="badge"):
    widget = label(text, name)
    widget.setFixedSize(width, 20)
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return widget


class SequenceGrid(QWidget):
    selected = Signal(object)
    height_changed = Signal(int)
    CELL_WIDTH = 26
    CELL_HEIGHT = 30
    GAP = 3

    def __init__(self):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(self.GAP)
        self.grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.buttons = {}
        self._keys = ()
        self._columns = 0

    def show_residues(self, residues, interface, selected):
        keys = tuple(residue.key for residue in residues)
        if keys != self._keys:
            for button in self.buttons.values():
                self.grid.removeWidget(button)
                button.deleteLater()
            self.buttons = {}
            self._keys = keys
            for residue in residues:
                button = QToolButton()
                button.setObjectName("residue")
                button.setText(f"{residue.letter}\n{residue.key.number}{residue.key.insertion}")
                button.setFixedSize(self.CELL_WIDTH, self.CELL_HEIGHT)
                description = f"{AMINO_ACIDS[residue.letter]} {residue.key.number} · Chain {residue.key.chain}"
                button.setToolTip(description)
                button.setAccessibleName(description)
                button.clicked.connect(
                    lambda checked=False, key=residue.key: self.selected.emit(key)
                )
                self.buttons[residue.key] = button
            self._arrange()
        for key, button in self.buttons.items():
            tone = "selected" if key == selected else key.chain if key in interface else "muted"
            if button.property("tone") != tone:
                button.setProperty("tone", tone)
                button.style().unpolish(button)
                button.style().polish(button)

    def _arrange(self):
        self._columns = max(1, (self.width() + self.GAP) // (self.CELL_WIDTH + self.GAP))
        for index, button in enumerate(self.buttons.values()):
            self.grid.addWidget(button, index // self._columns, index % self._columns)
        rows = (len(self.buttons) + self._columns - 1) // self._columns
        height = max(0, rows * (self.CELL_HEIGHT + self.GAP) - self.GAP)
        self.setMinimumHeight(height)
        self.height_changed.emit(height)

    def minimumSizeHint(self):
        return QSize(0, self.minimumHeight())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if max(1, (self.width() + self.GAP) // (self.CELL_WIDTH + self.GAP)) != self._columns:
            self._arrange()


class AffinityScale(QWidget):
    def __init__(self):
        super().__init__()
        self.value = None
        self.setFixedHeight(30)
        self.setAccessibleName("Binding change scale, minus four to plus four kcal per mole")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#858585"))
        gradient.setColorAt(0.5, QColor("#454545"))
        gradient.setColorAt(1, QColor("#c7c7c7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(0, 5, self.width(), 4, 2, 2)
        if self.value is not None:
            x = round((min(4, max(-4, self.value)) + 4) / 8 * (self.width() - 4)) + 2
            painter.setPen(QPen(QColor("#eeeeee"), 2))
            painter.drawLine(x, 2, x, 12)
        painter.setPen(QColor("#989898"))
        painter.drawText(0, 27, "Stronger −4")
        painter.drawText(self.width() // 2 - 4, 27, "0")
        text = "+4 Weaker"
        painter.drawText(self.width() - painter.fontMetrics().horizontalAdvance(text), 27, text)


class MainWindow(QMainWindow):
    residue_selected = Signal(object)
    cutoff_changed = Signal(float)
    replacement_changed = Signal(str)
    chain_changed = Signal(str)
    highlight_changed = Signal(bool)
    representation_changed = Signal(str)
    prediction_requested = Signal()

    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self._structure = None
        self._original = None
        self.setWindowTitle("ProteinBinding")
        self.resize(1280, 800)
        self.setMinimumSize(1040, 720)
        root = QWidget()
        root.setObjectName("workspace")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([920, 330])
        layout.addWidget(splitter, 1)

        viewer.residue_selected.connect(self.residue_selected)
        viewer.ready.connect(self._viewer_ready)
        viewer.failed.connect(self._viewer_failed)

    def _build_left(self):
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        structure_card, structure_layout = card()
        structure_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        structure_layout.setContentsMargins(0, 0, 0, 0)
        structure_layout.setSpacing(0)
        heading = QWidget()
        heading.setFixedHeight(32)
        heading_layout = QHBoxLayout(heading)
        heading_layout.setContentsMargins(8, 3, 8, 3)
        heading_layout.setSpacing(8)
        self.code = badge(44, name="pdbBadge")
        heading_layout.addWidget(self.code)
        self.structure_title = label("", "heading")
        self.structure_description = label("", "muted")
        heading_layout.addWidget(self.structure_title)
        heading_layout.addWidget(self.structure_description, 1)
        self.pdb_link = label("", "muted")
        self.pdb_link.setOpenExternalLinks(True)
        heading_layout.addWidget(self.pdb_link)
        structure_layout.addWidget(heading)
        structure_layout.addWidget(self.viewer, 1)

        controls = QWidget()
        controls.setObjectName("viewerToolbar")
        controls.setFixedHeight(36)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(8, 5, 8, 5)
        controls_layout.setSpacing(4)
        self.camera_buttons = []
        self.spin_button = self._camera_button("▶", "Auto rotate", "spin")
        self.spin_button.setCheckable(True)
        controls_layout.addWidget(self.spin_button)
        for text, hint, command in (
            ("+", "Zoom in", "zoom-in"),
            ("−", "Zoom out", "zoom-out"),
            ("◎", "Focus selected residue", "focus"),
            ("↺", "Reset camera", "reset"),
        ):
            controls_layout.addWidget(self._camera_button(text, hint, command))
        controls_layout.addSpacing(8)
        self.legend = label("", "muted")
        controls_layout.addWidget(self.legend)
        controls_layout.addStretch()
        self.viewer_status = label("Loading 3D…", "muted")
        controls_layout.addWidget(self.viewer_status)
        self.representation = QComboBox()
        self.representation.setObjectName("representation")
        self.representation.setFixedWidth(94)
        self.representation.setAccessibleName("Molecular representation")
        for text in ("Cartoon", "Sticks", "Surface"):
            self.representation.addItem(text, text.lower())
        self.representation.currentIndexChanged.connect(
            lambda: self.representation_changed.emit(self.representation.currentData())
        )
        controls_layout.addWidget(self.representation)
        controls.setToolTip("Drag to rotate · Scroll to zoom · Click a residue to select")
        structure_layout.addWidget(controls)
        layout.addWidget(structure_card, 1)

        sequence_card, sequence_layout = card()
        self.sequence_count = label("", "muted")
        self.chain = QComboBox()
        self.chain.setObjectName("sequenceChain")
        self.chain.setFixedWidth(128)
        self.chain.setAccessibleName("Sequence chain")
        self.chain.currentIndexChanged.connect(
            lambda: self.chain_changed.emit(self.chain.currentData())
        )
        sequence_layout.addWidget(
            section_header(
                label("Residue sequence", "sectionTitle"), self.sequence_count, self.chain
            )
        )
        self.sequence = SequenceGrid()
        self.sequence.selected.connect(self.residue_selected)
        sequence_scroll = QScrollArea()
        sequence_scroll.setWidgetResizable(True)
        sequence_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sequence_scroll.setWidget(self.sequence)
        sequence_scroll.setFixedHeight(96)
        self.sequence.height_changed.connect(
            lambda height: sequence_scroll.setFixedHeight(min(height, 132))
        )
        sequence_scroll.setToolTip("Colored residues meet the interface cutoff")
        sequence_layout.addWidget(sequence_scroll)
        layout.addWidget(sequence_card)
        return left

    def _camera_button(self, text, hint, command):
        button = QPushButton(text)
        button.setObjectName("cameraButton")
        button.setToolTip(hint)
        button.setAccessibleName(hint)
        button.setFixedSize(26, 24)
        button.setEnabled(False)
        button.clicked.connect(lambda checked=False: self._camera(command, checked))
        self.camera_buttons.append(button)
        return button

    def _camera(self, command, checked):
        if command == "spin":
            self.spin_button.setText("Ⅱ" if checked else "▶")
            command = "spin" if checked else "pause"
        elif command == "reset":
            self.spin_button.setChecked(False)
            self.spin_button.setText("▶")
        self.viewer.command(command)

    def _viewer_ready(self):
        self.viewer_status.hide()
        for button in self.camera_buttons:
            button.setEnabled(True)

    def _viewer_failed(self, message):
        self.viewer_status.setText("3D unavailable")
        self.viewer_status.setToolTip(message)
        self.viewer_status.show()

    def _build_right(self):
        scroll = QScrollArea()
        scroll.setObjectName("predictionSidebar")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(310)
        scroll.setMaximumWidth(390)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        inputs, inputs_layout = card()
        self.interface_count = badge(82)
        inputs_layout.addWidget(
            section_header(label("Interface & mutation", "sectionTitle"), self.interface_count)
        )
        cutoff_heading = QHBoxLayout()
        cutoff_heading.addWidget(label("Contact cutoff"))
        self.cutoff = QSlider(Qt.Orientation.Horizontal)
        self.cutoff.setObjectName("cutoff")
        self.cutoff.setAccessibleName("Contact cutoff in tenths of an angstrom")
        self.cutoff.setRange(30, 80)
        self.cutoff.setValue(50)
        self.cutoff.setToolTip("Contact cutoff: 3 Å (close contacts) to 8 Å (broader shell)")
        self.cutoff.valueChanged.connect(lambda value: self.cutoff_changed.emit(value / 10))
        cutoff_heading.addWidget(self.cutoff, 1)
        self.cutoff_value = label("5.0 Å", "cutoffValue")
        self.cutoff_value.setFixedSize(52, 24)
        self.cutoff_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cutoff_heading.addWidget(self.cutoff_value)
        inputs_layout.addLayout(cutoff_heading)
        self.highlight = QCheckBox("Highlight interface")
        self.highlight.setObjectName("highlightInterface")
        self.highlight.setChecked(True)
        self.highlight.toggled.connect(self.highlight_changed)
        inputs_layout.addWidget(self.highlight)
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        inputs_layout.addWidget(divider)
        self.residue_badge = label("", "residueBadge")
        self.residue_badge.setFixedSize(36, 38)
        self.residue_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(8)
        selection_layout.addWidget(self.residue_badge)
        description = QVBoxLayout()
        description.setSpacing(2)
        self.residue_name = label("", "sectionTitle")
        self.residue_details = label("", "muted")
        description.addWidget(self.residue_name)
        description.addWidget(self.residue_details)
        selection_layout.addLayout(description, 1)
        inputs_layout.addLayout(selection_layout)
        self.replacement = QComboBox()
        self.replacement.setObjectName("replacement")
        self.replacement.setAccessibleName("Replacement amino acid")
        self.replacement.currentIndexChanged.connect(
            lambda: self.replacement_changed.emit(self.replacement.currentData())
        )
        inputs_layout.addLayout(row(label("Replace with", "muted"), self.replacement))
        self.predict_button = QPushButton("Preview mutation effect  →")
        self.predict_button.setObjectName("predictButton")
        self.predict_button.setMinimumHeight(28)
        self.predict_button.clicked.connect(self.prediction_requested)
        inputs_layout.addWidget(self.predict_button)
        layout.addWidget(inputs)

        result, result_layout = card("resultCard")
        self.prediction_title = label("Predicted ΔΔG", "muted")
        result_layout.addWidget(
            section_header(self.prediction_title, badge(42, "DEMO", "demoBadge"))
        )
        self.prediction_value = label("—", "predictionValue")
        value_row = row(self.prediction_value, label("kcal/mol", "muted"))
        value_row.addStretch()
        self.prediction_direction = label("Ready to preview", "predictionDirection")
        value_row.addWidget(self.prediction_direction)
        result_layout.addLayout(value_row)
        self.scale = AffinityScale()
        result_layout.addWidget(self.scale)
        experiment_row = QHBoxLayout()
        experiment_row.addWidget(label("Experimental ΔΔG (demo)", "muted"))
        experiment_row.addStretch()
        self.experimental_value = label("—", "experimentalValue")
        experiment_row.addWidget(self.experimental_value)
        result_layout.addLayout(experiment_row)
        self.prediction_note = label("Illustrative values · No model connected", "muted", wrap=True)
        result_layout.addWidget(self.prediction_note)
        layout.addWidget(result)

        neighbors, neighbors_layout = card()
        self.neighbor_count = badge(32)
        neighbors_layout.addWidget(
            section_header(label("Nearby partner residues", "sectionTitle"), self.neighbor_count)
        )
        self.neighbors = QTableWidget(0, 3)
        self.neighbors.setObjectName("neighbors")
        self.neighbors.setHorizontalHeaderLabels(["Residue", "Chain", "Distance"])
        self.neighbors.verticalHeader().hide()
        self.neighbors.verticalHeader().setDefaultSectionSize(23)
        self.neighbors.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.neighbors.setShowGrid(False)
        self.neighbors.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.neighbors.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.neighbors.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.neighbors.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.neighbors.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.neighbors.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.neighbors.cellClicked.connect(self._select_neighbor)
        neighbors_layout.addWidget(self.neighbors)
        self.neighbors.setToolTip("Click a row to inspect its residue")
        layout.addWidget(neighbors)
        layout.addStretch()
        return scroll

    def _select_neighbor(self, row_index, column):
        key = self.neighbors.item(row_index, 0).data(Qt.ItemDataRole.UserRole)
        self.residue_selected.emit(key)

    def render(self, state: ViewState):
        if self._structure is not state.structure:
            self._structure = state.structure
            self.code.setText(state.structure.code)
            self.structure_title.setText(state.structure.title)
            self.structure_description.setText(state.structure.description)
            self.pdb_link.setText(
                f'<a style="color:#ababab;text-decoration:none" '
                f'href="https://www.rcsb.org/structure/{state.structure.code}">View in PDB ↗</a>'
            )
            self.legend.setText(
                " &nbsp; ".join(
                    f'<span style="color:{chain.color}">●</span> {chain.name} · {chain.id}'
                    for chain in state.structure.chains
                )
                + ' &nbsp; <span style="color:#f2c477">●</span> Selected'
            )
            with QSignalBlocker(self.chain):
                self.chain.clear()
                for chain in state.structure.chains:
                    self.chain.addItem(f"{chain.id} · {chain.name}", chain.id)
            self.viewer.load_structure(state.structure)

        residue = state.structure.residue(state.selected)
        with QSignalBlocker(self.replacement):
            if self._original != residue.letter:
                self._original = residue.letter
                self.replacement.clear()
                for letter, name in AMINO_ACIDS.items():
                    if letter != residue.letter:
                        self.replacement.addItem(f"{name} ({letter})", letter)
            self.replacement.setCurrentIndex(self.replacement.findData(state.replacement))
        with QSignalBlocker(self.chain):
            self.chain.setCurrentIndex(self.chain.findData(state.sequence_chain))
        with QSignalBlocker(self.cutoff):
            self.cutoff.setValue(round(state.cutoff * 10))
        with QSignalBlocker(self.highlight):
            self.highlight.setChecked(state.highlight)
        with QSignalBlocker(self.representation):
            self.representation.setCurrentIndex(self.representation.findData(state.representation))

        self.interface_count.setText(f"{len(state.interface)} residues")
        self.cutoff_value.setText(f"{state.cutoff:.1f} Å")
        self.residue_badge.setText(
            f'{residue.letter}<br><span style="font-size:10px">{residue.name}</span>'
        )
        self.residue_name.setText(f"{AMINO_ACIDS[residue.letter]} {state.selected.number}")
        membership = (
            "Interface residue" if state.selected in state.interface else "Outside interface"
        )
        self.residue_details.setText(f"Chain {state.selected.chain} · {membership}")
        chain_residues = tuple(
            r for r in state.structure.residues if r.key.chain == state.sequence_chain
        )
        self.sequence.show_residues(chain_residues, state.interface, state.selected)
        self.sequence_count.setText(f"{len(chain_residues)} residues")
        self.viewer.show_state(state)
        self.predict_button.setEnabled(not state.busy)
        self.predict_button.setText(
            "Loading preview…" if state.busy else "Preview mutation effect  →"
        )
        self._show_prediction(state)

        neighbors = tuple(n for n in residue.neighbors if n.distance <= state.cutoff)
        self.neighbor_count.setText(str(len(neighbors)))
        self.neighbors.setRowCount(len(neighbors))
        for index, neighbor in enumerate(neighbors):
            name = QTableWidgetItem(f"{neighbor.name} {neighbor.key.number}")
            name.setData(Qt.ItemDataRole.UserRole, neighbor.key)
            self.neighbors.setItem(index, 0, name)
            self.neighbors.setItem(index, 1, QTableWidgetItem(neighbor.key.chain))
            distance = QTableWidgetItem(f"{neighbor.distance:.2f} Å")
            distance.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.neighbors.setItem(index, 2, distance)
        self.neighbors.ensurePolished()
        header_height = self.neighbors.horizontalHeader().sizeHint().height()
        self.neighbors.setFixedHeight(
            header_height + 2 * self.neighbors.frameWidth() + max(2, min(8, len(neighbors))) * 23
        )

    def _show_prediction(self, state):
        result = state.prediction
        self.prediction_title.setText(f"Predicted ΔΔG · {state.request.label}")
        value = result.predicted if result else None
        self.prediction_value.setText(f"{value:+.2f}" if value is not None else "—")
        self.scale.value = value
        self.scale.update()
        experimental = result.experimental if result else None
        self.experimental_value.setText(f"{experimental:+.2f}" if experimental is not None else "—")
        note = "Illustrative values · No model connected"
        if state.error:
            direction, note = "Preview failed", state.error
        elif state.busy:
            direction = "Loading preview…"
        elif result is None:
            direction = "Ready to preview"
        elif value is None:
            direction, note = "No demo value", "Try D39 → A or N for a prepared example."
        else:
            direction = (
                "↗  Weaker binding"
                if value > 0
                else "↘  Stronger binding"
                if value < 0
                else "No change"
            )
        self.prediction_direction.setText(direction)
        self.prediction_note.setText(note)
