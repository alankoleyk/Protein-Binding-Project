"""
structure_parser.py

Parse PDB and mmCIF files with Biopython and expose the data as plain,
easily accessible attributes.

Usage
-----
    from structure_parser import parse_structure

    s = parse_structure("1abc.cif")        # or "1abc.pdb", "1abc.cif.gz"

    s.title, s.method, s.resolution        # metadata
    s.chain_ids                            # ['A', 'B']
    s.chains["A"].sequence                 # 'MKT...'
    s.chains["A"].residues[0].name         # 'MET'
    s.atoms[0].coord                       # (x, y, z)
    s.coords.shape                         # (n_atoms, 3) numpy array
    s.ligands                              # non-water hetero residues
    s.ca_coords["A"]                       # CA coordinates for chain A
    s.to_dataframe()                       # pandas DataFrame (if pandas installed)

CLI
---
    python structure_parser.py file1.cif file2.pdb
"""

from __future__ import annotations

import gzip
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
from Bio.PDB import MMCIFParser, PDBParser
from Bio.PDB.MMCIF2Dict import MMCIF2Dict
from Bio.PDB.Polypeptide import is_aa
from Bio.SeqUtils import seq1

# Nucleotide residue names -> one-letter codes
_NUCLEOTIDES = {
    "A": "A", "C": "C", "G": "G", "U": "U", "T": "T", "I": "I",
    "DA": "A", "DC": "C", "DG": "G", "DT": "T", "DU": "U", "DI": "I",
}


# --------------------------------------------------------------------------- #
# Data containers
# --------------------------------------------------------------------------- #
@dataclass
class AtomRecord:
    serial: int
    name: str
    element: str
    altloc: str
    coord: tuple[float, float, float]
    bfactor: float
    occupancy: float
    charge: Any  # may be None / str / float depending on source
    residue_name: str
    residue_number: int
    insertion_code: str
    chain_id: str
    model: int
    is_hetero: bool


@dataclass
class ResidueRecord:
    name: str
    number: int
    insertion_code: str
    chain_id: str
    model: int
    kind: str  # 'protein' | 'nucleic' | 'ligand' | 'water'
    hetfield: str
    atoms: list[AtomRecord] = field(default_factory=list)

    @property
    def one_letter(self) -> str:
        if self.kind == "protein":
            return seq1(self.name, undef_code="X")
        if self.kind == "nucleic":
            return _NUCLEOTIDES.get(self.name.strip(), "N")
        return ""

    @property
    def coords(self) -> np.ndarray:
        return np.array([a.coord for a in self.atoms], dtype=float)


@dataclass
class ChainRecord:
    id: str
    model: int
    residues: list[ResidueRecord] = field(default_factory=list)

    @property
    def polymer_residues(self) -> list[ResidueRecord]:
        return [r for r in self.residues if r.kind in ("protein", "nucleic")]

    @property
    def ligands(self) -> list[ResidueRecord]:
        return [r for r in self.residues if r.kind == "ligand"]

    @property
    def waters(self) -> list[ResidueRecord]:
        return [r for r in self.residues if r.kind == "water"]

    @property
    def sequence(self) -> str:
        """One-letter sequence of the *modelled* polymer residues."""
        return "".join(r.one_letter for r in self.polymer_residues)

    @property
    def atoms(self) -> list[AtomRecord]:
        return [a for r in self.residues for a in r.atoms]


