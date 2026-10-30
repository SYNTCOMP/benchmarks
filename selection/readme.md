# Benchmark selection

`tlsf.csv`, `tlsf-fin.csv`, and `parity.csv` record enabledness separately
from benchmark status. Everything is enabled by default; only exceptions need
entries. Adding a benchmark or a status CSV row does not require a manifest edit.
The header must be `pattern,params,enabled,reason`, with four fields per row:

- `pattern`: a benchmark path relative to the track root, using `/`, or a
  case-sensitive Python `fnmatch` glob. `*` also matches across `/` separators.
- `params`: empty for ordinary files or all instances of a parametric template;
  otherwise semicolon-separated assignments such as `n=5` or `n=5;m=2`.
  Names are case-sensitive, values match the status CSV text after trimming
  surrounding whitespace (`n=05` differs from `n=5`), and omitted parameters
  match any value. Each assignment combination must match at least
  one existing status CSV row for every template matched by the pattern.
- `enabled`: `0` to disable, `1` to enable. The last matching row wins.
- `reason`: optional free text. Quote CSV fields containing commas.

For example:

```csv
pattern,params,enabled,reason
lily/lilydemo04.tlsf,,0,too-easy
ltl2dba/parametric/ltl2dba_*.tlsf,,0,family excluded
ltl2dba/parametric/ltl2dba_E.tlsf,n=5,1,keep this instance
```

Parameter rules refer to the template in `parametric/`, not a generated
`*_pb_*_pe_.tlsf` filename. They require its adjacent status CSV. Pre-generated
files without a template (including TLSF-fin's current files) use path rules
with empty `params`.

The existing `parametric/*.csv` files remain status records with columns
`parameters...,refsize,status`; inline `//STATUS` tags are unchanged. Their rows
provide available parameter combinations, while the manifest determines which
of those combinations to generate. Unknown status does not disable an instance.
TLSF's existing `benchdirs` still defines which benchmark families are visited.
TLSF-fin retains its random sampling after filtering disabled files. The TLSF
and TLSF-fin manifests are header-only; parity disables confirmed duplicate
non-representatives. These changes prepare the 2027 selection, while the 2026
selection is frozen. Nim exclusions for issue #40 are handled separately.

From the repository root, use existing, empty output directories:

```sh
python3 tlsf/selectBenchmarks.py tlsf /tmp/tlsf-selection --saveFam -s
python3 tlsf-fin/selectBenchmarks.py tlsf-fin /tmp/tlsf-fin-selection
python3 parity/selectBenchmarks.py parity /tmp/parity-selection
python3 tlsf/genParametric.py tlsf/ltl2dba /tmp/ltl2dba-selection
```

These commands default to the track's manifest and accept `--manifest PATH`
to use another CSV (a header-only CSV enables everything). The standalone
generator resolves paths relative to the enclosing `tlsf` or `tlsf-fin`
directory, or its input directory when used outside a track tree. It defaults
to `tlsf.csv` when no enclosing track is identifiable. `Manifest(path)` in
`manifest.py` exposes `is_enabled(relpath, params=None)`, returning enabledness
and the last matching reason (default: `True, ""`).

Selection refuses non-empty output directories before writing any files;
it never deletes previous output. Use a fresh, empty directory for each run.
`families.json` and `structure.json` describe files written during that run.

The parity selector copies all enabled, available benchmarks by default.
`--target N --seed S` samples exactly N uniformly without replacement after
manifest filtering and skipping Git LFS pointers. Its default seed is 2027;
it writes `selection.json` with counts and selected paths/families. See the
[parity usage](../parity/readme.md) for details.

Run `python3 selection/checkSelection.py` to validate all three manifests.
Missing paths, unmatched globs, invalid parameter selections, and malformed
rows fail validation. Confirmed non-representatives in `parity/duplicates.csv`
must be disabled; a representative with no enabled replacement produces a
warning. Representatives and every replacement in a `duplicate-of:` chain must
be existing `.ehoa` benchmarks within the parity track, and the chain must end
at an effectively enabled benchmark. Suspected groups do not require exclusions.
Repeated parameter combinations within any `parametric/*.csv` produce warnings
with the repeated values and line numbers, even for disabled instances or CSVs
without a template. Only parameter columns are compared, using trimmed text;
`refsize` and `status` do not distinguish instances. These warnings do not fail
validation or change generation (repeated rows write the same filename).
Enabled instances with unknown or unrecognized status
produce warnings only. Validation inspects parity paths without reading `.ehoa`
contents, so Git LFS downloads are unnecessary. GitHub Actions runs the same
check on pushes and pull requests.

Run all regression tests with
`python3 -B -m unittest selection.test_manifest selection.test_parity_duplicates parity.testSelectBenchmarks parity.testFindDuplicates`.
The TLSF generation tests require `pandas` (`python3 -m pip install pandas`)
and skip with an explanation when it is missing; these tests do not use `syfco`.
