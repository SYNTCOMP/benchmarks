#!/usr/bin/env python3

import csv
import fnmatch
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from selection.manifest import Manifest


def read_status(template):
    path = template.with_suffix(".csv")
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source, strict=True)
        header = reader.fieldnames or []
        params = [name for name in header if name not in ("refsize", "status")]
        if (not params or len(set(header)) != len(header)
                or "refsize" not in header or "status" not in header):
            raise ValueError(f"{path}: expected parameters...,refsize,status")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}:{reader.line_num}: malformed status row")
            rows.append(({name: row[name].strip() for name in params},
                         row["status"].strip()))
    return rows


def check_manifest(manifest, track_root):
    errors = []
    warnings = []
    suffix = ".ehoa" if track_root.name == "parity" else ".tlsf"
    files = {path.relative_to(track_root).as_posix(): path
             for path in sorted(track_root.rglob("*" + suffix)) if path.is_file()}
    statuses = {}
    for relpath, path in files.items():
        if suffix == ".tlsf" and path.parent.name == "parametric":
            try:
                statuses[relpath] = read_status(path)
            except (OSError, csv.Error, ValueError) as error:
                errors.append(str(error))

    for rule in manifest.rules:
        location = f"{manifest.path}:{rule.line}"
        matches = [name for name in files if fnmatch.fnmatchcase(name, rule.pattern)]
        if not matches:
            kind = "glob matches nothing" if glob.has_magic(rule.pattern) else "benchmark file does not exist"
            errors.append(f"{location}: {kind}: {rule.pattern}")
        for name in matches:
            if not rule.params:
                continue
            if name not in statuses:
                errors.append(f"{location}: params on non-parametric file: {name}")
            elif not any(all(params.get(key) == value for key, value in rule.params.items())
                         for params, _ in statuses[name]):
                errors.append(f"{location}: no status CSV row matches {rule.params}: {name}")

    for name, rows in statuses.items():
        for params, status in rows:
            if (status.lower() not in ("realizable", "unrealizable")
                    and manifest.is_enabled(name, params)[0]):
                values = ";".join(f"{key}={value}" for key, value in params.items())
                warnings.append(f"{track_root.name}/{name} [{values}]: enabled with status {status!r}")
    return errors, warnings


def main():
    root = Path(__file__).resolve().parent.parent
    error_count = 0
    warning_count = 0
    for track in ("tlsf", "tlsf-fin", "parity"):
        try:
            manifest = Manifest(root / "selection" / (track + ".csv"))
        except ValueError as error:
            errors, warnings = [str(error)], []
        else:
            errors, warnings = check_manifest(manifest, root / track)
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        error_count += len(errors)
        warning_count += len(warnings)
    print(f"Checked 3 manifests: {error_count} errors, {warning_count} warnings")
    return bool(error_count)


if __name__ == "__main__":
    sys.exit(main())
