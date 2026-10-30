#!/usr/bin/env python3

import csv
import fnmatch
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from selection.manifest import Manifest


def read_status(path, warnings):
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source, strict=True)
        header = reader.fieldnames or []
        params = [name for name in header if name not in ("refsize", "status")]
        if (not params or len(set(header)) != len(header)
                or "refsize" not in header or "status" not in header):
            raise ValueError(f"{path}: expected parameters...,refsize,status")
        rows = []
        seen = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}:{reader.line_num}: malformed status row")
            values = {name: row[name].strip() for name in params}
            key = tuple(values.items())
            if key in seen:
                assignments = ";".join(f"{name}={value}" for name, value in values.items())
                warnings.append(f"{path}:{reader.line_num}: duplicate parameter row "
                                f"[{assignments}]; first at line {seen[key]}")
            else:
                seen[key] = reader.line_num
            rows.append((values, row["status"].strip()))
    return rows


def check_manifest(manifest, track_root):
    errors = []
    warnings = []
    suffix = ".ehoa" if track_root.name == "parity" else ".tlsf"
    files = {path.relative_to(track_root).as_posix(): path
             for path in sorted(track_root.rglob("*" + suffix)) if path.is_file()}
    statuses = {}
    if suffix == ".tlsf":
        # Include CSVs without a template, and still diagnose missing template CSVs.
        csv_paths = {path for path in track_root.rglob("*.csv")
                     if path.parent.name == "parametric" and path.is_file()}
        csv_paths.update(path.with_suffix(".csv") for path in files.values()
                         if path.parent.name == "parametric")
        for path in sorted(csv_paths):
            try:
                rows = read_status(path, warnings)
                relpath = path.with_suffix(".tlsf").relative_to(track_root).as_posix()
                if relpath in files:
                    statuses[relpath] = rows
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


def check_parity_duplicates(manifest, track_root):
    """Check recorded exclusions without loading or comparing benchmark games."""
    duplicates = track_root / "duplicates.csv"
    try:
        with duplicates.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source, strict=True)
            if reader.fieldnames != ["group", "level", "path", "representative"]:
                raise ValueError("expected header: group,level,path,representative")
            rows = []
            for row in reader:
                if (None in row or any(not value for value in row.values())
                        or row["level"] not in ("identical", "isomorphic", "suspected")):
                    raise ValueError(f"line {reader.line_num}: malformed duplicate row")
                if row["level"] != "suspected" and row["path"] != row["representative"]:
                    rows.append(row)
    except (OSError, csv.Error, ValueError) as error:
        return [f"{duplicates}: {error}"], []

    root = track_root.resolve()
    benchmarks = {path.relative_to(track_root).as_posix()
                  for path in track_root.rglob("*.ehoa")
                  if path.is_file() and path.resolve().is_relative_to(root)}

    def has_enabled_replacement(path):
        visited = set()
        while path not in visited and path in benchmarks:
            visited.add(path)
            enabled, reason = manifest.is_enabled(path)
            if enabled:
                return True
            if not reason.startswith("duplicate-of:"):
                return False
            path = reason[len("duplicate-of:"):]
        return False

    errors, warnings = [], []
    representatives = set()
    for row in rows:
        enabled, reason = manifest.is_enabled(row["path"])
        if enabled:
            errors.append(f"{manifest.path}: confirmed duplicate {row['path']} must be disabled "
                          f"(representative: {row['representative']})")
        # A duplicate-of reason may explicitly designate a replacement representative.
        representative = (reason[len("duplicate-of:"):]
                          if not enabled and reason.startswith("duplicate-of:")
                          else row["representative"])
        representatives.add(representative)
    for representative in sorted(representatives):
        if not has_enabled_replacement(representative):
            _, reason = manifest.is_enabled(representative)
            warnings.append(f"{manifest.path}: duplicate representative {representative} "
                            f"has no enabled replacement (reason: {reason!r})")
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
            if track == "parity":
                duplicate_errors, duplicate_warnings = check_parity_duplicates(manifest, root / track)
                errors.extend(duplicate_errors)
                warnings.extend(duplicate_warnings)
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
