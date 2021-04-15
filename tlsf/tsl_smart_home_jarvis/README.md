TLDR:
- `extracted-benchmarks` contains the main benchmarks, its sub-folders contain decomposed variants;
- `scenario-creator` and `versions`: if you want to create new benchmark variants, go there.


# J.A.R.V.I.S. TSL/TLSF Benchmark Suite

## Overview
Our benchmark set is categorized into three parts:
1. General Specifications
2. Splitted Specifications
3. Building Block Specifications
&nbsp;&nbsp;3.1. Scenario Creator
&nbsp;&nbsp;3.2. Versioned Specifications

## 1. General Specifications
The folder `extracted-benchmarks` contains almost all of our own specifications extracted out of our repository (therefore sha in specification names).
The specifications are given in TSL and in TLSF format.

We provide a runtime performance overview for these specifications: `stats__extracted-benchmarks.ods`. Benchmarks were done with `strix` and `(mini)bowser`. Also realizability information is noted, if it was available.

The given runtime statistics should give an overview over the hardness when it comes to solving (with strix).
We have a lot of benchmarks which will take below 10 seconds but also many which will take a considerable amount of time. Also some benchmarks have timed out for our setups (time given).

## 2. Splitted Specifications
Each specification out of the `General Specifications` has been splitted by the tool `tslsplit`. The ones,which could be partitioned into at least two independent specifications, are provided in `extracted-benchmarks` in the corresponding folders.
The specifications are again given in TSL and in TLSF format.

`stats__extracted-benchmarks.ods` also contains runtimes for splitted specifications. Benchmarks this time were done only with `strix`.

Some observations we want to highlight. We determined, that for the specification `Assumptions_a50cadd7`, splitting leads to comparable overall runtime for the case of `Assumptions_a50cadd7` showing potential for parallelization. Furthermore for specification families `Morning2s_*`, `Demo1_*` none of the original specifications could get solved within 5 hours, when the splitted versions would all be done within 30 minutes. At least for the case of strix and TSL this demonstrates that splitting can be a very crutial part in getting results in a reasonable amount of time.


## 3. Building Block Specifications
We also provide ways to create new specifications, which can be modified in the number of assumptions and guarantees in order to achieve different levels of hardness when it comes to solving.
The building block specifications are motivated by our Smart Home scenarios, having different smart devices with their own behavior (assumptions) plus requirements on how they should interact with themselves or the general environment (guarantees).

As these so called building block specifications are given in TSL, `tslresolve` and `tsl2tlsf` are a requirement, if one wants to generate TLSF specifications. See [tsltools@github](https://github.com/reactive-systems/tsltools).
To transform one specification *spec.tsl* from TSL to TLSF apply:
>$ tslresolve spec.tsl | tsl2tlsf > spec.tlsf

! Note that it is not possible to out of the box cross-combine specifications from the following two building block sets.

### 3.1. Scenario Creator
Contained in the folder `scenario-creator`.
See [scenario-creator/README.md](scenario-creator/README.md).
### 3.2. Versioned Specifications
Contained in the folder `versions`.
See [versions/README.md](versions/README.md).
