# Supervisory control of discrete event systems

These 63 basic TLSF specifications encode supervisory control problems from the
Modal Transition System Analyser (MTSA) benchmark suite. `silas` (`fsp2tlsf`)
generated the specifications from the FSP models. Hernán Gagliardi contributed them in
[SYNTCOMP/benchmarks#65](https://github.com/SYNTCOMP/benchmarks/issues/65).

Each FSP plant is a parallel composition of labelled transition systems that run
asynchronously and synchronize on shared events. Events occur one at a time.
The controller can enable only controllable events. The environment chooses
which enabled event occurs and can preempt the controller with an uncontrollable
event. The translation encodes this game in turns. The contributors designed
the encoding so that the TLSF specification is realizable under Mealy semantics
exactly when a supervisor can satisfy the requirements of the original DES
problem.

The inputs encode the last event, each plant component’s state and the relevant
fluent values. The outputs encode the proposed controllable event or `none`. An
enumerated variable with n possible values uses ⌈log₂ n⌉ bits. Comments in each
TLSF file list the bit codes and identify the encoding rule and model element
for each conjunct.

## Families

Each filename has the form `X-N-K.tlsf` or `X-N.tlsf`, where `X` is the
family code and the numbers give the parameters in the order shown below.

| Family | Description | Parameters | Instances |
| --- | --- | --- | ---: |
| AT | Air traffic control tower assigning holding heights and access to a single ramp | N planes, K heights | 6 |
| BW | Bidding workflow coordinating teams to approve or refuse a document | N teams, at most K evaluation steps per team | 9 |
| CM | Mice must reach the center infinitely often and may share a cell with a cat only at the center. | N cats and N mice, corridor of 2K+1 cells | 9 |
| DP | Dining philosophers sharing forks so that each eats infinitely often | N philosophers | 5 |
| GR | Gripper robot carrying balls between two rooms, one ball at a time | N balls | 6 |
| PS | Product and shipping service coordinating offers and orders | N identifies the submitted protocol version | 5 |
| SC | Drone controller switching safely from an old specification to a new one | Sensor values from 0 to N | 5 |
| TA | A travel agency must resolve every package request and may report success only after buying every requested amenity. | N amenities, at most K query steps per service | 9 |
| TL | Wonham's transfer line feeding workpieces through buffers to a test unit | N machines, buffer capacity K | 9 |

The contributors describe `PS-2` through `PS-5` as different protocol
versions. In the submitted TLSF files, `PS-4` reproduces `PS-2`, and `PS-5`
reproduces `PS-3`. Only the title and first header comment differ within each
pair. The selection keeps `PS-1`, `PS-2` and `PS-3`. The discrepancy is being
raised in [issue #65](https://github.com/SYNTCOMP/benchmarks/issues/65).

## Status

SYNTCOMP appended the status and reference-size trailers to the submitted TLSF
files. Acacia-Bonsai read the files directly and returned a result for 31 of the
63 instances within the 17 s limit per instance. It reported 29 as realizable.
For 27 of those, an AIGER controller passed model checking against the
specification. Those files are tagged `realizable`. For SYNTCOMP scoring,
`REF_SIZE` is the number of AND gates plus the number of latches in the
model-checked controller before minimization.

Acacia-Bonsai and Spot’s `ltlsynt` both reported `AT-1-2` and `AT-1-3` as
unrealizable. The `ltlsynt` runs used `syfco` to convert the TLSF files. These
two files are tagged `unrealizable` and have `REF_SIZE` set to `-1`. They have
one plane each and two and three heights, respectively, so both meet the
`K >= N` condition that Gagliardi gave for AT realizability. Gagliardi expected
most instances in the suite to be realizable.
[Issue #65](https://github.com/SYNTCOMP/benchmarks/issues/65)

The other 34 files are tagged `unknown`. Acacia-Bonsai reported `CM-2-1` and
`TL-2-3` as realizable. The controller check timed out for `CM-2-1` and ended
with an allocation error for `TL-2-3`. Acacia-Bonsai timed out on the remaining
32 instances. For unknown instances, `REF_SIZE` is `0`, which tells the
StarExec postprocessor to skip the reference-size ratio.

## License

The specifications are licensed under CC BY 4.0. See [LICENSE](LICENSE).
