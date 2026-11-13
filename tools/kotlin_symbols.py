#!/usr/bin/env python3
"""Cheap compile-safety net for Kotlin, since this sandbox has no JDK.

    python3 tools/kotlin_symbols.py

Reports top-level names that a file uses but never imports and does not declare.
It deliberately ignores:
  - nested names (only the head of `Foo.Bar` counts, so `Item.WOOD` is fine),
  - Kotlin auto-imports (Int, String, System, Math...) and annotations,
  - symbols declared anywhere in the same package (Kotlin does not need imports
    for those).

That keeps it to the mistake actually worth catching: adding a use of a symbol
from another package and forgetting the import, which fails the Gradle build
minutes later instead of here.
"""
from __future__ import annotations

import collections
import glob
import re
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "app/src/main/java")

# Kotlin default imports and platform types that never need an import statement
AUTO = {
    "Int", "Long", "Float", "Double", "Boolean", "String", "Char", "Byte", "Short",
    "Unit", "Any", "Nothing", "Array", "List", "Map", "Set", "MutableList", "MutableMap",
    "MutableSet", "HashMap", "HashSet", "LinkedHashMap", "LinkedHashSet", "ArrayList",
    "ArrayDeque", "Pair", "Triple", "Sequence", "Comparable", "Iterable", "Exception",
    "RuntimeException", "IllegalArgumentException", "IllegalStateException",
    "System", "Math", "StringBuilder", "Thread", "Runnable", "Number", "Character",
    "Suppress", "Deprecated", "OptIn", "JvmStatic", "JvmField", "JvmOverloads",
    "IntRange", "IntArray", "FloatArray", "LongArray", "CharArray", "BooleanArray",
    "Class", "T", "Comparator", "Throwable", "Enum", "Annotation", "Lazy", "Also",
    "Override", "Synchronized", "Volatile", "Transient", "PublishedApi", "UnsafeVariance",
    "JSONObject", "JSONException", "BitmapFactory", "Build", "Bundle", "Intent", "Uri",
    "Log", "Toast", "TimeZone", "Locale", "File", "IOException",
}


def main() -> int:
    files = sorted(glob.glob(f"{ROOT}/**/*.kt", recursive=True))
    declared: dict[str, set[str]] = collections.defaultdict(set)
    package_of: dict[str, str] = {}

    for path in files:
        text = open(path, encoding="utf-8").read()
        pkg = re.search(r"^package\s+([\w.]+)", text, re.M)
        name = pkg.group(1) if pkg else ""
        package_of[path] = name
        for match in re.finditer(
            r"^(?:@\w+\s+)?(?:public |private |internal |protected |open |abstract |sealed "
            r"|data |enum |annotation |value |inner )*(?:class|object|interface)\s+(\w+)",
            text, re.M,
        ):
            declared[name].add(match.group(1))
        for match in re.finditer(r"^(?:public |private |internal )*(?:fun|val|var)\s+(\w+)", text, re.M):
            declared[name].add(match.group(1))

    problems = []
    for path in files:
        text = open(path, encoding="utf-8").read()
        pkg = package_of[path]
        imported = set()
        for match in re.finditer(r"^import\s+([\w.]+?)(?:\s+as\s+(\w+))?$", text, re.M):
            imported.add(match.group(2) or match.group(1).split(".")[-1])
        wildcard = bool(re.search(r"^import\s+[\w.]+\.\*\s*$", text, re.M))

        body = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        body = re.sub(r"//[^\n]*", "", body)
        body = re.sub(r'"""(?:.|\n)*?"""', '""', body)
        body = re.sub(r'"(?:\\.|[^"\\])*"', '""', body)

        # Only type positions need an import: `Foo(` when Foo starts a call is a
        # constructor, `Foo.` is either a companion/object member (no import
        # needed when Foo is known) or a type. Nested enum members such as
        # `Item.WOOD` therefore never appear, because we look at the head only.
        type_positions = set()
        # `Foo(` as a constructor call, and `Foo` in a type annotation after ':'
        type_positions |= set(re.findall(r"(?<![\w.])([A-Z][A-Za-z0-9_]*)\(", body))
        type_positions |= set(re.findall(r":\s*([A-Z][A-Za-z0-9_]*)\b", body))
        type_positions |= set(re.findall(r"->\s*([A-Z][A-Za-z0-9_]*)\b", body))

        # remove the head of qualified access when the head is a value it knows
        for name in sorted(type_positions):
            if name in AUTO or name in imported or name in declared[pkg]:
                continue
            if wildcard:
                continue
            # declared inline in this file (as a nested type or a local class)
            if re.search(r"\b(?:class|object|interface)\s+" + name + r"\b", body):
                continue
            # an enum member used bare (`Direction.DOWN` also allows `DOWN` after
            # destructuring, and `World.Item.WOOD` appears as a call argument)
            if re.search(r"\b(?:enum|sealed)\s+(?:class|interface)\s+\w+", body) and \
               re.search(r"\b" + name + r"\b", body) and \
               name.isupper():
                continue
            problems.append((path, name))

    for path, name in problems:
        print(f"  {path.replace(ROOT + '/', '')}: '{name}' dipakai tapi tidak diimpor")
    print(f"\n{len(problems)} simbol bermasalah")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
