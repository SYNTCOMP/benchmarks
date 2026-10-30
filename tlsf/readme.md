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
