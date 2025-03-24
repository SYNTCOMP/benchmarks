#!/usr/bin/env python3

import csv
import os
import re
import sys, os
import argparse

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


def generateFromCSV(templateFName, csvFName, outFName, treeLike):
    info = []
    with open(csvFName, "r") as csvfile:
        df = pandas.read_csv(csvfile)
        sortNames = list(df.columns)
        sortNames.remove("status")
        sortNames.remove("refsize")

        df = df.sort_values(sortNames)
        header = list(df.columns)

        for _, row in df.iterrows():
            vals = [(h,r) for h,r in zip(header, row)]
            tags = dict()
            if "status" in header:
                tags["STATUS"] = row.status
            if "refsize" in header:
                tags["REF_SIZE"] = row["refsize"]
            nontags = [(k, str(v)) for (k, v) in vals if k not in ["status", "refsize"]]

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


def generateAllParametric(inputRoot, outputRoot, treeLike: bool):
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
                                   os.path.join(thisOutputRoot, basename), treeLike)
        if treeLike:
            info[basename] = thisInfo
        else:
            info += thisInfo
    return info


parser = argparse.ArgumentParser("parametrized TLSF generator")

parser.add_argument("inPath", type=str, help="The path to the parametric files")
parser.add_argument("outPath", type=str, help="The path where you want the generated files")
parser.add_argument("-t", "--treeLike", action="store_true", help="Generate a tree-like structure for all benchmarks")

if __name__ == "__main__":
    args = parser.parse_args()
    generateAllParametric(args.inPath, args.outPath, args.treeLike)
    exit(0)
