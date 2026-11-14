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
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "app/src/main/java")


def split_top_level(text: str) -> list[str]:
    """Split on commas that are not nested inside (), [] or {}."""
    parts, depth, current = [], 0, ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current)
    return parts


def arity_of(param_type: str) -> int | None:
    """How many parameters a lambda type takes, or None when it is not a lambda.

    `(Int, Int) -> Boolean` is 2, `() -> Unit` is 0, `(@Composable (Int) -> Unit)?`
    is 1. The order matters: strip annotation, strip a wrapping pair of
    parentheses, strip `?`, then read the parameter list. A regex that eats an
    empty `()` would silently turn a zero argument lambda into a one argument
    one, which is why the parentheses are removed by hand.
    """
    t = param_type.strip()
    # Peel the wrappers in whatever order they appear: an annotation can sit
    # outside the parentheses ("@Composable () -> Unit") or inside them
    # ("(@Composable () -> Unit)?"), and both mean the same type.
    for _ in range(6):
        before = t
        if t.startswith("@"):
            if " " not in t:
                return None
            t = t.split(None, 1)[1].strip()
        while t.endswith("?"):
            t = t[:-1].strip()
        if t.startswith("(") and t.endswith(")"):
            # unwrap only when the first paren matches the last character
            depth = 0
            wraps = True
            for i, ch in enumerate(t):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0 and i != len(t) - 1:
                        wraps = False
                        break
            if wraps:
                inner = t[1:-1].strip()
                if "->" in inner or inner.startswith("@"):
                    t = inner
        if t == before:
            break
    # 4. now it must be "(<params>) -> <return>"
    hit = re.match(r"^\(([^)]*)\)\s*->", t)
    if not hit:
        return None
    inner = hit.group(1).strip()
    if not inner:
        return 0
    return len([p for p in split_top_level(inner) if p.strip()])


def params_of(decl: str) -> list[tuple[str, bool, str]]:
    """(name, has_default, declared_type) for each top-level parameter.

    `inner` is the text between the outermost parentheses, which already has
    the wrapping pair removed, so the scan starts at depth 0 and the commas of
    a lambda type such as `(Int, Int) -> Boolean` are protected by their own
    bracket. Starting the scan at depth 1 (the classic off-by-one here) makes
    every lambda parameter swallow the rest of the signature.
    """
    inner = decl[decl.index("(") + 1: decl.rindex(")")]
    parts, depth, current = [], 0, ""
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
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
        if not part:
            continue
        # a parameter-level annotation ("@Composable content: ...") is not the name
        while part.startswith("@"):
            part = part.split(None, 1)[1].strip() if " " in part else ""
        if not part:
            continue
        name = re.match(r"(?:val\s+|var\s+)?(\w+)\s*:", part)
        if not name:
            continue
        after = part.split(":", 1)[1]
        # a default value may itself contain "=" (a comparison, a lambda):
        # the first top-level "=" is the default marker
        depth, cut = 0, len(after)
        for i, ch in enumerate(after):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "=" and depth == 0:
                cut = i
                break
        declared_type = after[:cut].strip()
        has_default = cut < len(after)
        out.append((name.group(1), has_default, declared_type))
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
            required = {p for p, has_default, _ in params if not has_default}
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

                passed = {}
                positional = 0
                for piece in pieces:
                    hit = re.match(r"\s*(\w+)\s*=(?!=)", piece)
                    if hit:
                        passed[hit.group(1)] = piece[hit.end():].strip()
                    elif piece.strip():
                        positional += 1

                missing = required - set(passed)
                if positional:
                    missing -= {p for p, _, _ in params[:positional]}
                # a trailing lambda fills the last parameter (the usual `content`
                # slot), which is legal and extremely common in Compose
                after = text[end:end + 200].lstrip()
                if after.startswith("{"):
                    missing -= {params[-1][0]}
                # A lambda passed to a two-argument slot must take two
                # arguments. `{ false }` in a `(Int, Int) -> Boolean` slot is a
                # compile error in Kotlin and it already reached CI once.
                # A lambda passed to a two-argument slot must take two
                # arguments. `{ false }` in a `(Int, Int) -> Boolean` slot is a
                # compile error in Kotlin, and one already reached CI because
                # nothing checked it locally.
                types = {p: t for p, _, t in params}
                named = [(name_, value) for name_, value in passed.items()]
                positional_args = [piece.strip() for piece in pieces
                                   if not re.match(r"\s*\w+\s*=(?!=)", piece)]
                for index, raw in enumerate(positional_args):
                    if index < len(params):
                        named.append((params[index][0], raw))

                for arg_name, value in named:
                    want = arity_of(types.get(arg_name, ""))
                    if want is None or not value.startswith("{"):
                        continue
                    # take the whole balanced lambda body, not just the first
                    # line: `{ _, _ -> false }` may wrap in the source
                    depth, end_brace = 0, len(value)
                    for i, ch in enumerate(value):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                end_brace = i
                                break
                    body = value[1:end_brace].strip()
                    arrow = re.match(r"^([\w\s,]*?)->", body)
                    if arrow:
                        have = len([x for x in arrow.group(1).split(",") if x.strip()])
                    elif want == 0:
                        continue          # a zero-arg slot ignores the body
                    elif "it" in body:
                        have = 1
                    else:
                        continue          # no parameter list: legal, unused params
                    if have != want:
                        line = text[:call.start()].count("\n") + 1
                        problems.append((path, line, name,
                                         [f"{arg_name} lambda {have} arg, butuh {want}"]))

                if missing:
                    line = text[:call.start()].count("\n") + 1
                    problems.append((path, line, name, sorted(missing)))

    for path, line, name, missing in problems:
        print(f"  {path.replace(ROOT + '/', '')}:{line}  {name}() tanpa {', '.join(missing)}")
    print(f"\n{len(problems)} panggilan bermasalah")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
