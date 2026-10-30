#!/usr/bin/env python3

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from selection.manifest import Manifest, check_output_directory


DEFAULT_SEED = 2027
LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"
# Same family prefix as tlsf/selectBenchmarks.py's parRE.
parRE = re.compile(r"(.*)_pb_(.*)_pe_.*")


def family(path):
    basename = Path(path).name
    match = parRE.fullmatch(basename)
    return match.group(1) if match else basename


def makeBenchmarks(inputRoot, outputRoot, manifest, target=None, seed=DEFAULT_SEED):
    """Filter first, then sample uniformly from sorted track-relative paths."""
    check_output_directory(outputRoot)
    input_root, output_root = Path(inputRoot), Path(outputRoot)
    if not input_root.is_dir():
        raise ValueError(f"benchmark path is not a directory: {inputRoot}")
    if target is not None and target < 0:
        raise ValueError("target must be non-negative")

    print(f"Seed: {seed}")
    paths = sorted(path.relative_to(input_root).as_posix()
                   for path in input_root.rglob("*.ehoa") if path.is_file())
    disabled = Counter()
    lfs_skipped = 0
    eligible = []
    for path in paths:
        enabled, reason = manifest.is_enabled(path)
        if not enabled:
            disabled[reason] += 1
            continue
        with (input_root / path).open("rb") as source:
            pointer = source.read(len(LFS_PREFIX)) == LFS_PREFIX
        if pointer:
            lfs_skipped += 1
            print(f"WARNING: skipping Git LFS pointer: {path}", file=sys.stderr)
            continue
        eligible.append(path)

    if target is not None and target > len(eligible):
        raise ValueError(f"target {target} exceeds {len(eligible)} eligible benchmarks")
    selected = (eligible if target is None
                else sorted(random.Random(seed).sample(eligible, target)))
    basenames = {}
    for path in selected:
        basename = Path(path).name
        if basename in basenames:
            raise ValueError(f"basename collision: {basenames[basename]} and {path}")
        basenames[basename] = path

    report = {
        "seed": seed,
        "target": target,
        "counts": {
            "found": len(paths),
            "disabled_by_reason": dict(sorted(disabled.items())),
            "lfs_skipped": lfs_skipped,
            "eligible": len(eligible),
            "selected": len(selected),
        },
        "selected": [{"path": path, "family": family(path)} for path in selected],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    for path in selected:
        shutil.copyfile(input_root / path, output_root / Path(path).name)
    with (output_root / "selection.json").open("w", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    print(f"selected {len(selected)} / found {len(paths)}, disabled {sum(disabled.values())}, "
          f"lfs-skipped {lfs_skipped}, eligible {len(eligible)}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Select parity benchmarks")
    parser.add_argument("benchmarkpath", help="Path to the benchmark-family directories")
    parser.add_argument("outputpath", help="Output folder (must be empty; created if absent)")
    parser.add_argument("--manifest", default=Path(__file__).resolve().parent.parent
                        / "selection/parity.csv",
                        help="Selection manifest (default: selection/parity.csv)")
    parser.add_argument("--target", type=int, metavar="N",
                        help="Select exactly N eligible benchmarks (default: all)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, metavar="S",
                        help=f"Random seed (default: {DEFAULT_SEED}); printed on every run")
    args = parser.parse_args()
    try:
        makeBenchmarks(args.benchmarkpath, args.outputpath, Manifest(args.manifest),
                       target=args.target, seed=args.seed)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
