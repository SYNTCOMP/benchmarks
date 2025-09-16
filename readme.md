## SYNTCOMP benchmarks

This repository contains all benchmarks collected over the years by [SYNTCOMP](http://www.syntcomp.org/) community.
There are several kinds of benchmarks:

- `aiger`: safety games encoded in the [extended AIGER](https://arxiv.org/pdf/1405.5793.pdf) format,
- `tlsf`: LTL synthesis encoded in [TLSF](https://arxiv.org/pdf/1604.02284.pdf) format,
- `tlsf-fin`: LTLf synthesis, that is LTL for finite words, encoded in
  [extended TLSF](https://arxiv.org/abs/2303.03839) format
- `parity`: parity games encoded in the [extended HOA](https://arxiv.org/pdf/1912.05793.pdf) format.

Their folders contain more descriptions.

## Submit new benchmarks

To submit a new benchmark

- create a new issue
- attach an archive with your new benchmarks with a sensible name
- the archive should also contain `readme.md` or `readme.pdf`
  describing the benchmarks, relevant papers, etc.

We will check if everything is ok, and then add to the repository.
Alternatively, you can create a pull request with your benchmarks.

## Download benchmarks

- year 2025: [TLSF](https://github.com/SYNTCOMP/benchmarks/releases/download/v2025.1/selection-ltl-2025v2.zip), [TLSF-fin](https://github.com/SYNTCOMP/benchmarks/releases/download/v2025.1/selection-ltlf-2025.zip), [parity](https://github.com/SYNTCOMP/benchmarks/releases/download/v2025.1/selection-parity-2025.zip)
- year 2024: [TLSF](https://github.com/SYNTCOMP/benchmarks/releases/download/v2024.0.1/tlsfSelection2024.zip), [TLSF-fin](https://github.com/SYNTCOMP/benchmarks/releases/download/v2024.0.1/tlsfFinSelection2024.zip), [parity](https://github.com/SYNTCOMP/benchmarks/releases/download/v2024.0.1/paritySelection2024.zip)
- year 2023: [TLSF](https://github.com/SYNTCOMP/benchmarks/releases/download/v2023.4/TLSF_2023.zip), [TLSF-fin](https://github.com/SYNTCOMP/benchmarks/releases/download/v2023.4/TLSF-fin_2023.zip), [parity](https://github.com/SYNTCOMP/benchmarks/releases/download/v2023.4/Parity_2023.zip)
- year 2022: [TLSF](https://github.com/SYNTCOMP/benchmarks/releases/download/v2022/TLSF_2022.zip), [parity](https://github.com/SYNTCOMP/benchmarks/releases/download/v2022/PGAME_2022.zip)
- year 2021: [TLSF](https://github.com/SYNTCOMP/benchmarks/releases/download/v2021/TLSF_2021.zip), parity [synthesis](https://github.com/SYNTCOMP/benchmarks/releases/download/v2021/PGAME_Synth_2021.zip) and [realizability](https://github.com/SYNTCOMP/benchmarks/releases/download/v2021/PGAME_Real_2021.zip)
- year 2020: [AIGER](https://github.com/5nizza/syntcomp_benchmarks/releases/download/v2020/AIGER_2020.zip), [TLSF](https://github.com/5nizza/syntcomp_benchmarks/releases/download/v2020/TLSF_2020.zip), for parity, see the repository.
- year 2019: [AIGER](https://github.com/5nizza/syntcomp_benchmarks/releases/download/v2019/AIGER_2019.zip), [TLSF](https://github.com/5nizza/syntcomp_benchmarks/releases/download/v2019/TLSF_2019.zip)
- for the years 2015-2018, see [here](https://syntcomp.react.uni-saarland.de/)


If you find bugs in benchmarks, please create an issue describing the problem.

