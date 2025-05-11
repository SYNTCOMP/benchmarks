# Chomp Game

The chomp game is a played as follows:

- You start with a rectangular chocolate bar divided into a NxM grid
- The bottom-left square (0,0) is poisoned
- Players take turns breaking off and eating pieces of the chocolate.
- On your turn, you choose any remaining square (i,j) of chocolate and break off (and eat) that piece along with all pieces that are above and to the right of it.
- The player who is forced to eat the poisoned piece loses.

In this specification, the controller (output player) starts, and we want to synthesize a strategy to force the environment to eat the poisoned square.

## Known properties

A strategy exists for all values of N>0, M>0 except N=M=1.

The specification for (N,M) should be isomorphic to the specification for (M,N), since this is just a transposition of the grid.

This specification was originally written by Alexandre Duret-Lutz to benchmark LTLf synthesizers, but if you remove "Finite" from the semantics, it should also generate a valid LTL specification.

Starting with Spot 2.14, `genltl --chomp-mealy=N,M` can be used to generate LTL/LTLf formulas comparable to those produced by this TLSF specification.

## Quick benchmark

To get a sense of how the parameters impact the difficulty, I made a very quick benchmark
to scan parameters 1≤N≤M≤4.  The tools used are `ltlfsynt` (from a development version
of what should become Spot 2.14) and `LydiaSyft` (v0.1.0-alpha).

| N | M | ltlfsynt | LydiaSyft |
|---|---|----------|-----------|
| 1 | 1 | 0.04     | 0.10      |
| 1 | 2 | 0.05     | 0.07      |
| 1 | 3 | 0.03     | 0.07      |
| 1 | 4 | 0.03     | 0.12      |
| 2 | 2 | 0.04     | 0.10      |
| 2 | 3 | 0.04     | 3.77      |
| 2 | 4 | 0.08     | >300      |
| 3 | 3 | 0.32     | >300      |
| 3 | 4 | 36.17    | SEGFAULT  |
| 4 | 4 | >300     | >300      |

## Author

Alexandre Duret-Lutz <adl@lrde.epita.fr>
