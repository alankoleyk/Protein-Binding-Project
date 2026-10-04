"""Real Qt/WebEngine integration tests; download the README resources first."""

import io
import json
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from PySide6.QtCore import QDir, QEventLoop, Qt, QThread, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

from contracts import ResidueKey
from src.__main__ import create_window
from tasks import QtTaskRunner

SOURCE = Path(__file__).resolve().parents[2] / "src"


class QtTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        QDir.addSearchPath("icons", str(SOURCE / "icons"))
        cls.app.setStyleSheet((SOURCE / "style.qss").read_text())

    def wait_until(self, condition, timeout=10000):
        if condition():
            return
        loop = QEventLoop()
        poll = QTimer()
        poll.timeout.connect(lambda: loop.quit() if condition() else None)
        poll.start(10)
        deadline = QTimer()
        deadline.setSingleShot(True)
        deadline.timeout.connect(loop.quit)
        deadline.start(timeout)
        loop.exec()
        poll.stop()
        deadline.stop()
        self.assertTrue(condition(), "Timed out waiting for Qt/JavaScript")


class GuiWorkflowTests(QtTestCase):
    def setUp(self):
        self.window, self.presenter, self.tasks = create_window()
        self.window.show()
        self.wait_until(lambda: self.window.spin_button.isEnabled())

    def tearDown(self):
        self.tasks.wait_for_done()
        self.app.processEvents()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def javascript(self, expression):
        result = []
        self.window.viewer.page().runJavaScript(f"JSON.stringify({expression})", result.append)
        self.wait_until(lambda: bool(result))
        self.assertTrue(result[0], "JavaScript did not return a JSON value")
        return json.loads(result[0])

    def test_real_structure_black_canvas_and_residue_pick(self):
        scene = self.javascript("""(() => {
            const atoms = proteinBinding.viewer.selectedAtoms({});
            return {count: atoms.length, chains: [...new Set(atoms.map(a => a.chain))],
                background: getComputedStyle(document.body).backgroundColor,
                contextLost: proteinBinding.viewer.getRenderer().isLost()};
        })()""")
        self.assertEqual(scene["count"], 1557)
        self.assertEqual(scene["chains"], ["A", "D"])
        self.assertEqual(scene["background"], "rgb(0, 0, 0)")
        self.assertFalse(scene["contextLost"])
        # Exercise the callback installed on the 3Dmol atom, across QWebChannel.
        self.javascript("""(() => {
            const atom = proteinBinding.viewer.selectedAtoms({chain: 'A', resi: 83})[0];
            atom.callback(atom);
            return true;
        })()""")
        self.wait_until(lambda: self.window.chain.currentData() == "A")
        self.assertEqual(self.presenter.state.selected, ResidueKey("A", 83))
        self.assertEqual(self.window.residue_name.text(), "Arginine 83")

    def test_prediction_and_input_invalidation(self):
        QTest.mouseClick(self.window.predict_button, Qt.MouseButton.LeftButton)
        self.wait_until(lambda: self.window.prediction_value.text() == "+3.20")
        self.assertEqual(self.window.experimental_value.text(), "+3.70")
        self.window.replacement.setCurrentIndex(self.window.replacement.findData("N"))
        self.assertEqual(self.window.prediction_value.text(), "—")
        QTest.mouseClick(self.window.predict_button, Qt.MouseButton.LeftButton)
        self.wait_until(lambda: self.window.prediction_value.text() == "+1.65")
        self.assertIn("D39N", self.window.prediction_title.text())

    def test_cutoff_sequence_and_neighbor_selection(self):
        self.window.cutoff.setValue(55)
        self.assertEqual(self.window.interface_count.text(), "46 residues")
        self.assertEqual(self.window.neighbors.rowCount(), 8)
        first = self.window.neighbors.item(0, 0)
        key = first.data(Qt.ItemDataRole.UserRole)
        sidebar = self.window.findChild(QScrollArea, "predictionSidebar")
        sidebar.ensureWidgetVisible(self.window.neighbors)
        self.app.processEvents()
        QTest.mouseClick(
            self.window.neighbors.viewport(),
            Qt.MouseButton.LeftButton,
            pos=self.window.neighbors.visualItemRect(first).center(),
        )
        self.assertEqual(self.presenter.state.selected, key)
        button = self.window.sequence.buttons[ResidueKey("A", 11)]
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.presenter.state.selected, ResidueKey("A", 11))
        self.assertEqual(self.window.residue_name.text(), "Alanine 11")
        self.assertEqual(self.window.replacement.currentData(), "G")

    def test_representation_and_camera_commands(self):
        self.window.representation.setCurrentIndex(self.window.representation.findData("sticks"))
        self.wait_until(lambda: self.presenter.state.representation == "sticks")
        # A round trip is ordered after the bridge's style update.
        color = self.javascript(
            "proteinBinding.viewer.selectedAtoms({chain: 'A', resi: 11})[0].style.stick.color"
        )
        self.assertEqual(color, "#62d7bf")
        camera = self.javascript("proteinBinding.viewer.getView()")
        self.window.camera_buttons[1].click()
        zoomed = self.javascript("proteinBinding.viewer.getView()")
        self.assertNotEqual(camera, zoomed)
        self.window.camera_buttons[-1].click()
        self.assertEqual(camera, self.javascript("proteinBinding.viewer.getView()"))

    def test_small_window_reflows_sequence_without_viewer_overlap(self):
        self.window.resize(1040, 720)
        sequence = self.window.sequence
        scroll = sequence.parentWidget().parentWidget()
        self.wait_until(lambda: scroll.horizontalScrollBar().maximum() == 0)
        self.app.processEvents()
        toolbar = self.window.findChild(QWidget, "viewerToolbar")
        self.assertLess(self.window.viewer.geometry().bottom(), toolbar.geometry().top())
        self.assertGreater(self.window.viewer.height(), 150)
        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
        for button in sequence.buttons.values():
            self.assertLessEqual(button.geometry().right(), sequence.width())

    def test_surface_rendering_completes(self):
        self.window.representation.setCurrentIndex(self.window.representation.findData("surface"))
        completed = []
        poll = QTimer()
        poll.timeout.connect(
            lambda: self.window.viewer.page().runJavaScript(
                "Object.keys(proteinBinding.viewer.surfaces).length === 2 && "
                "proteinBinding.viewer.surfacesFinished()",
                lambda ready: completed.append(True) if ready else None,
            )
        )
        poll.start(20)
        self.wait_until(lambda: bool(completed))
        poll.stop()
        self.assertFalse(self.javascript("proteinBinding.viewer.getRenderer().isLost()"))


class TaskRunnerTests(QtTestCase):
    def setUp(self):
        self.runner = QtTaskRunner()

    def tearDown(self):
        self.runner.wait_for_done()

    def test_worker_and_completion_run_on_correct_threads(self):
        outcome = []
        self.runner.submit(
            lambda: QThread.currentThread() == self.app.thread(),
            lambda was_gui: outcome.append((was_gui, QThread.currentThread() == self.app.thread())),
            lambda message: self.fail(message),
        )
        self.wait_until(lambda: bool(outcome))
        self.assertEqual(outcome, [(False, True)])

    def test_empty_exception_is_reported_as_failure(self):
        errors, results = [], []

        def fail():
            raise ValueError()

        with redirect_stderr(io.StringIO()):
            self.runner.submit(fail, results.append, errors.append)
            self.wait_until(lambda: bool(errors or results))
        self.assertEqual(results, [])
        self.assertEqual(errors, ["ValueError: "])


if __name__ == "__main__":
    unittest.main()
