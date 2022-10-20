#!/usr/bin/env python3

import bz2
import math
import os
import re
import signal
import sys


class TimeoutException(Exception):
    pass


def handler(signum, frame):
    raise TimeoutException("time ran out")


def hoaAccSign(priority):
    if priority == 0:
        return "f"
    rec = [""] * (priority + 1)
    rec[0] = "Inf(0)"
    for p in range(1, priority):
        if p % 2 == 0:
            rec[p] = f"(Inf({p}) | {rec[p - 1]})"
        else:
            rec[p] = f"(Fin({p}) & {rec[p - 1]})"
    if priority % 2 == 0:
        return f"Inf({priority}) | {rec[priority - 1]}"
    else:
        return f"Fin({priority}) & {rec[priority - 1]}"


class ParityGame:
    def __init__(self, filename):
        if filename.endswith(".bz2"):
            f = bz2.open(filename, "rt")
        else:
            f = open(filename, "r")
        # information to be obtained from the file
        self.names = []
        self.succ = []
        self.owner = []
        self.prio = []
        # let's get to reading that file then
        header = True
        for line in f.readlines():
            scolon = line.find(';')
            assert (scolon > -1)
            line = line[:scolon]
            if header:
                header = False
                hdrItems = line.split()
                assert (len(hdrItems) == 2)
                assert (hdrItems[0] == "parity")
                noVtces = int(hdrItems[1]) + 1
                self.prio = [0] * noVtces
                self.owner = [0] * noVtces
                self.succ = [[]] * noVtces
                self.name = [""] * noVtces
                self.maxoutdeg = -1
                self.maxpriority = -1
            else:
                line = re.sub(r",\s*", ",", line)
                vtxInfo = line.split()
                assert (len(vtxInfo) in [4, 5])
                idx = int(vtxInfo[0])
                assert (idx < len(self.prio))
                # start filling details for this vertex then
                self.prio[idx] = int(vtxInfo[1])
                self.maxpriority = max(self.maxpriority,
                                       self.prio[idx])
                self.owner[idx] = int(vtxInfo[2])
                self.succ[idx] = [int(s) for s in vtxInfo[3].split(',')]
                self.maxoutdeg = max(self.maxoutdeg,
                                     len(self.succ[idx]))
                if len(vtxInfo) == 5:
                    self.name[idx] = vtxInfo[4].strip()[1:-1]
                else:
                    self.name[idx] = f"vertex{idx}"
        self.noAP = math.floor(math.log(self.maxoutdeg, 2)) + 1

    def genSuccLabel(self, i, j):
        negAPs = [a for a in range(self.noAP) if ((1 << a) & j) == 0]
        posAPs = [a for a in range(self.noAP) if a not in negAPs]
        if self.owner[i] == 1:
            negAPs = [a + self.noAP for a in negAPs]
            posAPs = [a + self.noAP for a in posAPs]
        negLabel = " & ".join([f"!{a}" for a in negAPs])
        posLabel = " & ".join([str(a) for a in posAPs])
        return f"{negLabel} & {posLabel}"

    def toHoa(self, out=sys.stdout):
        print("HOA: v1", file=out)
        print(f"States: {len(self.prio)}", file=out)
        print("Start: 0", file=out)
        print(f"acc-name: parity max even {self.maxpriority + 1}", file=out)
        sign = hoaAccSign(self.maxpriority)
        print(f"Acceptance: {self.maxpriority + 1} {sign}", file=out)
        names0 = " ".join([f"\"pl0_{i}\"" for i in range(self.noAP)])
        names1 = " ".join([f"\"pl1_{i}\"" for i in range(self.noAP)])
        print(f"AP: {self.noAP * 2} {names0} {names1}", file=out)
        indices1 = " ".join([str(x) for x in range(self.noAP)])
        print(f"controllable-AP: {indices1}", file=out)
        print("properties: deterministic complete colored", file=out)
        print("--BODY--", file=out)
        for i in range(len(self.prio)):
            print(f"State: {i} \"{self.name[i]}\" { {self.prio[i]} }",
                  file=out)
            if len(self.succ[i]) == 1:
                print(f"[t] {self.succ[i][0]}", file=out)
            else:
                # we exclude the first to handle it later
                allLabels = []
                for j in range(1, len(self.succ[i])):
                    label = self.genSuccLabel(i, j)
                    print(f"[{label}] {self.succ[i][j]}", file=out)
                    allLabels.append(label)
                orLabels = " | ".join([f"({lab})" for lab in allLabels])
                negLabels = f"!({orLabels})"
                print(f"[{negLabels}] {self.succ[i][0]}", file=out)

        print("--END--")
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]} requires precisely one argument: "
              "a text file with a list of parity games in PGSolver format")
        exit(1)
    f = open(sys.argv[1])
    for line in f.readlines():
        line = line.strip()
        game = ParityGame(line)
        out = open(line + ".ehoa", "w")
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(10)
        try:
            game.toHoa(out)
            out.close()
        except TimeoutException as ex:
            print(f"Unexpected {ex=}, {type(ex)=}")
            out.close()
            os.remove(line + ".ehoa")
    exit(0)
