#!/usr/bin/env python3

import os
import random
import shutil
import sys


def makeBenchmarks(inputRoot, outputRoot):
    found = 0
    selected = 0
    for root, dirs, fnames in os.walk(inputRoot, topdown=True):
        dirs[:] = [d for d in dirs if d != outputRoot]
        for filename in fnames:
            # Random choice of benchmarks
            if filename.endswith(".tlsf"):
                found += 1
                # Only random select if not part of a family
                if (filename.find("_pb_") != -1 and filename.find("_pe_") != -1) or bool(random.getrandbits(1)):
                    selected += 1
                    fullname = os.path.join(root, filename)
                    print(f"Selecting benchmark {fullname}")
                    shutil.copy(fullname,
                                os.path.join(outputRoot, filename))
    print(f"Selected {selected} / {found} benchmarks")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Two positional arguments expected: \n"
              "  (1) the path to the benchmark-family directories\n"
              "  (2) the path where you want the benchmarks\n"
              "The output folder should exist.",
              file=sys.stderr)
        exit(1)
    else:
        makeBenchmarks(sys.argv[1], sys.argv[2])
        exit(0)
