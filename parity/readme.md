The folder contains benchmarks for the parity track.
The format is described [here](https://arxiv.org/pdf/1912.05793.pdf),
which itself is an extension of the Hanoi omega-automata [format](https://adl.github.io/hoaf/index.html).

Relevant references:
- [hoa-tools](https://github.com/gaperez64/hoa-tools) repository
- Keiren's [parity-game generator](https://github.com/jkeiren/paritygame-generator)

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
non-representatives, with `reason=duplicate-of:<representative>`, for a future
`selection/parity.csv` manifest. It does not edit that manifest. Use
`--max-size BYTES` to skip large inputs and `--timeout SECONDS` to change the
per-pair exact matching limit (default 10 seconds). LFS pointers, malformed
files, and unsupported automata are skipped with warnings on stderr. The module
docstring specifies the reduction, numbering, and supported input format.
Comparison includes unreachable vertices and ignores the distinguished initial
vertex, following label-stripped PGSolver graph isomorphism; these groups are
not a claim of automaton-language equivalence.

Run the regression checks with `python3 -B -m unittest parity.testFindDuplicates`.
