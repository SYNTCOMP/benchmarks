# Benchmark selection

Each track has a selection script. It walks the benchmarks, drops whatever the
track's manifest disables, and copies the rest into an output directory.

## Generating a selection

Run from the repository root. The output directory must exist and be empty
(only the parity script creates it for you); nothing is ever deleted.

```sh
mkdir -p /tmp/sel-tlsf /tmp/sel-tlsf-fin

python3 tlsf/selectBenchmarks.py tlsf /tmp/sel-tlsf --saveFam -s
python3 tlsf-fin/selectBenchmarks.py tlsf-fin /tmp/sel-tlsf-fin
python3 parity/selectBenchmarks.py parity /tmp/sel-parity                  # all eligible games
python3 parity/selectBenchmarks.py parity /tmp/sel-parity-200 --target 200 # or: random 200
```

What each one does:

- **TLSF** — no randomness. Copies every enabled `.tlsf` in the families listed
  in `benchdirs` (in `tlsf/selectBenchmarks.py`), and generates the parametric
  instances (see below). `-t` keeps the folder tree, `-s` writes
  `structure.json`, `--saveFam` writes `families.json`. Needs `pandas` and
  `syfco`.
- **TLSF-fin** — each enabled file outside a `_pb_…_pe_` family is kept with
  probability 1/2; family members are always kept. Reproducible via `--seed`
  (default 2027, printed on each run). Writes `selection.json` with the seed,
  counts and the chosen files. Colliding basenames get directory prefixes,
  recorded as `output`.
- **Parity** — no `--target`: copies every enabled game. With `--target N`: a
  uniform random sample of N enabled games, reproducible via `--seed` (default
  2027, printed on each run). Git LFS pointer files are skipped. Writes
  `selection.json` with the seed, counts and the chosen files.

Every script prints a `selected / found / disabled` summary and accepts
`--manifest PATH` to use a different manifest.

## Parametric families (TLSF)

A family lives in `<family>/parametric/` as a template `<name>.tlsf` plus a
status CSV `<name>.csv` with columns `<parameters…>,refsize,status`. For each
CSV row the manifest leaves enabled, the generator:

1. writes the row's values into the template's `PARAMETERS` block,
2. appends the row's status as a `//#!SYNTCOMP` block (`STATUS`, `REF_SIZE`),
3. checks the result with `syfco`, and
4. saves it as `<name>_pb_<v1>_<v2>…_pe_.tlsf`.

To add an instance, add a row to the CSV (status `unknown` is fine). To
generate one family on its own:
`mkdir OUT && python3 tlsf/genParametric.py tlsf/<family> OUT`.

## Manifests

`tlsf.csv`, `tlsf-fin.csv` and `parity.csv` list **exceptions only** —
everything is enabled unless a row says otherwise, so adding a benchmark never
requires touching them. Status lives elsewhere (status CSVs and `//STATUS`
tags); the manifest only decides what gets selected.

```csv
pattern,params,enabled,reason
lily/lilydemo04.tlsf,,0,too-easy
ltl2dba/parametric/ltl2dba_*.tlsf,,0,family excluded
ltl2dba/parametric/ltl2dba_E.tlsf,n=5,1,keep this instance
```

- `pattern`: path relative to the track root, or a glob (`*` also crosses `/`).
  For parametric families, point at the template, not a generated file.
- `params`: empty means all instances; `n=5` or `n=5;m=2` picks rows of the
  status CSV (values are compared as text, so `05` ≠ `5`).
- `enabled`: `0` or `1`. When several rows match, the last one wins.
- `reason`: free text, e.g. `duplicate-of:<path>` or an issue number.

`parity.csv` disables the confirmed duplicates in `parity/duplicates.csv`,
keeping one representative per group. Groups marked `suspected` (isomorphism
not confirmed) stay enabled.

## Checking

```sh
python3 selection/checkSelection.py
```

It fails on manifest rows that point at nothing, malformed rows, or confirmed
parity duplicates that are not disabled. It warns (without failing) about enabled
instances with unknown status and about repeated rows in status CSVs. CI runs
it on every push and pull request.

Tests: `python3 -B -m unittest selection.test_manifest selection.test_parity_duplicates tlsf-fin.testSelectBenchmarks parity.testSelectBenchmarks parity.testFindDuplicates`
(the TLSF tests skip if `pandas` is missing).
