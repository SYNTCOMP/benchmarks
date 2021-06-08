The benchmarks used in the LTL synthesis track. The benchmarks are in [TLSF](https://arxiv.org/pdf/1604.02284.pdf) format.

Relevant references:
- [`syfco`](https://github.com/reactive-systems/syfco): conversion from TLSF into Promela LTL, PSL, Wring, and other formats.
- [`combine_aiger`](https://github.com/reactive-systems/aiger-ltl-model-checker): model check AIGER solutions produced by TLSF synthesis tools
- [a collection](https://github.com/meyerphi/syntcomp-reference) of the smallest known models implementing some of the benchmarks

Some benchmarks are parametric in nature and their parameter values (as well
as other relevant information) is kept in CSV files. To generate all the
explicit TLSF files use `selectBenchmarks.py`
