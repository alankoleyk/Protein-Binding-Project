"""
Backend entry point: given a mutation like "G12V", make sure a mutant
structure exists (generate it if not), then return its steric and
electromagnetic scores as {"steric": float, "em": float}.

Assumes these modules sit in the same folder as this file:
    mutant_struc_gen.py   (contains make_mutant)
    steric_score_basic.py (contains main, returns the relative clash score)
    aa_array.py           (contains binding_strength, CONTACTS)
"""

from pathlib import Path

import aa_array
import mutant_struc_gen
import steric_hin as steric

# ---- settings (adjust paths to your project layout) -----------------------
HERE = Path(__file__).resolve().parent   # folder containing this script
DATA_DIR = HERE / "data"                  # local data/ folder next to run_back.py
MUTANT_DIR = DATA_DIR / "mutants"

WT_RAS_FILE = DATA_DIR / "4EFL.cif"
RAS_CHAIN = "A"
PI3K_FILE = DATA_DIR / "pi3k_gamma_apo_isolated.pdb"
PI3K_CHAIN = "A"
TEMPLATE_FILE = DATA_DIR / "1HE8.cif"
TMPL_RAS_CHAIN, TMPL_PI3K_CHAIN = "B", "A"
# ---------------------------------------------------------------------------


def mutant_path(mutation):
    """Return the path where this mutation's structure file lives, e.g.
    data/mutants/4EFL_G12V.pdb (whether or not it exists yet)."""
    return MUTANT_DIR / f"{WT_RAS_FILE.stem}_{mutation}.pdb"


def ensure_mutant_structure(mutation):
    """
    Return the path to the mutant structure, generating it with make_mutant
    only if it is not already in the mutants folder.
    """
    path = mutant_path(mutation)
    if not path.exists():
        mutant_struc_gen.OUT_DIR = str(MUTANT_DIR)
        mutant_struc_gen.make_mutant(
            str(WT_RAS_FILE), mutation, RAS_CHAIN, out_name=path.name)
    return path


def steric_value(mutant_file):
    """
    Point the steric script at the template and at wild type + this mutant,
    then return the mutant's clash score relative to wild type (float).
    """
    steric.TEMPLATE_FILE = str(TEMPLATE_FILE)
    steric.TMPL_RAS_CHAIN = TMPL_RAS_CHAIN
    steric.TMPL_PI3K_CHAIN = TMPL_PI3K_CHAIN
    steric.MODELS = [
        ("wildtype", str(WT_RAS_FILE), RAS_CHAIN, str(PI3K_FILE), PI3K_CHAIN),
        ("mutant", str(mutant_file), RAS_CHAIN, str(PI3K_FILE), PI3K_CHAIN),
    ]
    return steric.main()


def em_value(mutation):
    """
    Return the interface energy change (mutant minus wild type) from aa_array.
    A mutation at a residue that is not in the CONTACTS table does not change
    the table's interface energy, so it returns 0.0.
    """
    _, pos, _ = aa_array.parse_mutation(mutation)
    if pos not in aa_array.CONTACTS:
        return 0.0
    return float(aa_array.binding_strength([mutation]))


def run_back(mutation):
    """
    Main function. Takes a mutation string such as "G12V" and returns
    {"steric": relative clash score, "em": interface energy change}.
    """
    mutation = mutation.strip().upper()
    mutant_file = ensure_mutant_structure(mutation)
    return {"steric": steric_value(mutant_file), "em": em_value(mutation)}


if __name__ == "__main__":
    print(run_back("D33E"))