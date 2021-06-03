#!/usr/bin/env python3


import os
import re


vrs = {"status": re.compile(r"^//STATUS\s*:\s*(.*)$"),
       "refsize": re.compile(r"^//REF_SIZE\s*:\s*(.*)$"),
       "n": re.compile(r"^\s*n\s*=\s*(.*)\s*;\s*$")}


def getVals(filename):
    f = open(filename, 'r')
    vals = {"status": "unknown",
            "refsize": "0"}
    for line in f:
        for k, r in vrs.items():
            res = r.match(line)
            if res is not None:
                vals[k] = res.group(1).strip()
    f.close()
    return vals


if __name__ == "__main__":
    print(",".join(sorted(vrs)))
    for file in os.listdir("."):
        if not file.startswith("amba_decomposed_arbiter"):
            continue
        vals = getVals(file)
        print(",".join([vals[k] for k in sorted(vrs)]))
