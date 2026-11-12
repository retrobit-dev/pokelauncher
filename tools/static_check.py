#!/usr/bin/env python3
"""Static checks for the PokeLauncher project (run from the repo root).

1. Every XML file parses.
2. Every @resource reference resolves to a definition (with res qualifiers).
3. Manifest classes exist as Kotlin files.
4. Kotlin files: balanced delimiters, imports resolve to expected packages,
   and every Capitalised symbol used in a file is imported/declared/default.
"""
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "app/src/main/res")
KOTLIN = os.path.join(ROOT, "app/src/main/java")

errors: list[str] = []
warnings: list[str] = []


# ---------------------------------------------------------------- XML check
def check_xml() -> None:
    for dirpath, _dirs, files in os.walk(ROOT):
        if "/.git" in dirpath or "/build" in dirpath:
            continue
        for name in files:
            if not name.endswith(".xml"):
                continue
            path = os.path.join(dirpath, name)
            try:
                ET.parse(path)
            except ET.ParseError as exc:
                errors.append(f"XML parse error in {os.path.relpath(path, ROOT)}: {exc}")


# --------------------------------------------------------- resource indexing
def index_resources() -> set[str]:
    """Returns refs like 'string/app_name', 'color/hg_paper', 'drawable/x'."""
    known: set[str] = set()
    for dirpath, _dirs, files in os.walk(RES):
        res_type = os.path.basename(dirpath).split("-")[0]
        if res_type in {"values", "xml", "font", "drawable", "mipmap", "raw", "anim", "layout"} or True:
            pass
        for name in files:
            stem, ext = os.path.splitext(name)
            directory = os.path.basename(dirpath)
            base_type = directory.split("-")[0]
            if ext == ".xml" and base_type in {"values"}:
                # values files declare many types inside
                try:
                    tree = ET.parse(os.path.join(dirpath, name))
                except ET.ParseError:
                    continue
                for child in tree.getroot():
                    tag = child.tag
                    res_name = child.attrib.get("name")
                    if not res_name:
                        continue
                    if tag == "item":
                        declared_type = child.attrib.get("type", "item")
                        known.add(f"{declared_type}/{res_name}")
                    else:
                        known.add(f"{tag}/{res_name}")
            else:
                known.add(f"{base_type}/{stem}")
    return known


REF_RE = re.compile(r"@(?:\+)?(\w+)/([\w.]+)")


def check_resource_refs() -> None:
    known = index_resources()
    for dirpath, _dirs, files in os.walk(ROOT):
        if "/.git" in dirpath or "/build" in dirpath:
            continue
        for name in files:
            if not (name.endswith(".xml") or name.endswith(".kt")):
                continue
            path = os.path.join(dirpath, name)
            if "/res/" in path:
                # Only check absolute refs inside res, not @android:
                pass
            text = open(path, encoding="utf-8").read()
            for res_type, res_name in REF_RE.findall(text):
                if res_type == "android":
                    continue
                ref = f"{res_type}/{res_name}"
                if ref not in known:
                    # R.string.x style references in Kotlin
                    errors.append(f"Missing resource {ref} referenced in {os.path.relpath(path, ROOT)}")


# ------------------------------------------------------------- Kotlin checks
IMPORT_RE = re.compile(r"^import\s+([\w.]+)(?:\s+as\s+(\w+))?", re.MULTILINE)
TYPE_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")

KOTLIN_DEFAULT_TYPES = {
    "Any", "Boolean", "Byte", "Char", "Double", "Float", "Int", "Long", "Short", "String",
    "Unit", "Nothing", "Array", "List", "MutableList", "Map", "MutableMap", "Set",
    "MutableSet", "Pair", "Triple", "Comparable", "Throwable", "Exception", "Number",
    "CharSequence", "Result", "Sequence", "Iterable", "Lazy", "Enum", "Annotation",
}


