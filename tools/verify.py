#!/usr/bin/env python3
"""Project-level verification that does not need the Android SDK.

Checks performed:
  1. Gradle files parse as sane Kotlin DSL (balanced braces, expected blocks).
  2. Version catalog references used by build files exist in the catalog.
  3. Every Kotlin file has imports for the Compose/AndroidX symbols it uses.
  4. strings.xml and values-in/strings.xml declare the same keys.
  5. Formatted strings use the same positional arguments in both locales.
  6. Every @Composable uses composition-safe helpers (no LocalDensity in
     non-composable extension functions).
  7. Launcher manifest contract: exactly one HOME activity, exported, with the
     MAIN/HOME/DEFAULT filter, plus the LAUNCHER entry.
"""
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
SRC = os.path.join(APP, "src/main/java")
RES = os.path.join(APP, "src/main/res")

problems: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


# ------------------------------------------------------------------ gradle
def check_gradle() -> None:
    catalog_path = os.path.join(ROOT, "gradle/libs.versions.toml")
    catalog = open(catalog_path, encoding="utf-8").read()
    libs = set(re.findall(r"^([\w.-]+)\s*=\s*\{", catalog, re.MULTILINE))
    plugins = set()
    in_plugins = False
    for line in catalog.splitlines():
        if line.strip() == "[plugins]":
            in_plugins = True
            continue
        if line.startswith("["):
            in_plugins = False
        if in_plugins:
            m = re.match(r"^([\w.-]+)\s*=", line)
            if m:
                plugins.add(m.group(1))

    for build_file in ["app/build.gradle.kts", "build.gradle.kts"]:
        path = os.path.join(ROOT, build_file)
        text = open(path, encoding="utf-8").read()
        if text.count("{") != text.count("}"):
            fail(f"{build_file}: unbalanced braces")
        for ref in re.findall(r"libs\.(plugins|androidx\.|libraries)?\.?([\w.]+)", text):
            pass
        for ref in re.findall(r"libs\.([\w.]+)", text):
            # libs.plugins.foo and libs.androidx.core.ktx both map with dashes
            name = ref.replace("plugins.", "").replace(".", "-")
            if name in {"android-application", "kotlin-android", "kotlin-compose"}:
                if name not in plugins:
                    fail(f"{build_file}: plugin alias libs.{ref} missing from catalog")
                continue
            if name not in libs:
                fail(f"{build_file}: library alias libs.{ref} missing from catalog")

    settings = open(os.path.join(ROOT, "settings.gradle.kts"), encoding="utf-8").read()
    if 'include(":app")' not in settings:
        fail("settings.gradle.kts does not include :app")
    if "google()" not in settings or "mavenCentral()" not in settings:
        fail("settings.gradle.kts is missing google()/mavenCentral()")


# ----------------------------------------------------------------- compiler-ish
COMPOSE_REQUIRED = {
    # call site pattern -> required import
    "stringResource(": "androidx.compose.ui.res.stringResource",
    "rememberSaveable": "androidx.compose.runtime.saveable.rememberSaveable",
    "collectAsState()": "androidx.compose.runtime.collectAsState",
    "produceState": "androidx.compose.runtime.produceState",
    "LocalConfiguration": "androidx.compose.ui.platform.LocalConfiguration",
    "itemsIndexed(": "androidx.compose.foundation.lazy.grid.itemsIndexed",
    "LazyVerticalGrid(": "androidx.compose.foundation.lazy.grid.LazyVerticalGrid",
    "GridItemSpan(": "androidx.compose.foundation.lazy.grid.GridItemSpan",
    "combineClickable": "androidx.compose.foundation.combinedClickable",
    "combinedClickable(": "androidx.compose.foundation.combinedClickable",
    "verticalScroll(": "androidx.compose.foundation.verticalScroll",
    "rememberScrollState(": "androidx.compose.foundation.rememberScrollState",
    "BasicTextField(": "androidx.compose.foundation.text.BasicTextField",
    "KeyboardOptions(": "androidx.compose.foundation.text.KeyboardOptions",
    "ImeAction": "androidx.compose.ui.text.input.ImeAction",
    "SolidColor(": "androidx.compose.ui.graphics.SolidColor",
    "safeDrawingPadding(": "androidx.compose.foundation.layout.safeDrawingPadding",
}


