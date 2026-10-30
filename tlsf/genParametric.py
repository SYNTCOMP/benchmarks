#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from selection.manifest import Manifest, check_output_directory

import pandas

from utils import sortStrList


nameREStr = r"(?:[^\W\d]|@)[\w'@]*"
tokenRE = re.compile(r'//[^\n]*|/\*|"(?:\\.|[^"\\])*"|' + nameREStr + r'|\S', re.DOTALL)
commentRE = re.compile(r'/\*|\*/')


def tlsfTokens(source):
    tokens = []
    cursor = 0
    while cursor < len(source):
        match = tokenRE.search(source, cursor)
        if match is None:
            break
        token = match.group()
        cursor = match.end()
        if token == "/*":
            depth = 1
            while depth:
                marker = commentRE.search(source, cursor)
                if marker is None:
                    raise ValueError("unterminated block comment")
                depth += 1 if marker.group() == "/*" else -1
                cursor = marker.end()
        elif token == '"':
            raise ValueError("unterminated string")
        elif not token.startswith("//"):
            tokens.append((token, match.start(), match.end()))
    return tokens


def parameterAssignments(source):
    # Keep source offsets, but ignore comments and treat strings as single tokens.
    tokens = tlsfTokens(source)
    parameters = {}
    depth, section, found = 0, None, False
    for index, (token, _, _) in enumerate(tokens):
        if depth == 0 and token in ("INFO", "GLOBAL", "MAIN"):
            section = token
        if section == "GLOBAL" and depth == 1 and token == "PARAMETERS":
            found = True
            cursor = index + 1
            if cursor >= len(tokens) or tokens[cursor][0] != "{":
                raise ValueError("expected '{' after PARAMETERS")
            cursor += 1
            while cursor < len(tokens) and tokens[cursor][0] != "}":
                name, start, _ = tokens[cursor]
                if (not re.fullmatch(nameREStr, name)
                        or cursor + 2 >= len(tokens) or tokens[cursor + 1][0] != "="):
                    raise ValueError("expected a parameter assignment")
                if name in parameters:
                    raise ValueError(f"duplicate parameter declaration: {name}")
                end = cursor + 2
                brackets = []
                while end < len(tokens):
                    part = tokens[end][0]
                    if part == ";" and not brackets:
                        break
                    if part in ("(", "[", "{"):
                        brackets.append(part)
                    elif part in (")", "]", "}"):
                        if not brackets or brackets.pop() != {")": "(", "]": "[", "}": "{"}[part]:
                            raise ValueError(f"unterminated assignment for parameter {name}")
                    end += 1
                if end == len(tokens) or end == cursor + 2:
                    raise ValueError(f"missing value or semicolon for parameter {name}")
                parameters[name] = (start, tokens[end][2],
                                    tokens[cursor + 2][1], tokens[end - 1][2])
                cursor = end + 1
            if cursor == len(tokens):
                raise ValueError("unterminated PARAMETERS block")
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
    if not found:
        raise ValueError("no GLOBAL PARAMETERS block found")
    return parameters


def substituteParameters(source, values):
    parameters = parameterAssignments(source)
    replacements = dict(values)
    if len(replacements) != len(values):
        raise ValueError("duplicate CSV parameter")
    unknown = replacements.keys() - parameters.keys()
    missing = parameters.keys() - replacements.keys()
    if unknown:
        raise ValueError(f"CSV parameters not declared in template: {', '.join(sorted(unknown))}")
    if missing:
        raise ValueError(f"template parameters missing from CSV: {', '.join(sorted(missing))}")
    edits = []
    for name, (start, end, valueStart, valueEnd) in parameters.items():
        value = replacements[name]
        lineStart = source.rfind("\n", 0, start) + 1
        lineEnd = source.find("\n", end)
        lineEnd = len(source) if lineEnd == -1 else lineEnd + 1
        suffix = source[end:lineEnd]
        try:
            trailingCode = bool(tlsfTokens(suffix))
        except ValueError:
            # Keep the opening of a comment that continues onto another line.
            trailingCode = True
        if (not source[lineStart:start].strip() and not trailingCode
                and "\n" not in source[start:end]):
            # Retain the old generator's formatting for standalone assignments.
            edits.append((lineStart, lineEnd, f"{name} = {value};\n"))
        else:
            edits.append((valueStart, valueEnd, value))
    for start, end, value in sorted(edits, reverse=True):
        source = source[:start] + value + source[end:]
    return source


def runSyfco(args, source=None):
    try:
        result = subprocess.run(["syfco"] + args, input=source, text=True,
                                capture_output=True, check=True)
    except FileNotFoundError as error:
        raise ValueError("syfco is required for parametric generation; "
                         "install it and make it available on PATH") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        raise ValueError(f"syfco {' '.join(args)} failed: {detail}") from error
    return result.stdout


