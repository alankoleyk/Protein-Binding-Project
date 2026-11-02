import numpy as np
import pandas as pd

AA = list("ACDEFGHIKLMNPQRSTVWY")

# Kyte-Doolittle hydrophobicity and charge (inputs to the placeholder rule)
KD = dict(A=1.8, R=-4.5, N=-3.5, D=-3.5, C=2.5, Q=-3.5, E=-3.5, G=-0.4,
          H=-3.2, I=4.5, L=3.8, K=-3.9, M=1.9, F=2.8, P=-1.6, S=-0.8,
          T=-0.7, W=-0.9, Y=-1.3, V=4.2)
CHARGE = {a: 0 for a in AA}
CHARGE.update(K=1, R=1, D=-1, E=-1)
POLAR = set("STNQHYWKRDE")


def pair_energy(a, b):
    """Placeholder rule: hydrophobic packing + charge + polar."""
    e = 0.0
    if KD[a] > 0 and KD[b] > 0:
        e -= 0.05 * KD[a] * KD[b]
    e += 0.8 * CHARGE[a] * CHARGE[b]
    if a in POLAR and b in POLAR:
        e -= 0.3
    return e


# Build the table: rows = Ras residue, columns = PI3K residue
matrix = pd.DataFrame(
    [[pair_energy(a, b) for b in AA] for a in AA],
    index=AA, columns=AA,
)


def binding(ras_aa, pi3k_aa):
    return matrix.loc[ras_aa, pi3k_aa]

print(binding("D", "R"))

CONTACTS = {
    25: ("Q", ["L", "S"]),
    33: ("D", ["K", "K"]),   # K255, K251 (K251 uncertain)
    36: ("I", ["F"]),
    37: ("E", ["T", "K"]),
    38: ("D", ["K"]),        # K251
    39: ("S", ["S"]),        # S230
    40: ("Y", ["Q"]),
    41: ("R", ["T"]),
    63: ("E", ["K"]),        # K234
    64: ("Y", ["K"]),        # K234
}

def parse_mutation(m):
    m = m.strip().upper()
    wt, pos, new = m[0], m[1:-1], m[-1]
    if not pos.isdigit() or wt not in AA or new not in AA:
        raise ValueError(f"Bad mutation format: {m!r} (expected like 'D33E')")
    return wt, int(pos), new


def binding_strength(mutations):
    """Mutant minus wild-type interface energy. Negative = tighter."""
    mutated = {}
    for m in mutations:
        wt, pos, new = parse_mutation(m)
        if pos not in CONTACTS:
            raise ValueError(f"{m}: residue {pos} is not a contact residue")
        if CONTACTS[pos][0] != wt:
            raise ValueError(f"{m}: residue {pos} is {CONTACTS[pos][0]} in the contact table, not {wt}")
        if pos in mutated:
            raise ValueError(f"Residue {pos} mutated more than once")
        mutated[pos] = new

    wt_total = mut_total = 0.0
    for pos, (wt_aa, partners) in CONTACTS.items():
        new_aa = mutated.get(pos, wt_aa)
        for p in partners:
            wt_total += binding(wt_aa, p)
            mut_total += binding(new_aa, p)
    return mut_total - wt_total

binding_strength(["Q25L"])

