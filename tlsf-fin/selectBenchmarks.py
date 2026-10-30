#!/usr/bin/env python3

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import random
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from selection.manifest import Manifest, check_output_directory


DEFAULT_SEED = 2027
parRE = re.compile(r"(.*)_pb_(.*)_pe_.*")


def family(path):
    basename = Path(path).name
    match = parRE.fullmatch(basename)
    return match.group(1) if match else basename


def output_names(paths):
    """Assign flat names using the whole track, before filtering or sampling."""
    basenames = Counter(Path(path).name for path in paths)
    names = {path: Path(path).name for path in paths if basenames[Path(path).name] == 1}
    reserved = set(names.values())
    candidates = {}
    for path in sorted(paths):
        if basenames[Path(path).name] == 1:
            continue
        parts = Path(path).parts
        parents = list(reversed(parts[:-1]))
        choices = ["_".join(parents[:depth] + [parts[-1]])
                   for depth in range(1, len(parents) + 1)]
        candidates[path] = [name for name in choices if name not in reserved]
        if not candidates[path]:
            raise ValueError(f"cannot assign a unique output filename: {path}")

    # Grow ambiguous prefixes together; an exhausted prefix can stay while
    # the other files in its collision grow further.
    positions = dict.fromkeys(candidates, 0)
    while True:
        counts = Counter(candidates[path][index] for path, index in positions.items())
        ambiguous = [path for path, index in positions.items()
                     if counts[candidates[path][index]] > 1]
        growing = [path for path in ambiguous
                   if positions[path] + 1 < len(candidates[path])]
        if not growing:
            break
        for path in growing:
            positions[path] += 1

    owners = {candidates[path][index]: path for path, index in positions.items()
              if counts[candidates[path][index]] == 1}

    # Before failing, try reallocating earlier prefixes: one file may need a
    # short name while its neighbours can use longer ones.
    def assign(path, seen):
        for name in candidates[path]:
            if name in seen:
                continue
            seen.add(name)
            if name not in owners or assign(owners[name], seen):
                owners[name] = path
                return True
        return False

    for path in ambiguous:
        if not assign(path, set()):
            raise ValueError(f"cannot assign a unique output filename: {path}")
    names.update({path: name for name, path in owners.items()})
    return names


def makeBenchmarks(inputRoot, outputRoot, manifest, seed=DEFAULT_SEED):
    check_output_directory(outputRoot)
    print(f"Seed: {seed}")
    generator = random.Random(seed)
    paths = []
    for root, dirs, fnames in os.walk(inputRoot, topdown=True):
        dirs[:] = sorted(d for d in dirs if d != outputRoot)
        for filename in sorted(fnames):
            if filename.endswith(".tlsf"):
                fullname = os.path.join(root, filename)
                path = Path(os.path.relpath(fullname, inputRoot)).as_posix()
                paths.append(path)
    outputs = output_names(paths)
    found = len(paths)
    selected = []
    disabled = Counter()
    for path in paths:
        fullname = os.path.join(inputRoot, path)
        filename = Path(path).name
        enabled, reason = manifest.is_enabled(path)
        if not enabled:
            disabled[reason] += 1
            print(f"Skipping disabled benchmark {fullname}: {reason}")
            continue
        # Only random select if not part of a family
        if (filename.find("_pb_") != -1 and filename.find("_pe_") != -1) or bool(generator.getrandbits(1)):
            selected.append({"path": path, "family": family(filename), "output": outputs[path]})
            print(f"Selecting benchmark {fullname}")
            shutil.copy(fullname, os.path.join(outputRoot, outputs[path]))
    copied = sum(path.is_file() for path in Path(outputRoot).glob("*.tlsf"))
    assert copied == len(selected), f"copied {copied} files for {len(selected)} selected benchmarks"
    report = {
        "seed": seed,
        "counts": {
            "found": found,
            "disabled_by_reason": dict(sorted(disabled.items())),
            "eligible": found - sum(disabled.values()),
            "selected": len(selected),
        },
        "selected": sorted(selected, key=lambda row: row["path"]),
    }
    with (Path(outputRoot) / "selection.json").open("w", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    print(f"selected {len(selected)} / found {found}, disabled {sum(disabled.values())}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Select TLSF-fin benchmarks")
    parser.add_argument("benchmarkpath", help="Path to the benchmark-family directories")
    parser.add_argument("outputpath", help="Output folder (must exist and be empty)")
    parser.add_argument("--manifest", default=os.path.join(os.path.dirname(__file__),
                        "..", "selection", "tlsf-fin.csv"),
                        help="Selection manifest (default: selection/tlsf-fin.csv)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, metavar="S",
                        help=f"Random seed (default: {DEFAULT_SEED}); printed on every run")
    args = parser.parse_args()
    try:
        makeBenchmarks(args.benchmarkpath, args.outputpath, Manifest(args.manifest), seed=args.seed)
    except ValueError as error:
        parser.error(str(error))