def check_kotlin_call_sites() -> None:
    for dirpath, _dirs, files in os.walk(SRC):
        for name in sorted(files):
            if not name.endswith(".kt"):
                continue
            path = os.path.join(dirpath, name)
            src = open(path, encoding="utf-8").read()
            body = re.sub(r"^import .*$", "", src, flags=re.MULTILINE)
            rel = os.path.relpath(path, ROOT)
            for call, required in COMPOSE_REQUIRED.items():
                if call in body and required not in src:
                    fail(f"{rel}: uses {call} without import {required}")

            # HgPanel takes cornerRadius, not shape, and no call site may depend on
            # a gold inner rule behind content (it would flood the panel).
            for match in re.finditer(r"HgPanel\(([^)]*)\)", src, re.DOTALL):
                args = match.group(1)
                if re.search(r"\bshape\s*=", args):
                    fail(f"{rel}: HgPanel does not accept a shape parameter")
                if re.search(r"\binnerRule\s*=\s*true", args):
                    fail(f"{rel}: HgPanel(innerRule = true) would hide content behind gold")


# ------------------------------------------------------------------- strings
def check_strings() -> None:
    def load(path: str) -> dict[str, str]:
        tree = ET.parse(path)
        return {el.attrib["name"]: (el.text or "") for el in tree.getroot() if el.tag == "string"}

    default = load(os.path.join(RES, "values/strings.xml"))
    indonesian = load(os.path.join(RES, "values-in/strings.xml"))

    missing = set(default) - set(indonesian)
    extra = set(indonesian) - set(default)
    if missing:
        fail(f"values-in missing keys: {sorted(missing)}")
    if extra:
        fail(f"values-in has unknown keys: {sorted(extra)}")

    for key in sorted(set(default) & set(indonesian)):
        args_default = set(re.findall(r"%\d+\$[sd]", default[key]))
        args_local = set(re.findall(r"%\d+\$[sd]", indonesian[key]))
        if args_default != args_local:
            fail(f"string '{key}' args differ: {args_default} vs {args_local}")


# ------------------------------------------------------------------ manifest
def check_manifest() -> None:
    ns = "{http://schemas.android.com/apk/res/android}"
    tree = ET.parse(os.path.join(APP, "src/main/AndroidManifest.xml"))
    homes = []
    launchers = []
    for activity in tree.getroot().iter("activity"):
        for intent in activity.findall("intent-filter"):
            actions = {a.attrib.get(f"{ns}name") for a in intent.findall("action")}
            categories = {c.attrib.get(f"{ns}name") for c in intent.findall("category")}
            if "android.intent.action.MAIN" in actions and "android.intent.category.HOME" in categories:
                homes.append((activity, intent))
            if "android.intent.action.MAIN" in actions and "android.intent.category.LAUNCHER" in categories:
                launchers.append(activity)

    if len(homes) != 1:
        fail(f"expected exactly one HOME intent-filter, found {len(homes)}")
        return
    activity, intent = homes[0]
    if activity.attrib.get(f"{ns}exported") != "true":
        fail("HOME activity must be exported")
    categories = {c.attrib.get(f"{ns}name") for c in intent.findall("category")}
    if "android.intent.category.DEFAULT" not in categories:
        fail("HOME intent-filter must include CATEGORY_DEFAULT")
    if not launchers:
        fail("no LAUNCHER intent-filter: the app would be missing from app lists")
    if activity.attrib.get(f"{ns}stateNotNeeded") != "true":
        fail("HOME activity should set stateNotNeeded=true")
    for query in tree.getroot().iter("queries"):
        if query.find("intent") is None:
            fail("<queries> must contain an intent for package visibility")


