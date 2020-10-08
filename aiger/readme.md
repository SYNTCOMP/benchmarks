This folder contains benchmarks used in the AIGER track.
In this track, the safety properties are encoded as an AIGER circuit,
some signals and controlled by the environment while others by the system.
The task is to find an implementation for signals controlled by the system,
so that no matter what the environment does, the safety properties are satisfied.
See [here](https://arxiv.org/pdf/1405.5793.pdf) for more description of the format and the problem.

Some relevant references:
- original [AIGER](http://fmv.jku.at/aiger/) format used in the hardware model checking competition
- modified [`aiger.h`](https://github.com/5nizza/aisy/blob/master/aiger_swig/aiger.h) and [`aiger.c`](https://github.com/5nizza/aisy/blob/master/aiger_swig/aiger.c) whose functon `aiger_redefine_input_as_and` can be useful for writing the found model back into AIGER.

