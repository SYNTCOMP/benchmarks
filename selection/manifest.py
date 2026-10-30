import csv
import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path


def check_output_directory(path):
    output = Path(path)
    if not output.exists():
        return
    if not output.is_dir():
        raise ValueError(f"output path is not a directory: {path}")
    if any(output.iterdir()):
        raise ValueError(f"output directory is not empty: {path}; use an empty output directory")


def parse_params(text):
    params = {}
    if text:
        for assignment in text.split(";"):
            name, sep, value = assignment.partition("=")
            name, value = name.strip(), value.strip()
            if (not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name)
                    or not value or "=" in value or name in params):
                raise ValueError(f"invalid parameters: {text!r}")
            params[name] = value
    return params


@dataclass
class Rule:
    pattern: str
    params: dict
    enabled: bool
    reason: str
    line: int


class Manifest:
    def __init__(self, path):
        self.path = Path(path)
        self.rules = []
        try:
            with self.path.open(newline="", encoding="utf-8") as source:
                reader = csv.DictReader(source, strict=True)
                if reader.fieldnames != ["pattern", "params", "enabled", "reason"]:
                    raise ValueError("expected header: pattern,params,enabled,reason")
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError(f"line {reader.line_num}: expected four columns")
                    pattern = row["pattern"].strip()
                    enabled = row["enabled"].strip()
                    if (not pattern or pattern.startswith("/") or "\\" in pattern
                            or ":" in pattern
                            or any(part in ("", ".", "..") for part in pattern.split("/"))):
                        raise ValueError(f"line {reader.line_num}: invalid relative pattern {pattern!r}")
                    if enabled not in ("0", "1"):
                        raise ValueError(f"line {reader.line_num}: enabled must be 0 or 1")
                    try:
                        params = parse_params(row["params"].strip())
                    except ValueError as error:
                        raise ValueError(f"line {reader.line_num}: {error}") from error
                    self.rules.append(Rule(pattern, params, enabled == "1",
                                           row["reason"].strip(), reader.line_num))
        except (OSError, csv.Error, ValueError) as error:
            raise ValueError(f"{self.path}: {error}") from error

    def is_enabled(self, relpath, params=None):
        relpath = Path(relpath).as_posix()
        params = {name: str(value) for name, value in (params or {}).items()}
        enabled, reason = True, ""
        for rule in self.rules:
            if (fnmatch.fnmatchcase(relpath, rule.pattern)
                    and all(params.get(name) == value for name, value in rule.params.items())):
                enabled, reason = rule.enabled, rule.reason
        return enabled, reason
