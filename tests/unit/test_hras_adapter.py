import gzip
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from Bio.SeqUtils import seq3

from adapters.hras import HrasBackend
from backend.aa_array import CONTACTS
from contracts import PredictionRequest, ResidueKey


def contact_pdb(chain="B", changed_position=None, insertion=" "):
    """Small author-numbered structure; the extra insertion is not a contact site."""
    lines = []
    for serial, (number, (letter, _)) in enumerate(CONTACTS.items(), 1):
        name = seq3("A" if number == changed_position else letter).upper()
        lines.append(
            f"ATOM  {serial:5d}  CA  {name} {chain}{number:4d} "
            f"   {serial * 3.8:8.3f}{0.0:8.3f}{0.0:8.3f}  1.00 20.00           C  "
        )
    if insertion != " ":
        lines.append(
            f"ATOM     11  CA  ASP {chain}  33{insertion}"
            f"   {42.0:8.3f}{0.0:8.3f}{0.0:8.3f}  1.00 20.00           C  "
        )
    return "\n".join(lines) + "\nEND\n"


class HrasAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = HrasBackend()

    def test_real_mmcif_exposes_protein_and_the_exact_contact_table(self):
        structure = self.backend.load_structure()
        self.assertEqual(structure.code, "4EFL")
        self.assertEqual(structure.file_format, "mmcif")
        self.assertEqual([chain.id for chain in structure.chains], ["A"])
        self.assertEqual(len(structure.residues), 166)
        self.assertEqual({key.number for key in structure.contact_sites}, set(CONTACTS))
        self.assertEqual(structure.residue(ResidueKey("A", 33)).partners, ("K", "K"))
        self.assertFalse(structure.residue(ResidueKey("A", 11)).partners)

    def test_score_uses_backend_contacts_including_duplicate_partners(self):
        request = PredictionRequest("4EFL", ResidueKey("A", 33), "D", "A")
        result = self.backend.predict(request)
        # Two D-K contacts each change from -1.1 to 0 under the backend rule.
        self.assertAlmostEqual(result.predicted, 2.2)
        self.assertEqual(result.request, request)
        unchanged_energy = self.backend.predict(replace(request, replacement="E"))
        self.assertAlmostEqual(unchanged_energy.predicted, 0.0)

    def test_adapter_rejects_unsupported_requests_before_scoring(self):
        valid = PredictionRequest("4EFL", ResidueKey("A", 33), "D", "A")
        invalid = [
            replace(valid, residue=ResidueKey("A", 11), original="A", replacement="G"),
            replace(valid, residue=ResidueKey("B", 33)),
            replace(valid, residue=ResidueKey("A", 33, "A")),
            replace(valid, structure_code="OTHER"),
            replace(valid, original="E"),
            replace(valid, replacement="D"),
            replace(valid, replacement="X"),
        ]
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.backend.predict(request)

    def test_pdb_and_gzip_use_author_chain_and_residue_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix in (".pdb", ".pdb.gz"):
                with self.subTest(suffix=suffix):
                    path = Path(directory) / f"hras{suffix}"
                    opener = gzip.open if suffix.endswith("gz") else open
                    with opener(path, "wt") as output:
                        output.write(contact_pdb(insertion="A"))
                    backend = HrasBackend(path, "B")
                    structure = backend.load_structure()
                    self.assertEqual(len(structure.contact_sites), 10)
                    self.assertNotIn(ResidueKey("B", 33, "A"), structure.contact_sites)
                    result = backend.predict(
                        PredictionRequest("HRAS", ResidueKey("B", 33), "D", "A")
                    )
                    self.assertAlmostEqual(result.predicted, 2.2)

    def test_incompatible_structure_is_reported_at_load_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.pdb"
            path.write_text(contact_pdb(changed_position=33))
            with self.assertRaisesRegex(ValueError, "D33"):
                HrasBackend(path, "B")
            with self.assertRaisesRegex(ValueError, "Chain 'A'"):
                HrasBackend(path, "A")


if __name__ == "__main__":
    unittest.main()
