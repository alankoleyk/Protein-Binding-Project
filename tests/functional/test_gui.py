"""Real Qt/WebEngine checks; run with a desktop session and the local 3Dmol resource."""

import json
import time
import unittest
from pathlib import Path

from PySide6.QtCore import QDir
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from contracts import ResidueKey
from src.__main__ import create_window

SOURCE = Path(__file__).resolve().parents[2] / "src"


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        QDir.addSearchPath("icons", str(SOURCE / "icons"))
        cls.app.setStyleSheet((SOURCE / "style.qss").read_text())
        cls.window, cls.presenter, cls.tasks = create_window()
        cls.window.show()

    @classmethod
    def tearDownClass(cls):
        cls.tasks.wait_for_done()
        cls.window.close()
        cls.app.processEvents()

    def wait_for(self, predicate):
        deadline = time.monotonic() + 15
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertTrue(predicate(), "Timed out waiting for the GUI")

    def javascript(self, source):
        results = []
        self.window.viewer.page().runJavaScript(source, results.append)
        self.wait_for(lambda: bool(results))
        return results[0]

    def setUp(self):
        self.wait_for(lambda: self.window.viewer._scene_ready)

    def test_mmcif_renders_one_protein_chain_with_all_contact_sites(self):
        actual = json.loads(
            self.javascript("""
            JSON.stringify((() => {
              const atoms = window.proteinBinding.viewer.selectedAtoms({});
              return {
                chains: [...new Set(atoms.map(a => a.chain))],
                residues: [...new Set(atoms.map(a => a.resi))],
                hetero: atoms.some(a => a.hetflag),
              };
            })())
        """)
        )
        self.assertEqual(actual["chains"], ["A"])
        self.assertEqual(len(actual["residues"]), 166)
        self.assertFalse(actual["hetero"])
        self.assertTrue({25, 33, 36, 37, 38, 39, 40, 41, 63, 64} <= set(actual["residues"]))
        self.assertEqual(self.window.contact_count.text(), "10 sites")
        self.assertFalse(self.window.chain.isVisible())

    def test_sequence_and_3d_selection_enforce_contact_only_mutations(self):
        self.window.sequence.buttons[ResidueKey("A", 11)].click()
        self.assertFalse(self.window.replacement.isEnabled())
        self.assertFalse(self.window.predict_button.isEnabled())
        self.window.prediction_requested.emit()
        self.assertEqual(self.tasks._pending, {})
        self.assertIn("View only", self.window.residue_details.text())

        # Use the same atom callback that a click in the 3D viewer invokes.
        self.javascript("""
            (() => {
              const viewer = window.proteinBinding.viewer;
              const atom = viewer.selectedAtoms({chain: 'A', resi: 33})[0];
              atom.callback(atom, viewer);
            })()
        """)
        self.wait_for(lambda: self.presenter.state.selected == ResidueKey("A", 33))
        self.assertTrue(self.window.replacement.isEnabled())
        self.assertTrue(self.window.predict_button.isEnabled())
        self.assertIn("Lysine (K) × 2", self.window.partner_summary.text())
        self.window.replacement.setCurrentIndex(self.window.replacement.findData("A"))
        self.window.predict_button.click()
        self.wait_for(lambda: self.presenter.state.prediction is not None)
        self.assertEqual(self.window.prediction_value.text(), "+2.20")
        self.assertEqual(self.presenter.state.prediction.request.label, "D33A")
        self.assertEqual(self.window.prediction_note.text(), "To be calibrated")


if __name__ == "__main__":
    unittest.main()
