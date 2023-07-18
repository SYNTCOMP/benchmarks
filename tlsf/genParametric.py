#!/usr/bin/env python3

import csv
import os
import re
import sys, os

import pandas

from utils import sortStrList
import pandas as pd

# changed RE to account for comments after the semicolon
assignREStr = r"^\s*{}\s*=\s*(.*)\s*;.*$"


def generateParametric(templateFName, values, tags, outFName):
    fullName = outFName + \
               "_".join([v for (_, v) in values]) + \
               ".tlsf" 
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


def generateFromCSV(templateFName, csvFName, outFName):
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
            info += generateParametric(templateFName, nontags, tags, outFName)
    return info


def generateAllParametric(inputRoot, outputRoot):
    root = os.path.join(inputRoot, "parametric")
    info = []
    for filename in sortStrList(list(os.listdir(root))):
        if filename.endswith(".tlsf"):
            fullname = os.path.join(root, filename)
            print(f"Found template {fullname}")
            info += generateFromCSV(fullname, fullname[:-5] + ".csv",
                                    os.path.join(outputRoot, filename[:-5]))
    return info


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Two positional arguments expected: "
              "(1) the path to the parametric files "
              "(2) the path where you want the generated files",
              file=sys.stderr)
        exit(1)
    else:
        generateAllParametric(sys.argv[1], sys.argv[2])
        exit(0)
