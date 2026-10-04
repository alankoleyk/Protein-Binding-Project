"""The GUI's data and ports; independent of Qt and the scientific backend."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ResidueKey:
    chain: str
    number: int
    insertion: str = ""


@dataclass(frozen=True)
class Neighbor:
    key: ResidueKey
    name: str
    distance: float


@dataclass(frozen=True)
class Residue:
    key: ResidueKey
    name: str
    letter: str
    neighbors: tuple[Neighbor, ...]


@dataclass(frozen=True)
class Chain:
    id: str
    name: str
    color: str


@dataclass(frozen=True)
class Structure:
    code: str
    title: str
    description: str
    path: Path
    chains: tuple[Chain, ...]
    residues: tuple[Residue, ...]
    initial_selection: ResidueKey

    def residue(self, key: ResidueKey) -> Residue:
        return next(residue for residue in self.residues if residue.key == key)


@dataclass(frozen=True)
class PredictionRequest:
    structure_code: str
    residue: ResidueKey
    original: str
    replacement: str
    cutoff: float

    @property
    def label(self) -> str:
        return f"{self.original}{self.residue.number}{self.residue.insertion}{self.replacement}"


@dataclass(frozen=True)
class PredictionResult:
    request: PredictionRequest
    predicted: float | None
    experimental: float | None


@dataclass(frozen=True)
class ViewState:
    structure: Structure
    selected: ResidueKey
    interface: tuple[ResidueKey, ...]
    cutoff: float = 5.0
    replacement: str = "A"
    sequence_chain: str = "D"
    highlight: bool = True
    representation: str = "cartoon"
    prediction: PredictionResult | None = None
    busy: bool = False
    error: str = ""

    @property
    def request(self) -> PredictionRequest:
        return PredictionRequest(
            self.structure.code,
            self.selected,
            self.structure.residue(self.selected).letter,
            self.replacement,
            self.cutoff,
        )


class ViewPort(Protocol):
    def render(self, state: ViewState) -> None: ...


class BackendPort(Protocol):
    def load_structure(self) -> Structure: ...

    def find_interface(self, structure: Structure, cutoff: float) -> tuple[ResidueKey, ...]: ...

    def predict(self, request: PredictionRequest) -> PredictionResult: ...


class TaskPort(Protocol):
    def submit(
        self,
        work: Callable[[], PredictionResult],
        succeeded: Callable[[PredictionResult], None],
        failed: Callable[[str], None],
    ) -> None: ...
