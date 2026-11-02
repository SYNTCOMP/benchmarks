import csv
from pathlib import Path
import tempfile
import unittest

from selection.checkSelection import check_tlsf_duplicates
from selection.manifest import Manifest


class TlsfDuplicateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.track = self.root / "tlsf"
        parametric = self.track / "family/parametric"
        parametric.mkdir(parents=True)
        (parametric / "source.tlsf").touch()
        (parametric / "source.csv").write_text(
            "n,refsize,status\n2,0,realizable\n3,0,realizable\n4,0,unknown\n")
        self.rows = [
            [1, "isomorphic", "family/parametric/source.tlsf", "n=2",
             "family/parametric/source.tlsf", "n=2"],
            [1, "isomorphic", "family/parametric/source.tlsf", "n=3",
             "family/parametric/source.tlsf", "n=2"],
        ]

    def check(self, rules="family/parametric/source.tlsf,n=3,0,duplicate\n"):
        with (self.track / "duplicates.csv").open("w", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["group", "level", "path", "params",
                             "representative", "representative_params"])
            writer.writerows(self.rows)
        manifest = self.root / "tlsf.csv"
        manifest.write_text("pattern,params,enabled,reason\n" + rules)
        return check_tlsf_duplicates(Manifest(manifest), self.track)

    def test_only_confirmed_parameters_are_excluded(self):
        self.assertEqual(self.check(), ([], []))
        manifest = Manifest(self.root / "tlsf.csv")
        self.assertTrue(manifest.is_enabled("family/parametric/source.tlsf", {"n": 4})[0])
        errors, _ = self.check("")
        self.assertEqual(len(errors), 1)
        self.assertIn("must be disabled", errors[0])

    def test_last_matching_manifest_rule_controls_exclusion(self):
        errors, _ = self.check(
            "family/*,,0,exclude\nfamily/parametric/source.tlsf,n=2,1,keep\n"
            "family/parametric/source.tlsf,n=3,1,override\n")
        self.assertEqual(len(errors), 1)

    def test_stale_parameter_and_missing_source_are_errors(self):
        self.rows[1][3] = "n=999"
        errors, _ = self.check()
        self.assertIn("no exact status CSV row", errors[0])
        self.rows[1][2] = "missing.tlsf"
        errors, _ = self.check()
        self.assertIn("invalid TLSF duplicate source", errors[0])

    def test_nonparametric_sources_and_disabled_representative(self):
        (self.track / "a.tlsf").touch()
        (self.track / "b.tlsf").touch()
        self.rows = [[1, "identical", "a.tlsf", "", "a.tlsf", ""],
                     [1, "identical", "b.tlsf", "", "a.tlsf", ""]]
        self.assertEqual(self.check("b.tlsf,,0,duplicate\n"), ([], []))
        errors, warnings = self.check("*.tlsf,,0,excluded\n")
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_unconfirmed_and_inconsistent_records_are_errors(self):
        self.rows[1][1] = "suspected"
        errors, _ = self.check()
        self.assertIn("malformed", errors[0])
        self.rows[1][1] = "identical"
        errors, _ = self.check()
        self.assertIn("inconsistent", errors[0])


if __name__ == "__main__":
    unittest.main()
