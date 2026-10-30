#!/usr/bin/env python3

import csv
import os
import re
import sys, os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from selection.manifest import Manifest, check_output_directory

import pandas

from utils import sortStrList
import pandas as pd

# changed RE to account for comments after the semicolon
assignREStr = r"^\s*{}\s*=\s*(.*)\s*;.*$"


def generateParametric(templateFName, values, tags, outFName):
    fullName = outFName + "_pb_" +\
               "_".join([v for (_, v) in values]) + \
               "_pe_.tlsf" 
    with open(fullName, "w") as out:
        valREs = {k: re.compile(assignREStr.format(k)) for (k, _) in values}
        with open(templateFName, "r") as template:
            for line in template:
                for k, v in values:
                    res = valREs[k].match(line)
                    if res is not None:
                        line = f"{k} = {v};\n"
                        break
                out.write(line)
        # we also write all tags we know of
        out.write("//#!SYNTCOMP\n")
        for k in tags:
            out.write(f"//{k} : {tags[k]}\n")
        out.write("//#\n")
    return [os.path.basename(fullName)]


def generateFromCSV(templateFName, csvFName, outFName, treeLike,
                    manifest, trackRoot, counts):
    info = []
    with open(csvFName, "r") as csvfile:
        df = pandas.read_csv(csvfile)
        sortNames = list(df.columns)
        sortNames.remove("status")
        sortNames.remove("refsize")

        df = df.sort_values(sortNames)
        header = list(df.columns)
        # Preserve numeric ordering and tag types, but use CSV text for parameters.
        csvfile.seek(0)
        text = pandas.read_csv(csvfile, dtype=str, keep_default_na=False)

        for index, row in df.iterrows():
            tags = dict()
            if "status" in header:
                tags["STATUS"] = row.status
            if "refsize" in header:
                tags["REF_SIZE"] = row["refsize"]
            nontags = [(k, text.at[index, k].strip()) for k in sortNames]
            counts["found"] += 1
            relpath = os.path.relpath(templateFName, trackRoot)
            enabled, reason = manifest.is_enabled(relpath, dict(nontags))
            if not enabled:
                counts["disabled"] += 1
                print(f"Skipping disabled instance {relpath} {dict(nontags)}: {reason}")
                continue
            counts["selected"] += 1

            # If there is more than one nontag, we will create subfolders
            # Difficulty is assumed to increase
            thisOutFName = outFName
            if treeLike and len(nontags) > 1:
                nontags_short = nontags[:-1]
                baseFF, outFF = os.path.split(outFName)
                thisOutFFolder = os.path.join(baseFF, "para_" + outFF + "_" + "_".join([v for (_, v) in nontags_short]))
                os.makedirs(thisOutFFolder, exist_ok=True)
                thisOutFName = os.path.join(thisOutFFolder, outFF)

            info += generateParametric(templateFName, nontags, tags, thisOutFName)
    return info


def selectionRoot(path):
    path = os.path.abspath(path)
    root = path
    while os.path.basename(root) not in ("tlsf", "tlsf-fin"):
        parent = os.path.dirname(root)
        if parent == root:
            return path
        root = parent
    return root


def generateAllParametric(inputRoot, outputRoot, treeLike: bool,
                          manifest=None, trackRoot=None, counts=None):
    if trackRoot is None:
        trackRoot = selectionRoot(inputRoot)
    if manifest is None:
        track = os.path.basename(trackRoot)
        if track not in ("tlsf", "tlsf-fin"):
            track = "tlsf"
        manifest = Manifest(os.path.join(os.path.dirname(__file__), "..",
                                         "selection", track + ".csv"))
    if counts is None:
        counts = dict(found=0, selected=0, disabled=0)
    root = os.path.join(inputRoot, "parametric")
    if treeLike:
        info = {}
    else:
        info = []
    for filename in sortStrList(list(os.listdir(root))):
        if not filename.endswith(".tlsf"):
            continue
        basename = filename[:-5]
        if not os.path.isfile(os.path.join(root, basename + ".csv")):
            raise RuntimeError(f"File {os.path.join(root, basename + ".csv")} needed for parametric generation not found")
        fullname = os.path.join(root, filename)
        print(f"Found template {fullname}")
        thisOutputRoot = outputRoot
        if treeLike:
            thisOutputRoot = os.path.join(thisOutputRoot, "param_" + basename)
            os.makedirs(thisOutputRoot, exist_ok=True)
        thisInfo = generateFromCSV(fullname, os.path.join(root, basename + ".csv"),
                                   os.path.join(thisOutputRoot, basename), treeLike,
                                   manifest, trackRoot, counts)
        if treeLike:
            if thisInfo:
                info[basename] = thisInfo
        else:
            info += thisInfo
    return info


parser = argparse.ArgumentParser("parametrized TLSF generator")

parser.add_argument("inPath", type=str, help="The path to the parametric files")
parser.add_argument("outPath", type=str, help="The path where you want the generated files (must be empty)")
parser.add_argument("-t", "--treeLike", action="store_true", help="Generate a tree-like structure for all benchmarks")
parser.add_argument("--manifest", help="Selection manifest (default: selection/<track>.csv)")

if __name__ == "__main__":
    args = parser.parse_args()
    try:
        check_output_directory(args.outPath)
    except ValueError as error:
        parser.error(str(error))
    manifest = Manifest(args.manifest) if args.manifest else None
    counts = dict(found=0, selected=0, disabled=0)
    generateAllParametric(args.inPath, args.outPath, args.treeLike,
                          manifest=manifest, counts=counts)
    print(f"selected {counts['selected']} / found {counts['found']}, disabled {counts['disabled']}")
    exit(0)
