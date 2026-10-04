"""Composition root: concrete implementations are connected only here."""

import sys
from pathlib import Path

from PySide6.QtCore import QDir
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from adapters.demo import DemoBackend
from presenter import MainPresenter
from tasks import QtTaskRunner
from view import MainWindow
from viewer import MoleculeView


def create_window():
    window = MainWindow(MoleculeView())
    tasks = QtTaskRunner()
    presenter = MainPresenter(window, DemoBackend(), tasks)
    window.residue_selected.connect(presenter.select_residue)
    window.cutoff_changed.connect(presenter.set_cutoff)
    window.replacement_changed.connect(presenter.set_replacement)
    window.chain_changed.connect(presenter.set_sequence_chain)
    window.highlight_changed.connect(presenter.set_highlight)
    window.representation_changed.connect(presenter.set_representation)
    window.prediction_requested.connect(presenter.predict)
    presenter.start()
    return window, presenter, tasks


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ProteinBinding")
    QDir.addSearchPath("icons", str(Path(__file__).with_name("icons")))
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#101821"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#101821"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#dce4ed"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#dce4ed"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#dce4ed"))
    app.setPalette(palette)
    app.setStyleSheet(Path(__file__).with_name("style.qss").read_text())
    window, presenter, tasks = create_window()
    app.aboutToQuit.connect(tasks.wait_for_done)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
