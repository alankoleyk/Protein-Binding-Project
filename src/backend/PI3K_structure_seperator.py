'''
this script takes the PI3k -Gamma strcuture bound to IPI-549 inhibitor, the only one available due to the volatility of the 
binding pocket on PI3K, and strips away the inhibitor structure, leaving only PI3K in its active form

'''

import os
from Bio.PDB import MMCIFParser, PDBIO, Select
from Bio.PDB.Polypeptide import is_aa


class ProteinOnly(Select):
    """Keep only amino acid residues; drop ligands, water, ions."""

    def accept_residue(self, residue):
        return is_aa(residue, standard=False)


# Paths
data_dir = "data"
input_file = os.path.join(data_dir, "6XRL.cif")   # match your actual file name
output_file = os.path.join(data_dir, "pi3k_gamma_apo_isolated.pdb")

if not os.path.exists(input_file):
    raise FileNotFoundError(f"Could not find {input_file}. Current directory: {os.getcwd()}")

parser = MMCIFParser(QUIET=True)
structure = parser.get_structure("PI3K", input_file)

io = PDBIO()
io.set_structure(structure)
io.save(output_file, select=ProteinOnly())

print(f"Saved apo structure to {output_file}")
io = PDBIO()
io.set_structure(structure)
io.save("pi3k_gamma_apo_isolated.pdb", select=ProteinOnly())