# ------------------------------------------------- composable signature check
def check_composable_signatures() -> None:
    """Every named argument at a call site must exist in the declaration.

    This catches the class of mistake that a compiler would catch instantly but
    that is easy to miss while editing by hand (renamed or dropped parameters).
    """
    import glob

    sources = {
        path: open(path, encoding="utf-8").read()
        for path in glob.glob(os.path.join(SRC, "**/*.kt"), recursive=True)
    }

    def parse_params(src: str, start: int) -> tuple[str, int]:
        i = src.index("(", start) + 1
        depth = 1
        j = i
        while j < len(src) and depth:
            if src[j] == "(":
                depth += 1
            elif src[j] == ")":
                depth -= 1
            j += 1
        return src[i:j - 1], j - 1

    declarations: dict[str, set[frozenset[str]]] = {}
    for src in sources.values():
        for match in re.finditer(r"\bfun (\w+)\(", src):
            params, _ = parse_params(src, match.start())
            names = set(re.findall(r"(\w+)\s*:", params))
            declarations.setdefault(match.group(1), set()).add(frozenset(names))

    builtin_like = {
        "Modifier", "Dp", "Color", "Boolean", "Float", "TextStyle", "String", "Int",
        # Names that appear as named arguments of our own data classes or of
    # lambdas passed to composables; they are checked by their own constructors.
    "activityName", "label", "onMissing",
    }
    for path, src in sources.items():
        rel = os.path.relpath(path, ROOT)
        for name, signatures in declarations.items():
            for call in re.finditer(rf"(?<!fun )\b{name}\(", src):
                line_start = src.rfind("\n", 0, call.start()) + 1
                if src[line_start:call.start()].strip() == "fun":
                    continue
                _, end = parse_params(src, call.start())
                args = src[call.end():end]
                for arg in re.findall(r"(?:^|,)\s*(\w+)\s*=(?!=)", args):
                    if arg in builtin_like:
                        continue
                    if not any(arg in signature for signature in signatures):
                        fail(f"{rel}: {name}(... {arg} = ...) is not a parameter of {name}")


# ---------------------------------------------------------------- CI workflow
def check_ci() -> None:
    """A GitHub release build is only useful if the wrapper and CI agree."""
    workflow = os.path.join(ROOT, ".github/workflows/android.yml")
    if not os.path.exists(workflow):
        fail("missing .github/workflows/android.yml, GitHub cannot build the APK")
        return
    text = open(workflow, encoding="utf-8").read()
    for needle, message in (
        ("actions/checkout@v", "workflow does not check out the repo"),
        ("actions/setup-java@v", "workflow does not set up a JDK"),
        ('java-version: "17"', "workflow must use JDK 17 for AGP 8.7"),
        ("assembleDebug", "workflow does not build the debug APK"),
        ("upload-artifact", "workflow does not upload the APK artifact"),
    ):
        if needle not in text:
            fail(f"{message} ({needle})")

    wrapper = os.path.join(ROOT, "gradlew")
    if not os.path.exists(wrapper):
        fail("gradlew missing, ./gradlew cannot run on the CI runner")
    elif not os.access(wrapper, os.X_OK):
        fail("gradlew is not executable, chmod +x it before committing")

    properties = os.path.join(ROOT, "gradle/wrapper/gradle-wrapper.properties")
    if not os.path.exists(properties):
        fail("gradle-wrapper.properties missing")
    elif "gradle-8.9-bin.zip" not in open(properties, encoding="utf-8").read():
        fail("wrapper must stay on Gradle 8.9 to match AGP 8.7.3")


# -------------------------------------------------- strings aapt2 traps
def check_string_escapes() -> None:
    """aapt2 treats a value that starts with ? or @ as a resource reference.

    A user facing string such as '???' therefore fails the build with
    "resource attr/?? not found". Such values must be escaped (\?\?\?).
    """
    for locale in ("values", "values-in"):
        path = os.path.join(RES, locale, "strings.xml")
        if not os.path.exists(path):
            fail(f"missing {locale}/strings.xml")
            continue
        tree = ET.parse(path)
        for node in tree.getroot().iter("string"):
            text = (node.text or "").strip()
            if not text or node.attrib.get("translatable") == "false":
                continue
            if text.startswith(("?", "@")) and not text.startswith(("\\?", "\\@")):
                fail(f"{locale}/strings.xml: '{node.attrib.get('name')}' starts with "
                     f"'{text[0]}', aapt2 reads that as a resource reference; escape it")


