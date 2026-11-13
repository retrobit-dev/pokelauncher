#!/usr/bin/env python3
"""Checks named arguments on calls to this project's own @Composable functions.

    python3 tools/kotlin_calls.py

The compiler catches a missing named argument, but only in CI, which costs a
build. This catches it locally: for every `@Composable fun Name(...)` it reads
the parameter list, then finds `Name(` call sites and reports parameters with no
default that the call never passes.

It understands the common shapes in this project (defaults, trailing lambdas,
nested calls) and stays quiet when unsure, because a false alarm here is worse
than a missed check.
"""
from __future__ import annotations

import glob
import re
import sys

ROOT = "app/src/main/java"


def params_of(decl: str) -> list[tuple[str, bool]]:
    """(name, has_default) for each top-level parameter of a function."""
    inner = decl[decl.index("(") + 1: decl.rindex(")")]
    # split on commas that are not inside (), <>, {} or a default expression
    parts, depth, current = [], 0, ""
    for ch in inner:
        if ch in "(<{[":
            depth += 1
        elif ch in ")>}]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current)

    out = []
    for part in parts:
        part = part.strip()
        if not part or part.startswith("@"):
            continue
        name = re.match(r"(?:val\s+|var\s+)?(\w+)\s*:", part)
        if not name:
            continue
        out.append((name.group(1), "=" in part.split(":", 1)[1]))
    return out


def main() -> int:
    files = sorted(glob.glob(f"{ROOT}/**/*.kt", recursive=True))
    signatures = {}
    for path in files:
        text = open(path, encoding="utf-8").read()
        for match in re.finditer(
            r"@Composable\s+(?:private\s+|internal\s+|public\s+)?fun\s+(\w+)\s*\(((?:.|\n)*?)\)\s*\{",
            text,
        ):
            signatures[match.group(1)] = params_of(
                match.group(1) + "(" + match.group(2) + ")"
            )

    if not signatures:
        print("tidak ada fungsi @Composable ditemukan")
        return 1

    problems = []
    for path in files:
        text = open(path, encoding="utf-8").read()
        for name, params in signatures.items():
            required = {p for p, has_default in params if not has_default}
            if not required:
                continue
            for call in re.finditer(rf"(?<!fun )\b{name}\s*\(", text):
                start = call.end()
                depth, end = 1, start
                while end < len(text) and depth:
                    if text[end] == "(":
                        depth += 1
                    elif text[end] == ")":
                        depth -= 1
                    end += 1
                args = text[start:end - 1]
                if not args.strip():
                    continue  # probably the declaration itself

                # split the argument list on top-level commas only: nested calls,
                # generics and lambdas all contain commas of their own
                # Only brackets and braces nest. Angle brackets are left out on
                # purpose: `food > 0` is a comparison, and counting it as a
                # closing generic makes the split swallow the next argument.
                pieces, depth, current = [], 0, ""
                for ch in args:
                    if ch in "([{":
                        depth += 1
                    elif ch in ")]}":
                        depth -= 1
                    if ch == "," and depth == 0:
                        pieces.append(current)
                        current = ""
                    else:
                        current += ch
                if current.strip():
                    pieces.append(current)

                passed = set()
                positional = 0
                for piece in pieces:
                    hit = re.match(r"\s*(\w+)\s*=(?!=)", piece)
                    if hit:
                        passed.add(hit.group(1))
                    elif piece.strip():
                        positional += 1

                missing = required - passed
                if positional:
                    missing -= {p for p, _ in params[:positional]}
                # a trailing lambda fills the last parameter (the usual `content`
                # slot), which is legal and extremely common in Compose
                after = text[end:end + 200].lstrip()
                if after.startswith("{"):
                    missing -= {params[-1][0]}
                if missing:
                    line = text[:call.start()].count("\n") + 1
                    problems.append((path, line, name, sorted(missing)))

    for path, line, name, missing in problems:
        print(f"  {path.replace(ROOT + '/', '')}:{line}  {name}() tanpa {', '.join(missing)}")
    print(f"\n{len(problems)} panggilan bermasalah")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
