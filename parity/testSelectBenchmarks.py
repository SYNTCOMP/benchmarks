import contextlib
import csv
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from parity.selectBenchmarks import DEFAULT_SEED, LFS_PREFIX, family, makeBenchmarks
from selection.manifest import Manifest


class SelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="parity-selection-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.track = self.root / "parity"
        self.track.mkdir()
        self.output = self.root / "output"

    def benchmark(self, path, contents=b"HOA: v1\nbenchmark\n"):
        file = self.track / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(contents)
        return file

    def manifest(self, rows=()):
        path = self.root / "manifest.csv"
        with path.open("w", newline="") as output:
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(("pattern", "params", "enabled", "reason"))
            writer.writerows(rows)
        return Manifest(path)

    def select(self, manifest=None, **options):
        with contextlib.redirect_stdout(io.StringIO()) as log:
            report = makeBenchmarks(self.track, self.output, manifest or self.manifest(), **options)
        self.assertIn(f"Seed: {report['seed']}", log.getvalue())
        self.assertEqual(json.loads((self.output / "selection.json").read_text()), report)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()),
                         sorted(["selection.json"] + [Path(row["path"]).name
                                                      for row in report["selected"]]))
        for row in report["selected"]:
            self.assertEqual((self.track / row["path"]).read_bytes(),
                             (self.output / Path(row["path"]).name).read_bytes())
        return report

    def test_uncapped_filters_manifest_and_lfs_before_selection(self):
        self.benchmark("z/plain.ehoa")
        self.benchmark("a/family_pb_2_3_pe_.tlsf.ehoa")
        self.benchmark("a/suspected.ehoa")
        self.benchmark("a/excluded.ehoa")
        self.benchmark("a/duplicate.ehoa")
        self.benchmark("a/pointer.ehoa", LFS_PREFIX + b"\noid sha256:abc\nsize 10\n")
        self.benchmark("a/disabled-pointer.ehoa", LFS_PREFIX)
        self.benchmark("ignore.txt")
        manifest = self.manifest([
            ("a/*", "", 0, "whole family"),
            ("a/family_pb_2_3_pe_.tlsf.ehoa", "", 1, "keep"),
            ("a/suspected.ehoa", "", 1, "unconfirmed"),
            ("a/pointer.ehoa", "", 1, "download required"),
            ("a/duplicate.ehoa", "", 0, "duplicate-of:z/plain.ehoa"),
        ])
        with contextlib.redirect_stderr(io.StringIO()) as warnings:
            report = self.select(manifest)
        self.assertIn("Git LFS pointer: a/pointer.ehoa", warnings.getvalue())
        self.assertNotIn("disabled-pointer", warnings.getvalue())
        self.assertEqual(report["seed"], DEFAULT_SEED)
        self.assertIsNone(report["target"])
        self.assertEqual(report["counts"], {
            "found": 7, "disabled_by_reason": {"whole family": 2,
                                               "duplicate-of:z/plain.ehoa": 1},
            "lfs_skipped": 1, "eligible": 3, "selected": 3,
        })
        self.assertEqual(report["selected"], [
            {"path": "a/family_pb_2_3_pe_.tlsf.ehoa", "family": "family"},
            {"path": "a/suspected.ehoa", "family": "suspected.ehoa"},
            {"path": "z/plain.ehoa", "family": "plain.ehoa"},
        ])

    def test_target_reproducibility_and_local_random_state(self):
        # Deliberately create files in reverse order, with uneven family sizes.
        for index in reversed(range(40)):
            self.benchmark(f"games/large_pb_{index}_pe_.ehoa")
        self.benchmark("single.ehoa")
        original = random.getstate()
        reports = []
        for index, seed in enumerate((1, 1, 2)):
            self.output = self.root / f"output-{index}"
            report = self.select(target=15, seed=seed)
            reports.append(report)
            selected = [row["path"] for row in report["selected"]]
            self.assertEqual(selected, sorted(set(selected)))
            self.assertEqual(len(selected), 15)
            self.assertEqual(report["counts"]["eligible"], 41)
        self.assertEqual(reports[0], reports[1])
        self.assertNotEqual(reports[0]["selected"], reports[2]["selected"])
        self.assertEqual(random.getstate(), original)

    def test_sampling_uses_all_and_only_eligible_paths_without_family_caps(self):
        for path in ("z.ehoa", "a_pb_2_pe_.ehoa", "a_pb_1_pe_.ehoa", "disabled.ehoa"):
            self.benchmark(path)
        self.benchmark("pointer.ehoa", LFS_PREFIX)
        manifest = self.manifest([("disabled.ehoa", "", 0, "exclude")])
        with patch("parity.selectBenchmarks.random.Random") as generator:
            generator.return_value.sample.return_value = ["z.ehoa", "a_pb_2_pe_.ehoa"]
            with contextlib.redirect_stderr(io.StringIO()):
                report = self.select(manifest, target=2, seed=123)
        generator.assert_called_once_with(123)
        generator.return_value.sample.assert_called_once_with(
            ["a_pb_1_pe_.ehoa", "a_pb_2_pe_.ehoa", "z.ehoa"], 2)
        self.assertEqual(report["counts"]["selected"], 2)

    def test_zero_exact_and_empty_selections(self):
        self.benchmark("game.ehoa")
        for index, target in enumerate((0, 1)):
            self.output = self.root / f"output-{index}"
            self.assertEqual(self.select(target=target)["counts"]["selected"], target)
        (self.track / "game.ehoa").unlink()
        self.output = self.root / "empty-output"
        report = self.select()
        self.assertEqual(report["counts"]["eligible"], 0)
        self.assertEqual(report["selected"], [])

    def test_invalid_target_or_input_writes_nothing(self):
        self.benchmark("game.ehoa")
        manifest = self.manifest()
        for target, message in ((-1, "non-negative"), (2, "exceeds 1 eligible")):
            with self.subTest(target=target), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, message):
                    makeBenchmarks(self.track, self.output, manifest, target=target)
                self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError, "benchmark path is not a directory"):
            makeBenchmarks(self.track / "missing", self.output, manifest)
        self.assertFalse(self.output.exists())

    def test_collisions_fail_before_copying(self):
        self.benchmark("first/shared.ehoa", b"first\n")
        self.benchmark("second/shared.ehoa", b"second\n")
        self.output.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "basename collision: .*shared.ehoa.*shared.ehoa"):
                makeBenchmarks(self.track, self.output, self.manifest())
        self.assertEqual(list(self.output.iterdir()), [])
        report = self.select(self.manifest([("second/*", "", 0, "disabled")]))
        self.assertEqual(report["counts"]["selected"], 1)

    def test_nonempty_output_is_preserved(self):
        self.benchmark("game.ehoa")
        self.output.mkdir()
        previous = self.output / ".previous-output"
        previous.write_bytes(b"keep\n")
        with self.assertRaisesRegex(ValueError, "output directory is not empty"):
            makeBenchmarks(self.track, self.output, self.manifest())
        self.assertEqual(list(self.output.iterdir()), [previous])
        self.assertEqual(previous.read_bytes(), b"keep\n")

    def test_cli_options_and_errors(self):
        self.benchmark("game.ehoa")
        script = Path(__file__).with_name("selectBenchmarks.py")
        args = [sys.executable, "-B", str(script), str(self.track), str(self.output),
                "--manifest", str(self.manifest().path)]
        invalid = subprocess.run(args + ["--target", "2"], capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("exceeds 1 eligible", invalid.stderr)
        self.assertNotIn("Traceback", invalid.stderr)
        self.assertFalse(self.output.exists())
        run = subprocess.run(args + ["--target", "1", "--seed", "99"],
                             check=True, capture_output=True, text=True)
        self.assertIn("Seed: 99", run.stdout)
        report = json.loads((self.output / "selection.json").read_text())
        self.assertEqual((report["seed"], report["target"]), (99, 1))

    def test_family_prefix_matches_tlsf_convention(self):
        self.assertEqual(family("nested/amba__pb_2_3_pe_.tlsf.ehoa"), "amba_")
        self.assertEqual(family("nested/plain.tlsf.ehoa"), "plain.tlsf.ehoa")
        self.assertEqual(family("nested/incomplete_pb_2.ehoa"), "incomplete_pb_2.ehoa")


if __name__ == "__main__":
    unittest.main()
