import itertools
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selection.auditTlsfGames import colorize, verify


class TlsfGameAuditTests(unittest.TestCase):
    def test_colouring_empty_marks_preserves_max_even_acceptance(self):
        hoa = ("HOA: v1\nacc-name: parity max even 2\n"
               "Acceptance: 2 Fin(1) & Inf(0)\n--BODY--\n"
               "State: 0\n[t] 0\n[t] 0 {0}\n[t] 0 {1}\n--END--\n")
        coloured = colorize(hoa)
        self.assertIn("[t] 0 {1}\n[t] 0 {2}\n[t] 0 {3}", coloured)
        self.assertEqual(colorize(coloured), coloured)
        # Every periodic suffix over these three edge types has the same verdict.
        for length in (1, 2, 3):
            for cycle in itertools.product((None, 0, 1), repeat=length):
                before = 0 in cycle and 1 not in cycle
                after = max(1 if p is None else p + 2 for p in cycle) % 2 == 0
                self.assertEqual(before, after, cycle)

    def test_buchi_unmarked_suffix_remains_rejecting(self):
        hoa = ("HOA: v1\nacc-name: Buchi\nAcceptance: 1 Inf(0)\n"
               "--BODY--\nState: 0\n[t] 0\n[t] 0 {0}\n--END--\n")
        coloured = colorize(hoa)
        self.assertIn("acc-name: parity max even 3", coloured)
        self.assertIn("[t] 0 {1}\n[t] 0 {2}", coloured)
        for cycle in itertools.product((None, 0), repeat=3):
            self.assertEqual(0 in cycle, max(1 if p is None else 2 for p in cycle) % 2 == 0)


class HistoricalPairTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        release = self.root / "selection/releases/syntcomp26v2"
        release.mkdir(parents=True)
        (release / "tlsf-duplicate-pairs.csv").write_text(
            "path,params,representative,representative_params\nb.tlsf,n=2;u=1,a.tlsf,n=2\n")
        (self.root / "tlsf").mkdir()
        self.duplicates = self.root / "tlsf/duplicates.csv"
        self.duplicates.write_text(
            "group,level,path,params,representative,representative_params\n"
            "1,isomorphic,a.tlsf,n=2,a.tlsf,n=2\n1,isomorphic,b.tlsf,u=1;n=2,a.tlsf,n = 2\n")
        self.index = self.root / "selection/tlsf-game-audit.csv"
        self.index.write_text("instance,path,params\na,a.tlsf,n= 2\nb,b.tlsf,u=1; n=2\n")
        self.game = ("HOA: v1\nStates: 2\nStart: 0\nAP: 0\ncontrollable-AP: \n"
                     "acc-name: parity max even 3\nAcceptance: 3 Inf(2) | (Fin(1) & Inf(0))\n"
                     "--BODY--\nState: 0\n[t] 0 {2}\nState: 1\n[t] 1 {1}\n--END--\n")
        (self.root / "a.ehoa").write_text(self.game)
        (self.root / "b.ehoa").write_text(self.game)

    def verify(self):
        with patch("selection.auditTlsfGames.ROOT", self.root):
            verify(self.root)

    def test_missing_historical_endpoints_fail(self):
        for entries, missing in [("", "b.tlsf"), ("a,a.tlsf,n=2\n", "b.tlsf"),
                                 ("b,b.tlsf,n=2;u=1\n", "a.tlsf")]:
            with self.subTest(entries=entries):
                self.index.write_text("instance,path,params\n" + entries)
                with self.assertRaisesRegex(ValueError, "missing from historical TLSF game audit: .*" + missing):
                    self.verify()

    def test_ignores_new_group_sharing_an_indexed_endpoint(self):
        with self.duplicates.open("a") as table:
            table.write("2,identical,x.tlsf,,x.tlsf,\n2,identical,a.tlsf,n= 2,x.tlsf,\n")
        self.verify()

    def test_missing_historical_pair_in_duplicate_table_fails(self):
        self.duplicates.write_text("group,level,path,params,representative,representative_params\n")
        with self.assertRaisesRegex(ValueError, "missing from tlsf/duplicates.csv"):
            self.verify()

    def test_equivalent_parameter_spellings_reach_rooted_game_comparison(self):
        (self.root / "b.ehoa").write_text(self.game.replace("Start: 0", "Start: 1"))
        with self.assertRaisesRegex(ValueError, "rooted game equality not confirmed"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
