#!/usr/bin/env python3

import os
import random
import shutil
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from selection.manifest import Manifest, check_output_directory


def makeBenchmarks(inputRoot, outputRoot, manifest):
    check_output_directory(outputRoot)
    found = 0
    selected = 0
    disabled = 0
    for root, dirs, fnames in os.walk(inputRoot, topdown=True):
        dirs[:] = [d for d in dirs if d != outputRoot]
        for filename in fnames:
            # Random choice of benchmarks
            if filename.endswith(".tlsf"):
                found += 1
                fullname = os.path.join(root, filename)
                enabled, reason = manifest.is_enabled(os.path.relpath(fullname, inputRoot))
                if not enabled:
                    disabled += 1
                    print(f"Skipping disabled benchmark {fullname}: {reason}")
                    continue
                # Only random select if not part of a family
                if (filename.find("_pb_") != -1 and filename.find("_pe_") != -1) or bool(random.getrandbits(1)):
                    selected += 1
                    print(f"Selecting benchmark {fullname}")
                    shutil.copy(fullname,
                                os.path.join(outputRoot, filename))
    print(f"selected {selected} / found {found}, disabled {disabled}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Select TLSF-fin benchmarks")
    parser.add_argument("benchmarkpath", help="Path to the benchmark-family directories")
    parser.add_argument("outputpath", help="Output folder (must exist and be empty)")
    parser.add_argument("--manifest", default=os.path.join(os.path.dirname(__file__),
                        "..", "selection", "tlsf-fin.csv"),
                        help="Selection manifest (default: selection/tlsf-fin.csv)")
    args = parser.parse_args()
    try:
        makeBenchmarks(args.benchmarkpath, args.outputpath, Manifest(args.manifest))
    except ValueError as error:
        parser.error(str(error))
