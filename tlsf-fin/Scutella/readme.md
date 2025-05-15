This is an LTLf version of Scutellà's example from her paper [A note on Dowling and Gallier's top-down algorithm for propositional Horn satisfiability](https://doi.org/10.1016/0743-1066(90)90026-2).

LTLf synthesis tools that construct a reachability game on-the-fly while solving it at the same time may be subject to a similar bug.  Because the issue depends on the order in which successors are explored, the four specifications provided here differ only in the polarity of the variables `a` and `b`.

These four specifications are all realizable.  They can be used with Moore or Mealy semantics, because only only player makes a choice at the current step.

Author: Alexandre Duret-Lutz <adl@lrde.epita.fr>, based on a drawing by Shufang Zhu <Shufang.Zhu@liverpool.ac.uk>, based itself on Scutellà's example.
