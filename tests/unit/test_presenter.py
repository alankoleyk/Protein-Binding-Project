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


def make_presenter():
    view, tasks = FakeView(), DeferredTasks()
    presenter = MainPresenter(view, DemoBackend(), tasks)
    presenter.start()
    return presenter, view, tasks


def test_demo_interface_uses_precomputed_distances():
    presenter, view, _ = make_presenter()
    assert len(view.state.interface) == 41
    presenter.set_cutoff(5.5)
    assert len(view.state.interface) == 46
    residue = view.state.structure.residue(ResidueKey("D", 39))
    assert sum(neighbor.distance <= 5.5 for neighbor in residue.neighbors) == 8


def test_prediction_reports_busy_then_a_result_for_the_submitted_mutation():
    presenter, view, tasks = make_presenter()
    presenter.predict()
    assert view.state.busy
    presenter.predict()
    assert len(tasks.jobs) == 1
    tasks.finish()
    assert not view.state.busy
    assert view.state.prediction.request.label == "D39A"
    assert view.state.prediction.predicted == 3.2


def test_late_result_cannot_overwrite_a_new_mutation():
    presenter, view, tasks = make_presenter()
    presenter.predict()
    presenter.set_replacement("N")
    presenter.predict()
    tasks.finish(1)
    tasks.finish(0)
    assert view.state.prediction.request.label == "D39N"


def test_cutoff_change_invalidates_a_pending_prediction():
    presenter, view, tasks = make_presenter()
    presenter.predict()
    presenter.set_cutoff(6.0)
    tasks.finish()
    assert view.state.prediction is None
    assert not view.state.busy


def test_display_changes_preserve_prediction():
    presenter, view, tasks = make_presenter()
    presenter.predict()
    tasks.finish()
    result = view.state.prediction
    presenter.set_highlight(False)
    presenter.set_representation("sticks")
    presenter.set_sequence_chain("A")
    assert view.state.prediction == result


def test_residue_selection_switches_chain_and_avoids_identity_substitution():
    presenter, view, _ = make_presenter()
    presenter.select_residue(ResidueKey("A", 11))
    assert view.state.sequence_chain == "A"
    assert view.state.replacement == "G"


def test_unavailable_fixture_is_not_fabricated():
    presenter, view, tasks = make_presenter()
    presenter.set_replacement("W")
    presenter.predict()
    tasks.finish()
    assert view.state.prediction.predicted is None
    assert view.state.prediction.experimental is None


def test_backend_error_restores_controls_and_keeps_input():
    presenter, view, tasks = make_presenter()
    presenter.predict()
    tasks.jobs[0][2]("Model could not be loaded")
    assert not view.state.busy
    assert view.state.error == "Model could not be loaded"
    assert view.state.selected == ResidueKey("D", 39)
