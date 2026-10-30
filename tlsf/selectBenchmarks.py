#!/usr/bin/env python3

import os
import shutil
import argparse
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from selection.manifest import Manifest, check_output_directory

from genParametric import generateAllParametric
from utils import sortStrList

parser = argparse.ArgumentParser("Create all tlsf instances")

parser.add_argument("benchmarkpath", type=str,
                    help="the path to the benchmark-family directories")
parser.add_argument("outputpath", type=str,
                    help="the path where you want the benchmarks (must be empty)")
parser.add_argument("-s", "--savestruct", action="store_true",
                    help="If set, creates a structure.json containing "\
                    "information about the benchmark families.")
parser.add_argument("-t", "--treeLike", action="store_true",
                    help="Generate a tree-like structure for all benchmarks")
parser.add_argument("--saveFam", action="store_true",
                    help="Save information about the different families")
parser.add_argument("--manifest", default=os.path.join(os.path.dirname(__file__),
                    "..", "selection", "tlsf.csv"),
                    help="Selection manifest (default: selection/tlsf.csv)")


benchdirs = ["amba/amba", # PSC: I suppose?
             "amba/amba_decomposed",
             "amba/amba_gr1/specs",
             "arbiters_s4",
             "arbiters_zoo",
             "chomp_game",
             "collector",
             "full_arbiter_log",
             "full_arbiter_unreal",
             "generalized_buffer",
             "gui_glue_code_synthesis",
             "lift",
             "lily",
             "load_balancer",
             "load_balancer_unreal",
             "ltl2dba",
             "ltl2dba/non_parametric_from_acacia",
             "ltl2dpa",
             "ltl_f/generated_TLSF",
             "ltl_with_hints",
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
             "tsl_smart_home_jarvis/extracted-benchmarks",
             "sweap",
             ]


def makeBenchmarks(args):
    inputRoot = args.benchmarkpath
    outputRoot = args.outputpath
    check_output_directory(outputRoot)
    treeLike = args.treeLike
    info = {}
    written = dict()
    manifest = Manifest(args.manifest)
    counts = dict(found=0, selected=0, disabled=0)

    for d in benchdirs:
        thisOutputRoot = outputRoot
        if treeLike:
            thisOutputRoot = os.path.join(thisOutputRoot, d)
            os.makedirs(thisOutputRoot, exist_ok=True)
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
                counts["found"] += 1
                enabled, reason = manifest.is_enabled(os.path.relpath(fullname, inputRoot))
                if not enabled:
                    counts["disabled"] += 1
                    print(f"Skipping disabled benchmark {fullname}: {reason}")
                    continue
                counts["selected"] += 1
                shutil.copy(fullname,
                            os.path.join(thisOutputRoot, filename))
                info[d].append(filename)
                written[filename] = None
        if hasParametric:
            info[d] = generateAllParametric(root, thisOutputRoot, treeLike,
                                            manifest, inputRoot, counts)
            groups = info[d].values() if treeLike else [info[d]]
            for filenames in groups:
                for filename in filenames:
                    written[filename] = None
    print(f"selected {counts['selected']} / found {counts['found']}, disabled {counts['disabled']}")
    return info, written

import re, json
parRE = re.compile(r"(.*)_pb_(.*)_pe_.*")

def genFam_(path:str, files, ftype=".tlsf") -> None:

    allFam = dict()

    def store_(inst:str, allFam) -> None:
        par = re.match(parRE, inst)
        if par is None:
            allFam[inst] = [[0, inst]]
        else:
            if len(par.groups()) != 2:
                raise RuntimeError(f"Multiple par groups in {inst}")
            pars = [int(x) for x in par.group(2).split("_")]
            if len(pars) == 1:
                thisFam = allFam.setdefault(par.group(1), [])
            else:
                thisFam = allFam.setdefault(par.group(1), dict())
                for idx in range(len(pars)-2):
                    thisFam = thisFam.setdefault(pars[idx], dict())
                thisFam = thisFam.setdefault(pars[-2], [])
            thisFam.append([pars[-1], inst])
    
    for inst in files:
        if not inst.endswith(ftype):
            continue
        inst = inst[:-5]
        store_(inst, allFam)

    print(allFam)

    def rec_(e):
        if type(e) == list:
            e.sort(key=lambda x:x[0])
        else:
            for k, v in e.items():
                rec_(v)

    rec_(allFam)

    with open(os.path.join(path, "families.json"), "w") as fp:
        json.dump(allFam, fp)

if __name__ == "__main__":
    args = parser.parse_args()
    try:
        info, written = makeBenchmarks(args)
    except ValueError as error:
        parser.error(str(error))
    if args.savestruct:
        with open(os.path.join(args.outputpath, "structure.json"), "w") as fp:
            json.dump(info, fp)

    if args.saveFam:
        genFam_(args.outputpath, written)
    exit(0)
