"""Real, precomputed 1BRS geometry with explicitly invented prediction fixtures."""

import json
from pathlib import Path

from contracts import (
    Chain,
    Neighbor,
    PredictionRequest,
    PredictionResult,
    Residue,
    ResidueKey,
    Structure,
)

DATA = Path(__file__).with_name("demo_residues.json")
STRUCTURE_PATH = Path(__file__).resolve().parents[1] / "resources/demo/1brs.pdb"

# These pairs are invented UI examples, not model outputs or experimental measurements.
PREDICTIONS = {
    ("D", 39, "A"): (3.2, 3.7),
    ("D", 39, "N"): (1.65, 2.0),
    ("A", 83, "A"): (2.15, 2.75),
    ("A", 87, "A"): (1.1, 1.65),
    ("D", 35, "A"): (2.4, 2.15),
    ("A", 59, "A"): (1.85, 2.1),
    ("D", 29, "A"): (0.8, 0.4),
    ("D", 38, "F"): (0.45, -0.1),
    ("A", 102, "A"): (2.9, 3.35),
    ("D", 76, "A"): (-0.25, -0.55),
    ("A", 27, "A"): (0.65, 1.2),
    ("D", 44, "A"): (-0.1, 0.3),
}


class DemoBackend:
    def load_structure(self) -> Structure:
        records = json.loads(DATA.read_text())
        residues = tuple(
            Residue(
                ResidueKey(record["chain"], record["number"]),
                record["name"],
                record["letter"],
                tuple(
                    Neighbor(
                        ResidueKey(neighbor["chain"], neighbor["number"]),
                        neighbor["name"],
                        neighbor["distance"],
                    )
                    for neighbor in record["neighbors"]
                ),
            )
            for record in records
        )
        return Structure(
            code="1BRS",
            title="Barnase × Barstar",
            description="Bacillus amyloliquefaciens · X-ray · 2.00 Å",
            path=STRUCTURE_PATH,
            chains=(Chain("A", "Barnase", "#62d7bf"), Chain("D", "Barstar", "#a699ef")),
            residues=residues,
            initial_selection=ResidueKey("D", 39),
        )

    def find_interface(self, structure: Structure, cutoff: float) -> tuple[ResidueKey, ...]:
        return tuple(
            residue.key
            for residue in structure.residues
            if any(neighbor.distance <= cutoff for neighbor in residue.neighbors)
        )

    def predict(self, request: PredictionRequest) -> PredictionResult:
        values = PREDICTIONS.get(
            (request.residue.chain, request.residue.number, request.replacement)
        )
        if values is None:
            return PredictionResult(request, None, None)
        return PredictionResult(request, *values)
