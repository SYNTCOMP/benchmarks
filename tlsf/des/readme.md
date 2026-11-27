# Supervisory control of discrete event systems

Hernán Gagliardi contributed these 63 basic TLSF specifications in
[issue #65](https://github.com/SYNTCOMP/benchmarks/issues/65). The tool
`silas` (`fsp2tlsf`) generated them from FSP models of supervisory control
problems in the Modal Transition System Analyser (MTSA) benchmark suite.

In each FSP model, the plant is a parallel composition of labelled transition
systems. The components run asynchronously and synchronize on shared events.
One event occurs at a time. The controller can enable only controllable events,
and the environment chooses which enabled event occurs. It can preempt the
controller by choosing an uncontrollable event. The contributors designed the
turn-based encoding so that the TLSF specification is realizable under Mealy
semantics exactly when a supervisor can meet the original DES requirements.

The inputs record the last event and the state of each plant component, along
with the relevant fluent values. The controller uses the outputs to propose a
controllable event or `none`. An enumerated variable with n possible values
takes ⌈log₂ n⌉ bits. The comments in each TLSF file list the bit codes and say
which encoding rule and model element each conjunct comes from.

## Families

The filenames are `X-N-K.tlsf` or `X-N.tlsf`, where `X` is the family code.
The table gives the parameters in filename order.

| Family | Description | Parameters | Submitted files |
| --- | --- | --- | ---: |
| AT | An air traffic control tower assigns holding heights and controls access to a single ramp. | N planes, K heights | 6 |
| BW | Engineering teams evaluate a document in a bidding workflow. The controller approves or refuses the document. | N teams, at most K evaluation steps per team | 9 |
| CM | Mice must reach the center infinitely often. They may share a cell with a cat only at the center. | N cats and N mice, corridor of 2K+1 cells | 9 |
| DP | Dining philosophers share forks so that each philosopher eats infinitely often. | N philosophers | 5 |
| GR | A gripper robot carries balls between two rooms, one ball at a time. | N balls | 6 |
| PS | A product and shipping service coordinates offers and orders. | N identifies the submitted protocol version | 5 |
| SC | A drone controller must switch safely from an old specification to a new one. | N is the sensor-range parameter. Both `SC-1` and `SC-2` encode 0, 1 and 2. | 5 |
| TA | A travel agency must resolve every package request. It may report success only after buying every requested amenity. | N amenities, at most K query steps per service | 9 |
| TL | Wonham's transfer line feeds workpieces through buffers to a test unit. | N machines, buffer capacity K | 9 |

The submission contains five PS files. `PS-4` duplicates `PS-2`, and `PS-5`
duplicates `PS-3`. Only the title and first header comment differ within each
pair. The [selection manifest](../../selection/tlsf.csv) disables `PS-4` and
`PS-5` and keeps `PS-1` through `PS-3` enabled.

## Status

SYNTCOMP appended the status and reference-size trailers to the submitted
files. Acacia-Bonsai read the TLSF files directly, with a 17 s limit per
instance. It returned a result for 31 of the 63 instances and reported 29 as
realizable.

For 27 of those 29, the AIGER controller from Acacia-Bonsai passed model
checking against the specification. These files have the tag `realizable`.
The controller check timed out on `CM-2-1` and failed with an allocation error
(`std::bad_alloc`) on `TL-2-3`. Both are tagged `unknown`, as are the 32
instances on which Acacia-Bonsai itself timed out.

Acacia-Bonsai found `AT-1-2` and `AT-1-3` unrealizable. Spot's `ltlsynt` gave
the same result after conversion with `syfco`, and both files have the tag
`unrealizable`. In [issue #65](https://github.com/SYNTCOMP/benchmarks/issues/65),
Gagliardi expected most of the suite to be realizable and gave `K >= N` as the
criterion for AT realizability. Both results conflict with that criterion.
Each instance has one plane, with two heights in `AT-1-2` and three in `AT-1-3`.

For SYNTCOMP scoring, `REF_SIZE` counts the AND gates plus latches in the
model-checked controller that Acacia-Bonsai emitted with its default reduction.
Its value is `-1` for the two unrealizable instances and `0` for the 34
unknowns. A value of `0` tells the StarExec postprocessor to skip the
reference-size ratio.

## License

The specifications are licensed under CC BY 4.0. See [LICENSE](LICENSE).
