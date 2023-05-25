#!/usr/bin/env python3

import os
import shutil
import sys

from genParametric import generateAllParametric

benchdirs = ["amba/amba",
             "amba/amba_decomposed",
             "amba/amba_gr1/specs",
             "arbiters_s4",
             "arbiters_zoo",
             "collector",
             "detector",
             "detector_unreal",
             "full_arbiter_log",
             "full_arbiter_unreal",
             "generalized_buffer",
             "gui_glue_code_synthesis",
             "lift",
             "lily",
             "load_balancer",
             "load_balancer_unreal",
             "ltl2dba",
             "ltl2dpa",
             "mux",
             "nary_latch",
             "prioritized_arbiter",
             "prioritized_arbiter_log",
             "prioritized_arbiter_unreal",
             "robot_grid",
             "round_robin_arbiter",
             "round_robin_arbiter_unreal",
             "shift",
             "simple_arbiter_log",
             "simple_arbiter_unreal",
             "tsl_paper",
             "tsl_smart_home_jarvis/extracted-benchmarks"
             ]


def makeBenchmarks(inputRoot, outputRoot):
    for d in benchdirs:
        root = os.path.join(inputRoot, d)
        hasParametric = False
        for filename in os.listdir(root):
            if filename == "parametric":
                print("Found parametric benchmarks!")
                hasParametric = True
            elif filename.endswith(".tlsf"):
                fullname = os.path.join(root, filename)
                print(f"Found benchmark {fullname}")
                shutil.copy(fullname,
                            os.path.join(outputRoot, filename))
        if hasParametric:
            generateAllParametric(root, outputRoot)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Two positional arguments expected: "
              "(1) the path to the benchmark-family directories"
              "(2) the path where you want the benchmarks",
              file=sys.stderr)
        exit(1)
    else:
        makeBenchmarks(sys.argv[1], sys.argv[2])
        exit(0)
