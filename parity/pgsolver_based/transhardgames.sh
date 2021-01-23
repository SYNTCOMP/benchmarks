#!/bin/bash

# Translate benchmarks that are hard for particular algorithms

# Jurdzinski games
for (( d = 50; d <= 100; d += 5 )) do
    for (( w = 100; w <= 500; w += 50 )) do
        echo "Translating jurdzinski game d = $d, w = $w"
        python3 pg2hoa.py jgame_${d}_${w}.pg > jgame_${d}_${w}.ehoa
    done
done

# Recursive ladder games
for (( n = 10; n <= 1000; n += 10 )) do
    echo "Translating recursive-ladder game n = $n"
    python3 pg2hoa.py rladdergame_${n}.pg > rladdergame_${n}.ehoa
done

# Model checker ladder games
for (( n = 10; n <= 1000; n += 10 )) do
    echo "Translating model-checker-ladder game n = $n"
    python3 pg2hoa.py mcladdergame_${n}.pg > mcladdergame_${n}.ehoa
done
