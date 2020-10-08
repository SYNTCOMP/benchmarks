Driver Synthesis Benchmarks
===========================

These benchmarks are for the Termite driver synthesis tool.

http://www.ertos.nicta.com.au/research/drivers/synthesis/

The files are named driver_XYZ.aag, where
   - X=a means that the benchmark has been translated as it is
   - X=b is a simplified version (certain state variables are removed if they
     have nothing to do with the specification)
   - X=c is even more simplified (reduced data widths)
   - X=d is even more simplified (more signals removed)
   - Y is the fairness-to-safety reduction constant. The original specification
     contains a Buechi constraint. We reduced this Buechi constraint into a
     safety property by saying that the property must be satisfied after at
     most Y time steps again and again (the maximum distance between two time
     steps where the condition is satisfied is Y). The versions with Y<=7 are
     most likely unrealizable, the versions with Y>7 are most likely realizable.
     For X=d and X=c this realizability bound was established by our BDD-based
     synthesis tool. For X=a and X=b this is just a guess (the tool did not
     terminate).
   - Z is either `y` or `n`, specifying whether or not the file has been
     optimized with ABC.

Translation from Verilog into AIGER done by Robert Koenighofer, using VL2MV and
ABC (see the comments in the file for the exact sequence of commands).