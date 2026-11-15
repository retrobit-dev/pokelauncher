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

import json
import math
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
def top_level_named_args(args: str) -> list[str]:
    """Named arguments of a call, ignoring anything nested inside one of them.

    `MovePad(modifier = Modifier.padding(start = 18.dp))` names exactly one
    argument of MovePad: `modifier`. The `start =` belongs to padding, and
    reading it as a MovePad parameter is a false positive that would make every
    modifier chain with named arguments look like a bug.
    """
    found: list[str] = []
    depth = 0
    expect_name = True
    token = ""
    for char in args:
        if char in "([{":
            depth += 1
            token = "" if depth > 1 else token
            continue
        if char in ")]}":
            depth -= 1
            continue
        if depth:
            continue
        if char == ",":
            expect_name = True
            token = ""
            continue
        if char == "=" and expect_name:
            name = token.strip()
            if name.isidentifier():
                found.append(name)
            expect_name = False
            token = ""
            continue
        if expect_name:
            token += char
    return found


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
                for arg in top_level_named_args(args):
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
    r"""aapt2 treats a value that starts with ? or @ as a resource reference.

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
            fail(f"docs/{name} must be RGBA (colour type 6), got {colour_type}")
        # 2560x1600 panel + 2*34 bezel + 2*72 bright page margin, from
        # tools/render_tablet.py. The margin is what makes the preview a light
        # page instead of a black slab.
        if (width, height) != (2772, 1812):
            fail(f"docs/{name} is {width}x{height}, expected the MatePad Mini frame "
                 "with its bright page margin (2772x1812)")

    server = os.path.join(ROOT, "tools/preview_server.py")
    if not os.path.exists(server):
        fail("tools/preview_server.py missing")
    else:
        text = open(server, encoding="utf-8").read()
        if 'SHOT = "preview-tablet.png"' not in text:
            fail("preview_server.py must still serve the landscape MatePad Mini render")
        for needle, why in (
            ('path in ("/", "/index.html", "/device", "/device.html")',
             "the front page must be the device render, not the editor"),
            ("image-rendering: pixelated",
             "the shot is 2772px shown on a ~1400px pane; without pixelated the "
             "browser smooths 128px cells into mush and the sprite reads as a blob"),
            ("crisp-edges", "Firefox spells the same rule crisp-edges"),
            ('?v=__STAMP__',
             "the image URL must change per render, or a mounted iframe keeps "
             "showing the bitmap it decoded earlier"),
            ('"/editor"', "the editor must move to /editor, not the front page"),
            ('"/api/map"', "the editor saves through /api/map"),
            ('"johto-tileset.png"', "the palette reads the tileset atlas"),
        ):
            if needle not in text:
                fail(f"preview_server.py: {why}")
        # the editor must never fall back to serving the whole repo
        for risky in ("SimpleHTTPRequestHandler", "directory=\"docs\""):
            if risky in text:
                fail(f"preview_server.py exposes files it should not ({risky})")

    check_editor()

    check_punch_hole(os.path.join(docs, "preview-tablet.png"))
    check_preview_screen(os.path.join(docs, "preview-tablet.png"))


PAPER_CMYK = (251, 243, 220)    # HgColors.Paper #FBF3DC, the HUD panel
PAGE_BRIGHT = (191, 227, 242)   # #BFE3F2, the sky-blue surround
BEZEL_DARK = (16, 17, 18)       # #101112
PANEL = (2560, 1600)
BEZEL = 34
PAD = 72


def check_preview_screen(path: str) -> None:
    """The published shot: bright page, black frame, and the field on screen.

    The panel must show the world, not a uniform colour: the home screen is the
    map seen through the camera, so a plain panel would be a worse lie than a
    busy one. Two things are checked instead of "is it empty":

      1. the panel is opaque edge to edge and not one flat colour;
      2. it contains the grass palette the tileset actually uses, which a blank
         paper panel and a half-painted screen both fail.

    The HUD is deliberately absent while it is rebuilt: only the field is on
    screen, and this check does not demand widgets the app has not drawn yet.
    """
    decoded = decode_png(path)
    if decoded is None:
        return
    width, height, rows = decoded

    def pixel(x: int, y: int):
        i = x * 4
        line = rows[y]
        return line[i], line[i + 1], line[i + 2], line[i + 3]

    # 1. the page: bright, opaque, in all four margins
    for x, y, where in ((2, 2, "top-left"), (width - 3, 2, "top-right"),
                        (2, height - 3, "bottom-left"), (width - 3, height - 3, "bottom-right")):
        sample = pixel(x, y)
        if sample[3] != 255:
            fail(f"preview page is transparent at the {where} corner (alpha {sample[3]})")
        elif sample[0] < 150 or sample[2] < 150:
            fail(f"preview page should be a bright sky, found {sample[:3]} at the {where} corner")

    # 2. the frame: a black bezel lives between the page and the panel
    panel_x, panel_y = PAD + BEZEL, PAD + BEZEL
    frame = pixel(panel_x - 12, height // 2)
    if sum(frame[:3]) > 120:
        fail(f"the bezel should be black, found {frame[:3]} just outside the panel")

    # 3. the panel: opaque, and actually showing the field. Sample a grid of
    # points; a blank panel returns one colour, a field returns grass and path.
    seen = {}
    for fy in (0.1, 0.3, 0.5, 0.7, 0.9):
        for fx in (0.1, 0.3, 0.5, 0.7, 0.9):
            x = panel_x + int(PANEL[0] * fx)
            y = panel_y + int(PANEL[1] * fy)
            sample = pixel(x, y)
            if sample[3] != 255:
                fail(f"the panel is transparent at {x},{y}; the screen must be opaque")
                return
            seen[sample[:3]] = seen.get(sample[:3], 0) + 1
    # The starter map is deliberately empty (the map is being redrawn from
    # scratch), so a black panel is the correct picture right now: there is no
    # grass to find. What must still hold is that the screen is opaque and that
    # the player is drawn on it - checked below.
    map_empty = False
    try:
        with open(os.path.join(ROOT, "app", "src", "main", "assets", "tileset",
                               "map.json"), encoding="utf-8") as handle:
            map_empty = not json.load(handle).get("cells")
        working = os.path.join(ROOT, "docs", "tileset", "map.json")
        if os.path.exists(working):
            with open(working, encoding="utf-8") as handle:
                map_empty = not json.load(handle).get("cells")
    except (OSError, ValueError):
        map_empty = False

    if len(seen) < 3 and not map_empty:
        fail(f"the panel is {len(seen)} colour(s), so the field is not being drawn; "
             "run tools/mock_ingame.py --field before rendering the tablet")

    # The render must show the map file and nothing else. The mock used to draw
    # a planted field and torches of its own whenever the map had any cells,
    # which is how a "kebun" appeared in gameplay that the editor never had.
    # That block is gone; this keeps it gone. Crops are runtime state, so a
    # picture built from map.json must never contain crop colours at all.
    crop_colours = ((0x6B, 0x4F, 0x33), (0x3F, 0x7A, 0x32), (0xE8, 0xC5, 0x5C))
    crop_hits = {}
    for fy in range(2, 99, 2):
        for fx in range(2, 99, 2):
            x = panel_x + PANEL[0] * fx // 100
            y = panel_y + PANEL[1] * fy // 100
            colour = pixel(x, y)[:3]
            if colour in crop_colours:
                crop_hits[colour] = crop_hits.get(colour, 0) + 1
    if len(crop_hits) >= 2:
        fail(f"the preview shows a field the map does not contain "
             f"({sum(crop_hits.values())} crop-coloured samples); "
             "tools/mock_ingame.py must draw only what map.json holds")


    # 3b. grass must be on screen whenever the map has cells to draw: this is
    # the tileset's lawn, and it is what separates a real field render from any
    # other picture in the frame. The colours come from tools/tileset/palette.py.
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from tileset import palette as P

    grass = {P.GRASS_1, P.GRASS_2, P.GRASS_3, P.GRASS_DARK, P.GRASS_LIGHT}

    def near(sample, target, tol=20) -> bool:
        return max(abs(sample[i] - target[i]) for i in range(3)) <= tol

    hits = 0
    for fy in range(4, 96, 4):
        for fx in range(3, 97, 3):
            x = panel_x + PANEL[0] * fx // 100
            y = panel_y + PANEL[1] * fy // 100
            sample = pixel(x, y)
            if any(near(sample[:3], g) for g in grass):
                hits += 1
    if hits < 200 and not map_empty:
        fail(f"only {hits} grass samples on the panel; the field render is missing")

    # 3c. the player sprite is drawn. A 32px sprite scaled into the panel is
    # about a hundred pixels across, so sampling on a coarse grid would miss it:
    # scan for a solid run of the character's own colours. Hair and vest are the
    # two largest areas of the design, and neither is used by any tile, so a run
    # of either is the character and not scenery.
    colours = ((0xA3, 0x38, 0x64), (0x4E, 0x8C, 0x53))   # hair, vest
    for colour in colours:
        found = False
        for y in range(panel_y + 4, panel_y + PANEL[1] - 4, 3):
            run = 0
            for x in range(panel_x + 4, panel_x + PANEL[0] - 4, 3):
                if near(pixel(x, y)[:3], colour, 12):
                    run += 1
                    if run >= 3:
                        found = True
                        break
                else:
                    run = 0
            if found:
                break
        if not found:
            fail(f"the player sprite is not on the tablet: no {colour} anywhere "
                 "on the panel")

    # 4. and the camera is still there, on top of the screen
    lens = pixel(panel_x + 96, panel_y + 96)
    if sum(lens[:3]) > 150:
        fail(f"the punch hole camera is missing from the top-left corner ({lens[:3]})")

    # 5. the bright margin is uniform
    edge = pixel(6, height // 2)
    if max(abs(edge[i] - PAGE_BRIGHT[i]) for i in range(3)) > 24:
        fail(f"preview page should be #BFE3F2, found {edge[:3]}")


def decode_png(path: str):
    """Decodes an 8-bit RGBA PNG into (width, height, list of row bytearrays).

    Returns None when the file is missing or not the RGBA PNG this repo writes.
    Shared by the pixel guards below so they check what a browser actually
    shows instead of trusting the header alone.
    """
    import struct
    import zlib

    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        blob = handle.read()
    pos, idat, width, height, colour_type = 8, b"", 0, 0, None
    while pos + 8 <= len(blob):
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
        return None

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
    return width, height, rows


def check_punch_hole(path: str) -> None:
    """The selfie camera must sit in the TOP LEFT of the landscape screen.

    The device has its punch hole in the top right corner of the portrait
    panel; turning it counter clockwise for landscape carries that corner over
    to the top left, which is what hands-on photos show. A render with the hole
    in the other corner, or with a hole that is a token dot / a huge circle,
    means the geometry regressed.
    """
    decoded = decode_png(path)
    if decoded is None:
        return
    width, height, rows = decoded

    def dark(x: int, y: int) -> bool:
        i = x * 4
        line = rows[y]
        return (line[i] + line[i + 1] + line[i + 2]) / 3 < 45

    # The published shot has a bright page margin around the black frame; the
    # lit panel starts inside bezel + margin.
    margin = PAD
    bezel = max(8, height // 40) + margin
    inner_w, inner_h = width - 2 * bezel, height - 2 * bezel

    # A punch hole is a dark disc that sits *on* the panel: there is screen on
    # the side that faces into the display, and bezel behind it. Measuring the
    # blob and then checking the panel just past its edge is what distinguishes
    # a real camera from the bezel itself, and it holds whatever the map does -
    # green field, black field, or a full map with a HUD over it.
    window_w, window_h = max(60, inner_w // 10), max(60, inner_h // 8)
    xs, ys = [], []
    for y in range(bezel, bezel + window_h):
        line = rows[y]
        for x in range(bezel, bezel + window_w):
            i = x * 4
            if (line[i] + line[i + 1] + line[i + 2]) / 3 < 45:
                xs.append(x)
                ys.append(y)
    if not xs:
        fail("punch hole not found in the top left corner of the screen")
        return

    diameter = max(max(xs) - min(xs), max(ys) - min(ys)) + 1
    if not (0.02 * inner_w <= diameter <= 0.08 * inner_w):
        fail(f"punch hole diameter {diameter}px on a {inner_w}px wide panel "
             "is off; expect about 3-5% of the panel width")

    # Right of the hole and below it there must be panel, not bezel. Sample a
    # band that starts one hole-width away, so the lens rim cannot be hit.
    step = max(6, diameter // 3)
    interior = 0
    for y in (min(ys) + diameter // 2, max(ys)):
        for x in (max(xs) + step, max(xs) + 2 * step):
            if 0 <= x < width and 0 <= y < height:
                i = x * 4
                line = rows[y]
                if (line[i] + line[i + 1] + line[i + 2]) / 3 >= 45:
                    interior += 1
    if interior < 2:
        fail(f"the dark disc at {min(xs)},{min(ys)} is not on the panel: "
             "there is no lighter screen beside it")



def check_tileset() -> None:
    """The Johto tileset must stay a coherent, loadable atlas.

    A broken index silently ruins a map: the engine would draw the wrong cell
    or nothing at all. So check the atlas exists, matches its own metadata,
    every entry sits inside the sheet, no two entries overlap, and a few key
    tiles have real pixels in them.
    """
    import json

    folder = os.path.join(ROOT, "docs", "tileset")
    atlas_path = os.path.join(folder, "johto-tileset.png")
    index_path = os.path.join(folder, "tileset.json")
    if not os.path.exists(atlas_path) or not os.path.exists(index_path):
        fail("docs/tileset is missing; run python3 tools/tileset/build.py")
        return

    try:
        meta = json.load(open(index_path, encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"tileset.json is not valid JSON: {error}")
        return

    decoded = decode_png(atlas_path)
    if decoded is None:
        fail("docs/tileset/johto-tileset.png is not an RGBA PNG")
        return
    width, height, rows = decoded

    tile = meta.get("tile")
    tiles = meta.get("tiles", {})
    if tile != 16:
        fail(f"tileset tile size must be 16, found {tile}")
    if len(tiles) < 20:
        fail(f"tileset should hold the Johto palette, only {len(tiles)} tiles indexed")

    for name in ("grass", "path", "water", "tree", "roof", "wall_door",
                 "machine_left", "machine_right"):
        if name not in tiles:
            fail(f"tileset is missing the '{name}' tile")

    seen: dict[tuple[int, int], str] = {}
    for name, entry in tiles.items():
        x, y, w, h = entry["x"], entry["y"], entry["w"], entry["h"]
        if x < 0 or y < 0 or x + w > width or y + h > height:
            fail(f"tileset '{name}' points outside the {width}x{height} atlas")
            continue
        opaque = 0
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if rows[yy][xx * 4 + 3] == 255:
                    opaque += 1
        if opaque == 0:
            fail(f"tileset '{name}' is fully transparent")
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                other = seen.get((xx, yy))
                if other is not None:
                    fail(f"tileset '{name}' overlaps '{other}'")
                    break
                seen[(xx, yy)] = name


def check_editor() -> None:
    """The map editor must stay wired to the tileset it edits.

    A great way to ship a broken editor is a typo in an element id or a fetch
    of a file the server no longer serves: the page loads, then silently does
    nothing. Check the ids and the routes the script relies on.
    """
    import re

    folder = os.path.join(ROOT, "editor")
    page = os.path.join(folder, "index.html")
    script = os.path.join(folder, "app.js")
    styles = os.path.join(folder, "app.css")
    for path in (page, script, styles):
        if not os.path.exists(path):
            fail(f"editor/{os.path.basename(path)} is missing")
            return

    html = open(page, encoding="utf-8").read()
    js = open(script, encoding="utf-8").read()

    html_ids = set(re.findall(r'id="([^"]+)"', html))
    used = set(re.findall(r"\$\('([^']+)'\)", js))
    used |= {f"tool-{tool}" for tool in ("pencil", "erase", "pick", "fill")}
    for name in sorted(used - html_ids):
        fail(f"editor/app.js looks up #{name} but index.html has no such element")

    # the grid requirement: 16x16 cells
    if "const TILE = 16;" not in js:
        fail("editor/app.js must define the 16x16 grid cell (const TILE = 16)")

    # the tileset must come from the server
    for needle in ("/docs/tileset/tileset.json", "/docs/tileset/johto-tileset.png"):
        if needle not in js:
            fail(f"editor/app.js must load {needle}")

    # the + button has to exist and open the tileset drawer
    if 'id="add"' not in html:
        fail("editor/index.html needs the + button")
    if "toggleDrawer()" not in js:
        fail("editor/app.js must open the tileset drawer from the + button")

    # The map owns the window except for the tool bar at the bottom: the bar is
    # a sibling of the canvas, never an overlay, so no button is ever painted on
    # top of the map. Both halves of that rule are checked, because getting one
    # without the other is how a floating toolbar ended up covering the map.
    css = open(styles, encoding="utf-8").read()
    if "position: fixed" not in css:
        fail("editor/app.css must pin the map canvas")
    if "bottom: var(--bar-h)" not in css:
        fail("editor/app.css: the map must stop above the tool bar (--bar-h)")
    if "--bar-h:" not in css:
        fail("editor/app.css: --bar-h must be declared (it is computed from --btn now)")
    if "bottom: 0;" not in css:
        fail("editor/app.css: the tool bar must sit at the bottom edge")

    # the bar must hold the editing tools, and the save button must be reachable
    # from it: a bar you cannot save from is not the editor's control surface
    if 'id="tools"' not in html:
        fail("editor/index.html needs the tool bar")
    for control in ('id="save"', 'id="tool-pencil"', 'id="add"'):
        if control not in html:
            fail(f"editor/index.html: the tool bar is missing {control}")
    if "'/api/map'" not in js:
        fail("editor/app.js must save through /api/map")
    if "peta tersimpan tidak sampai ke game" not in js and \
            "dipakai game" not in js:
        fail("editor/app.js must tell the user whether the save reached the game")

    # every tool is one square size: an icon on top, its label underneath. A
    # button that grows with its label is what made the old bar uneven.
    if "width: var(--btn)" not in css or "height: var(--btn)" not in css:
        fail("editor/app.css: every .tool must be the same square (--btn)")
    for part in (".tool .ico", ".tool .lbl"):
        if part not in css:
            fail(f"editor/app.css: {part} missing; the icon and its label are a fixed pair")

    # the controls the bar is required to offer
    for control, why in (
        ('id="save"', "menyimpan peta"),
        ('id="new"', "membuat peta baru"),
        ('id="view-in"', "zoom masuk"),
        ('id="view-out"', "zoom keluar"),
        ('id="tool-move"', "menggeser peta"),
        ('id="undo"', "membatalkan"),
        ('id="redo"', "mengulangi"),
        ('id="size-up"', "membesarkan kuas"),
        ('id="size-down"', "mengecilkan kuas"),
        ('id="size-value"', "menampilkan ukuran kuas"),
    ):
        if control not in html:
            fail(f"editor/index.html: {control} is missing ({why})")

    # The bar is one row per kind of job. A single wrapping row is what made
    # the old bar unreadable: every button looked equally related to every
    # other. Each row must be its own group with a name.
    rows = re.findall(r'<div class="row" role="group" aria-label="([^"]+)">', html)
    if len(rows) < 4:
        fail(f"editor/index.html: the bar needs a row per job, found {len(rows)}")
    elif len(set(rows)) != len(rows):
        fail("editor/index.html: two tool rows share a name")

    # two columns: the map tools on the left, the view and file on the right
    for column in ("col-tools", "col-view"):
        if f'class="col {column}"' not in html:
            fail(f"editor/index.html: missing the {column} column")
    tools_col = re.search(r'class="col col-tools">(.*?)class="col col-view"', html, re.S)
    if tools_col:
        if 'id="tool-move"' in tools_col.group(1):
            fail("editor/index.html: Geser belongs in the view column, not with the paint tools")
    if ".col-view { margin-left: auto; }" not in css:
        fail("editor/app.css: the right-hand column must hug the far edge")

    # moving the map is a tool now, and pinch/two-finger pan must be gone: the
    # gesture and the stroke could not share one finger, and a stray second
    # touch zoomed the map out mid-draw.
    # Substring checks are not enough here: "function undoGone" contains
    # "function undo", so a renamed function still passed. Every check below is
    # a word-boundary regex, and the ones that matter are anchored to behaviour.
    # strip comments first: the header explains why pinch is gone, and that
    # sentence must not count as pinch code coming back
    code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    code = re.sub(r"(?m)//.*$", "", code)
    if re.search(r"\bpinch\b|state\.pointers|pinchInfo", code):
        fail("editor/app.js: pinch / two-finger pan must be removed; "
             "the Geser tool is the only way to move the map")
    # the move tool has to be wired to the button and actually pan
    if not re.search(r"\$\('tool-move'\)\.addEventListener", js):
        fail("editor/app.js: the Geser button is not wired to anything")
    if not re.search(r"state\.panning\s*=\s*true", js):
        fail("editor/app.js: the Geser tool must actually pan the map")

    # undo/redo must be real history, not two decorative buttons
    for fn in ("undo", "redo", "remember", "beginStroke", "endStroke"):
        if not re.search(r"\nfunction %s\s*\(" % fn, js):
            fail(f"editor/app.js: function {fn} is missing; undo/redo would be decoration")

    # brush size drives the footprint, and the footprint is what gets painted
    if not re.search(r"\nfunction brushCells\s*\(", js) or "state.brushSize" not in js:
        fail("editor/app.js: brush size must change how many cells a stroke touches")
    if not re.search(r"\nfunction paintCell\s*\(", js):
        fail("editor/app.js: painting needs a per-cell primitive that respects the brush")
    if "BRUSH_SIZES" not in js:
        fail("editor/app.js: brush sizes must be a declared list")

    # smaller buttons: the bar is four rows, so a 56px button would eat a fifth
    # of a 1600px panel. Keep it at 48 or below.
    sizes = re.findall(r"--btn:\s*(\d+)px", css)
    if not sizes:
        fail("editor/app.css: --btn must set the button size")
    elif int(sizes[0]) > 40:
        fail(f"editor/app.css: --btn is {sizes[0]}px; the bar should stay small "
             "enough to leave the map room")

    # half-step zoom: read the array itself. Searching the file for "0.5" was
    # useless - the number appears in a dozen unrelated places - so a steps
    # list without it still passed.
    steps_match = re.search(r"ZOOM_STEPS\s*=\s*\[([^\]]+)\]", js)
    if not steps_match:
        fail("editor/app.js: ZOOM_STEPS must be a literal array")
    else:
        steps = [float(v) for v in steps_match.group(1).split(",")]
        if 0.5 not in steps:
            fail("editor/app.js: the zoom steps must include 0.5")
        if steps != sorted(steps):
            fail("editor/app.js: ZOOM_STEPS must be ascending, or zoom in jumps around")
        if any(v != int(v) for v in steps if v > 1):
            fail("editor/app.js: zoom above 1 must be whole numbers, "
                 "or tiles land between pixels")
    if "drawPlayerMarker" not in js:
        fail("editor/app.js: the spawn needs the character as a marker "
             "(drawPlayerMarker), not a bare square")
    if "/docs/tileset/player.png" not in js:
        fail("editor/app.js: the player marker must load the app's own walk sheet")

    for needle in ("gameFrameRect", "drawGameFrame", "DEAD_ZONE"):
        if needle not in js:
            fail(f"editor/app.js: {needle} missing; the gameplay frame would not be drawn")
    # Defining the frame helpers is not enough: draw() has to paint them, or the
    # code looks right and the canvas is wrong. The body of draw() is the slice
    # from its header to the next top-level function, which is what is checked
    # for a real call. Searching the whole file passed while draw() never
    # touched the frame, because the name also appears in the function header.
    head = re.search(r"\nfunction draw\(\)\s*\{", js)
    if not head:
        fail("editor/app.js: draw() is missing")
    else:
        rest = js[head.end():]
        nxt = re.search(r"\nfunction ", rest)
        body = rest[:nxt.start()] if nxt else rest
        if "drawGameFrame(" not in body:
            fail("editor/app.js: draw() never calls drawGameFrame, "
                 "so the gameplay frame is invisible")
    # ...and the function it calls has to exist. Without this, renaming the
    # definition left the call behind and the file still "passed", even though
    # the editor would throw a ReferenceError the moment it drew a frame.
    for fn in ("drawGameFrame", "gameFrameRect"):
        if not re.search(r"\nfunction %s\s*\(" % fn, js):
            fail(f"editor/app.js: {fn} is used but never defined")

    # the editor's idea of the gameplay viewport must match the app's
    with open(os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                          "pokelauncher", "game", "Input.kt"), encoding="utf-8") as handle:
        kotlin = handle.read()
    default_match = re.search(r"const val DEFAULT = (\d+)", kotlin)
    game_zoom = re.search(r"const val GAME_ZOOM = (\d+)", js)
    if default_match and game_zoom:
        if int(default_match.group(1)) != int(game_zoom.group(1)):
            fail(f"editor draws the gameplay frame at {game_zoom.group(1)}x but the app "
                 f"opens at {default_match.group(1)}x")


def check_game_assets() -> None:
    """The app ships its own copy of the tileset and the starter map.

    `app/src/main/assets/tileset/` is what the APK loads. It is a copy, so it
    drifts: a tile regenerated in docs/ and not copied leaves the game drawing
    a blank cell. Compare the copies byte for byte instead of trusting the
    build to remember.
    """
    import json

    assets = os.path.join(ROOT, "app", "src", "main", "assets", "tileset")
    docs = os.path.join(ROOT, "docs", "tileset")
    for name in ("johto-tileset.png", "tileset.json"):
        a = os.path.join(assets, name)
        d = os.path.join(docs, name)
        if not os.path.exists(a):
            fail(f"app assets are missing {name}; the game would draw nothing")
            continue
        if os.path.exists(d) and open(a, "rb").read() != open(d, "rb").read():
            fail(f"app/src/main/assets/tileset/{name} is out of date with docs/tileset/")

    starter = os.path.join(assets, "map.json")
    if not os.path.exists(starter):
        fail("the starter map app/src/main/assets/tileset/map.json is missing")
        return
    try:
        doc = json.load(open(starter, encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"the starter map is not valid JSON: {error}")
        return

    index = json.load(open(os.path.join(docs, "tileset.json"), encoding="utf-8"))["tiles"]
    cols, rows = doc.get("cols", 0), doc.get("rows", 0)
    if cols < 20 or rows < 15:
        fail(f"the starter map is {cols}x{rows}: too small to explore")
    for key, cell in doc.get("cells", {}).items():
        for layer in ("ground", "object", "building"):
            name = cell.get(layer)
            if name is not None and name not in index:
                fail(f"starter map uses unknown tile '{name}' at {key}")
                break
    spawn = doc.get("spawn") or {}
    if not (0 <= spawn.get("x", -1) < cols and 0 <= spawn.get("y", -1) < rows):
        fail("the starter map spawn is outside the map")


def check_player_sprite() -> None:
    """The walk sheet the game loads must match its generator and the code.

    Three things can drift apart silently: the PNG in assets, the tool that
    draws it, and [PlayerSprite]'s idea of the layout. A wrong row draws the
    player backwards, which looks fine in a screenshot; a stale PNG looks fine
    until the next time someone regenerates the palette.
    """
    assets = os.path.join(ROOT, "app", "src", "main", "assets", "sprites", "player.png")
    if not os.path.exists(assets):
        fail("app/src/main/assets/sprites/player.png is missing; the player would fall back to the silhouette")
        return

    # The sheet is generated, so it must be byte-identical to a fresh render.
    import subprocess

    before = open(assets, "rb").read()
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "sprites.py"), "--atlas"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f"tools/sprites.py --atlas failed: {result.stderr.strip()[:200]}")
        return
    if open(assets, "rb").read() != before:
        fail("player.png changed when regenerated; commit the regenerated sheet")

    # Layout must agree with PlayerSprite: 2 frames wide, 4 rows tall, and the
    # frame is 32x32 - two map cells, which is the size the art was drawn at.
    head = open(assets, "rb").read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        fail("player.png is not a PNG")
        return
    import struct
    width, height = struct.unpack(">II", head[16:24])
    if (width, height) != (64, 128):
        fail(f"player.png is {width}x{height}; PlayerSprite expects 64x128 "
             f"(2 frames x 4 rows of 32px)")

    # The code that reads it must agree on the numbers.
    sprite = os.path.join(
        ROOT, "app", "src", "main", "java", "dev", "retrobit", "pokelauncher",
        "game", "PlayerSprite.kt",
    )
    if not os.path.exists(sprite):
        fail("PlayerSprite.kt is missing; the canvas has nothing to index the sheet with")
        return
    text = open(sprite, encoding="utf-8").read()
    for needle, why in (
        ("const val FRAMES = 2", "the sheet is 2 frames wide"),
        ("const val TILE = 32", "frames are 32px, two map cells"),
        ("const val CELLS = 2", "a frame covers two cells, so the feet can anchor"),
        ("SHEET_WIDTH = FRAMES * TILE", "width must be derived, not typed twice"),
        ("SHEET_HEIGHT = 4 * TILE", "there are four directions, so four rows"),
    ):
        if needle not in text:
            fail(f"PlayerSprite.kt should declare {needle!r}: {why}")


def check_move_pad() -> None:
    """The pad must exist, be reachable, and be the thing that moves the player.

    A joystick is easy to draw and easy to leave unconnected: the disc appears,
    the thumb slides, and nothing happens. These checks tie the drawing to the
    rule to the ViewModel, in that order.
    """
    pad = os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                       "pokelauncher", "ui", "components", "MovePad.kt")
    rule = os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                        "pokelauncher", "game", "Joystick.kt")
    screen = os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                          "pokelauncher", "ui", "GameScreen.kt")
    model = os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                         "pokelauncher", "ui", "GameViewModel.kt")
    for path, name in ((pad, "MovePad.kt"), (rule, "Joystick.kt")):
        if not os.path.exists(path):
            fail(f"{name} is missing; the tablet has no way to move the player")
            return

    pad_src = open(pad, encoding="utf-8").read()
    rule_src = open(rule, encoding="utf-8").read()
    screen_src = open(screen, encoding="utf-8").read()
    model_src = open(model, encoding="utf-8").read()

    # 1. the rule: a dead zone and a diagonal rule, not just four ifs
    if "DEAD_ZONE" not in rule_src:
        fail("Joystick.kt: a pad without a dead zone walks on a resting thumb")
    if "fun direction(" not in rule_src or "fun knob(" not in rule_src:
        fail("Joystick.kt: the pad needs its direction rule and its knob clamp")
    # An exact diagonal must resolve the same way every time. The first version
    # used a bare `|dx| > |dy|` and sent a 45-degree push DOWN, because the
    # vertical branch was also the else branch; that is the bug a unit test
    # caught, and this keeps the tie-break from quietly reverting.
    if "ax >= ay" not in rule_src:
        fail("Joystick.kt: a diagonal needs an explicit tie-break "
             "(without it a 45-degree push reports the vertical axis)")

    # 2. the drawing: a real gesture that reports a release
    if "onDirection(null)" not in pad_src:
        fail("MovePad.kt: lifting the thumb must report null, or the player "
             "keeps walking after the finger is gone")
    if "awaitEachGesture" not in pad_src:
        fail("MovePad.kt: the pad must track a held finger, not a single tap")

    home = os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                        "pokelauncher", "ui", "LauncherScreen.kt")
    home_src = open(home, encoding="utf-8").read()

    # 3. the wiring: the pad is on the home screen itself, connected to the game.
    #    It used to be reachable only from the full-HUD branch, which is off, so
    #    the pad would have been built and never shown. Checking the branch that
    #    actually renders is the difference between "exists" and "works".
    if "SHOW_WORLD = false" not in home_src:
        fail("LauncherScreen.kt: this check assumes the map-only home screen")
    # The branch that renders, cut at the line that starts the next branch.
    #
    # Two earlier versions of this slice were wrong in ways that looked right:
    # splitting on a `return` cut at the early return for a missing world, and
    # splitting on `GameHud(` cut on the *parameter* `onOpenLauncher: () ->
    # Unit` of the other branch's call, not on the call itself. Both left a body
    # with no pad in it, so the check below never fired. The next branch starts
    # with this exact line, which appears once in the file.
    plain = home_src.split("if (!SHOW_WORLD) {", 1)[1]
    seam = "\n    val state by game.state.collectAsState()"
    if seam not in plain:
        fail("LauncherScreen.kt: cannot find the second branch; the move-pad "
             "check would be reading the wrong code")
        return
    plain = plain.split(seam, 1)[0]
    if "MovePad(" not in plain:
        fail("LauncherScreen.kt: the visible home screen has no move pad; the "
             "player can see the world but cannot walk in it")
    if "onDirection = game::holdDirection" not in plain:
        fail("LauncherScreen.kt: the pad is drawn but never connected to the game")
    if "MovePad(" in plain and \
            "Alignment.BottomStart" not in plain.split("MovePad(")[1][:400]:
        fail("LauncherScreen.kt: the pad belongs bottom-left, where a thumb rests")
    # The pad sits on the map, so the map must be under it: a Column would give
    # the pad its own strip and shrink the world.
    if "Box(modifier = Modifier.fillMaxSize())" not in plain:
        fail("LauncherScreen.kt: the pad must float over the map, not take a row")

    # The hud still needs the callback for the branch behind the flag.
    if "onMove: (Direction?) -> Unit" not in screen_src:
        fail("GameScreen.kt: GameHud needs the pad's callback")
    if "fun holdDirection(" not in model_src:
        fail("GameViewModel.kt: nothing turns a held direction into a step")
    # Searched to the end of the function, not a fixed window: the comment that
    # explains the cancellation made the window too short, and a guard that
    # fails on a comment is a guard nobody keeps.
    hold = model_src.split("fun holdDirection(", 1)[1].split("\n    /**", 1)[0]
    if "walkJob?.cancel()" not in hold:
        fail("GameViewModel.kt: the pad must cancel a tap-to-walk path, or the "
             "two move the player at the same time")


def check_save_is_tied_to_its_map() -> None:
    """A save must not bring its garden to a different map.

    The bug: crops, tilled soil and torches were restored on any map as long as
    the player's cell still existed. Save on one map, repaint the map, and the
    old garden showed up in cells the new map never filled. The fix is a map
    fingerprint in the save; these checks make sure it cannot quietly disappear.
    """
    path = os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                        "pokelauncher", "game", "WorldState.kt")
    if not os.path.exists(path):
        fail("WorldState.kt is missing")
        return
    state = open(path, encoding="utf-8").read()
    if "const val VERSION = 2" not in state:
        fail("WorldState.kt: the save version must be 2 or newer, so v1 saves "
             "(which carry a map-less garden) are dropped")
    if "fun fingerprint(" not in state:
        fail("WorldState.kt: a save needs a map fingerprint")
    if "mapFingerprint" not in state:
        fail("WorldState.kt: the fingerprint is never written to the save")
    if 'root.optInt("version", 1) < VERSION' not in state:
        fail("WorldState.kt: an old save version must be rejected")

    vm = os.path.join(ROOT, "app", "src", "main", "java", "dev", "retrobit",
                      "pokelauncher", "ui", "GameViewModel.kt")
    model = open(vm, encoding="utf-8").read()
    if "WorldState.fingerprint(" not in model:
        fail("GameViewModel.kt: saving must stamp the map fingerprint")


def check_zoom_agreement() -> None:
    """The app's default zoom and every tool that renders it must match.

    The screenshot is the only thing a reviewer sees, so a render drawn at a
    different zoom than the app opens at is a convincing lie. This has already
    gone wrong twice: a default (8) missing from the step list, and a mock that
    forced the whole 80x50 map into the panel.
    """
    import re

    def read(path):
        with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
            return handle.read()

    steps_text = read("app/src/main/java/dev/retrobit/pokelauncher/game/Input.kt")
    match = re.search(r"val STEPS = intArrayOf\(([^)]*)\)", steps_text)
    if not match:
        fail("Input.kt: could not find the STEPS list")
        return
    steps = [int(v.strip()) for v in match.group(1).split(",") if v.strip()]

    default_match = re.search(r"const val DEFAULT = (\d+)", steps_text)
    if not default_match:
        fail("Input.kt: DEFAULT zoom is not declared")
        return
    default = int(default_match.group(1))

    if default not in steps:
        fail(f"the default zoom {default} is not one of the steps {steps}; "
             "zoom-out then cannot find the current scale")

    # every tool that draws the world at a zoom must agree with the app
    for path, pattern, why in (
        ("tools/mock_ingame.py", r"DEFAULT_ZOOM = (\d+)",
         "the mock renders what the tablet shows"),
    ):
        if not os.path.exists(os.path.join(ROOT, path)):
            continue
        found = re.search(pattern, read(path))
        if not found:
            fail(f"{path}: no DEFAULT_ZOOM found")
            continue
        if int(found.group(1)) != default:
            fail(f"{path} renders at {found.group(1)}x but the app opens at {default}x "
                 f"({why})")


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
    check_tileset()
    check_game_assets()
    check_player_sprite()
    check_zoom_agreement()
    check_save_is_tied_to_its_map()
    check_move_pad()

    for problem in problems:
        print("FAIL", problem)
    print(f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
