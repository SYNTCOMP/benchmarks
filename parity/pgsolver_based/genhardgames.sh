#!/bin/bash

# Generate several benchmarks that are hard for particular algorithms

# Jurdzinski games
for (( d = 50; d <= 100; d += 5 )) do
    for (( w = 100; w <= 500; w += 50 )) do
        echo "Generating jurdzinski game d = $d, w = $w"
        bin/jurdzinskigame $d $w > jgame_${d}_${w}.pg
    done
done

# Recursive ladder games
for (( n = 10; n <= 1000; n += 10 )) do
    echo "Generating recursive-ladder game n = $n"
    bin/recursiveladder $n > rladdergame_${n}.pg
done

# Model checker ladder games
for (( n = 10; n <= 1000; n += 10 )) do
    echo "Generating model-checker-ladder game n = $n"
    bin/modelcheckerladder $n > mcladdergame_${n}.pg
done