@dataclass
class ParsedStructure:
    path: str
    file_format: str  # 'pdb' | 'mmcif'
    structure_id: str

    # Metadata (None when absent in the file)
    title: Optional[str] = None
    method: Optional[str] = None
    resolution: Optional[float] = None
    deposition_date: Optional[str] = None
    release_date: Optional[str] = None
    keywords: Optional[str] = None
    space_group: Optional[str] = None
    cell: Optional[dict[str, float]] = None  # a, b, c, alpha, beta, gamma

    # Raw dictionaries, in case you need something not surfaced above
    header: dict[str, Any] = field(default_factory=dict)  # Bio header (PDB) / {}
    mmcif_dict: dict[str, Any] = field(default_factory=dict)  # full MMCIF2Dict

    # Entities (mmCIF only): entity_id -> {"description", "type", "sequence", "chains"}
    entities: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Models / chains / residues / atoms
    n_models: int = 0
    models: dict[int, dict[str, ChainRecord]] = field(default_factory=dict)
    atoms: list[AtomRecord] = field(default_factory=list)  # all models, flat
    residues: list[ResidueRecord] = field(default_factory=list)  # all models, flat

    # The underlying Bio.PDB Structure object, for anything custom
    bio_structure: Any = None

    # ----- convenient views (first model by default) -----
    @property
    def chains(self) -> dict[str, ChainRecord]:
        return self.models.get(0, {})

    @property
    def chain_ids(self) -> list[str]:
        return list(self.chains)

    @property
    def sequences(self) -> dict[str, str]:
        return {cid: c.sequence for cid, c in self.chains.items()}

    @property
    def ligands(self) -> list[ResidueRecord]:
        return [r for c in self.chains.values() for r in c.ligands]

    @property
    def waters(self) -> list[ResidueRecord]:
        return [r for c in self.chains.values() for r in c.waters]

    @property
    def coords(self) -> np.ndarray:
        """(n_atoms, 3) coordinates of the first model."""
        return np.array(
            [a.coord for a in self.atoms if a.model == 0], dtype=float
        ).reshape(-1, 3)

    @property
    def ca_coords(self) -> dict[str, np.ndarray]:
        """Alpha-carbon coordinates per chain (first model)."""
        out: dict[str, np.ndarray] = {}
        for cid, chain in self.chains.items():
            pts = [
                a.coord
                for r in chain.residues
                if r.kind == "protein"
                for a in r.atoms
                if a.name == "CA"
            ]
            if pts:
                out[cid] = np.array(pts, dtype=float)
        return out

    @property
    def bfactors(self) -> np.ndarray:
        return np.array([a.bfactor for a in self.atoms if a.model == 0], dtype=float)

    def to_dataframe(self):
        """All atoms (all models) as a pandas DataFrame."""
        import pandas as pd  # optional dependency

        rows = []
        for a in self.atoms:
            d = a.__dict__.copy()
            d["x"], d["y"], d["z"] = d.pop("coord")
            rows.append(d)
        return pd.DataFrame(rows)

    def summary(self) -> str:
        lines = [
            f"File        : {self.path} ({self.file_format})",
            f"ID          : {self.structure_id}",
            f"Title       : {self.title}",
            f"Method      : {self.method}",
            f"Resolution  : {self.resolution}",
            f"Models      : {self.n_models}",
            f"Chains      : {', '.join(self.chain_ids) or '-'}",
            f"Atoms       : {len(self.atoms)} (all models)",
            f"Ligands     : {sorted({r.name for r in self.ligands}) or '-'}",
            f"Waters      : {len(self.waters)}",
        ]
        for cid, seq in self.sequences.items():
            shown = seq if len(seq) <= 60 else seq[:57] + "..."
            lines.append(f"  chain {cid:<3}: {len(seq):>5} res  {shown}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _detect_format(path: Path) -> str:
    suffixes = [s.lower() for s in path.suffixes]
    if suffixes and suffixes[-1] == ".gz":
        suffixes = suffixes[:-1]
    ext = suffixes[-1] if suffixes else ""
    if ext in (".cif", ".mmcif"):
        return "mmcif"
    if ext in (".pdb", ".ent"):
        return "pdb"
    # Fall back to sniffing content
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt") as fh:
        for line in fh:
            if line.startswith("data_"):
                return "mmcif"
            if line.startswith(("HEADER", "ATOM", "HETATM", "REMARK", "TITLE")):
                return "pdb"
    raise ValueError(f"Could not determine file format for {path}")


def _open_text(path: Path):
    return gzip.open(path, "rt") if path.suffix.lower() == ".gz" else open(path, "rt")


def _first(d: dict, key: str) -> Optional[str]:
    """MMCIF2Dict returns lists for most keys; return the first usable value."""
    v = d.get(key)
    if v is None:
        return None
    if isinstance(v, list):
        v = v[0] if v else None
    if v in (None, "?", "."):
        return None
    return v


def _to_float(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _classify(res) -> str:
    hetfield = res.id[0]
    if hetfield == "W" or res.get_resname().strip() in ("HOH", "WAT", "DOD"):
        return "water"
    name = res.get_resname().strip()
    if is_aa(res, standard=False) and hetfield == " ":
        return "protein"
    if name in _NUCLEOTIDES and hetfield == " ":
        return "nucleic"
    if hetfield != " ":
        return "ligand"
    return "protein" if is_aa(res, standard=False) else "nucleic"


def _mmcif_metadata(s: ParsedStructure, d: dict) -> None:
    s.title = _first(d, "_struct.title")
    s.method = _first(d, "_exptl.method")
    s.resolution = next(
        (
            r
            for r in (
                _to_float(_first(d, k))
                for k in (
                    "_refine.ls_d_res_high",
                    "_em_3d_reconstruction.resolution",
                    "_reflns.d_resolution_high",
                )
            )
            if r is not None
        ),
        None,
    )
    s.deposition_date = _first(d, "_pdbx_database_status.recvd_initial_deposition_date")
    s.release_date = _first(d, "_pdbx_audit_revision_history.revision_date")
    s.keywords = _first(d, "_struct_keywords.text")
    s.space_group = _first(d, "_symmetry.space_group_name_H-M")
    cell = {
        k: _to_float(_first(d, f"_cell.{src}"))
        for k, src in (
            ("a", "length_a"), ("b", "length_b"), ("c", "length_c"),
            ("alpha", "angle_alpha"), ("beta", "angle_beta"), ("gamma", "angle_gamma"),
        )
    }
    s.cell = cell if any(v is not None for v in cell.values()) else None

    # Entities
    def _as_list(key):
        v = d.get(key, [])
        return v if isinstance(v, list) else [v]

    ids = _as_list("_entity.id")
    descs = _as_list("_entity.pdbx_description")
    types = _as_list("_entity.type")
    poly_ids = _as_list("_entity_poly.entity_id")
    poly_seqs = _as_list("_entity_poly.pdbx_seq_one_letter_code_can")
    poly_strands = _as_list("_entity_poly.pdbx_strand_id")
    poly = {
        i: (seq.replace("\n", ""), strands.split(","))
        for i, seq, strands in zip(poly_ids, poly_seqs, poly_strands)
    }
    for i, desc, typ in zip(ids, descs, types):
        seq, chains = poly.get(i, (None, []))
        s.entities[i] = {
            "description": desc, "type": typ, "sequence": seq, "chains": chains,
        }


def _pdb_metadata(s: ParsedStructure, header: dict) -> None:
    s.header = dict(header)
    s.title = header.get("name") or None
    s.method = header.get("structure_method") or None
    s.resolution = header.get("resolution")
    s.deposition_date = header.get("deposition_date") or None
    s.release_date = header.get("release_date") or None
    s.keywords = header.get("keywords") or None


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def parse_structure(path: str | Path, structure_id: Optional[str] = None) -> ParsedStructure:
    """Parse a PDB or mmCIF file (optionally .gz) into a ParsedStructure."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    fmt = _detect_format(path)
    sid = structure_id or path.name.split(".")[0]

    with _open_text(path) as fh:
        if fmt == "mmcif":
            bio = MMCIFParser(QUIET=True).get_structure(sid, fh)
        else:
            bio = PDBParser(QUIET=True).get_structure(sid, fh)

    parsed = ParsedStructure(
        path=str(path), file_format=fmt, structure_id=sid, bio_structure=bio
    )

    if fmt == "mmcif":
        with _open_text(path) as fh:
            parsed.mmcif_dict = dict(MMCIF2Dict(fh))
        _mmcif_metadata(parsed, parsed.mmcif_dict)
        # Prefer the entry id from the file if present
        entry_id = _first(parsed.mmcif_dict, "_entry.id")
        if entry_id and structure_id is None:
            parsed.structure_id = entry_id
    else:
        _pdb_metadata(parsed, bio.header)

    for m_idx, model in enumerate(bio):
        parsed.models[m_idx] = {}
        for chain in model:
            c_rec = ChainRecord(id=chain.id, model=m_idx)
            for res in chain:
                r_rec = ResidueRecord(
                    name=res.get_resname().strip(),
                    number=res.id[1],
                    insertion_code=res.id[2].strip(),
                    chain_id=chain.id,
                    model=m_idx,
                    kind=_classify(res),
                    hetfield=res.id[0].strip(),
                )
                for atom in res:
                    a_rec = AtomRecord(
                        serial=atom.get_serial_number(),
                        name=atom.get_name(),
                        element=atom.element,
                        altloc=atom.get_altloc().strip(),
                        coord=tuple(float(x) for x in atom.coord),
                        bfactor=float(atom.get_bfactor()),
                        occupancy=float(atom.get_occupancy() or 0.0),
                        charge=getattr(atom, "pqr_charge", None),
                        residue_name=r_rec.name,
                        residue_number=r_rec.number,
                        insertion_code=r_rec.insertion_code,
                        chain_id=chain.id,
                        model=m_idx,
                        is_hetero=r_rec.kind in ("ligand", "water"),
                    )
                    r_rec.atoms.append(a_rec)
                    parsed.atoms.append(a_rec)
                c_rec.residues.append(r_rec)
                parsed.residues.append(r_rec)
            parsed.models[m_idx][chain.id] = c_rec
    parsed.n_models = len(parsed.models)
    return parsed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python structure_parser.py <file.pdb|file.cif> [...]")
    for f in sys.argv[1:]:
        print(parse_structure(f).summary())
        print()
