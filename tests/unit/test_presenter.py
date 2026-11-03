import unittest

from adapters.hras import HrasBackend
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
    @classmethod
    def setUpClass(cls):
        cls.backend = HrasBackend()

    def setUp(self):
        self.view = FakeView()
        self.tasks = DeferredTasks()
        self.presenter = MainPresenter(self.view, self.backend, self.tasks)
        self.presenter.start()

    def test_starts_on_a_contact_site_in_the_single_loaded_chain(self):
        state = self.view.state
        self.assertEqual(state.sequence_chain, "A")
        self.assertTrue(state.can_mutate)
        self.assertNotEqual(state.request.original, state.replacement)

    def test_prediction_reports_busy_then_the_backend_score(self):
        self.presenter.select_residue(ResidueKey("A", 33))
        self.presenter.predict()
        self.assertTrue(self.view.state.busy)
        self.presenter.predict()
        self.assertEqual(len(self.tasks.jobs), 1)
        self.tasks.finish()
        self.assertFalse(self.view.state.busy)
        self.assertEqual(self.view.state.prediction.request.label, "D33A")
        self.assertAlmostEqual(self.view.state.prediction.predicted, 2.2)

    def test_old_completion_leaves_the_new_request_busy(self):
        self.presenter.predict()
        self.presenter.set_replacement("N")
        self.presenter.predict()
        self.tasks.finish(0)
        self.assertTrue(self.view.state.busy)
        self.assertIsNone(self.view.state.prediction)
        self.tasks.finish(1)
        self.assertEqual(self.view.state.prediction.request.label, "Q25N")

    def test_old_error_does_not_replace_the_current_result(self):
        self.presenter.predict()
        self.presenter.set_replacement("N")
        self.presenter.predict()
        self.tasks.finish(1)
        self.tasks.jobs[0][2]("Outdated failure")
        self.assertEqual(self.view.state.error, "")
        self.assertEqual(self.view.state.prediction.request.label, "Q25N")

    def test_non_contact_residues_are_view_only(self):
        self.presenter.select_residue(ResidueKey("A", 11))
        before = self.view.state
        self.presenter.set_replacement("N")
        self.presenter.predict()
        self.assertFalse(self.view.state.can_mutate)
        self.assertEqual(self.view.state, before)
        self.assertEqual(self.tasks.jobs, [])

    def test_selecting_a_non_contact_invalidates_pending_results(self):
        self.presenter.predict()
        self.presenter.select_residue(ResidueKey("A", 11))
        self.tasks.finish()
        self.assertIsNone(self.view.state.prediction)
        self.assertFalse(self.view.state.busy)
        self.presenter.select_residue(ResidueKey("A", 33))
        self.presenter.predict()
        self.tasks.finish(1)
        self.assertEqual(self.view.state.prediction.request.label, "D33G")

    def test_display_changes_preserve_prediction(self):
        self.presenter.predict()
        self.tasks.finish()
        result = self.view.state.prediction
        self.presenter.set_highlight(False)
        self.presenter.set_representation("sticks")
        self.assertEqual(self.view.state.prediction, result)

    def test_backend_error_restores_controls_and_keeps_input(self):
        self.presenter.predict()
        self.tasks.jobs[0][2]("Calculation failed")
        self.assertFalse(self.view.state.busy)
        self.assertEqual(self.view.state.error, "Calculation failed")
        self.assertEqual(self.view.state.selected, ResidueKey("A", 25))


if __name__ == "__main__":
    unittest.main()
