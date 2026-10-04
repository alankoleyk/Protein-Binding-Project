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
    layout.setSpacing(12)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


def card(name="card"):
    widget = QFrame()
    widget.setObjectName(name)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(14)
    return widget, layout


class SequenceGrid(QWidget):
    selected = Signal(object)

    def __init__(self):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(5)
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
                button.setFixedSize(35, 43)
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
        self._columns = max(1, (self.width() + 5) // 40)
        for index, button in enumerate(self.buttons.values()):
            self.grid.addWidget(button, index // self._columns, index % self._columns)
        rows = (len(self.buttons) + self._columns - 1) // self._columns
        self.setMinimumHeight(max(0, rows * 48 - 5))

    def minimumSizeHint(self):
        return QSize(0, self.minimumHeight())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if max(1, (self.width() + 5) // 40) != self._columns:
            self._arrange()


class AffinityScale(QWidget):
    def __init__(self):
        super().__init__()
        self.value = None
        self.setFixedHeight(38)
        self.setAccessibleName("Binding change scale, minus four to plus four kcal per mole")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#62d7bf"))
        gradient.setColorAt(0.5, QColor("#607180"))
        gradient.setColorAt(1, QColor("#f2c477"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(0, 7, self.width(), 5, 2, 2)
        if self.value is not None:
            x = round((min(4, max(-4, self.value)) + 4) / 8 * (self.width() - 4)) + 2
            painter.setPen(QPen(QColor("#f5f0e6"), 2))
            painter.drawLine(x, 3, x, 16)
        painter.setPen(QColor("#8293a6"))
        painter.drawText(0, 33, "Stronger −4")
        painter.drawText(self.width() // 2 - 4, 33, "0")
        text = "+4 Weaker"
        painter.drawText(self.width() - painter.fontMetrics().horizontalAdvance(text), 33, text)


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
        self.resize(1380, 920)
        self.setMinimumSize(1040, 720)
        root = QWidget()
        root.setObjectName("workspace")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(18)

        header = QHBoxLayout()
        header.addWidget(label("◈", "brandMark"))
        brand = QVBoxLayout()
        brand.setSpacing(3)
        brand.addWidget(label("ProteinBinding", "brand"))
        brand.addWidget(label("STRUCTURE → INTERFACE → MUTATION", "eyebrow"))
        header.addLayout(brand)
        header.addStretch()
        header.addWidget(label("●  LOCAL DEMO", "badge"))
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(18)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([930, 380])
        layout.addWidget(splitter, 1)
        footer = QHBoxLayout()
        footer.addWidget(label("Known structure. One substitution at a time.", "muted"))
        footer.addStretch()
        footer.addWidget(label("Real structure · Illustrative predictions", "muted"))
        layout.addLayout(footer)

        viewer.residue_selected.connect(self.residue_selected)
        viewer.ready.connect(self._viewer_ready)
        viewer.failed.connect(self._viewer_failed)

    def _build_left(self):
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        structure_card, structure_layout = card()
        structure_layout.setContentsMargins(0, 0, 0, 0)
        structure_layout.setSpacing(0)
        heading = QWidget()
        heading_layout = QHBoxLayout(heading)
        heading_layout.setContentsMargins(20, 17, 20, 17)
        heading_layout.setSpacing(14)
        self.code = label("", "pdbBadge")
        heading_layout.addWidget(self.code)
        title = QVBoxLayout()
        title.setSpacing(5)
        self.structure_title = label("", "heading")
        self.structure_description = label("", "muted")
        title.addWidget(self.structure_title)
        title.addWidget(self.structure_description)
        heading_layout.addLayout(title, 1)
        self.pdb_link = label()
        self.pdb_link.setOpenExternalLinks(True)
        heading_layout.addWidget(self.pdb_link)
        structure_layout.addWidget(heading)
        structure_layout.addWidget(self.viewer, 1)

        controls = QWidget()
        controls.setObjectName("viewerToolbar")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(20, 8, 20, 16)
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
        controls_layout.addStretch()
        self.viewer_status = label("Loading 3D…", "muted")
        controls_layout.addWidget(self.viewer_status)
        structure_layout.addWidget(controls)

        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(20, 13, 20, 13)
        self.legend = label()
        bottom_layout.addWidget(self.legend)
        bottom_layout.addStretch()
        self.representation = QComboBox()
        self.representation.setObjectName("representation")
        self.representation.setAccessibleName("Molecular representation")
        for text in ("Cartoon", "Sticks", "Surface"):
            self.representation.addItem(text, text.lower())
        self.representation.currentIndexChanged.connect(
            lambda: self.representation_changed.emit(self.representation.currentData())
        )
        bottom_layout.addWidget(self.representation)
        structure_layout.addWidget(bottom)
        layout.addWidget(structure_card, 1)

        sequence_card, sequence_layout = card()
        sequence_heading = QHBoxLayout()
        sequence_heading.addWidget(label("Residue sequence", "sectionTitle"))
        sequence_heading.addStretch()
        self.chain = QComboBox()
        self.chain.setObjectName("sequenceChain")
        self.chain.setAccessibleName("Sequence chain")
        self.chain.currentIndexChanged.connect(
            lambda: self.chain_changed.emit(self.chain.currentData())
        )
        sequence_heading.addWidget(self.chain)
        sequence_layout.addLayout(sequence_heading)
        self.sequence = SequenceGrid()
        self.sequence.selected.connect(self.residue_selected)
        sequence_scroll = QScrollArea()
        sequence_scroll.setWidgetResizable(True)
        sequence_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sequence_scroll.setWidget(self.sequence)
        sequence_scroll.setMinimumHeight(100)
        sequence_scroll.setMaximumHeight(150)
        sequence_layout.addWidget(sequence_scroll)
        sequence_footer = QHBoxLayout()
        sequence_footer.addWidget(label("Colored residues meet the interface cutoff", "muted"))
        sequence_footer.addStretch()
        self.sequence_count = label("", "muted")
        sequence_footer.addWidget(self.sequence_count)
        sequence_layout.addLayout(sequence_footer)
        layout.addWidget(sequence_card)
        return left

    def _camera_button(self, text, hint, command):
        button = QPushButton(text)
        button.setObjectName("cameraButton")
        button.setToolTip(hint)
        button.setAccessibleName(hint)
        button.setFixedSize(34, 32)
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
        self.viewer_status.setText("Drag to rotate · Scroll to zoom")
        for button in self.camera_buttons:
            button.setEnabled(True)

    def _viewer_failed(self, message):
        self.viewer_status.setText("3D unavailable")
        self.viewer_status.setToolTip(message)

    def _build_right(self):
        scroll = QScrollArea()
        scroll.setObjectName("predictionSidebar")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(345)
        scroll.setMaximumWidth(475)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 3, 0)
        layout.setSpacing(16)

        inputs, inputs_layout = card()
        heading = QHBoxLayout()
        heading.addWidget(label("Interface & mutation", "sectionTitle"))
        heading.addStretch()
        self.interface_count = label("", "badge")
        heading.addWidget(self.interface_count)
        inputs_layout.addLayout(heading)
        inputs_layout.addSpacing(5)
        cutoff_heading = QHBoxLayout()
        cutoff_heading.addWidget(label("Contact cutoff"))
        cutoff_heading.addStretch()
        self.cutoff_value = label("5.0 Å", "cutoffValue")
        cutoff_heading.addWidget(self.cutoff_value)
        inputs_layout.addLayout(cutoff_heading)
        self.cutoff = QSlider(Qt.Orientation.Horizontal)
        self.cutoff.setObjectName("cutoff")
        self.cutoff.setAccessibleName("Contact cutoff in tenths of an angstrom")
        self.cutoff.setRange(30, 80)
        self.cutoff.setValue(50)
        self.cutoff.valueChanged.connect(lambda value: self.cutoff_changed.emit(value / 10))
        inputs_layout.addWidget(self.cutoff)
        cutoff_labels = QHBoxLayout()
        cutoff_labels.addWidget(label("3 Å · close contacts", "muted"))
        cutoff_labels.addStretch()
        cutoff_labels.addWidget(label("8 Å · broader shell", "muted"))
        inputs_layout.addLayout(cutoff_labels)
        self.highlight = QCheckBox("Highlight interface")
        self.highlight.setObjectName("highlightInterface")
        self.highlight.setChecked(True)
        self.highlight.toggled.connect(self.highlight_changed)
        inputs_layout.addWidget(self.highlight)
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        inputs_layout.addWidget(divider)
        inputs_layout.addWidget(label("SELECTED RESIDUE", "eyebrow"))
        self.residue_badge = label("", "residueBadge")
        self.residue_badge.setFixedSize(56, 60)
        self.residue_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(14)
        selection_layout.addWidget(self.residue_badge)
        description = QVBoxLayout()
        description.setSpacing(6)
        self.residue_name = label("", "sectionTitle")
        self.residue_details = label("", "muted")
        description.addWidget(self.residue_name)
        description.addWidget(self.residue_details)
        selection_layout.addLayout(description, 1)
        inputs_layout.addLayout(selection_layout)
        inputs_layout.addWidget(label("Substitute with", "muted"))
        self.replacement = QComboBox()
        self.replacement.setObjectName("replacement")
        self.replacement.setAccessibleName("Replacement amino acid")
        self.replacement.currentIndexChanged.connect(
            lambda: self.replacement_changed.emit(self.replacement.currentData())
        )
        inputs_layout.addWidget(self.replacement)
        self.predict_button = QPushButton("Preview mutation effect  →")
        self.predict_button.setObjectName("predictButton")
        self.predict_button.setMinimumHeight(44)
        self.predict_button.clicked.connect(self.prediction_requested)
        inputs_layout.addWidget(self.predict_button)
        inputs_layout.addWidget(
            label(
                "Loads a fixed demo result. No prediction model is connected.", "muted", wrap=True
            )
        )
        layout.addWidget(inputs)

        result, result_layout = card("resultCard")
        result_heading = QHBoxLayout()
        self.prediction_title = label("Predicted ΔΔG", "muted")
        result_heading.addWidget(self.prediction_title)
        result_heading.addStretch()
        result_heading.addWidget(label("DEMO", "demoBadge"))
        result_layout.addLayout(result_heading)
        self.prediction_value = label("—", "predictionValue")
        value_row = row(self.prediction_value, label("kcal/mol", "muted"))
        value_row.addStretch()
        result_layout.addLayout(value_row)
        self.prediction_direction = label("Ready to preview", "predictionDirection")
        result_layout.addWidget(self.prediction_direction)
        self.scale = AffinityScale()
        result_layout.addWidget(self.scale)
        experiment_row = QHBoxLayout()
        experiment_row.addWidget(label("Experimental ΔΔG (demo)", "muted"))
        experiment_row.addStretch()
        self.experimental_value = label("—", "experimentalValue")
        experiment_row.addWidget(self.experimental_value)
        result_layout.addLayout(experiment_row)
        self.prediction_note = label(
            "Both values are invented for this prototype.", "muted", wrap=True
        )
        result_layout.addWidget(self.prediction_note)
        layout.addWidget(result)

        neighbors, neighbors_layout = card()
        neighbors_heading = QHBoxLayout()
        neighbors_heading.addWidget(label("Nearby partner residues", "sectionTitle"))
        neighbors_heading.addStretch()
        self.neighbor_count = label("", "badge")
        neighbors_heading.addWidget(self.neighbor_count)
        neighbors_layout.addLayout(neighbors_heading)
        self.neighbors = QTableWidget(0, 3)
        self.neighbors.setObjectName("neighbors")
        self.neighbors.setHorizontalHeaderLabels(["Residue", "Chain", "Distance"])
        self.neighbors.verticalHeader().hide()
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
        self.neighbors.setMinimumHeight(120)
        self.neighbors.cellClicked.connect(self._select_neighbor)
        neighbors_layout.addWidget(self.neighbors)
        neighbors_layout.addWidget(label("Click a row to inspect its residue.", "muted"))
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
                f'<a style="color:#91a2b5;text-decoration:none" '
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
        self.sequence_count.setText(f"{len(chain_residues)} resolved residues")
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
            self.neighbors.setRowHeight(index, 32)
        self.neighbors.setFixedHeight(34 + max(2, min(6, len(neighbors))) * 32)

    def _show_prediction(self, state):
        result = state.prediction
        residue = state.structure.residue(state.selected)
        mutation = f"{residue.letter}{residue.key.number}{state.replacement}"
        self.prediction_title.setText(f"Predicted ΔΔG · {mutation}")
        value = result.predicted if result else None
        self.prediction_value.setText(f"{value:+.2f}" if value is not None else "—")
        self.scale.value = value
        self.scale.update()
        experimental = result.experimental if result else None
        self.experimental_value.setText(f"{experimental:+.2f}" if experimental is not None else "—")
        if state.error:
            direction, note = "Preview failed", state.error
        elif state.busy:
            direction, note = "Loading preview…", "You can keep exploring the structure."
        elif result is None:
            direction, note = "Ready to preview", "Both values are invented for this prototype."
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
            note = "Fixed illustrative values; no prediction model is connected."
        self.prediction_direction.setText(direction)
        self.prediction_note.setText(note)