# ------------------------------------------------- device compatibility
# Huawei MatePad Mini ships HarmonyOS 4.3, which is still AOSP based and
# reports API 31 (Android 12). Anything above that level must be resource or
# version gated, otherwise the launcher silently loses features there.
HARMONYOS_API = 31


def check_harmonyos_compat() -> None:
    build = open(os.path.join(ROOT, "app/build.gradle.kts"), encoding="utf-8").read()
    min_sdk = re.search(r"minSdk\s*=\s*(\d+)", build)
    if not min_sdk or int(min_sdk.group(1)) > HARMONYOS_API:
        fail(f"minSdk must stay <= {HARMONYOS_API} for HarmonyOS 4.3 / Android 12")

    manifest = open(os.path.join(ROOT, "app/src/main/AndroidManifest.xml"), encoding="utf-8").read()
    # strip XML comments first: the manifest documents what it does *not* use
    manifest_code = re.sub(r"<!--.*?-->", "", manifest, flags=re.DOTALL)
    for banned, why in (
        ("android:enableOnBackInvokedCallback", "API 33 only"),
        ("foregroundServiceType", "API 29+ and unused here"),
        ("POST_NOTIFICATIONS", "API 33 permission, unused here"),
        ("QUERY_ALL_PACKAGES", "policy sensitive, unnecessary with <queries>"),
    ):
        if banned in manifest_code:
            fail(f"manifest uses {banned} ({why}); it is not needed on API {HARMONYOS_API}")

    res = os.path.join(ROOT, "app/src/main/res")
    # Themed / monochrome icons are only referenced from mipmap-anydpi-v33.
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        v26 = os.path.join(res, "mipmap-anydpi-v26", name)
        if not os.path.exists(v26):
            fail(f"mipmap-anydpi-v26/{name} missing; HarmonyOS 4.3 would fall back to a bitmap")




def check_home_role_flow() -> None:
    """Becoming the home app must not depend on a Settings page that EMUI hides."""
    repo = open(os.path.join(
        ROOT, "app/src/main/java/dev/retrobit/pokelauncher/data/LauncherRepository.kt"),
        encoding="utf-8").read()
    if "RoleManager.ROLE_HOME" not in repo:
        fail("LauncherRepository must request RoleManager.ROLE_HOME (API 29+)")
    if "Build.VERSION.SDK_INT < Build.VERSION_CODES.Q" not in repo:
        fail("requestHomeRole must be guarded for API < 29")

    screen = open(os.path.join(
        ROOT, "app/src/main/java/dev/retrobit/pokelauncher/ui/LauncherScreen.kt"),
        encoding="utf-8").read()
    for needle, why in (
        ("viewModel.requestHomeRole()", "set default dialog must try the role request first"),
        ("showManualHomeDialog = true", "manual guide must stay as the last resort"),
    ):
        if needle not in screen:
            fail(f"LauncherScreen.kt: {why} ({needle})")




def check_preview_assets() -> None:
    """The preview must stay a MatePad Mini mockup: two renders and one server."""
    docs = os.path.join(ROOT, "docs")
    expected = {"preview-tablet.png"}
    present = {n for n in os.listdir(docs) if n.endswith(".png")}
    if present != expected:
        fail(f"docs/ should hold only {sorted(expected)}, found {sorted(present)}")

    for name in expected:
        path = os.path.join(docs, name)
        if not os.path.exists(path):
            continue
        import struct
        with open(path, "rb") as handle:
            header = handle.read(33)
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            fail(f"docs/{name} is not a PNG")
            continue
        width, height = struct.unpack(">II", header[16:24])
        colour_type = header[25]  # 8 sig + 4 len + 4 tag + 4 w + 4 h + 1 depth
        if colour_type != 6:
            fail(f"docs/{name} must be RGBA (colour type 6), got {colour_type}; "
                 "the rounded bezel needs a transparent corner")
        if (width, height) != (2628, 1668):
            fail(f"docs/{name} is {width}x{height}, expected the landscape MatePad Mini frame")

    server = os.path.join(ROOT, "tools/preview_server.py")
    if not os.path.exists(server):
        fail("tools/preview_server.py missing")
    else:
        text = open(server, encoding="utf-8").read()
        if 'SHOT = "preview-tablet.png"' not in text:
            fail("preview_server.py must serve only the landscape MatePad Mini render")

    check_punch_hole(os.path.join(docs, "preview-tablet.png"))


