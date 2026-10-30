import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from genParametric import generateParametric, runSyfco, substituteParameters


TEMPLATE = '''//#!SYNTCOMP
//STATUS : unknown
//#
INFO {
  TITLE: "PARAMETERS { n = 99; }"
  DESCRIPTION: "Parameter-like text inside a string:
n = 123;
"
  SEMANTICS: Mealy
  TARGET: Mealy
}
GLOBAL {
  // PARAMETERS { n = 100; }
  /* A multi-line comment containing a nested comment and fake block:
     /* nested */ PARAMETERS { bogus = 100; }
     // This line comment marker is inside the block comment.
  */
  PARAMETERS /* n = 101; */ {
    n /* before the value */ = // another comment
      1 + 1; m = 2; // two assignments on one line
  }
  DEFINITIONS {
    copy = n;
    stay(x) = G x;
  }
}
MAIN {
  INPUTS { a[n]; b[m]; }
  OUTPUTS { out; }
  GUARANTEES { stay(out); }
}
// trailing comment without a newline'''


class ParametricTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="parametric-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.template = self.root / "template.tlsf"
        self.template.write_text(TEMPLATE)

    def generate(self, values, tags=None):
        names = generateParametric(str(self.template), values, tags or {},
                                   str(self.root / "generated"))
        return self.root / names[0]

    def test_substitution_preserves_structure_comments_and_tags(self):
        output = self.generate([("n", "5"), ("m", "4")],
                               {"STATUS": "realizable", "REF_SIZE": 10})
        text = output.read_text()
        expected = TEMPLATE.replace("1 + 1; m = 2;", "5; m = 4;")
        self.assertTrue(text.startswith(expected + "\n"))
        self.assertTrue(text.endswith("//#!SYNTCOMP\n//STATUS : realizable\n"
                                      "//REF_SIZE : 10\n//#\n"))
        self.assertEqual(text.count("//#!SYNTCOMP"), 2)
        self.assertEqual(runSyfco([str(output), "-p"]).strip(), "n, m")
        signals = runSyfco([str(output), "-ins"]).strip().split(", ")
        self.assertEqual(set(signals), {f"a_{i}" for i in range(5)} |
                                      {f"b_{i}" for i in range(4)})
        # Basic TLSF expands definitions; compare with independent overrides.
        self.assertEqual(runSyfco([str(output), "-f", "basic"]),
                         runSyfco([str(self.template), "-f", "basic",
                                   "-op", "n=5", "-op", "m=4"]))

    def test_filename_keeps_csv_parameter_text(self):
        output = self.generate([("n", "05"), ("m", "2")])
        self.assertEqual(output.name, "generated_pb_05_2_pe_.tlsf")
        self.assertIn("05; m = 2;", output.read_text())

    def test_parameter_names_must_match_declarations(self):
        for values, message in (([("typo", "3")], "not declared"),
                                ([("n", "3")], "missing from CSV"),
                                ([("n", "3"), ("n", "4")], "duplicate CSV")):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, message):
                self.generate(values)
            self.assertEqual(list(self.root.glob("generated*")), [])

    def test_invalid_value_fails_without_output(self):
        with self.assertRaisesRegex(ValueError, "syfco.*failed"):
            self.generate([("n", "unknown"), ("m", "2")])
        self.assertEqual(list(self.root.glob("generated*")), [])

    def test_invalid_template_fails_without_output(self):
        self.template.write_text("not TLSF")
        with self.assertRaisesRegex(ValueError, "no GLOBAL PARAMETERS"):
            self.generate([("n", "3")])
        self.assertEqual(list(self.root.glob("generated*")), [])

    def test_invalid_generated_tlsf_is_not_written(self):
        with patch("genParametric.runSyfco", side_effect=ValueError("invalid")):
            with self.assertRaisesRegex(ValueError, "generated_pb_3_2_pe_.*invalid"):
                self.generate([("n", "3"), ("m", "2")])
        self.assertEqual(list(self.root.glob("generated*")), [])

    def test_missing_syfco_has_clear_error(self):
        with patch("genParametric.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(ValueError, "syfco is required.*PATH"):
                self.generate([("n", "3"), ("m", "2")])
        self.assertEqual(list(self.root.glob("generated*")), [])

    def test_tabs_and_standalone_assignments_keep_legacy_formatting(self):
        self.template.write_text(TEMPLATE.replace(
            "    n /* before the value */ = // another comment\n"
            "      1 + 1; m = 2; // two assignments on one line",
            "  \tn = 1;  // n≥1\n    m = 2;"))
        output = self.generate([("n", "5"), ("m", "4")])
        self.assertIn("\nn = 5;\nm = 4;\n", output.read_text())
        self.assertNotIn("n≥1", output.read_text())
        runSyfco([str(output), "-c"])

    def test_all_assignments_can_share_the_block_line(self):
        self.template.write_text(TEMPLATE.replace(
            "  PARAMETERS /* n = 101; */ {\n"
            "    n /* before the value */ = // another comment\n"
            "      1 + 1; m = 2; // two assignments on one line\n  }",
            "  PARAMETERS { n = 2; m = 2; }"))
        output = self.generate([("n", "5"), ("m", "4")])
        self.assertIn("PARAMETERS { n = 5; m = 4; }", output.read_text())

    def test_parameters_in_separate_blocks(self):
        self.template.write_text(TEMPLATE.replace(
            "      1 + 1; m = 2; // two assignments on one line",
            "      1 + 1;\n  }\n  PARAMETERS { m = 2; // second block"))
        runSyfco([str(self.template), "-c"])
        output = self.generate([("n", "5"), ("m", "4")])
        self.assertIn("PARAMETERS { m = 4; // second block", output.read_text())
        self.assertEqual(runSyfco([str(output), "-p"]).strip(), "n, m")
        self.assertEqual(set(runSyfco([str(output), "-ins"]).strip().split(", ")),
                         {f"a_{i}" for i in range(5)} | {f"b_{i}" for i in range(4)})

    def test_duplicate_parameter_across_blocks_fails_without_output(self):
        self.template.write_text(TEMPLATE.replace(
            "  DEFINITIONS {", "  PARAMETERS { n = 7; }\n  DEFINITIONS {"))
        with self.assertRaisesRegex(ValueError, "duplicate parameter declaration: n"):
            self.generate([("n", "5"), ("m", "4")])
        self.assertEqual(list(self.root.glob("generated*")), [])

    def test_leading_at_parameter_name_from_csv(self):
        family = self.root / "family"
        parametric = family / "parametric"
        parametric.mkdir(parents=True)
        source = TEMPLATE.replace("n /* before", "@n /* before")
        source = source.replace("copy = n;", "copy = @n;").replace("a[n]", "a[@n]")
        (parametric / "test.tlsf").write_text(source)
        (parametric / "test.csv").write_text("@n,m,refsize,status\n3,2,0,unknown\n")
        manifest = self.root / "manifest.csv"
        manifest.write_text("pattern,params,enabled,reason\n")
        output_dir = self.root / "output"
        output_dir.mkdir()
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("genParametric.py")),
             str(family), str(output_dir), "--manifest", str(manifest)],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = output_dir / "test_pb_3_2_pe_.tlsf"
        self.assertEqual(runSyfco([str(output), "-p"]).strip(), "@n, m")
        self.assertEqual(set(runSyfco([str(output), "-ins"]).strip().split(", ")),
                         {"a_0", "a_1", "a_2", "b_0", "b_1"})

    def test_parenthesized_multiline_value(self):
        self.template.write_text(TEMPLATE.replace("1 + 1", "(1 +\n 1)"))
        output = self.generate([("n", "5"), ("m", "4")])
        self.assertIn("5; m = 4;", output.read_text())

    def test_unicode_and_prime_parameter_names(self):
        source = TEMPLATE.replace("n /*", "ä /*").replace("copy = n;", "copy = ä;")
        source = source.replace("a[n]", "a[ä]").replace("m =", "m' =").replace("b[m]", "b[m']")
        self.template.write_text(source)
        output = self.generate([("ä", "5"), ("m'", "4")])
        self.assertIn("5; m' = 4;", output.read_text())
        self.assertEqual(runSyfco([str(output), "-p"]).strip(), "ä, m'")

    def test_trailing_block_comment_continuing_on_next_line(self):
        self.template.write_text(TEMPLATE.replace(
            "1 + 1; m = 2; // two assignments on one line",
            "1 + 1;\n    m = 2; /* comment\n     still a comment */"))
        output = self.generate([("n", "5"), ("m", "4")])
        self.assertIn("m = 4; /* comment\n     still a comment */", output.read_text())

    def test_malformed_parameter_declarations_fail(self):
        cases = ("n = 1; n = 2;", "n = (1;", "n = ;", "n = 1", "n 1;",
                 "n = 1 /* unclosed;", 'n = "unclosed;')
        for declarations in cases:
            source = "GLOBAL { PARAMETERS { " + declarations + " } }"
            with self.subTest(declarations=declarations), self.assertRaises(ValueError):
                substituteParameters(source, [("n", "3")])

    def test_cli_reports_missing_syfco_without_traceback(self):
        family = self.root / "family"
        parametric = family / "parametric"
        parametric.mkdir(parents=True)
        (parametric / "test.tlsf").write_text(TEMPLATE)
        (parametric / "test.csv").write_text("n,m,refsize,status\n3,2,0,unknown\n")
        manifest = self.root / "manifest.csv"
        manifest.write_text("pattern,params,enabled,reason\n")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("genParametric.py")),
             str(family), str(self.root / "output"), "--manifest", str(manifest)],
            env=dict(os.environ, PATH=str(self.root)), text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("syfco is required", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