def generateParametric(templateFName, values, tags, outFName):
    fullName = outFName + "_pb_" +\
               "_".join([v for (_, v) in values]) + \
               "_pe_.tlsf"
    with open(templateFName, "r") as template:
        try:
            specification = substituteParameters(template.read(), values)
        except ValueError as error:
            raise ValueError(f"{templateFName}: {error}") from error
    if not specification.endswith("\n"):
        specification += "\n"
    specification += "//#!SYNTCOMP\n"
    for k in tags:
        specification += f"//{k} : {tags[k]}\n"
    specification += "//#\n"
    # Validate the actual output before creating a benchmark file.
    try:
        runSyfco(["-in", "-c"], specification)
    except ValueError as error:
        raise ValueError(f"{fullName}: {error}") from error
    with open(fullName, "w") as out:
        out.write(specification)
    return [os.path.basename(fullName)]


def generateFromCSV(templateFName, csvFName, outFName, treeLike,
                    manifest, trackRoot, counts):
    info = []
    with open(csvFName, "r") as csvfile:
        df = pandas.read_csv(csvfile)
        sortNames = list(df.columns)
        sortNames.remove("status")
        sortNames.remove("refsize")

        df = df.sort_values(sortNames)
        header = list(df.columns)
        # Preserve numeric ordering and tag types, but use CSV text for parameters.
        csvfile.seek(0)
        text = pandas.read_csv(csvfile, dtype=str, keep_default_na=False)

        for index, row in df.iterrows():
            tags = dict()
            if "status" in header:
                tags["STATUS"] = row.status
            if "refsize" in header:
                tags["REF_SIZE"] = row["refsize"]
            nontags = [(k, text.at[index, k].strip()) for k in sortNames]
            counts["found"] += 1
            relpath = os.path.relpath(templateFName, trackRoot)
            enabled, reason = manifest.is_enabled(relpath, dict(nontags))
            if not enabled:
                counts["disabled"] += 1
                print(f"Skipping disabled instance {relpath} {dict(nontags)}: {reason}")
                continue
            counts["selected"] += 1

            # If there is more than one nontag, we will create subfolders
            # Difficulty is assumed to increase
            thisOutFName = outFName
            if treeLike and len(nontags) > 1:
                nontags_short = nontags[:-1]
                baseFF, outFF = os.path.split(outFName)
                thisOutFFolder = os.path.join(baseFF, "para_" + outFF + "_" + "_".join([v for (_, v) in nontags_short]))
                os.makedirs(thisOutFFolder, exist_ok=True)
                thisOutFName = os.path.join(thisOutFFolder, outFF)

            info += generateParametric(templateFName, nontags, tags, thisOutFName)
    return info


def selectionRoot(path):
    path = os.path.abspath(path)
    root = path
    while os.path.basename(root) not in ("tlsf", "tlsf-fin"):
        parent = os.path.dirname(root)
        if parent == root:
            return path
        root = parent
    return root


def generateAllParametric(inputRoot, outputRoot, treeLike: bool,
                          manifest=None, trackRoot=None, counts=None):
    if trackRoot is None:
        trackRoot = selectionRoot(inputRoot)
    if manifest is None:
        track = os.path.basename(trackRoot)
        if track not in ("tlsf", "tlsf-fin"):
            track = "tlsf"
        manifest = Manifest(os.path.join(os.path.dirname(__file__), "..",
                                         "selection", track + ".csv"))
    if counts is None:
        counts = dict(found=0, selected=0, disabled=0)
    root = os.path.join(inputRoot, "parametric")
    if treeLike:
        info = {}
    else:
        info = []
    for filename in sortStrList(list(os.listdir(root))):
        if not filename.endswith(".tlsf"):
            continue
        basename = filename[:-5]
        if not os.path.isfile(os.path.join(root, basename + ".csv")):
            raise RuntimeError(f"File {os.path.join(root, basename + ".csv")} needed for parametric generation not found")
        fullname = os.path.join(root, filename)
        print(f"Found template {fullname}")
        thisOutputRoot = outputRoot
        if treeLike:
            thisOutputRoot = os.path.join(thisOutputRoot, "param_" + basename)
            os.makedirs(thisOutputRoot, exist_ok=True)
        thisInfo = generateFromCSV(fullname, os.path.join(root, basename + ".csv"),
                                   os.path.join(thisOutputRoot, basename), treeLike,
                                   manifest, trackRoot, counts)
        if treeLike:
            if thisInfo:
                info[basename] = thisInfo
        else:
            info += thisInfo
    return info


parser = argparse.ArgumentParser("parametrized TLSF generator")

parser.add_argument("inPath", type=str, help="The path to the parametric files")
parser.add_argument("outPath", type=str, help="The path where you want the generated files (must be empty)")
parser.add_argument("-t", "--treeLike", action="store_true", help="Generate a tree-like structure for all benchmarks")
parser.add_argument("--manifest", help="Selection manifest (default: selection/<track>.csv)")

if __name__ == "__main__":
    args = parser.parse_args()
    try:
        check_output_directory(args.outPath)
        manifest = Manifest(args.manifest) if args.manifest else None
        counts = dict(found=0, selected=0, disabled=0)
        generateAllParametric(args.inPath, args.outPath, args.treeLike,
                              manifest=manifest, counts=counts)
    except ValueError as error:
        parser.error(str(error))
    print(f"selected {counts['selected']} / found {counts['found']}, disabled {counts['disabled']}")
    exit(0)
