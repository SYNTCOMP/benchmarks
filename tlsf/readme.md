The benchmarks used in the LTL synthesis track. The benchmarks are in [TLSF](https://arxiv.org/pdf/1604.02284.pdf) format.

Relevant references:
- [`syfco`](https://github.com/reactive-systems/syfco): conversion from TLSF into Promela LTL, PSL, Wring, and other formats.
- [`combine_aiger`](https://github.com/reactive-systems/aiger-ltl-model-checker): model check AIGER solutions produced by TLSF synthesis tools
- [a collection](https://github.com/meyerphi/syntcomp-reference) of the smallest known models implementing some of the benchmarks

Some benchmarks are parametric in nature and their parameter values, status,
and reference sizes are kept in adjacent `parametric/*.csv` files. These are
status records; enabledness is controlled separately by
[`selection/tlsf.csv`](../selection/tlsf.csv), with everything enabled by default.
Use `selectBenchmarks.py` to copy enabled ordinary benchmarks and generate
enabled parameter combinations from the status CSVs. The existing `benchdirs`
list defines the available families. Both `selectBenchmarks.py` and
`genParametric.py` accept `--manifest PATH`; see the
[manifest format and examples](../selection/readme.md).

Parametric generation requires Python's existing `pandas` dependency and the
[`syfco`](https://github.com/reactive-systems/syfco) executable on `PATH`.
The generator replaces assignments only in `GLOBAL { PARAMETERS { ... } }`,
handling comments, multiple assignments per line, and multi-line values. CSV
parameter names must match the template declarations. It retains the existing
formatting of generated standalone assignments and appends the `//#!SYNTCOMP`
status/reference-size tags. It checks the generated TLSF with `syfco -in -c`
before writing it; syfco errors stop generation.

Direct overrides with `syfco -f full -op name=value` were tested with syfco
1.2.1.2. Although full output retains the high-level structure and comments,
tabs before parameter assignments can shift the replacement into a comment
(for example in `arbiters_zoo/parametric/arbiter_with_cancel.tlsf`), producing
invalid TLSF. Textual substitution avoids this issue without changing the
generated benchmarks.
