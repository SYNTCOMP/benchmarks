The folder contains benchmarks for the parity track.
The format is described [here](https://arxiv.org/pdf/1912.05793.pdf),
which itself is an extension of the Hanoi omega-automata [format](https://adl.github.io/hoaf/index.html).

Relevant references:
- [hoa-tools](https://github.com/gaperez64/hoa-tools) repository
- Keiren's [parity-game generator](https://github.com/jkeiren/paritygame-generator)

### Preparing the 2027 selection

The 2026 selection is frozen. For 2027, `selectBenchmarks.py` recursively finds
`.ehoa` files and applies [`selection/parity.csv`](../selection/parity.csv).
Benchmarks default to enabled; the last matching manifest row wins. Confirmed
duplicates remain in the repository but their non-representatives are disabled
with `duplicate-of:<representative>` reasons. Unconfirmed `suspected` groups
stay enabled.

Run from the repository root with Python 3 (standard library only):

```sh
# Uncapped: copy every eligible benchmark.
python3 parity/selectBenchmarks.py parity /tmp/parity-all
# Choose exactly 200 uniformly at random, without replacement.
python3 parity/selectBenchmarks.py parity /tmp/parity-200 --target 200 --seed 1
# Optionally use a different selection manifest.
python3 parity/selectBenchmarks.py parity /tmp/parity-custom --manifest custom.csv
```

The output directory must be empty; it is created if absent. A non-empty
directory is rejected before writing. Copies have a flat layout, and selected
paths with colliding basenames cause an error before any copies are written.
`--target N` accepts zero and fails if N is negative or exceeds the eligible
count. Without `--target`, all eligible files are selected. There are no family
caps or quotas. `--seed` defaults to **2027** and is printed on every run.
Sampling uses a local Python random generator over sorted relative paths, so
the same inputs and seed reproduce the selection with the same Python version.
Git LFS pointer stubs are skipped with a warning; download the benchmark
contents before selection to include those files.

Each output includes `selection.json`, containing `seed`, `target` (`null` for
uncapped), `counts`, and a sorted `selected` list of `{path, family}` objects.
Paths are relative to the supplied parity root. Families use the basename
prefix before `_pb_..._pe_`, matching the TLSF selector, or the entire basename
when there is no parameter marker. Counts contain `found`, `disabled_by_reason`
(a reason-to-count mapping), `lfs_skipped`, `eligible`, and `selected`.
Manifest exclusions are counted first; LFS skips count pointers among the
remaining files. Thus found = sum(disabled_by_reason) + lfs_skipped + eligible.

Run `python3 selection/checkSelection.py` to validate the manifests and check
that all confirmed non-representatives are disabled. It warns when a duplicate
representative has no enabled replacement. An explicit `duplicate-of:<path>`
reason can point to a replacement; every path in a chain must identify an
existing `.ehoa` benchmark within the parity track, ending at an effectively
enabled benchmark (using the last matching manifest rule).
The check reads the duplicate table, without loading benchmark contents.

### Duplicate games

[`duplicates.csv`](duplicates.csv) lists groups of benchmarks whose games are
identical or isomorphic after stripping labels, using Knor's default symbolic
game reduction. Paths are relative to this folder. The representative is the
shortest path, breaking ties lexicographically. Each confirmed group is marked
`identical` when its numbered graphs agree, or `isomorphic` when vertex
renumbering is needed. `suspected` rows record pairs whose exact comparison
timed out; they do not establish duplicates.

Regenerate from the repository root with Python 3 (standard library only):

```sh
python3 parity/findDuplicates.py --jobs 4
python3 parity/findDuplicates.py --jobs 4 --manifest-rows > /tmp/parity-duplicates-manifest.csv
```

The second command also prints `pattern,params,enabled,reason` rows for confirmed
non-representatives, with `reason=duplicate-of:<representative>`, for
`selection/parity.csv`. It does not edit that manifest. To refresh exclusions
from the existing table without rescanning games, the equivalent conversion is:

```sh
python3 - <<'PY'
import csv
import sys
with open('parity/duplicates.csv', newline='') as source:
    rows = list(csv.DictReader(source))
writer = csv.writer(sys.stdout, lineterminator='\n')
writer.writerow(('pattern', 'params', 'enabled', 'reason'))
for row in rows:
    if row['level'] in ('identical', 'isomorphic') and row['path'] != row['representative']:
        writer.writerow((row['path'], '', 0, 'duplicate-of:' + row['representative']))
PY
```

Merge these rows with any other manifest rules, preserving their precedence. Use
`--max-size BYTES` to skip large inputs and `--timeout SECONDS` to change the
per-pair exact matching limit (default 10 seconds). LFS pointers, malformed
files, and unsupported automata are skipped with warnings on stderr. The module
docstring specifies the reduction, numbering, and supported input format.
Comparison includes unreachable vertices and ignores the distinguished initial
vertex, following label-stripped PGSolver graph isomorphism; these groups are
not a claim of automaton-language equivalence.

Run the regression checks with
`python3 -B -m unittest parity.testSelectBenchmarks parity.testFindDuplicates`
and `python3 -B -m unittest discover -s selection -p 'test_*.py'`.
