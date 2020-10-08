Huffman Encoder
===============

The benchmark is taken from the paper at SYNT'15 "Framework for Specifying Synthesis Problems". 

The idea is: given the Huffman decoder, synthesize the encoder.

The specification attaches a to-be-synthesized encoder to a given Huffman decoder, and then compares inputs to the encoder and outputs of the decoder -- they should match.

The source is in extended SMV format. 
To convert into SYNTCOMP format, use the scripts from that paper.

The version `k10` is realizable, `k9` is unrealizable (derived from the same liveness spec with different `k`).

ayrat.khalimov
