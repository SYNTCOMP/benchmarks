# Supervisory control of discrete event systems

These 63 specifications come from the MTSA (Modal Transition System Analyser)
benchmark suite. Hernán Gagliardi contributed the basic TLSF specifications,
generated from FSP by `silas` (`fsp2tlsf`), in
[SYNTCOMP/benchmarks#65](https://github.com/SYNTCOMP/benchmarks/issues/65).

Each FSP plant is a parallel composition of labelled transition systems.
The components run asynchronously and synchronize on shared events. One event
occurs at a time. The controller can enable controllable events. The environment
chooses which enabled event occurs and can preempt the controller with an
uncontrollable event. The TLSF specification is realizable under Mealy semantics
if and only if a supervisor exists for the original plant.

The inputs encode the last event, the state of each plant component and the
values of the relevant fluents. The outputs encode the controllable event the
controller proposes. An enumerated variable with n possible values uses
⌈log₂ n⌉ bits. Each file lists the bit codes and identifies the encoding rule
and model element for each conjunct.

## Families

Each filename has the form `X-N-K.tlsf` or `X-N.tlsf`, where `X` is the
family code and the numbers give the parameters in the order shown below.

| Family | Description | Parameters | Instances |
| --- | --- | --- | ---: |
| AT | Air traffic control tower assigning holding heights and access to a single ramp | N planes, K heights | 6 |
| BW | Bidding workflow coordinating teams to approve or refuse a document | N teams, at most K evaluation steps per team | 9 |
| CM | Cat and mouse game in which mice must reach the center and avoid cats elsewhere | N cats and N mice, corridor of 2K+1 cells | 9 |
| DP | Dining philosophers sharing forks so that each eats infinitely often | N philosophers | 5 |
| GR | Gripper robot carrying balls between two rooms, one ball at a time | N balls | 6 |
| PS | Product and shipping service coordinating offers and orders | N identifies one of five protocol variants | 5 |
| SC | Drone controller switching safely from an old specification to a new one | Sensor values from 0 to N | 5 |
| TA | Travel agency coordinating web services to fulfill vacation package requests | N amenities, at most K query steps per service | 9 |
| TL | Wonham's transfer line feeding workpieces through buffers to a test unit | N machines, buffer capacity K | 9 |

## Status

The authors expect most instances to be realizable. For AT, they state that a
supervisor exists if and only if there are at least as many heights as planes.

With its native TLSF frontend and a 17 s limit per instance, Acacia-Bonsai
decided 31 of the 63 instances. The `STATUS` tags reflect the following results.

- **27 realizable.** For each, Acacia-Bonsai synthesized an AIGER controller
  that was model-checked against the specification. Its `REF_SIZE` is the
  AND-gate count of that controller without minimization.
- **2 unrealizable.** The status table records that Acacia-Bonsai and Spot's
  `ltlsynt` (via `syfco`) both reported AT-1-2 and AT-1-3 unrealizable.
  These instances have one plane and two or three heights, respectively.
  The discrepancy with the authors' rule awaits clarification in
  [issue #65](https://github.com/SYNTCOMP/benchmarks/issues/65).
- **34 unknown.** Acacia-Bonsai reported CM-2-1 and TL-2-3 realizable, but
  their controller checks did not finish. The other 32 instances timed out.

`REF_SIZE` is `-1` for every instance without a checked controller.

## License

The specifications are licensed under CC BY 4.0. See [LICENSE](LICENSE).
