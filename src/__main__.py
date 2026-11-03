"""Composition root: concrete implementations are connected only here."""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QDir
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from adapters.hras import DEFAULT_STRUCTURE, HrasBackend
from presenter import MainPresenter
from tasks import QtTaskRunner
from view import MainWindow
from viewer import MoleculeView


def create_window(path=DEFAULT_STRUCTURE, chain_id="A"):
    backend = HrasBackend(path, chain_id)
    window = MainWindow(MoleculeView())
    tasks = QtTaskRunner()
    presenter = MainPresenter(window, backend, tasks)
    window.residue_selected.connect(presenter.select_residue)
    window.replacement_changed.connect(presenter.set_replacement)
    window.chain_changed.connect(presenter.set_sequence_chain)
    window.highlight_changed.connect(presenter.set_highlight)
    window.representation_changed.connect(presenter.set_representation)
    window.prediction_requested.connect(presenter.predict)
    presenter.start()
    return window, presenter, tasks


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore predefined HRas contact-site mutations.")
    parser.add_argument("--structure", type=Path, default=DEFAULT_STRUCTURE)
    parser.add_argument("--chain", default="A", help="HRas author chain ID (default: A)")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("ProteinBinding")
    QDir.addSearchPath("icons", str(Path(__file__).with_name("icons")))
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#191919"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#191919"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#dedede"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#dedede"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#dedede"))
    app.setPalette(palette)
    app.setStyleSheet(Path(__file__).with_name("style.qss").read_text())
    try:
        window, presenter, tasks = create_window(args.structure, args.chain)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    app.aboutToQuit.connect(tasks.wait_for_done)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
