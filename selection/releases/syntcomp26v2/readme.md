# SYNTCOMP 2026 v2 selections

This release removes duplicates from the 2026 TLSF and parity selections. The
original `v2026` and `v2025.1` assets are unchanged. TLSF-fin is outside this
revision.

| Track | Original 2026 | v2 | Redundant instances removed |
| --- | ---: | ---: | ---: |
| TLSF | 1,586 | 1,541 | 45 |
| Parity | 484 | 432 | 52 |

The TLSF selector regenerates the current enabled corpus. The parity selection
preserves the groups represented in the original 2026 panel, using the current
canonical representative of each confirmed group. It selects these groups
directly, without sampling from the full eligible pool. In 27 cases, the canonical
representative was outside the original panel. All 484 original games were
matched byte-for-byte to current repository blobs before grouping; 219 required
filename changes.
[`parity-v2026.csv`](parity-v2026.csv) records every original filename, current
path, selected representative and original SHA-256. The new parity selector uses
the release-specific [`parity.csv`](parity.csv).

## TLSF origins and confirmation

The audit follows the recently closed
[issue #55](https://github.com/SYNTCOMP/benchmarks/issues/55) and its implementation in
[#57](https://github.com/SYNTCOMP/benchmarks/pull/57) and
[#58](https://github.com/SYNTCOMP/benchmarks/pull/58). The default parity manifest
already disables its 143 confirmed non-representatives for future selections.

[`tlsf-game-origins.csv`](../../tlsf-game-origins.csv) traces all 83 TLSF-based
rows in that report, including the unconfirmed KitchenTimer pair. Paths are
relative to the TLSF track. Generated filenames map to templates and explicit
parameter tuples; `amba_decomposed_lock__pb_*` has an extra historical underscore.
The old unsuffixed `ltl2dba_C2`, `ltl2dba_R` and `ltl2dba_E` games use `n=1`,
as their formulas and AP sets show, rather than today's template default `n=2`.
The old `prioritized_arbiter_unreal_pb_1/2_pe_` and
`round_robin_arbiter_unreal_pb_1/2_pe_` names refer to the two variant templates,
at `(n=2,u=1)` and `n=2`, respectively. They do not mean `n=1` and `n=2` of
one template.

Eight source files were already removed by
[`e30f266f`](https://github.com/SYNTCOMP/benchmarks/commit/e30f266f699fff9913903474b5a1f3fe0e5ad91f)
for [issue #25](https://github.com/SYNTCOMP/benchmarks/issues/25).
`full_arbiter` is outside the TLSF selector's current family list. Neither case
requires a new exclusion. Historical names and paths remain in the trace.

We rebuilt games from the 81 current instances listed in
[`tlsf-game-audit.csv`](../../tlsf-game-audit.csv): the remaining traced sources
and every currently listed parameter of `amba_decomposed_lock`. SyFCo 1.2.1.2
lowers the effective Mealy formula, Spot 2.16 constructs complete deterministic
parity automata, and the issue's Knor-style residual-game reduction compares
their label-stripped graphs. Empty acceptance marks are completed with a neutral
losing priority without changing the language. The audit confirmed exact
isomorphism for every excluded pair, with the initial vertex mapping to the
initial vertex. All 81 regenerated outputs reproduce byte-for-byte on the
recorded tools.

The audit found 45 redundant current instances across 17 groups, recorded in
[`tlsf/duplicates.csv`](../../../tlsf/duplicates.csv) and disabled in
[`selection/tlsf.csv`](../../tlsf.csv). The 45 instances occur in both the
2025 and 2026 TLSF releases. In particular:

- 20 `amba_decomposed_lock` instances are replaced by `n=2`, including the
  listed larger values through `n=200`; untested future parameter values are
  not automatically excluded.
- The Button group removes five TSL-derived instances; other TSL groups include
  board controllers, SPI/Torcs and counter variants.
- `ltl2dba_C2[n=1]` is replaced by `ltl2dba_R[n=1]`, with other parameters kept.
- `prioritized_arbiter_unreal1[n=2;u=1]` is replaced by variant 2 at `n=2`.

Historical groups that no longer match under current TLSF conversion stay
enabled. These include `lilydemo01/02`, `ltl2dpa11/15`, `ltl2dpa23/24`, the full
arbiter unreal variants and the round-robin unreal variants. The unconfirmed
KitchenTimer pair stays enabled. Game equality here is a structural selection
criterion, not a claim of TLSF language equivalence or equal translation cost.
The standard manifest checker now rejects re-enabling a recorded TLSF duplicate
and validates its exact source parameter tuple.

## Reproduce

Use a complete checkout, Python with pandas, and `syfco` on `PATH`:

```sh
python3 -B selection/checkSelection.py
python3 -B -m unittest discover -s selection -p 'test_*.py'
python3 -B -m unittest parity.testSelectBenchmarks parity.testFindDuplicates
python3 -B selection/releases/syntcomp26v2/build.py /tmp/syntcomp26v2-release
```

The output directory must be empty. The builder invokes the current TLSF and
parity selection scripts, checks the expected panel sizes, rejects skipped LFS
contents, and writes `tlsf.zip`, `parity.zip`, per-file hashes in
`selection-audit.json`, the applied manifests, logs and `SHA256SUMS`. ZIP members
are sorted, with fixed timestamps and modes. `families.json` and `structure.json`
come from the TLSF selector; `selection.json` comes from the parity selector.
The current generator uses `_pb_..._pe_` filenames for SWEAP instances that were
previously shipped as individually named files; current Lily fixes are included.

To regenerate and independently verify the TLSF game evidence, also put Spot's
`ltl2tgba` on `PATH`:

```sh
python3 -B selection/auditTlsfGames.py /tmp/tlsf-games
python3 -B parity/findDuplicates.py --root /tmp/tlsf-games --out /tmp/tlsf-game-duplicates.csv --jobs 4
python3 -B selection/auditTlsfGames.py /tmp/tlsf-games --verify
```

The audit script never edits the manifests or duplicate tables. It prints tool
versions into `versions.json`. The verification fails if an exact match times out
or a recorded pair no longer matches. Unsupported or suspected matches do not
justify an exclusion.
