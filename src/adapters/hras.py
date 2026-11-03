"""Translate the team's structure parser and fixed HRas contact table for the GUI."""

from pathlib import Path

from backend.aa_array import AA, CONTACTS, binding_strength
from backend.structure_parser import parse_structure
from contracts import Chain, PredictionRequest, PredictionResult, Residue, ResidueKey, Structure

DEFAULT_STRUCTURE = Path(__file__).resolve().parents[2] / "reference/hras_project/4EFL.cif"


class HrasBackend:
    def __init__(self, path: Path = DEFAULT_STRUCTURE, chain_id: str = "A"):
        parsed = parse_structure(path)
        if chain_id not in parsed.chains:
            raise ValueError(f"Chain {chain_id!r} is not in {path.name}.")
        protein = [r for r in parsed.chains[chain_id].residues if r.kind == "protein"]
        by_key = {ResidueKey(chain_id, r.number, r.insertion_code): r for r in protein}
        for number, (original, _) in CONTACTS.items():
            key = ResidueKey(chain_id, number)
            if key not in by_key or by_key[key].one_letter != original:
                raise ValueError(
                    f"Chain {chain_id} must contain {original}{number} to match the HRas contact table."
                )

        residues = tuple(
            Residue(
                key=key,
                name=r.name,
                letter=r.one_letter,
                partners=tuple(CONTACTS[r.number][1])
                if r.number in CONTACTS and not r.insertion_code
                else (),
            )
            for key, r in by_key.items()
        )
        description = [parsed.method] if parsed.method else []
        if parsed.resolution is not None:
            description.append(f"{parsed.resolution:.2f} Å")
        description.append(f"Chain {chain_id}")
        self.structure = Structure(
            code=parsed.structure_id.upper(),
            title="H-Ras",
            description=" · ".join(description),
            path=Path(parsed.path),
            file_format=parsed.file_format,
            chains=(Chain(chain_id, "H-Ras", "#62d7bf"),),
            residues=residues,
            initial_selection=ResidueKey(chain_id, next(iter(CONTACTS))),
        )

    def load_structure(self) -> Structure:
        return self.structure

    def predict(self, request: PredictionRequest) -> PredictionResult:
        if request.structure_code != self.structure.code:
            raise ValueError("The prediction request does not match the loaded structure.")
        if request.residue not in self.structure.contact_sites:
            raise ValueError("Mutations are limited to the predefined HRas contact sites.")
        if request.replacement not in AA or request.replacement == request.original:
            raise ValueError("Choose a different standard amino acid for the mutation.")
        # The backend checks the original letter against CONTACTS as well.
        score = binding_strength([request.label])
        return PredictionResult(request, float(score))
