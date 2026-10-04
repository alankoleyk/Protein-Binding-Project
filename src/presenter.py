"""Application flow, with no knowledge of Qt widgets or the backend's API."""

from dataclasses import replace

from contracts import (
    BackendPort,
    PredictionRequest,
    PredictionResult,
    ResidueKey,
    TaskPort,
    ViewPort,
    ViewState,
)


class MainPresenter:
    def __init__(self, view: ViewPort, backend: BackendPort, tasks: TaskPort):
        self.view = view
        self.backend = backend
        self.tasks = tasks
        self._revision = 0
        structure = backend.load_structure()
        self.state = ViewState(
            structure=structure,
            selected=structure.initial_selection,
            sequence_chain=structure.initial_selection.chain,
            interface=backend.find_interface(structure, 5.0),
        )

    def start(self) -> None:
        self.view.render(self.state)

    def _render(self, **changes) -> None:
        self.state = replace(self.state, **changes)
        self.view.render(self.state)

    def _invalidate(self, **changes) -> None:
        self._revision += 1
        self._render(prediction=None, busy=False, error="", **changes)

    def select_residue(self, key: ResidueKey) -> None:
        if key == self.state.selected:
            return
        residue = self.state.structure.residue(key)
        replacement = self.state.replacement
        if replacement == residue.letter:
            replacement = "G" if residue.letter == "A" else "A"
        self._invalidate(selected=key, sequence_chain=key.chain, replacement=replacement)

    def set_cutoff(self, cutoff: float) -> None:
        if cutoff != self.state.cutoff:
            interface = self.backend.find_interface(self.state.structure, cutoff)
            self._invalidate(cutoff=cutoff, interface=interface)

    def set_replacement(self, replacement: str) -> None:
        if replacement != self.state.replacement:
            self._invalidate(replacement=replacement)

    def set_sequence_chain(self, chain: str) -> None:
        self._render(sequence_chain=chain)

    def set_highlight(self, highlight: bool) -> None:
        self._render(highlight=highlight)

    def set_representation(self, representation: str) -> None:
        self._render(representation=representation)

    def predict(self) -> None:
        if self.state.busy:
            return
        residue = self.state.structure.residue(self.state.selected)
        request = PredictionRequest(
            self.state.structure.code,
            residue.key,
            residue.letter,
            self.state.replacement,
            self.state.cutoff,
        )
        revision = self._revision
        self._render(busy=True, prediction=None, error="")
        self.tasks.submit(
            lambda: self.backend.predict(request),
            lambda result: self._complete(revision, result),
            lambda message: self._fail(revision, message),
        )

    def _complete(self, revision: int, result: PredictionResult) -> None:
        if revision == self._revision:
            self._render(busy=False, prediction=result)

    def _fail(self, revision: int, message: str) -> None:
        if revision == self._revision:
            self._render(busy=False, error=message)
