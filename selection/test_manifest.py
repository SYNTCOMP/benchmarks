import contextlib
import importlib.util
import io
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selection.checkSelection import check_manifest, main
from selection.manifest import Manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="selection-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.track = self.root / "tlsf"
        self.template = self.track / "family/parametric/example.tlsf"
        self.template.parent.mkdir(parents=True)
        self.template.write_text(
            'INFO { TITLE: "test" DESCRIPTION: "test" SEMANTICS: Mealy TARGET: Mealy }\n'
            'GLOBAL { PARAMETERS { n = 1; m = 2; } }\n'
            'MAIN { INPUTS { a[n]; } OUTPUTS { b; } GUARANTEES { b; } }\n')
        self.template.with_suffix(".csv").write_text(
            "n,m,refsize,status\n1,2,0,unknown\n2,3,4,realizable\n")
        (self.track / "family/plain.tlsf").touch()

    def manifest(self, rows=""):
        path = self.root / "manifest.csv"
        path.write_text("pattern,params,enabled,reason\n" + rows)
        return Manifest(path)

    def require_pandas(self):
        if importlib.util.find_spec("pandas") is None:
            self.skipTest("TLSF generation tests require pandas; install with: python3 -m pip install pandas")

    def tlsf_selector(self):
        self.require_pandas()
        repo = Path(__file__).resolve().parent.parent
        with patch.object(sys, "path", [str(repo / "tlsf")] + sys.path):
            selector = runpy.run_path(str(repo / "tlsf/selectBenchmarks.py"))
        # These tests cover selection; tlsf/test_genParametric.py checks syfco.
        checker = patch("genParametric.runSyfco", return_value="")
        checker.start()
        self.addCleanup(checker.stop)
        return selector

    def test_default_and_last_matching_rule(self):
        manifest = self.manifest(
            "family/*,,0,whole family\n"
            "family/parametric/example.tlsf,n=1,1,keep one\n"
            "family/parametric/example.tlsf,n=1;m=2,0,override\n")
        self.assertEqual(manifest.is_enabled("other/new.tlsf"), (True, ""))
        self.assertEqual(manifest.is_enabled("family/plain.tlsf"), (False, "whole family"))
        name = "family/parametric/example.tlsf"
        self.assertEqual(manifest.is_enabled(name, {"n": 1, "m": 3}), (True, "keep one"))
        self.assertEqual(manifest.is_enabled(name, {"n": 1, "m": 2}), (False, "override"))
        self.assertEqual(manifest.is_enabled(name), (False, "whole family"))
        self.assertEqual(manifest.is_enabled("Family/plain.tlsf"), (True, ""))

    def test_csv_quoting_and_empty_manifest(self):
        manifest = self.manifest('family/plain.tlsf,,0,"reason, with comma"\n')
        self.assertEqual(manifest.is_enabled("family/plain.tlsf"), (False, "reason, with comma"))
        self.assertEqual(self.manifest().is_enabled("family/plain.tlsf"), (True, ""))

    def test_malformed_manifests(self):
        rows = [
            "family/plain.tlsf,,yes,reason\n",
            "family/plain.tlsf,,0\n",
            "family/plain.tlsf,,0,reason,extra\n",
            ",,0,empty pattern\n",
            "/family/plain.tlsf,,0,absolute\n",
            "../family/plain.tlsf,,0,parent traversal\n",
            "family\\plain.tlsf,,0,backslash\n",
            "family/plain.tlsf,n=,0,empty value\n",
            "family/plain.tlsf,n=1;n=2,0,duplicate key\n",
            "family/plain.tlsf,n=1;,0,trailing separator\n",
            "family/plain.tlsf,n,0,no assignment\n",
            'family/plain.tlsf,,0,"unterminated\n',
        ]
        for row in rows:
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.manifest(row)
        path = self.root / "bad-header.csv"
        path.write_text("pattern,enabled\n")
        with self.assertRaises(ValueError):
            Manifest(path)

    def test_validator_rejects_missing_paths_and_invalid_params(self):
        cases = [
            ("family/missing.tlsf,,0,missing\n", "does not exist"),
            ("missing/*.tlsf,,0,missing\n", "glob matches nothing"),
            ("family/plain.tlsf,n=1,0,ordinary\n", "non-parametric"),
            ("family/parametric/example.tlsf,n=99,0,missing value\n", "no status CSV row"),
            ("family/parametric/example.tlsf,n=1;m=3,0,missing combination\n", "no status CSV row"),
            ("family/parametric/example.tlsf,typo=1,0,missing parameter\n", "no status CSV row"),
            ("family/*.tlsf,n=1,0,mixed glob\n", "non-parametric"),
        ]
        for row, message in cases:
            with self.subTest(row=row):
                errors, _ = check_manifest(self.manifest(row), self.track)
                self.assertTrue(any(message in error for error in errors), errors)

    def test_unknown_status_warns_only_when_enabled(self):
        errors, warnings = check_manifest(self.manifest(), self.track)
        self.assertFalse(errors)
        self.assertEqual(len(warnings), 1)
        errors, warnings = check_manifest(self.manifest(
            "family/parametric/example.tlsf,n=1,0,unknown\n"), self.track)
        self.assertFalse(errors)
        self.assertFalse(warnings)
        errors, warnings = check_manifest(self.manifest(
            "family/*,,0,all\nfamily/parametric/example.tlsf,n=1,1,re-enable\n"), self.track)
        self.assertFalse(errors)
        self.assertEqual(len(warnings), 1)

    def test_duplicate_parameters_warn_regardless_of_tags_or_enabledness(self):
        self.template.with_suffix(".csv").write_text(
            "n,m,refsize,status\n 1 ,2,0,realizable\n2,3,4,realizable\n"
            "1, 2 ,10,unrealizable\n1,2,11,realizable\n")
        for rules in ("", "family/*,,0,disabled\n"):
            with self.subTest(rules=rules):
                errors, warnings = check_manifest(self.manifest(rules), self.track)
                self.assertEqual(errors, [])
                self.assertEqual(len(warnings), 2)
                for line, warning in zip((4, 5), warnings):
                    self.assertIn(f"{self.template.with_suffix('.csv')}:{line}:", warning)
                    self.assertIn("duplicate parameter row [n=1;m=2]", warning)
                    self.assertIn("first at line 2", warning)

    def test_distinct_parameter_text_and_combinations_are_not_duplicates(self):
        self.template.with_suffix(".csv").write_text(
            "n,m,refsize,status\n1,2,0,realizable\n1,3,0,realizable\n01,2,0,realizable\n")
        self.assertEqual(check_manifest(self.manifest(), self.track), ([], []))

    def test_duplicate_parameters_warn_in_csv_without_a_template(self):
        path = self.track / "unselected/nested/parametric/orphan.csv"
        path.parent.mkdir(parents=True)
        path.write_text("n,refsize,status\n2,0,realizable\n2,1,realizable\n")
        errors, warnings = check_manifest(self.manifest(), self.track)
        self.assertEqual(errors, [])
        duplicates = [warning for warning in warnings if "duplicate parameter row" in warning]
        self.assertEqual(len(duplicates), 1)
        self.assertIn(f"{path}:3:", duplicates[0])

    def test_parity_validation_never_reads_benchmark_contents(self):
        track = self.root / "parity"
        family = track / "keiren"
        family.mkdir(parents=True)
        (family / "pointer.ehoa").touch()
        (family / "game.ehoa").touch()
        manifest = self.manifest("keiren/*.ehoa,,0,duplicates\n")
        with patch.object(Path, "open", side_effect=AssertionError("must only stat parity files")):
            self.assertEqual(check_manifest(manifest, track), ([], []))

    def test_recursive_selectors_filter_before_sampling(self):
        repo = Path(__file__).resolve().parent.parent
        for track_name, suffix in (("tlsf-fin", ".tlsf"), ("parity", ".ehoa")):
            with self.subTest(track=track_name):
                track = self.root / track_name
                family = track / "family"
                family.mkdir(parents=True)
                (family / ("keep" + suffix)).write_text("enabled benchmark\n")
                (family / ("skip" + suffix)).write_text("disabled benchmark\n")
                manifest = self.manifest(f"family/*,,0,all\nfamily/keep{suffix},,1,keep\n")
                output = self.root / (track_name + "-output")
                output.mkdir()
                args = [str(repo / track_name / "selectBenchmarks.py"),
                        str(track), str(output), "--manifest", str(manifest.path)]
                log = io.StringIO()
                with patch.object(sys, "argv", args), patch("random.Random") as generator:
                    sample = generator.return_value.getrandbits
                    sample.return_value = 1
                    with contextlib.redirect_stdout(log):
                        runpy.run_path(args[0], run_name="__main__")
                if track_name == "parity":
                    sample.assert_not_called()
                    self.assertTrue((output / "selection.json").is_file())
                else:
                    generator.assert_called_once_with(2027)
                    sample.assert_called_once_with(1)
                    self.assertTrue((output / "selection.json").is_file())
                self.assertEqual([file.name for file in output.glob("*" + suffix)], ["keep" + suffix])
                self.assertEqual((output / ("keep" + suffix)).read_text(), "enabled benchmark\n")
                self.assertIn("selected 1 / found 2, disabled 1", log.getvalue())

    def test_selectors_refuse_nonempty_output_without_modifying_it(self):
        self.assert_selectors_preserve_nonempty_output(
            ("tlsf-fin/selectBenchmarks.py", "parity/selectBenchmarks.py"))

    def test_tlsf_selectors_refuse_nonempty_output_without_modifying_it(self):
        self.require_pandas()
        self.assert_selectors_preserve_nonempty_output(
            ("tlsf/selectBenchmarks.py", "tlsf/genParametric.py"))

    def assert_selectors_preserve_nonempty_output(self, scripts):
        repo = Path(__file__).resolve().parent.parent
        manifest = self.manifest()
        for script in scripts:
            for entry in (".previous-output", "previous-directory"):
                with self.subTest(script=script, entry=entry):
                    with tempfile.TemporaryDirectory(dir=self.root) as directory:
                        output = Path(directory)
                        previous = output / entry
                        if entry.endswith("directory"):
                            previous.mkdir()
                            previous = previous / "benchmark.tlsf"
                        previous.write_bytes(b"previous output\n")
                        before = {str(path.relative_to(output)): path.read_bytes()
                                  for path in output.rglob("*") if path.is_file()}
                        result = subprocess.run(
                            [sys.executable, str(repo / script), str(self.track),
                             str(output), "--manifest", str(manifest.path)],
                            capture_output=True, text=True)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("output directory is not empty", result.stderr)
                        self.assertNotIn("Traceback", result.stderr)
                        self.assertEqual(result.stdout, "")
                        after = {str(path.relative_to(output)): path.read_bytes()
                                 for path in output.rglob("*") if path.is_file()}
                        self.assertEqual(after, before)

    def test_parameter_exclusions_use_original_csv_text(self):
        generate = self.tlsf_selector()["generateAllParametric"]
        for value in ("05", "5", "NA", "1e1"):
            with self.subTest(value=value):
                self.template.with_suffix(".csv").write_text(
                    f"n,refsize,status\n{value},0,unknown\n")
                manifest = self.manifest(
                    f"family/parametric/example.tlsf,n={value},0,exclude\n")
                self.assertEqual(check_manifest(manifest, self.track), ([], []))
                with tempfile.TemporaryDirectory(dir=self.root) as output:
                    counts = dict(found=0, selected=0, disabled=0)
                    with contextlib.redirect_stdout(io.StringIO()):
                        info = generate(self.template.parent.parent, output, False,
                                        manifest, self.track, counts)
                    self.assertEqual(info, [])
                    self.assertEqual(list(Path(output).iterdir()), [])
                    self.assertEqual(counts, dict(found=1, selected=0, disabled=1))

    def test_parameter_text_is_preserved_with_numeric_generation_order(self):
        generate = self.tlsf_selector()["generateAllParametric"]
        self.template.write_text(self.template.read_text().replace(" m = 2;", ""))
        self.template.with_suffix(".csv").write_text(
            "n,refsize,status\n 05 ,0,unknown\n5,1,realizable\n10,2,realizable\n2,3,realizable\n")
        manifest = self.manifest("family/parametric/example.tlsf,n=05,0,exclude\n")
        self.assertEqual(check_manifest(manifest, self.track), ([], []))
        for exclude in (True, False):
            with self.subTest(exclude=exclude), tempfile.TemporaryDirectory(dir=self.root) as output:
                counts = dict(found=0, selected=0, disabled=0)
                with contextlib.redirect_stdout(io.StringIO()):
                    info = generate(self.template.parent.parent, output, False,
                                    manifest if exclude else self.manifest(), self.track, counts)
                expected = ["example_pb_2_pe_.tlsf", "example_pb_5_pe_.tlsf",
                            "example_pb_10_pe_.tlsf"]
                if not exclude:
                    expected.insert(1, "example_pb_05_pe_.tlsf")
                    self.assertIn("n = 05;", (Path(output) / expected[1]).read_text())
                self.assertEqual(info, expected)
                self.assertEqual(counts, dict(found=4, selected=len(expected), disabled=int(exclude)))

    def test_tlsf_metadata_uses_only_files_written_in_this_run(self):
        selector = self.tlsf_selector()
        self.template.write_text(self.template.read_text().replace(" m = 2;", ""))
        self.template.with_suffix(".csv").write_text(
            "n,refsize,status\n1,0,unknown\n2,1,realizable\n")
        ordinary = self.track / "ordinary"
        ordinary.mkdir()
        (ordinary / "keep.tlsf").write_text("ordinary benchmark\n")
        manifest = self.manifest(
            "family/plain.tlsf,,0,exclude ordinary\n"
            "family/parametric/example.tlsf,n=1,0,exclude instance\n")
        for tree in (False, True):
            with self.subTest(tree=tree), tempfile.TemporaryDirectory(dir=self.root) as directory:
                output = Path(directory)
                args = SimpleNamespace(benchmarkpath=str(self.track), outputpath=str(output),
                                       treeLike=tree, manifest=str(manifest.path))
                make = selector["makeBenchmarks"]
                with patch.dict(make.__globals__, benchdirs=["family", "ordinary"]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        info, written = make(args)
                expected = ["example_pb_2_pe_.tlsf", "keep.tlsf"]
                self.assertEqual(list(written), expected)
                parametric = expected[:1]
                self.assertEqual(info, {"family": {"example": parametric} if tree else parametric,
                                        "ordinary": ["keep.tlsf"]})
                self.assertEqual(sorted(path.name for path in output.rglob("*.tlsf")), expected)
                (output / "unrelated.tlsf").write_text("not written by selection\n")
                with patch("os.listdir", side_effect=AssertionError("metadata must use written files")):
                    with contextlib.redirect_stdout(io.StringIO()):
                        selector["genFam_"](str(output), written)
                self.assertEqual(json.loads((output / "families.json").read_text()),
                                 {"example": [[2, "example_pb_2_pe_"]], "keep": [[0, "keep"]]})
                before = {str(path.relative_to(output)): path.read_bytes()
                          for path in output.rglob("*") if path.is_file()}
                disabled = self.root / "disabled.csv"
                disabled.write_text("pattern,params,enabled,reason\n*,,0,disable all\n")
                args.manifest = str(disabled)
                with self.assertRaisesRegex(ValueError, "output directory is not empty"):
                    make(args)
                after = {str(path.relative_to(output)): path.read_bytes()
                         for path in output.rglob("*") if path.is_file()}
                self.assertEqual(after, before)

    def test_checker_exit_status(self):
        selection = self.root / "selection"
        selection.mkdir()
        for track in ("tlsf", "tlsf-fin", "parity"):
            (self.root / track).mkdir(exist_ok=True)
            (selection / (track + ".csv")).write_text("pattern,params,enabled,reason\n")
        (self.root / "parity/duplicates.csv").write_text("group,level,path,representative\n")
        with patch("selection.checkSelection.__file__", str(selection / "checkSelection.py")):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            self.template.with_suffix(".csv").write_text(
                "n,m,refsize,status\n1,2,0,realizable\n1,2,1,unrealizable\n")
            with contextlib.redirect_stdout(io.StringIO()) as log:
                self.assertEqual(main(), 0)
            self.assertIn("WARNING:", log.getvalue())
            self.assertIn("duplicate parameter row [n=1;m=2]", log.getvalue())
            self.assertIn("0 errors, 1 warnings", log.getvalue())
            (selection / "parity.csv").write_text(
                "pattern,params,enabled,reason\nkeiren/missing.ehoa,,0,missing\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
