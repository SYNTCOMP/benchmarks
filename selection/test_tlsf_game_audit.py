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

    def test_unrooted_isomorphism_does_not_justify_a_tlsf_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "selection").mkdir()
            (root / "tlsf").mkdir()
            games = root / "games"
            games.mkdir()
            (root / "selection/tlsf-game-audit.csv").write_text(
                "instance,path,params\na.tlsf,a.tlsf,\nb.tlsf,b.tlsf,\n")
            (root / "tlsf/duplicates.csv").write_text(
                "group,level,path,params,representative,representative_params\n"
                "1,isomorphic,a.tlsf,,a.tlsf,\n1,isomorphic,b.tlsf,,a.tlsf,\n")
            hoa = ("HOA: v1\nStates: 2\nStart: {start}\nAP: 0\ncontrollable-AP: \n"
                   "acc-name: parity max even 3\nAcceptance: 3 Inf(2) | (Fin(1) & Inf(0))\n"
                   "--BODY--\nState: 0\n[t] 0 {{2}}\nState: 1\n[t] 1 {{1}}\n--END--\n")
            (games / "a.tlsf.ehoa").write_text(hoa.format(start=0))
            (games / "b.tlsf.ehoa").write_text(hoa.format(start=1))
            with patch("selection.auditTlsfGames.ROOT", root):
                with self.assertRaisesRegex(ValueError, "rooted game equality not confirmed"):
                    verify(games)


if __name__ == "__main__":
    unittest.main()
