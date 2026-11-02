#!/usr/bin/env python3
"""Rebuild the current TLSF games traced from parity issue #55.

Needs pandas, SyFCo and Spot's ltl2tgba. Run findDuplicates.py on the output
afterwards. This does not edit either selection manifest or duplicate table.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tlsf"))
from genParametric import substituteParameters
from selection.manifest import check_output_directory, parse_params


def verify(output):
    """Verify the recorded pairs exactly, requiring vertex 0 to map to 0."""
    from parity.findDuplicates import read_game, seed_colours, predecessors, isomorphic
    with (ROOT / "selection/tlsf-game-audit.csv").open(newline="") as source:
        instances = {(row["path"], row["params"]): row["instance"] for row in csv.DictReader(source)}
    with (ROOT / "tlsf/duplicates.csv").open(newline="") as source:
        rows = list(csv.DictReader(source))
    cache = {}

    def load(key):
        if key not in cache:
            game = read_game(output / (instances[key] + ".ehoa"))
            signatures = [s + (v == 0,) for v, s in enumerate(seed_colours(game, predecessors(game)))]
            cache[key] = (game, signatures)
        return cache[key]

    verified = 0
    for row in rows:
        key = (row["path"], row["params"])
        representative = (row["representative"], row["representative_params"])
        if key == representative:
            continue
        a, sa = load(key)
        b, sb = load(representative)
        palette = {s: i for i, s in enumerate(sorted(set(sa + sb)))}
        if isomorphic(a, b, [palette[s] for s in sa], [palette[s] for s in sb], timeout=10) is not True:
            raise ValueError(f"rooted game equality not confirmed: {key} / {representative}")
        verified += 1
    print(f"Verified {verified} duplicate pairs, preserving the initial vertex")


def colorize(hoa):
    """Complete max-even colours without changing acceptance of unmarked runs.

    Shift existing priorities by two, and mark empty transitions with losing
    priority 1. Thus infinitely many marked edges dominate the new neutral
    colour; an entirely unmarked suffix remains rejecting. Buchi is the
    special case with accepting priority 2 and unmarked priority 1.
    """
    header, body = hoa.split("--BODY--\n")
    if "acc-name: Buchi\n" in header:
        header = header.replace("acc-name: Buchi", "acc-name: parity max even 3")
        header = header.replace("Acceptance: 1 Inf(0)",
                                "Acceptance: 3 Inf(2) | (Fin(1) & Inf(0))")
        shift = lambda match: "{2}"
    else:
        if all(re.search(r"\{\d+\}$", line) for line in body.splitlines()
               if line.startswith("[")):
            return hoa
        match = re.search(r"acc-name: parity max even (\d+)", header)
        if not match:
            raise ValueError("expected max-even parity acceptance")
        count, expression = int(match[1]) + 2, "Inf(0)"
        for priority in range(1, count):
            expression = (f"Inf({priority}) | ({expression})" if priority % 2 == 0
                          else f"Fin({priority}) & ({expression})")
        header = re.sub(r"acc-name: parity max even \d+",
                        f"acc-name: parity max even {count}", header)
        header = re.sub(r"Acceptance: .*", f"Acceptance: {count} {expression}", header)
        shift = lambda match: "{" + str(int(match[1]) + 2) + "}"
    lines = []
    for line in body.splitlines():
        if line.startswith("["):
            line = (re.sub(r"\{(\d+)\}$", shift, line)
                    if re.search(r"\{\d+\}$", line) else line + " {1}")
        lines.append(line)
    return header + "--BODY--\n" + "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="empty output directory")
    parser.add_argument("--syfco", default="syfco")
    parser.add_argument("--ltl2tgba", default="ltl2tgba")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--verify", action="store_true", help="verify recorded pairs in an existing output")
    args = parser.parse_args()
    if args.verify:
        verify(args.output)
        return
    if args.jobs < 1 or args.timeout <= 0:
        parser.error("jobs and timeout must be positive")
    check_output_directory(args.output)
    args.output.mkdir(parents=True, exist_ok=True)
    with (ROOT / "selection/tlsf-game-audit.csv").open(newline="") as source:
        rows = list(csv.DictReader(source))

    def run(command, source=None):
        return subprocess.run(command, input=source, capture_output=True, text=True,
                              check=True, timeout=args.timeout).stdout

    def translate(row):
        source = (ROOT / "tlsf" / row["path"]).read_text()
        if row["params"]:
            source = substituteParameters(source, list(parse_params(row["params"]).items()))
        formula = run([args.syfco, "-in", "-f", "ltl", "-m", "fully", "-os", "mealy"], source)
        outputs = {name.strip() for name in run([args.syfco, "-in", "-outs"], source).split(",")}
        hoa = run([args.ltl2tgba, "-D", "-C", "--colored-parity=max even", "--high",
                   "--hoaf=t", "-f", formula.strip()])
        ap = next(line for line in hoa.splitlines() if line.startswith("AP:"))
        names = re.findall(r'"((?:\\.|[^"\\])*)"', ap)
        controlled = " ".join(str(i) for i, name in enumerate(names) if name in outputs)
        hoa = colorize(hoa).replace("--BODY--", "controllable-AP: " + controlled + "\n--BODY--")
        (args.output / (row["instance"] + ".ehoa")).write_text(hoa)
        return row["instance"]

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for name in pool.map(translate, rows):
            print(name, flush=True)
    versions = {"syfco": run([args.syfco, "--version"]).splitlines()[0],
                "ltl2tgba": run([args.ltl2tgba, "--version"]).splitlines()[0]}
    (args.output / "versions.json").write_text(json.dumps(versions, indent=2) + "\n")


if __name__ == "__main__":
    main()