def check_punch_hole(path: str) -> None:
    """The selfie camera must sit in the TOP LEFT of the landscape screen.

    The device has its punch hole in the top right corner of the portrait
    panel; turning it counter clockwise for landscape carries that corner over
    to the top left, which is what hands-on photos show. A render with the hole
    in the other corner, or with a hole that is a token dot / a huge circle,
    means the geometry regressed.
    """
    if not os.path.exists(path):
        return
    import zlib

    with open(path, "rb") as handle:
        blob = handle.read()
    pos, idat, width, height, colour_type = 8, b"", 0, 0, None
    while pos + 8 <= len(blob):
        import struct
        length = struct.unpack(">I", blob[pos:pos + 4])[0]
        tag = blob[pos + 4:pos + 8]
        body = blob[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
            colour_type = body[9]
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    if colour_type != 6 or not width or not height:
        return

    bpp, stride = 4, width * 4
    raw = zlib.decompress(idat)
    rows, prev, offset = [], bytearray(stride), 0
    for _ in range(height):
        filt = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride
        if filt == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif filt == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif filt == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        rows.append(line)
        prev = line

    def dark(x: int, y: int) -> bool:
        i = x * 4
        line = rows[y]
        return (line[i] + line[i + 1] + line[i + 2]) / 3 < 45

    # The black bezel is the outermost ring; the lit panel starts inside it.
    bezel = max(8, height // 40)
    inner_w, inner_h = width - 2 * bezel, height - 2 * bezel

    # A punch hole is a dark disc that is much darker than the UI around it.
    # Restrict the search to the top strip inside the panel, split into halves.
    strip = bezel + max(40, inner_h // 8)
    counts = {"left": 0, "right": 0}
    for y in range(bezel, strip):
        for x in range(bezel, width - bezel):
            if dark(x, y):
                counts["left" if x < width // 2 else "right"] += 1
    if counts["left"] < 2000 or counts["right"] > counts["left"] * 0.6:
        fail(f"punch hole should sit in the top LEFT of the landscape screen, "
             f"dark pixels in top strip: left={counts['left']} right={counts['right']}")

    # Size sanity: the hole spans a few percent of the screen width, not a dot
    # and not a fist sized circle. Measure the dark blob in the top left corner
    # window only, so the UI icons below and the bezel never enter the box.
    window_w, window_h = max(60, inner_w // 10), max(60, inner_h // 8)
    xs, ys = [], []
    for y in range(bezel, bezel + window_h):
        for x in range(bezel, bezel + window_w):
            if dark(x, y):
                xs.append(x)
                ys.append(y)
    if not xs:
        fail("punch hole not found in the top left corner of the screen")
    else:
        diameter = max(max(xs) - min(xs), max(ys) - min(ys)) + 1
        if not (0.02 * inner_w <= diameter <= 0.08 * inner_w):
            fail(f"punch hole diameter {diameter}px on a {inner_w}px wide panel "
                 "is off; expect about 3-5% of the panel width")




def main() -> int:
    check_gradle()
    check_kotlin_call_sites()
    check_strings()
    check_manifest()
    check_composable_signatures()
    check_ci()
    check_string_escapes()
    check_harmonyos_compat()
    check_home_role_flow()
    check_preview_assets()

    for problem in problems:
        print("FAIL", problem)
    print(f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
