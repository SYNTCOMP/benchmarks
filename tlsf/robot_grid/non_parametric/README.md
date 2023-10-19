# Specs `gr_*.tlsf`

The specs have the shape `Forall i: GF_i -> Forall j: GF_j`,
so these are GR(1) specs; they use three parity colors only.
There are pickup-delivery stations, doors, walls (black), and fences (gray).
Robot and the moving object cannot go through the walls.
The moving object also cannot go through the fence, so it moves in the middle zone only.
The moving object moves on even ticks only.
For specs 1...8: all maps have the same size 8x16.
The number of assumptions and guarantees increases:
1 -- GF-> GF&GFg
2 -- 2GF -> 4GF
and so on.

The benchmarks were created using the generator script written by Ruediger and modified by Ayrat, taken from slugs synthesizer.

# Specs `ltl_*.tlsf`

These specs have the shape `(FG & Forall i: GF_i) -> (FG & Forall j: GF_j)`,
so they are not GR(1) anymore. They require five parity colors.

Here are the components of the spec:
- there is a moving obstacle
- a gray wall for the moving obstacle but which is transparent for the robot
- doors
- delivery-pickup stations
- favourable path for robot
- fav path for the moving obstacle
- the mov obstacle cannot get through the very top door as well
The spec requires to deliver all requested pick-ups, avoid collisions, and eventually use favorable paths for both players.

The maps from 1 to 8 all have the same size 16x8,
with increasing number of delivery-pickup stations and walls:
1 -- GF FG -> GF GF FG
2 -- GF GF FG -> 4GF FG
3 -- 3GF FG -> 6GF FG
and so on.

The benchmarks were created using the generator script written by Ruediger and modified by Ayrat, taken from slugs synthesizer.



All specs are realisable.
