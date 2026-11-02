#!/usr/bin/env python3
"""Build the deduplicated 2026 TLSF and parity panels with the current selectors."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from selection.manifest import Manifest, check_output_directory
from selection.checkSelection import check_manifest, check_parity_duplicates, check_tlsf_duplicates


def build(output):
    check_output_directory(output)
    parity_manifest = Path(__file__).with_name("parity.csv")
    for track, path, check in (("tlsf", ROOT / "selection/tlsf.csv", check_tlsf_duplicates),
                               ("parity", parity_manifest, check_parity_duplicates)):
        manifest = Manifest(path)
        errors, _ = check_manifest(manifest, ROOT / track)
        duplicate_errors, _ = check(manifest, ROOT / track)
        if errors or duplicate_errors:
            raise ValueError("\n".join(errors + duplicate_errors))
    output.mkdir(parents=True, exist_ok=True)
    (output / "tlsf").mkdir()
    commands = [
        [sys.executable, "-B", "tlsf/selectBenchmarks.py", "tlsf", str(output / "tlsf"),
         "--saveFam", "-s"],
        [sys.executable, "-B", "parity/selectBenchmarks.py", "parity", str(output / "parity"),
         "--manifest", str(parity_manifest), "--seed", "2026"],
    ]
    for command, track in zip(commands, ("tlsf", "parity")):
        with (output / (track + ".log")).open("w") as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    parity_report = json.loads((output / "parity/selection.json").read_text())
    if parity_report["counts"]["lfs_skipped"]:
        raise ValueError("parity release is incomplete: download Git LFS contents first")
    counts = {track: len(list((output / track).glob("*" + suffix)))
              for track, suffix in (("tlsf", ".tlsf"), ("parity", ".ehoa"))}
    if counts != {"tlsf": 1541, "parity": 432}:
        raise ValueError(f"unexpected panel sizes: {counts}; inspect changed inputs before releasing")
    with parity_manifest.with_name("parity-v2026.csv").open(newline="") as source:
        original = list(csv.DictReader(source))
    expected = {row["representative"] for row in original}
    if {row["path"] for row in parity_report["selected"]} != expected:
        raise ValueError("parity selection does not preserve exactly the v2026 groups")
    for row in original:
        data = (ROOT / "parity" / row["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError(f"original v2026 parity game changed: {row['path']}")
    report = {
        "release": "syntcomp26v2",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version.split()[0],
        "syfco": subprocess.check_output(["syfco", "--version"], text=True).splitlines()[0],
        "counts": counts,
        "sha256": {},
    }
    for track in counts:
        members = {}
        with zipfile.ZipFile(output / (track + ".zip"), "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as archive:
            for path in sorted((output / track).iterdir()):
                relative = track + "/" + path.name
                data = path.read_bytes()
                info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data, compresslevel=9)
                members[relative] = hashlib.sha256(data).hexdigest()
        report["sha256"][track] = members
    (output / "selection-audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for name in ("tlsf.csv", "parity.csv", "tlsf-game-audit.csv", "tlsf-game-origins.csv"):
        shutil.copyfile(ROOT / "selection" / name, output / name)
    shutil.copyfile(ROOT / "tlsf/duplicates.csv", output / "tlsf-duplicates.csv")
    shutil.copyfile(ROOT / "parity/duplicates.csv", output / "parity-duplicates.csv")
    shutil.copyfile(parity_manifest, output / "parity-v2.csv")
    shutil.copyfile(parity_manifest.with_name("parity-v2026.csv"), output / "parity-v2026.csv")
    names = sorted(path for path in output.iterdir() if path.is_file())
    (output / "SHA256SUMS").write_text("".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n" for path in names))
    print(json.dumps(counts, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="empty output directory")
    args = parser.parse_args()
    try:
        build(args.output.resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
