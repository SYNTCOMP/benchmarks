# LIFT BENCHMARK (all parameterised)

This elevator-controller specifications are inspired by the one from

> 'Synthesis of Reactive (1) Designs' (Bloem, Jobstmann, Piterman, Pnueli, Sa'ar).

The controller serves `n` floors. It maintains the current floor in its output `f` ranging over `{0,...n-1\}` (or over `0...~log2(n)` for the unary encoded versions). The controller must ensure that `f` changes sequentially and does not jump. The outputs `up` and `down`  indicate the direction of lift movement. The inputs `b[0]...b[n]` indicates that the button on floor `i` was pressed. The specifications require that the lift does not move unless it is going to a floor with a pressed button or going down.

The benchmark comes in several versions:

- `lift.tlsf`,  `lift_unary_enc.tlsf`, `lift_wrong_physics_unreal.tlsf`:
  These are the first versions of the benchmark. In addition to signals `b[..]`, `f[..]`, `up`, `down`, these versions have an output  `serve`, indicating that the floor is being served. The benchmarks requires every reguesting floor to be eventually served. It also requires the lift to eventually move to floor `0` if there are not requests.
  The version `unary_enc` uses the unary encoding of the floors; thus, `f` ranges over `0...~log2(n)`. The version `wrong_physics` is unrealisable due to the wrong encoding of the physics of the lift movement.

- `lift_gr1.tlsf` , `lift_gr1+.tlsf`:
  These are the 'second' versions of the behchmark.
  As before, it uses input signals `b[0]...b[n]` and output signals `f[0]...f[n]`, `up`, `down`. Additionally, it uses an output `open` to indicate the door is open, and the lift should not move with the open door. It should also not open the door on floors not requesting the lift (the meaning of `open` is quite similar to that of `serve`). As before, no spurious movements. There are more properties in addition to these standard ones. There is an input `obstacle`, and the lift should not close the door when there is an obstacle; we assume that `GF(!obstacle)` holds.
  The version `gr1` is the GR1 encoding of the above specification.
  The version `gr1+` is not GR1 anymore since it contains a few more properties. It has an output `req_power` indicating that the lift requested power for its motor, and input `grant_power` indicating that the power was granted. The lift cannot move unless `grant_power` is high. We assume `GF req_power -> GF grant_power`, which takes the specification beyond GR1.
  Source: TBA.



author: ayrat
