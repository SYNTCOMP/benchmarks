import contextlib
import csv
import importlib
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from selection.manifest import Manifest


selector = importlib.import_module("tlsf-fin.selectBenchmarks")


class SelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tlsf-fin-selection-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.track = self.root / "tlsf-fin"
        self.track.mkdir()
        self.output = self.root / "output"

    def benchmark(self, path, contents=b"benchmark\n"):
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
        self.output.mkdir()
        with contextlib.redirect_stdout(io.StringIO()) as log:
            report = selector.makeBenchmarks(self.track, self.output,
                                             manifest or self.manifest(), **options)
        self.assertIn(f"Seed: {report['seed']}", log.getvalue())
        counts = report["counts"]
        self.assertIn(f"selected {counts['selected']} / found {counts['found']}, "
                      f"disabled {sum(counts['disabled_by_reason'].values())}", log.getvalue())
        self.assertEqual(json.loads((self.output / "selection.json").read_text()), report)
        self.assertEqual(sorted(path.name for path in self.output.iterdir()),
                         sorted(["selection.json"] + [row["output"] for row in report["selected"]]))
        self.assertEqual(len(list(self.output.glob("*.tlsf"))), counts["selected"])
        paths = [row["path"] for row in report["selected"]]
        self.assertEqual(paths, sorted(set(paths)))
        for row in report["selected"]:
            self.assertEqual(row["family"], selector.family(row["path"]))
            self.assertEqual((self.track / row["path"]).read_bytes(),
                             (self.output / row["output"]).read_bytes())
        return report

    def snapshot(self):
        return {path.name: path.read_bytes() for path in self.output.iterdir()}

    def test_seed_reproducibility_and_local_random_state(self):
        # Deliberately create directories and files in reverse order.
        for directory in ("z", "a"):
            for index in reversed(range(20)):
                self.benchmark(f"{directory}/game-{directory}-{index:02}.tlsf")
        original = random.getstate()
        reports, snapshots = [], []
        for index, options in enumerate(({}, {}, {"seed": selector.DEFAULT_SEED + 1})):
            self.output = self.root / f"output-{index}"
            reports.append(self.select(**options))
            snapshots.append(self.snapshot())
        self.assertEqual(reports[0]["seed"], selector.DEFAULT_SEED)
        self.assertEqual(reports[0], reports[1])
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertNotEqual(reports[0]["selected"], reports[2]["selected"])
        self.assertEqual(random.getstate(), original)

    def test_traversal_order_does_not_change_output(self):
        self.benchmark("root.tlsf")
        for directory in ("z/nested", "z", "a/nested", "a"):
            for index in reversed(range(10)):
                name = directory.replace("/", "-")
                self.benchmark(f"{directory}/game-{name}-{index:02}.tlsf")
        self.select()
        expected = self.snapshot()
        walk = selector.os.walk

        def reversed_walk(*args, **kwargs):
            for root, dirs, fnames in walk(*args, **kwargs):
                dirs.reverse()
                fnames.reverse()
                yield root, dirs, fnames

        self.output = self.root / "reordered-output"
        with patch.object(selector.os, "walk", reversed_walk):
            self.select()
        self.assertEqual(self.snapshot(), expected)

    def test_families_always_kept_and_disabled_files_filtered_before_sampling(self):
        for path in ("a/family_pb_2_3_pe_.tlsf", "a/family_pb_1_pe_.tlsf",
                     "a/suspected.tlsf", "a/excluded.tlsf", "a/disabled_pb_1_pe_.tlsf",
                     "z/plain.tlsf", "z/duplicate.tlsf", "ignore.txt"):
            self.benchmark(path)
        manifest = self.manifest([
            ("a/*", "", 0, "whole family"),
            ("a/family_pb_*_pe_.tlsf", "", 1, "keep"),
            ("a/suspected.tlsf", "", 1, "unconfirmed"),
            ("z/duplicate.tlsf", "", 0, "duplicate-of:z/plain.tlsf"),
        ])
        with patch.object(selector.random, "Random") as generator:
            generator.return_value.getrandbits.side_effect = [0, 1]
            report = self.select(manifest)
        generator.assert_called_once_with(selector.DEFAULT_SEED)
        sample = generator.return_value.getrandbits
        self.assertEqual(sample.call_count, 2)
        sample.assert_called_with(1)
        self.assertEqual(report["counts"], {
            "found": 7,
            "disabled_by_reason": {"whole family": 2, "duplicate-of:z/plain.tlsf": 1},
            "eligible": 4,
            "selected": 3,
        })
        self.assertEqual(report["selected"], [
            {"path": "a/family_pb_1_pe_.tlsf", "family": "family", "output": "family_pb_1_pe_.tlsf"},
            {"path": "a/family_pb_2_3_pe_.tlsf", "family": "family", "output": "family_pb_2_3_pe_.tlsf"},
            {"path": "z/plain.tlsf", "family": "plain.tlsf", "output": "plain.tlsf"},
        ])

    def test_colliding_names_are_independent_of_seed_and_manifest(self):
        expected = {"a/001.tlsf": "a_001.tlsf", "b/001.tlsf": "b_001.tlsf",
                    "z/unique.tlsf": "unique.tlsf"}
        for path in expected:
            self.benchmark(path, path.encode())
        selections = []
        for index, seed in enumerate((2, 0, 1)):
            self.output = self.root / f"output-{index}"
            report = self.select(seed=seed)
            selections.append({row["path"] for row in report["selected"]})
            for row in report["selected"]:
                self.assertEqual(row["output"], expected[row["path"]])
        self.assertEqual(len(selections[0]), 3)
        self.assertNotEqual(selections[1], selections[2])
        self.output = self.root / "filtered-output"
        report = self.select(self.manifest([("b/*", "", 0, "disabled")]), seed=2)
        self.assertEqual({row["path"]: row["output"] for row in report["selected"]},
                         {path: name for path, name in expected.items() if not path.startswith("b/")})

    def test_prefixes_extend_past_shared_parents_and_reserved_basenames(self):
        paths = ["outer/a/shared/001.tlsf", "b/shared/001.tlsf", "shared_a_001.tlsf"]
        self.assertEqual(selector.output_names(paths), {
            "outer/a/shared/001.tlsf": "shared_a_outer_001.tlsf",
            "b/shared/001.tlsf": "shared_b_001.tlsf",
            "shared_a_001.tlsf": "shared_a_001.tlsf",
        })

    def test_prefixes_are_unique_across_different_basename_groups(self):
        paths = ["x/a_b/foo.tlsf", "c/foo.tlsf", "y/a/b_foo.tlsf", "d/b_foo.tlsf"]
        expected = {"x/a_b/foo.tlsf": "a_b_x_foo.tlsf", "c/foo.tlsf": "c_foo.tlsf",
                    "y/a/b_foo.tlsf": "a_y_b_foo.tlsf", "d/b_foo.tlsf": "d_b_foo.tlsf"}
        self.assertEqual(selector.output_names(paths), expected)
        self.assertEqual(selector.output_names(list(reversed(paths))), expected)

    def test_prefixes_reallocate_before_reporting_impossible_collisions(self):
        self.assertEqual(selector.output_names([
            "a/b/001.tlsf", "z/b/001.tlsf", "b_a/001.tlsf",
        ]), {
            "a/b/001.tlsf": "b_001.tlsf",
            "z/b/001.tlsf": "b_z_001.tlsf",
            "b_a/001.tlsf": "b_a_001.tlsf",
        })

    def test_exhausted_prefix_can_stay_while_another_grows(self):
        self.assertEqual(selector.output_names([
            "a_b/001.tlsf", "outer/b/a/001.tlsf", "a_001.tlsf",
        ]), {
            "a_b/001.tlsf": "a_b_001.tlsf",
            "outer/b/a/001.tlsf": "a_b_outer_001.tlsf",
            "a_001.tlsf": "a_001.tlsf",
        })

    def test_impossible_names_fail_before_copying_even_if_disabled(self):
        for paths in (
                ["001.tlsf", "a/001.tlsf"],
                ["a_b/001.tlsf", "b/a/001.tlsf", "a_001.tlsf"]):
            with self.subTest(paths=paths):
                with self.assertRaisesRegex(ValueError, "unique output filename"):
                    selector.output_names(paths)
        for path in paths:
            self.benchmark(path)
        manifest = self.manifest([("*", "", 0, "all disabled")])
        self.output.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "unique output filename"):
                selector.makeBenchmarks(self.track, self.output, manifest)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_colliding_families_keep_source_family_and_markers(self):
        basename = "family_pb_1_pe_.tlsf"
        for directory in ("a", "b"):
            self.benchmark(f"{directory}/{basename}", directory.encode())
        with patch.object(selector.random, "Random") as generator:
            generator.return_value.getrandbits.return_value = 0
            report = self.select()
        generator.return_value.getrandbits.assert_not_called()
        self.assertEqual(report["counts"]["selected"], 2)
        for row in report["selected"]:
            self.assertEqual(row["family"], "family")
            self.assertEqual(row["output"], f"{Path(row['path']).parent.name}_{basename}")
            self.assertIsNotNone(selector.parRE.fullmatch(row["output"]))

    def test_empty_and_all_disabled_selections_write_report(self):
        report = self.select()
        self.assertEqual(report["counts"], {
            "found": 0, "disabled_by_reason": {}, "eligible": 0, "selected": 0,
        })
        self.assertEqual(report["selected"], [])
        self.benchmark("disabled_pb_1_pe_.tlsf")
        self.output = self.root / "disabled-output"
        report = self.select(self.manifest([("*", "", 0, "exclude all")]))
        self.assertEqual(report["counts"], {
            "found": 1, "disabled_by_reason": {"exclude all": 1}, "eligible": 0, "selected": 0,
        })
        self.assertEqual(report["selected"], [])

    def test_cli_default_and_explicit_seed(self):
        self.benchmark("game.tlsf")
        script = Path(__file__).with_name("selectBenchmarks.py")
        manifest = self.manifest()
        for index, seed in enumerate((None, 99)):
            self.output = self.root / f"output-{index}"
            self.output.mkdir()
            args = [sys.executable, "-B", str(script), str(self.track), str(self.output),
                    "--manifest", str(manifest.path)]
            if seed is not None:
                args += ["--seed", str(seed)]
            run = subprocess.run(args, check=True, capture_output=True, text=True)
            expected = selector.DEFAULT_SEED if seed is None else seed
            self.assertIn(f"Seed: {expected}", run.stdout)
            report = json.loads((self.output / "selection.json").read_text())
            self.assertEqual(report["seed"], expected)


if __name__ == "__main__":
    unittest.main()
