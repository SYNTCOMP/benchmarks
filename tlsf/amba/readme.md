# AMBA BENCHMARKS

The folder contains AMBA-bus related benchmarks.

- `amba`: these are the benchmarks taken from Barbara Jobstmann PhD thesis [1], without any additional conversion into GR1; thus, they are LTL and are the most natural to understand.

- `amba_decomposed`: this version divides the AMBA into components and describes the LTL specifications of those components.

- `amba_gr1` contains the GR1 version from [2] plus a slightly advanced (LTL) version. It is not parameterised in TLSF, and instead uses the benchmark generator script. The script is the python translation of the original perl version of [2]. Additionally, it allows you to generate the Slugs version (instead of TLSF) and a few LTL variants. Note that although `amba_thesis` and this version should have the same semantics and be just a different encodings of the same thing, there are _not_: it seems that the guys [2] deviated from [1].


[1]:  Applications and Optimizations for LTL Synthesis, PhD thesis by Barbara Jobstmann
[2]:  Synthesis of Reactive (1) Designs,  by Bloem, Jobstmann, Piterman, Pnueli, Sa'ar.
