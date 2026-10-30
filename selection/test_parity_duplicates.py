import contextlib
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selection.checkSelection import check_parity_duplicates, main
from selection.manifest import Manifest


class ParityDuplicateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="parity-duplicate-check-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.track = self.root / "parity"
        self.track.mkdir()
        for name in ("representative.ehoa", "duplicate.ehoa", "replacement.ehoa", "suspected.ehoa"):
            (self.track / name).touch()
        self.duplicates = self.track / "duplicates.csv"
        self.write_duplicates([
            (1, "identical", "representative.ehoa", "representative.ehoa"),
            (1, "identical", "duplicate.ehoa", "representative.ehoa"),
            (2, "suspected", "representative.ehoa", "representative.ehoa"),
            (2, "suspected", "suspected.ehoa", "representative.ehoa"),
        ])

    def write_duplicates(self, rows):
        with self.duplicates.open("w", newline="") as output:
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(("group", "level", "path", "representative"))
            writer.writerows(rows)

    def manifest(self, rows="duplicate.ehoa,,0,duplicate-of:representative.ehoa\n"):
        path = self.root / "parity.csv"
        path.write_text("pattern,params,enabled,reason\n" + rows)
        return Manifest(path)

    def check(self, rows="duplicate.ehoa,,0,duplicate-of:representative.ehoa\n"):
        return check_parity_duplicates(self.manifest(rows), self.track)

    def test_confirmed_duplicates_must_be_disabled_but_suspected_stay_enabled(self):
        self.assertEqual(self.check(), ([], []))
        errors, warnings = self.check("")
        self.assertEqual(len(errors), 1)
        self.assertIn("duplicate.ehoa must be disabled", errors[0])
        self.assertEqual(warnings, [])
        self.assertTrue(self.manifest().is_enabled("suspected.ehoa")[0])

    def test_isomorphic_duplicates_also_require_exclusion(self):
        self.write_duplicates([(1, "isomorphic", "duplicate.ehoa", "representative.ehoa")])
        errors, _ = self.check("")
        self.assertEqual(len(errors), 1)
        self.assertEqual(self.check(), ([], []))

    def test_effective_enabledness_respects_globs_and_overrides(self):
        self.assertEqual(self.check("duplicat*,,0,exclude\n"), ([], []))
        errors, _ = self.check("duplicat*,,0,exclude\nduplicate.ehoa,,1,override\n")
        self.assertEqual(len(errors), 1)

    def test_disabled_representative_without_replacement_warns(self):
        errors, warnings = self.check(
            "duplicate.ehoa,,0,duplicate-of:representative.ehoa\n"
            "representative.ehoa,,0,too-easy\n")
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("representative.ehoa has no enabled replacement", warnings[0])
        self.assertIn("too-easy", warnings[0])

    def test_replacement_chains_end_at_enabled_file(self):
        self.assertEqual(self.check(
            "duplicate.ehoa,,0,duplicate-of:representative.ehoa\n"
            "representative.ehoa,,0,duplicate-of:replacement.ehoa\n"), ([], []))

    def test_duplicate_can_explicitly_designate_replacement(self):
        self.assertEqual(self.check(
            "duplicate.ehoa,,0,duplicate-of:replacement.ehoa\n"
            "representative.ehoa,,0,too-easy\n"), ([], []))

    def test_non_benchmark_replacements_warn_at_every_step(self):
        (self.track / "readme.md").touch()
        (self.track / "other.tlsf").touch()
        (self.track / "directory.ehoa").mkdir()
        for replacement in ("readme.md", "other.tlsf", "directory.ehoa", "missing.ehoa"):
            cases = [
                f"duplicate.ehoa,,0,duplicate-of:{replacement}\n"
                "representative.ehoa,,0,too-easy\n",
                "duplicate.ehoa,,0,duplicate-of:representative.ehoa\n"
                f"representative.ehoa,,0,duplicate-of:{replacement}\n",
            ]
            for rows in cases:
                with self.subTest(replacement=replacement, rows=rows):
                    errors, warnings = self.check(rows)
                    self.assertEqual(errors, [])
                    self.assertEqual(len(warnings), 1)
                    self.assertIn("has no enabled replacement", warnings[0])

    def test_recorded_representative_must_be_a_benchmark(self):
        (self.track / "readme.md").touch()
        self.write_duplicates([(1, "identical", "duplicate.ehoa", "readme.md")])
        errors, warnings = self.check("duplicate.ehoa,,0,excluded\n")
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("readme.md has no enabled replacement", warnings[0])

    def test_replacements_must_stay_within_the_parity_track(self):
        outside = self.root / "other-track/outside.ehoa"
        outside.parent.mkdir()
        outside.touch()
        (self.track / "outside-link.ehoa").symlink_to(outside)
        for replacement in ("../other-track/outside.ehoa", str(outside), "outside-link.ehoa"):
            with self.subTest(replacement=replacement):
                errors, warnings = self.check(
                    f"duplicate.ehoa,,0,duplicate-of:{replacement}\n"
                    "representative.ehoa,,0,too-easy\n")
                self.assertEqual(errors, [])
                self.assertEqual(len(warnings), 1)

    def test_replacement_enabledness_uses_last_matching_glob_and_override(self):
        rows = ("duplicate.ehoa,,0,duplicate-of:representative.ehoa\n"
                "representative.ehoa,,0,duplicate-of:replacement.ehoa\n"
                "replace*,,0,excluded family\n")
        errors, warnings = self.check(rows)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(self.check(rows + "replacement.ehoa,,1,re-enabled\n"), ([], []))

    def test_missing_cyclic_and_disabled_replacements_warn(self):
        cases = [
            "representative.ehoa,,0,duplicate-of:missing.ehoa\n",
            "representative.ehoa,,0,duplicate-of:duplicate.ehoa\n",
            "representative.ehoa,,0,duplicate-of:replacement.ehoa\n"
            "replacement.ehoa,,0,excluded\n",
        ]
        for rows in cases:
            with self.subTest(rows=rows):
                errors, warnings = self.check(
                    "duplicate.ehoa,,0,duplicate-of:representative.ehoa\n" + rows)
                self.assertFalse(errors)
                self.assertEqual(len(warnings), 1)

    def test_validation_never_opens_benchmark_contents(self):
        manifest = self.manifest()
        original = Path.open

        def guarded(path, *args, **kwargs):
            if path.suffix == ".ehoa":
                self.fail("checker must not read benchmark contents")
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", guarded):
            self.assertEqual(check_parity_duplicates(manifest, self.track), ([], []))

    def test_missing_or_malformed_duplicate_table_is_an_error(self):
        for contents in ("bad,header\n", "group,level,path,representative\n1,identical,x\n",
                         "group,level,path,representative\n1,typo,x,y\n"):
            with self.subTest(contents=contents):
                self.duplicates.write_text(contents)
                errors, _ = self.check()
                self.assertEqual(len(errors), 1)
                self.assertIn("duplicates.csv", errors[0])
        self.duplicates.unlink()
        errors, _ = self.check()
        self.assertEqual(len(errors), 1)

    def test_checker_exit_status_includes_duplicate_errors_and_warning_only_success(self):
        selection = self.root / "selection"
        selection.mkdir()
        for track in ("tlsf", "tlsf-fin"):
            (self.root / track).mkdir()
            (selection / (track + ".csv")).write_text("pattern,params,enabled,reason\n")
        parity_manifest = selection / "parity.csv"
        with patch("selection.checkSelection.__file__", str(selection / "checkSelection.py")):
            parity_manifest.write_text(self.manifest("").path.read_text())
            with contextlib.redirect_stdout(io.StringIO()) as log:
                self.assertEqual(main(), 1)
            self.assertIn("confirmed duplicate duplicate.ehoa", log.getvalue())
            parity_manifest.write_text(self.manifest(
                "duplicate.ehoa,,0,duplicate-of:representative.ehoa\n"
                "representative.ehoa,,0,too-easy\n").path.read_text())
            with contextlib.redirect_stdout(io.StringIO()) as log:
                self.assertEqual(main(), 0)
            self.assertIn("0 errors, 1 warnings", log.getvalue())


if __name__ == "__main__":
    unittest.main()
