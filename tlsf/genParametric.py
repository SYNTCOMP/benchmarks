#!/usr/bin/env python3

import csv
import os
import re
import sys

# changed RE to account for comments after the semicolon
assignREStr = r"^\s*{}\s*=\s*(.*)\s*;.*$"


def generateParametric(templateFName, values, tags, outFName):
    out = open(outFName +
               "_".join([values[k] for k in sorted(values)]) +
               ".tlsf", "w")
    valREs = {k: re.compile(assignREStr.format(k)) for k in values}
    with open(templateFName, "r") as template:
        for line in template:
            for k in values:
                res = valREs[k].match(line)
                if res is not None:
                    line = f"{k} = {values[k]};\n"
                    break
            out.write(line)
    # we also write all tags we know of
    out.write("//#!SYNTCOMP\n")
    for k in tags:
        out.write(f"//{k} : {tags[k]}\n")
    out.write("//#\n")
    out.close()


def generateFromCSV(templateFName, csvFName, outFName):
    with open(csvFName, "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        lineCount = 0
        for row in reader:
            if lineCount == 0:
                header = row.copy()
            else:
                vals = dict(zip(header, row))
                tags = dict()
                if "status" in vals:
                    tags["STATUS"] = vals["status"]
                if "refsize" in vals:
                    tags["REF_SIZE"] = vals["refsize"]
                nontags = {k: vals[k] for k in vals
                           if k not in ["status", "refsize"]}
                print("Retrieved tags and values from csv")
                print(f"{vals}")
                generateParametric(templateFName, nontags, tags, outFName)
            lineCount += 1


def generateAllParametric(inputRoot, outputRoot):
    root = os.path.join(inputRoot, "parametric")
    for filename in os.listdir(root):
        if filename.endswith(".tlsf"):
            fullname = os.path.join(root, filename)
            print(f"Found template {fullname}")
            generateFromCSV(fullname, fullname[:-5] + ".csv",
                            os.path.join(outputRoot, filename[:-5]))


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
