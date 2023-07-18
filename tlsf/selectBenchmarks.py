#!/usr/bin/env python3

import os
import shutil
import sys
import argparse

from genParametric import generateAllParametric
from utils import sortStrList

<<<<<<< HEAD
benchdirs = ["amba/amba",
=======
parser = argparse.ArgumentParser("Create all tlsf instances")

parser.add_argument("benchmarkpath", type=str, help="the path to the benchmark-family directories")
parser.add_argument("outputpath", type=str, help="the path where you want the benchmarks")
parser.add_argument("-s", "--savestruct", action="store_true",
                    help="If set, creates a structure.json containing information "\
                    "about the benchmark families.")




benchdirs = ["amba/amba", # PSC: I suppose?
>>>>>>> 4c8d3d2 (feat: Generating benchmarks now exports a structure)
             "amba/amba_decomposed",
             "amba/amba_gr1/specs",
             "arbiters_s4",
             "arbiters_zoo",
             "collector",
             # "detector", (equivalent to ltl2dba_C2)
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
             "ltl_f/generated_TLSF",
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


def makeBenchmarks(args):
    inputRoot = args.benchmarkpath
    outputRoot = args.outputpath
    info = {}
    for d in benchdirs:
        root = os.path.join(inputRoot, d)
        hasParametric = False
        info[d] = []
        for filename in sortStrList(list(os.listdir(root))):
            if filename == "parametric":
                print("Found parametric benchmarks!")
                hasParametric = True
            elif filename.endswith(".tlsf"):
                fullname = os.path.join(root, filename)
                print(f"Found benchmark {fullname}")
                info[d].append(filename)
                shutil.copy(fullname,
                            os.path.join(outputRoot, filename))
        if hasParametric:
            info[d] = generateAllParametric(root, outputRoot)
    return info


if __name__ == "__main__":
<<<<<<< HEAD
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
=======
    args = parser.parse_args()
    info = makeBenchmarks(args)
    if args.savestruct:
        import json
        with open(os.path.join(args.outputpath, "structure.json"), "w") as fp:
            json.dump(info, fp)

    exit(0)
>>>>>>> 4c8d3d2 (feat: Generating benchmarks now exports a structure)