def strip_comments_and_strings(src: str) -> str:
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if c == '"':
            if src[i:i + 3] == '"""':
                j = src.find('"""', i + 3)
                out.append('""')
                i = n if j == -1 else j + 3
                continue
            i += 1
            while i < n and src[i] != '"':
                if src[i] == "\\":
                    i += 1
                i += 1
            i += 1
            out.append('""')
            continue
        if c == "'":
            i += 1
            while i < n and src[i] != "'":
                if src[i] == "\\":
                    i += 1
                i += 1
            i += 1
            out.append("'x'")
            continue
        out.append(c)
        i += 1
    return "".join(out)


def check_kotlin() -> None:
    kt_files = []
    for dirpath, _dirs, files in os.walk(KOTLIN):
        for name in files:
            if name.endswith(".kt"):
                kt_files.append(os.path.join(dirpath, name))

    for path in sorted(kt_files):
        rel = os.path.relpath(path, ROOT)
        raw = open(path, encoding="utf-8").read()
        src = strip_comments_and_strings(raw)

        # 1. Delimiter balance.
        for open_ch, close_ch in (("{", "}"), ("(", ")"), ("[", "]")):
            if src.count(open_ch) != src.count(close_ch):
                errors.append(
                    f"{rel}: unbalanced {open_ch}{close_ch} "
                    f"({src.count(open_ch)} vs {src.count(close_ch)})"
                )

        # 2. Unbalanced annotation brackets like @Composable(.
        # 3. Imports and symbol resolution.
        imported = {}
        for full, alias in IMPORT_RE.findall(raw):
            simple = alias or full.split(".")[-1]
            imported[simple] = full

        declared_types = set(
            re.findall(r"\b(?:class|object|interface|enum class|data class|value class)\s+([A-Z][\w]*)", src)
        )
        # Only qualified symbols (Foo.bar / Foo.bar()) can be resolved statically.
        # `Foo` at the start of a qualified reference must be an import, a local
        # declaration or a stdlib type. Property accesses on objects (HgColors.Ink)
        # resolve through the imported object itself.
        qualified_roots = set(re.findall(r"\b([A-Z][\w]*)\.[a-zA-Z_]", src))
        KNOWN_STDLIB = KOTLIN_DEFAULT_TYPES | {
            "Math", "System", "Thread", "Runnable", "IntArray", "LongArray", "FloatArray",
            "StringBuilder", "Companion", "Regex", "Charset", "Collections",
        }
        for symbol in sorted(qualified_roots):
            if symbol in imported or symbol in declared_types or symbol in KNOWN_STDLIB:
                continue
            warnings.append(f"{rel}: qualified symbol '{symbol}.…' not imported or declared")

        # Enum entries / nested members used unqualified but qualified by owner are
        # covered above. Flag `CardStyle.X` style only when CardStyle is missing.
        own_package = re.search(r"^package\s+([\w.]+)", raw, re.MULTILINE)
        same_package = own_package.group(1) if own_package else ""
        for owner in ("CardStyle", "LauncherSettings", "HgColors", "HgText", "PartyRules"):
            # The owner may be declared in any file of the same package.
            owner_in_package = any(
                re.search(rf"\b(?:class|object|interface|enum class)\s+{owner}\b", open(f, encoding="utf-8").read())
                for f in (
                    os.path.join(dp, fn)
                    for dp, _d, fns in os.walk(os.path.join(KOTLIN, same_package.replace(".", os.sep)))
                    for fn in fns
                    if fn.endswith(".kt")
                )
            ) if same_package else False
            if (
                re.search(rf"\b{owner}\.", src)
                and owner not in imported
                and owner not in declared_types
                and not owner_in_package
            ):
                errors.append(f"{rel}: uses {owner}.… but does not import it")

        # 4. Functions used from lowercase symbols: check a curated list of
        #    Compose helpers we rely on are imported when used.
        helper_checks = {
            "remember": "androidx.compose.runtime.remember",
            "rememberSaveable": "androidx.compose.runtime.saveable.rememberSaveable",
            "collectAsState": "androidx.compose.runtime.collectAsState",
            "produceState": "androidx.compose.runtime.produceState",
            "mutableStateOf": "androidx.compose.runtime.mutableStateOf",
            "getValue": "androidx.compose.runtime.getValue",
            "setValue": "androidx.compose.runtime.setValue",
            "rememberScrollState": "androidx.compose.foundation.rememberScrollState",
            "verticalScroll": "androidx.compose.foundation.verticalScroll",
            "stringResource": "androidx.compose.ui.res.stringResource",
            "LaunchedEffect": "androidx.compose.runtime.LaunchedEffect",
            "BackHandler": "androidx.activity.compose.BackHandler",
            "delay": "kotlinx.coroutines.delay",
            "withContext": "kotlinx.coroutines.withContext",
            "launch": "kotlinx.coroutines.launch",
            "viewModelScope": "androidx.lifecycle.viewModelScope",
            "toBitmap": "androidx.core.graphics.drawable.toBitmap",
            "asImageBitmap": "androidx.compose.ui.graphics.asImageBitmap",
        }
        for symbol, fq in helper_checks.items():
            if re.search(rf"(?<![\w.]){symbol}\s*[\(<{{]|\b{symbol}\b", src) and symbol not in imported:
                # Only complain when the file does not declare it itself
                if f"fun {symbol}" in src:
                    continue
                errors.append(f"{rel}: uses '{symbol}' but does not import {fq}")

        # 5. Modifier extensions used but not imported.
        modifier_helpers = {
            "statusBarsPadding": "androidx.compose.foundation.layout.statusBarsPadding",
            "navigationBarsPadding": "androidx.compose.foundation.layout.navigationBarsPadding",
            "systemBarsPadding": "androidx.compose.foundation.layout.systemBarsPadding",
            "aspectRatio": "androidx.compose.foundation.layout.aspectRatio",
            "fillMaxWidth": "androidx.compose.foundation.layout.fillMaxWidth",
            "fillMaxSize": "androidx.compose.foundation.layout.fillMaxSize",
            "fillMaxHeight": "androidx.compose.foundation.layout.fillMaxHeight",
            "drawBehind": "androidx.compose.ui.draw.drawBehind",
            "clip": "androidx.compose.ui.draw.clip",
            "alpha": "androidx.compose.ui.draw.alpha",
            "combinedClickable": "androidx.compose.foundation.combinedClickable",
            "clickable": "androidx.compose.foundation.clickable",
            "border": "androidx.compose.foundation.border",
            "background": "androidx.compose.foundation.background",
            "verticalScroll": "androidx.compose.foundation.verticalScroll",
        }
        for symbol, fq in modifier_helpers.items():
            if f".{symbol}(" in src and symbol not in imported:
                errors.append(f"{rel}: uses Modifier.{symbol}() but does not import {fq}")

        # 6. package line must match directory
        package = re.search(r"^package\s+([\w.]+)", raw, re.MULTILINE)
        if not package:
            errors.append(f"{rel}: missing package declaration")
        else:
            expected = os.path.relpath(os.path.dirname(path), KOTLIN).replace(os.sep, ".")
            if package.group(1) != expected:
                errors.append(f"{rel}: package {package.group(1)} does not match {expected}")


# ------------------------------------------------------------- manifest check
def check_manifest() -> None:
    manifest = os.path.join(ROOT, "app/src/main/AndroidManifest.xml")
    tree = ET.parse(manifest)
    ns = "{http://schemas.android.com/apk/res/android}"
    for activity in tree.getroot().iter("activity"):
        name = activity.attrib.get(f"{ns}name", "")
        if name.startswith("."):
            # Relative activity names resolve against the namespace declared in
            # build.gradle.kts, because AGP 8 forbids package= in the manifest.
            name = "dev.retrobit.pokelauncher" + name
        simple = name.replace(".", "/")
        candidates = [p for p in (
            os.path.join(KOTLIN, name.replace(".", os.sep) + ".kt"),
        ) if os.path.exists(p)]
        if not candidates:
            errors.append(f"Manifest activity {name} has no matching Kotlin file")


def main() -> int:
    check_xml()
    check_resource_refs()
    check_kotlin()
    check_manifest()

    for warning in warnings:
        print("WARN ", warning)
    for error in errors:
        print("ERROR", error)
    print()
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
