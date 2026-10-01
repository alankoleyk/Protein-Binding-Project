from Bio.PDB import MMCIFParser

parser = MMCIFParser()
hras_structure = parser.get_structure("4EFL", "4EFL.cif")
residues = list(hras_structure.get_residues())
chain = list(hras_structure.get_chains())[0]
#print(residues)
for i in chain:
    print(residues)