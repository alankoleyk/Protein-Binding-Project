import unittest

from adapters.demo import DemoBackend
from contracts import ResidueKey
from presenter import MainPresenter


class FakeView:
    def render(self, state):
        self.state = state


class DeferredTasks:
    def __init__(self):
        self.jobs = []

    def submit(self, work, succeeded, failed):
        self.jobs.append((work, succeeded, failed))

    def finish(self, index=0):
        work, succeeded, _ = self.jobs[index]
        succeeded(work())


class PresenterTests(unittest.TestCase):
    def setUp(self):
        self.view = FakeView()
        self.tasks = DeferredTasks()
        self.presenter = MainPresenter(self.view, DemoBackend(), self.tasks)
        self.presenter.start()

    def test_demo_interface_uses_precomputed_distances(self):
        self.assertEqual(len(self.view.state.interface), 41)
        self.presenter.set_cutoff(5.5)
        self.assertEqual(len(self.view.state.interface), 46)
        residue = self.view.state.structure.residue(ResidueKey("D", 39))
        self.assertEqual(sum(neighbor.distance <= 5.5 for neighbor in residue.neighbors), 8)

    def test_prediction_reports_busy_then_a_result_for_the_submitted_mutation(self):
        self.presenter.predict()
        self.assertTrue(self.view.state.busy)
        self.presenter.predict()
        self.assertEqual(len(self.tasks.jobs), 1)
        self.tasks.finish()
        self.assertFalse(self.view.state.busy)
        self.assertEqual(self.view.state.prediction.request.label, "D39A")
        self.assertEqual(self.view.state.prediction.predicted, 3.2)

    def test_late_result_cannot_overwrite_a_new_mutation(self):
        self.presenter.predict()
        self.presenter.set_replacement("N")
        self.presenter.predict()
        self.tasks.finish(1)
        self.tasks.finish(0)
        self.assertEqual(self.view.state.prediction.request.label, "D39N")

    def test_cutoff_change_invalidates_a_pending_prediction(self):
        self.presenter.predict()
        self.presenter.set_cutoff(6.0)
        self.tasks.finish()
        self.assertIsNone(self.view.state.prediction)
        self.assertFalse(self.view.state.busy)

    def test_display_changes_preserve_prediction(self):
        self.presenter.predict()
        self.tasks.finish()
        result = self.view.state.prediction
        self.presenter.set_highlight(False)
        self.presenter.set_representation("sticks")
        self.presenter.set_sequence_chain("A")
        self.assertEqual(self.view.state.prediction, result)

    def test_residue_selection_switches_chain_and_avoids_identity_substitution(self):
        self.presenter.select_residue(ResidueKey("A", 11))
        self.assertEqual(self.view.state.sequence_chain, "A")
        self.assertEqual(self.view.state.replacement, "G")

    def test_unavailable_fixture_is_not_fabricated(self):
        self.presenter.set_replacement("W")
        self.presenter.predict()
        self.tasks.finish()
        self.assertIsNone(self.view.state.prediction.predicted)
        self.assertIsNone(self.view.state.prediction.experimental)

    def test_backend_error_restores_controls_and_keeps_input(self):
        self.presenter.predict()
        self.tasks.jobs[0][2]("Model could not be loaded")
        self.assertFalse(self.view.state.busy)
        self.assertEqual(self.view.state.error, "Model could not be loaded")
        self.assertEqual(self.view.state.selected, ResidueKey("D", 39))


if __name__ == "__main__":
    unittest.main()
