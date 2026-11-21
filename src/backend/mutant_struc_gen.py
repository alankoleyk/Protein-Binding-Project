"""
Create a point-mutant structure from a wild-type structure with PDBFixer.

The backbone is left untouched, so the mutant stays in the same frame as the
wild type. The new side chain is placed in a default rotamer and its
neighbours are NOT repacked.
Requires: pdbfixer, openmm  (conda install -c conda-forge pdbfixer)
"""

import os

from pdbfixer import PDBFixer
from openmm.app import PDBFile

OUT_DIR = os.path.join("data", "mutants")   # all mutant files are written here

ONE_TO_THREE = {
    "A": "ALA", "R": "ARG", "N": "ASN", "D": "ASP", "C": "CYS",
    "Q": "GLN", "E": "GLU", "G": "GLY", "H": "HIS", "I": "ILE",
    "L": "LEU", "K": "LYS", "M": "MET", "F": "PHE", "P": "PRO",
    "S": "SER", "T": "THR", "W": "TRP", "Y": "TYR", "V": "VAL",
}


def to_fixer_format(mutation):
    """
    Convert a mutation string to PDBFixer's 'WTRES-NUMBER-NEWRES' format.
    Accepts one-letter ('G12V') or three-letter ('GLY-12-VAL') notation.
    """
    if "-" in mutation:
        return mutation.upper()
    wt, number, new = mutation[0].upper(), mutation[1:-1], mutation[-1].upper()
    return f"{ONE_TO_THREE[wt]}-{number}-{ONE_TO_THREE[new]}"


def make_mutant(wt_file, mutations, chain_id, out_name=None):
    """
    Mutate residues in a wild-type structure and write the result as a PDB.

    wt_file   : path to the wild-type structure; .cif (e.g. "data/4EFL.cif") or
                .pdb, detected from the file extension
    mutations : one mutation string or a list, e.g. "G12V" or ["G12V", "Q61L"]
                (numbers must match the residue numbering in wt_file)
    chain_id  : chain that contains the residues to mutate, e.g. "A"
    out_name  : file name for the mutant .pdb (original residue numbering
                kept). Written into OUT_DIR (data/mutants). If omitted, a name
                is built from the input file and mutations, e.g.
                'hras_G12V.pdb'.

    Returns the full output path (inside OUT_DIR) so it can be passed
    straight into the scoring script.
    """
    if isinstance(mutations, str):
        mutations = [mutations]
    if out_name is None:
        stem = os.path.splitext(os.path.basename(wt_file))[0]
        out_name = f"{stem}_{'_'.join(mutations)}.pdb"
    os.makedirs(OUT_DIR, exist_ok=True)
    out_file = os.path.join(OUT_DIR, os.path.basename(out_name))

    fixer = PDBFixer(filename=wt_file)
    fixer.applyMutations([to_fixer_format(m) for m in mutations], chain_id)

    # rebuild side-chain atoms for the mutated residues only; do not add
    # any residues that are missing from the original structure
    fixer.findMissingResidues()
    fixer.missingResidues = {}
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()

    with open(out_file, "w") as fh:
        PDBFile.writeFile(fixer.topology, fixer.positions, fh, keepIds=True)
    return out_file


if __name__ == "__main__":
    print(make_mutant("data/4EFL.cif", "G12V", "A"))