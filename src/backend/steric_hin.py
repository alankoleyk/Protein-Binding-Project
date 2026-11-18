RAS_CIF, RAS_CHAIN = "data/4EFL.cif", "A"
PI3K_FILE, PI3K_CHAIN = "data/pi3k_gamma_apo_isolated.pdb", "A"
TEMPLATE_CIF = "data/1HE8.cif"


"""
Steric clash score for HRas / PI3K bound exactly as in a template complex.

Each protein is superimposed (CA atoms) onto its chain in the template
complex, which places the pair in the template's bound orientation. The
steric clash is then scored once, with no further movement of either protein.
Designed so that mutant models (e.g. AlphaFold) can be framed on the same
template and compared with a reference (e.g. wild type).
Requires: biopython, numpy, scipy
"""

import numpy as np
from scipy.spatial import cKDTree
from Bio.PDB import MMCIFParser, PDBParser, Superimposer
from Bio.Align import PairwiseAligner
from Bio.Data.IUPACData import protein_letters_3to1

# ---- user settings --------------------------------------------------------
TEMPLATE_FILE = "data/1HE8.cif"
TMPL_RAS_CHAIN, TMPL_PI3K_CHAIN = "B", "A"
TOLERANCE = 0.4   # allowed vdW overlap (A) before an atom pair counts as a clash

# Structures to score: (label, ras_file, ras_chain, pi3k_file, pi3k_chain)
# The FIRST entry is the reference (e.g. wild type); its relative score = 1.0


MODELS = [
    ("wildtype", "data/4EFL.cif", "A", "data/pi3k_gamma_apo_isolated.pdb", "A"),
    # ("mutant1", "hras_mut1.cif", "A", "pi3k_mut1.pdb", "A"),
]
# ---------------------------------------------------------------------------

VDW = {"C": 1.70, "N": 1.55, "O": 1.52, "S": 1.80}  # Bondi radii (A)


def get_chain(path, chain_id):
    """
    Parse a .cif or .pdb file (parser chosen by file extension) and return
    the requested chain of the first model.
    """
    if path.lower().endswith(".pdb"):
        parser = PDBParser(QUIET=True)
    else:
        parser = MMCIFParser(QUIET=True)
    return parser.get_structure("s", path)[0][chain_id]


def get_residues(chain):
    """Return the standard amino-acid residues of a chain (no water/ligands)."""
    return [r for r in chain if r.id[0] == " "]


def get_heavy_atoms(chain):
    """Return (coords Nx3, vdW radii N) for all non-hydrogen atoms of a chain."""
    coords, radii = [], []
    for res in get_residues(chain):
        for atom in res:
            # PDB files may lack the element column; fall back to atom name
            el = (atom.element or atom.get_id()[0]).strip().upper()
            if el in ("H", "D"):
                continue
            coords.append(atom.coord)
            radii.append(VDW.get(el, 1.70))
    return np.array(coords), np.array(radii)


def get_sequence(residues):
    """Return the one-letter sequence string for a list of residues."""
    return "".join(protein_letters_3to1.get(r.get_resname().title(), "X")
                   for r in residues)


def matched_ca_atoms(fixed_chain, moving_chain):
    """
    Sequence-align two chains and return two equal-length lists of CA atoms
    (fixed, moving) for the aligned residue pairs. Alignment lets mutants and
    models with different numbering still map onto the template.
    """
    fixed_res, moving_res = get_residues(fixed_chain), get_residues(moving_chain)
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aln = aligner.align(get_sequence(fixed_res), get_sequence(moving_res))[0]
    fixed_ca, moving_ca = [], []
    for (f0, f1), (m0, m1) in zip(*aln.aligned):
        for i, j in zip(range(f0, f1), range(m0, m1)):
            if "CA" in fixed_res[i] and "CA" in moving_res[j]:
                fixed_ca.append(fixed_res[i]["CA"])
                moving_ca.append(moving_res[j]["CA"])
    return fixed_ca, moving_ca


def place_on_template(chain, template_chain):
    """
    Superimpose `chain` onto `template_chain` using aligned CA atoms and
    return (heavy-atom coords in the template frame, vdW radii, CA RMSD).
    """
    fixed_ca, moving_ca = matched_ca_atoms(template_chain, chain)
    sup = Superimposer()
    sup.set_atoms(fixed_ca, moving_ca)
    rot, tran = sup.rotran
    coords, radii = get_heavy_atoms(chain)
    return coords @ rot + tran, radii, sup.rms


def steric_score(coords_a, radii_a, coords_b, radii_b, tolerance=TOLERANCE):
    """
    Sum of squared vdW overlaps between all atom pairs of two sets.
    overlap = max(0, (r_i + r_j - tolerance) - distance)
    Returns (raw_score, number_of_clashing_pairs).
    """
    tree = cKDTree(coords_b)
    cutoff = radii_a.max() + radii_b.max()
    score, n_clash = 0.0, 0
    for i, neighbours in enumerate(tree.query_ball_point(coords_a, cutoff)):
        if not neighbours:
            continue
        d = np.linalg.norm(coords_b[neighbours] - coords_a[i], axis=1)
        overlap = (radii_a[i] + radii_b[neighbours] - tolerance) - d
        overlap = overlap[overlap > 0]
        score += np.sum(overlap ** 2)
        n_clash += len(overlap)
    return score, n_clash


def score_model(ras_file, ras_chain, pi3k_file, pi3k_chain):
    """
    Place HRas and PI3K on the template and return
    (raw_score, n_clash, ras_rmsd, pi3k_rmsd).
    """
    t_ras = get_chain(TEMPLATE_FILE, TMPL_RAS_CHAIN)
    t_pi3k = get_chain(TEMPLATE_FILE, TMPL_PI3K_CHAIN)
    ras_xyz, ras_r, ras_rmsd = place_on_template(
        get_chain(ras_file, ras_chain), t_ras)
    pi3k_xyz, pi3k_r, pi3k_rmsd = place_on_template(
        get_chain(pi3k_file, pi3k_chain), t_pi3k)
    raw, n_clash = steric_score(ras_xyz, ras_r, pi3k_xyz, pi3k_r)
    return raw, n_clash, ras_rmsd, pi3k_rmsd


def main(verbose=False):
    """
    Score the models in MODELS and return one float: the LAST model's raw
    clash score divided by the FIRST model's (wild type). With only wild type
    listed this returns 1.0; with a mutant added it returns mutant / wild type.
    Set verbose=True to also print a summary table.
    """
    results = [(label, *score_model(rf, rc, pf, pc))
               for label, rf, rc, pf, pc in MODELS]
    ref = max(results[0][1], 1e-6)
    if verbose:
        print("label        raw_score  relative  n_clash  rmsd_ras  rmsd_pi3k")
        for label, raw, n, r1, r2 in results:
            print(f"{label:12s} {raw:9.3f}  {raw / ref:8.3f}  {n:7d}  "
                  f"{r1:8.2f}  {r2:9.2f}")
    return float(results[-1][1] / ref)
 
 
if __name__ == "__main__":
    print(main(verbose=True))