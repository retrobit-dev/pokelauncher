#!/usr/bin/env python3
"""Draws sprite candidates for the player, as an option sheet.

    python3 tools/sprites.py                   # docs/sprites/options.png
    python3 tools/sprites.py --chars           # per character contact sheet

Why a generator and not a PNG: a sprite is a list of rows in the source, so a
change is one line in a diff, not a binary the reviewer has to open. It also
means the palette can be swapped for a variant without redrawing anything.

The sprite is 16x16, the same cell as the map, and shares the HeartGold palette
(red cap, pale skin, blue jacket, dark boots). Four directions, two walk frames
each: the grid the engine already expects.

Shading rules, so every candidate reads the same at 3x on the tablet:
  - light from the top-left, one pixel of shadow on the right and bottom rim;
  - the outline is a single dark colour, never pure black, so it sits on grass
    without looking like a hole;
  - feet stay on the bottom row, and the body never uses the last two columns,
    so the sprite fits the cell without bleeding into the next one.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from tileset.pixels import Image  # noqa: E402

W = H = 16
PAL = {
    "K": (0x2C, 0x24, 0x18),   # outline, dark warm brown (never pure black)
    "R": (0xC5, 0x3A, 0x2D),   # cap and jacket, HeartGold red
    "r": (0x9A, 0x2A, 0x20),   # red shadow
    "S": (0xF2, 0xC7, 0x9A),   # skin
    "s": (0xD8, 0xA5, 0x7A),   # skin shadow
    "B": (0x3E, 0x5C, 0x8A),   # trousers / bag strap blue
    "b": (0x2C, 0x42, 0x66),   # blue shadow
    "W": (0xFF, 0xFB, 0xF0),   # eye white
    "Y": (0xE8, 0xC5, 0x5C),   # hair / gold trim
    "G": (0x6B, 0x8F, 0x5A),   # bag, muted green
    "g": (0x4E, 0x6B, 0x42),   # bag shadow
    "H": (0x6B, 0x45, 0x2B),   # brown hair, distant enough from skin to read
    "h": (0x4A, 0x2E, 0x1C),   # brown hair shadow
    "T": (0x8A, 0x6B, 0x4A),   # tan cloth / helmet leather
}


def blank() -> list[list[str]]:
    return [["." for _ in range(W)] for _ in range(H)]


def put(rows: list[list[str]], x: int, y: int, ch: str) -> None:
    if 0 <= x < W and 0 <= y < H:
        rows[y][x] = ch


def fill(rows, x0, y0, x1, y1, ch) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(rows, x, y, ch)


# The three candidates share a skeleton so they can be judged fairly: same
# height, same eye line, same foot row. What changes is silhouette, palette and
# head shape, which is what actually reads at 3x on the tablet.

# --------------------------------------------------------------- candidate A
def hero_red() -> dict[str, list[list[str]]]:
    """A: the trainer from the prototype, cleaned up. Cap, jacket, jeans."""
    frames = {}
    for name in ("down", "up", "side"):
        for step in (0, 1):
            r = blank()
            # cap: crown, then a brim that clears the eyes on the front view
            fill(r, 5, 1, 10, 2, "R")
            fill(r, 4, 3, 11, 3, "R")
            put(r, 3, 4, "R")          # brim tip, front only
            fill(r, 5, 4, 10, 7, "S")  # face
            put(r, 5, 7, "s")
            put(r, 10, 6, "s")
            put(r, 10, 7, "s")
            if name == "down":
                put(r, 6, 5, "K")
                put(r, 9, 5, "K")
            elif name == "up":
                fill(r, 5, 4, 10, 5, "Y")   # hair under the cap, no face
            else:
                put(r, 9, 5, "K")
                put(r, 4, 4, "s")           # back of the cheek
            # torso
            fill(r, 5, 8, 10, 11, "B")
            fill(r, 6, 8, 9, 8, "R")        # collar
            fill(r, 4, 8, 4, 10, "R")       # near sleeve
            fill(r, 11, 8, 11, 10, "b")     # far sleeve
            put(r, 4, 11, "s")              # hand
            put(r, 11, 11, "s")
            # legs: two columns with a dark gap, so the stride is legible
            fill(r, 5, 12, 6, 14, "B")
            fill(r, 9, 12, 10, 14, "B")
            fill(r, 5, 15, 6, 15, "K")
            fill(r, 9, 15, 10, 15, "K")
            fill(r, 6, 12, 6, 14, "K")           # gap between the legs
            fill(r, 9, 12, 9, 14, "K")
            if step:
                fill(r, 5, 14, 7, 14, "K")       # left foot planted
                fill(r, 9, 13, 10, 14, "K")      # right boot lifted
            frames[f"{name}_{step}"] = outlined(r)
    return frames


# --------------------------------------------------------------- candidate B
def ranger_green() -> dict[str, list[list[str]]]:
    """B: a farmhand. Straw hat, green overalls, spade over the shoulder."""
    frames = {}
    for name in ("down", "up", "side"):
        for step in (0, 1):
            r = blank()
            # straw hat: brim two rows above the face, dark band under it
            fill(r, 3, 2, 12, 2, "Y")
            fill(r, 5, 1, 10, 1, "Y")
            put(r, 3, 2, "g")
            put(r, 12, 2, "g")
            fill(r, 5, 3, 10, 3, "g")
            fill(r, 5, 4, 10, 7, "S")
            put(r, 5, 7, "s")
            put(r, 10, 6, "s")
            if name == "down":
                put(r, 6, 5, "K")
                put(r, 9, 5, "K")
            elif name == "up":
                fill(r, 5, 4, 10, 5, "Y")
            else:
                put(r, 9, 5, "K")
                put(r, 4, 4, "s")
            # overalls with red shirt sleeves
            fill(r, 5, 8, 10, 11, "G")
            fill(r, 5, 8, 10, 8, "R")
            fill(r, 4, 8, 4, 10, "R")
            fill(r, 11, 8, 11, 10, "g")
            put(r, 7, 9, "g")
            put(r, 8, 9, "g")
            put(r, 4, 11, "s")
            put(r, 11, 11, "s")
            if name != "down":                 # spade on the back
                fill(r, 12, 4, 12, 9, "s")
                fill(r, 11, 3, 13, 3, "B")
            fill(r, 5, 12, 6, 14, "G")
            fill(r, 9, 12, 10, 14, "G")
            fill(r, 5, 15, 6, 15, "K")
            fill(r, 9, 15, 10, 15, "K")
            fill(r, 6, 12, 6, 14, "K")
            fill(r, 9, 12, 9, 14, "K")
            if step:
                fill(r, 5, 14, 7, 14, "K")
                fill(r, 9, 13, 10, 14, "K")
            frames[f"{name}_{step}"] = outlined(r)
    return frames


# --------------------------------------------------------------- candidate C
def kid_cap() -> dict[str, list[list[str]]]:
    """C: a kid. Bigger round head, short body: reads best at 1x."""
    frames = {}
    for name in ("down", "up", "side"):
        for step in (0, 1):
            r = blank()
            # round hair: three rows, narrower at the top
            fill(r, 5, 1, 10, 1, "K")
            fill(r, 4, 2, 11, 3, "K")
            fill(r, 5, 4, 10, 7, "S")
            put(r, 4, 4, "K")
            put(r, 11, 4, "K")
            put(r, 5, 7, "s")
            put(r, 10, 6, "s")
            if name == "down":
                fill(r, 6, 5, 7, 5, "K")
                fill(r, 8, 5, 9, 5, "K")
            elif name == "up":
                fill(r, 4, 4, 11, 6, "K")
            else:
                put(r, 9, 5, "K")
                put(r, 4, 6, "s")
            # short body, red tee, blue shorts
            fill(r, 5, 8, 10, 10, "R")
            fill(r, 4, 8, 4, 9, "R")
            fill(r, 11, 8, 11, 9, "r")
            fill(r, 5, 11, 10, 12, "B")
            fill(r, 4, 11, 4, 12, "B")
            fill(r, 11, 11, 11, 12, "b")
            # short legs, sandals
            fill(r, 4, 13, 6, 14, "S")
            fill(r, 9, 13, 11, 14, "S")
            fill(r, 4, 15, 6, 15, "K")
            fill(r, 9, 15, 11, 15, "K")
            if step:
                fill(r, 4, 14, 6, 14, "K")
                fill(r, 10, 15, 11, 15, "S")
            frames[f"{name}_{step}"] = outlined(r)
    return frames


# --------------------------------------------------------------- candidate D
def traveller_pony() -> dict[str, list[list[str]]]:
    """D: a traveller. Ponytail, cream blouse, red skirt, boots."""
    frames = {}
    for name in ("down", "up", "side"):
        for step in (0, 1):
            r = blank()
            # hair: crown plus a ponytail that hangs on the side view
            fill(r, 5, 1, 10, 2, "H")
            fill(r, 4, 3, 11, 3, "H")
            fill(r, 4, 4, 4, 7, "H")
            fill(r, 11, 4, 11, 7, "h")
            fill(r, 5, 4, 10, 7, "S")
            put(r, 5, 7, "s")
            put(r, 10, 6, "s")
            if name == "down":
                put(r, 6, 5, "K")
                put(r, 9, 5, "K")
                put(r, 8, 7, "s")          # mouth
            elif name == "up":
                fill(r, 4, 3, 11, 6, "H")  # all hair from behind
            else:
                put(r, 9, 5, "K")
                fill(r, 12, 4, 12, 8, "H") # ponytail
                put(r, 4, 4, "s")
            # blouse + skirt
            fill(r, 5, 8, 10, 9, "W")
            fill(r, 4, 8, 4, 9, "W")
            fill(r, 11, 8, 11, 9, "s")
            fill(r, 4, 10, 11, 11, "R")
            put(r, 4, 11, "r")
            put(r, 11, 11, "r")
            # legs and boots
            fill(r, 5, 12, 6, 13, "S")
            fill(r, 9, 12, 10, 13, "S")
            fill(r, 5, 14, 6, 15, "K")
            fill(r, 9, 14, 10, 15, "K")
            if step:
                fill(r, 5, 15, 6, 15, "S")
                fill(r, 9, 14, 10, 14, "b")
            frames[f"{name}_{step}"] = outlined(r)
    return frames


# --------------------------------------------------------------- candidate E
def miner_dark() -> dict[str, list[list[str]]]:
    """E: a miner. Helmet lamp, beard, brown work clothes."""
    frames = {}
    for name in ("down", "up", "side"):
        for step in (0, 1):
            r = blank()
            # helmet with a lamp at the front
            fill(r, 4, 1, 11, 2, "Y")
            fill(r, 3, 3, 12, 3, "T")
            if name != "up":
                put(r, 7, 2, "W")
                put(r, 8, 2, "W")
            fill(r, 5, 4, 10, 7, "S")
            put(r, 5, 7, "s")
            put(r, 10, 6, "s")
            if name == "down":
                put(r, 6, 5, "K")
                put(r, 9, 5, "K")
                fill(r, 6, 6, 9, 7, "h")   # beard
            elif name == "up":
                fill(r, 4, 3, 11, 5, "K")  # hair under the helmet
            else:
                put(r, 9, 5, "K")
                fill(r, 9, 6, 11, 7, "h")  # beard, side
                put(r, 4, 4, "s")
            # work clothes
            fill(r, 5, 8, 10, 11, "G")
            fill(r, 4, 8, 4, 10, "G")
            fill(r, 11, 8, 11, 10, "g")
            fill(r, 6, 9, 9, 9, "K")       # belt
            put(r, 8, 9, "Y")
            fill(r, 5, 12, 6, 14, "b")
            fill(r, 9, 12, 10, 14, "b")
            fill(r, 5, 15, 6, 15, "K")
            fill(r, 9, 15, 10, 15, "K")
            if step:
                fill(r, 5, 14, 6, 14, "K")
                fill(r, 9, 15, 10, 15, "b")
            frames[f"{name}_{step}"] = outlined(r)
    return frames


CANDIDATES = {
    "A": ("Trainer merah", hero_red),
    "B": ("Petani jerami", ranger_green),
    "C": ("Anak kecil", kid_cap),
    "D": ("Pengelana", traveller_pony),
    "E": ("Penambang", miner_dark),
}


def outlined(rows: list[list[str]]) -> list[list[str]]:
    """Puts a one pixel outline around the silhouette.

    Drawn by code rather than by hand: a hand drawn outline is the first thing
    to break when a limb moves, and it is invisible until the sprite is on a
    dark tile. Kept inside the 16x16 cell, so the feet lose their outline on
    the last row instead of spilling - the boots are already dark there.
    """
    out = [row[:] for row in rows]
    for y in range(H):
        for x in range(W):
            if rows[y][x] != ".":
                continue
            # A pixel in a one wide vertical gap (between the legs) is inside
            # the silhouette. Outlining it turns a pair of legs into a comb.
            open_left = x > 0 and rows[y][x - 1] == "."
            open_right = x < W - 1 and rows[y][x + 1] == "."
            if open_left and open_right:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and rows[ny][nx] not in (".", "K"):
                    out[y][x] = "K"
                    break
    return out


def draw(rows: list[list[str]]) -> Image:
    img = Image(W, H)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            img.dot(x, y, PAL[ch])
    return img


def sheet(frames: dict[str, list[list[str]]], scale: int = 4) -> Image:
    """One row per direction, two columns of walk frames."""
    order = [("down", 0), ("down", 1), ("up", 0), ("up", 1),
             ("side", 0), ("side", 1)]
    pad = 2
    cols, rows = len(order), 1
    cell = W * scale
    img = Image(cols * (cell + pad) + pad, rows * (cell + pad) + pad,
                fill=(0x5C, 0x7A, 0x45))    # grass, so the outline can be judged
    for index, (direction, step) in enumerate(order):
        art = draw(frames[f"{direction}_{step}"])
        x0 = pad + index * (cell + pad)
        y0 = pad
        for y in range(H):
            for x in range(W):
                r, g, b, a = art.px(x, y)
                if not a:
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        img.dot(x0 + x * scale + dx, y0 + y * scale + dy, (r, g, b))
    return img


LABELS = {
    "A": "A  TRAINER MERAH",
    "B": "B  PETANI JERAMI",
    "C": "C  ANAK KECIL",
    "D": "D  PENGELANA",
    "E": "E  PENAMBANG",
}
VIEWS = (("down", 0), ("down", 1), ("up", 0), ("up", 1), ("side", 0), ("side", 1))
VIEW_NAMES = ("DEPAN", "", "BELAKANG", "", "SAMPING", "")
SIZES = (1, 2, 3, 4, 6)


def options_sheet(scale: int = 6) -> Image:
    """Every candidate stacked, one row per character, labelled."""
    pad = 20
    cell = W * scale
    gutter = 10
    label_w = 360          # "A  PETANI JERAMI" is 16 glyphs at 6*2 px pitch
    row_w = len(VIEWS) * (cell + gutter) - gutter
    width = pad * 2 + label_w + row_w
    row_h = cell + 56
    strip_h = W * max(SIZES) + 46            # real-size strip, 1x .. 6x
    height = pad * 2 + 26 + len(CANDIDATES) * row_h + strip_h + 40
    img = Image(width, height, fill=(0xFB, 0xF3, 0xDC))   # paper, like the HUD

    ink = (0x3B, 0x2F, 0x1E)
    faint = (0x9A, 0x87, 0x68)

    # column titles, once, above the first row
    x = pad + label_w
    for index, name in enumerate(VIEW_NAMES):
        if name:
            text(img, x + index * (cell + gutter) + 4, pad - 2, name, 2, faint)

    for row, (key, (_, maker)) in enumerate(CANDIDATES.items()):
        y0 = pad + 26 + row * row_h
        text(img, pad, y0 + cell // 2 - 14, LABELS[key], 2, ink)
        frames = maker()
        x = pad + label_w
        for direction, step in VIEWS:
            art = draw(frames[f"{direction}_{step}"])
            # grass patch behind each frame so the silhouette is judged honestly
            for yy in range(cell):
                for xx in range(cell):
                    img.dot(x + xx, y0 + yy, (0x5C, 0x7A, 0x45))
            for yy in range(H):
                for xx in range(W):
                    r, g, b, a = art.px(xx, yy)
                    if not a:
                        continue
                    for dy in range(scale):
                        for dx in range(scale):
                            img.dot(x + xx * scale + dx, y0 + yy * scale + dy, (r, g, b))
            x += cell + gutter

    # ---- real-size strip: the same front frame at every scale the game uses,
    # so the sheet answers "does it read on the tablet" and not only at 6x.
    strip_y = pad + 26 + len(CANDIDATES) * row_h + 8
    text(img, pad, strip_y, "UKURAN TAMPIL", 2, ink)
    text(img, pad + 190, strip_y + 2, "(TINGGI 16 PX, SEL 16 PX)", 1, faint)
    cursor = pad
    for size in SIZES:
        art = draw(CANDIDATES["A"][1]()["down_0"])
        for yy in range(W):
            for xx in range(W):
                r, g, b, a = art.px(xx, yy)
                if not a:
                    continue
                for dy in range(size):
                    for dx in range(size):
                        img.dot(cursor + xx * size + dx, strip_y + 24 + yy * size + dy, (r, g, b))
        text(img, cursor, strip_y + 30 + W * size, f"{size}X", 1, faint)
        cursor += W * size + 20

    text(img, pad, height - 26, "16 X 16  -  4 ARAH  -  2 FRAME JALAN  -  DEPAN / BELAKANG / SAMPING", 2, faint)
    return img


FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
    "F": ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "01110", "00001", "00001", "10001", "01110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    " ": ["00000"] * 7,
    # digits and punctuation: without them a label like "16 X 16" renders as
    # gaps, which is how a footer looked like two overlapping strings
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11110", "00001", "00110", "00001", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
}


def text(img: Image, x: int, y: int, label: str, scale: int, colour) -> None:
    """5x7 block font, one pixel of tracking. No external font file."""
    cx = x
    for ch in label.upper():
        for gy, bits in enumerate(FONT.get(ch, FONT[" "])):
            for gx, bit in enumerate(bits):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            img.dot(cx + gx * scale + dx, y + gy * scale + dy, colour)
        cx += 6 * scale


def mirror(rows: list[list[str]]) -> list[list[str]]:
    """Flip a side-facing frame, so one drawn direction serves both ways."""
    return [list(reversed(row)) for row in rows]


# Atlas row order. The Kotlin sheet indexes it by Direction.ordinal, so the
# two must stay in the same order as the enum: UP, DOWN, LEFT, RIGHT.
ATLAS_ROWS = ("up", "down", "left", "right")


def atlas_frames(frames: dict[str, list[list[str]]]) -> dict[str, list[list[str]]]:
    return {
        "up": [frames["up_0"], frames["up_1"]],
        "down": [frames["down_0"], frames["down_1"]],
        "left": [mirror(frames["side_0"]), mirror(frames["side_1"])],
        "right": [frames["side_0"], frames["side_1"]],
    }


def atlas(chosen: str = "C") -> Image:
    """The sheet the game loads: four rows by two frames, 16x16 each.

    Left is the mirror of right rather than hand-drawn: at 16px the two are
    indistinguishable, and one drawn direction cannot drift out of sync with
    the other.
    """
    frames = atlas_frames(CANDIDATES[chosen][1]())
    img = Image(2 * W, len(ATLAS_ROWS) * H)
    for row, key in enumerate(ATLAS_ROWS):
        for col, rows in enumerate(frames[key]):
            art = draw(rows)
            for y in range(H):
                for x in range(W):
                    r, g, b, a = art.px(x, y)
                    if a:
                        img.dot(col * W + x, row * H + y, (r, g, b))
    return img


def main(argv: list[str]) -> None:
    out_dir = os.path.join(ROOT, "docs", "sprites")
    os.makedirs(out_dir, exist_ok=True)
    if "--chars" in argv:
        for key, (label, maker) in CANDIDATES.items():
            img = sheet(maker())
            path = os.path.join(out_dir, f"candidate-{key.lower()}.png")
            img.to_png(path)
            print(f"{path}  {img.w}x{img.h}  {label}")
        return
    if "--atlas" in argv:
        # written to the app assets, not docs: this file is what the APK loads
        chosen = "C"
        for i, arg in enumerate(argv):
            if arg == "--atlas" and i + 1 < len(argv):
                chosen = argv[i + 1].upper()
        img = atlas(chosen)
        path = os.path.join(ROOT, "app", "src", "main", "assets", "sprites",
                            "player.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.to_png(path)
        print(f"{path}  {img.w}x{img.h}  {CANDIDATES[chosen][0]}")
        return
    img = options_sheet()
    path = os.path.join(out_dir, "options.png")
    img.to_png(path)
    print(f"{path}  {img.w}x{img.h}  {len(CANDIDATES)} calon sprite, 3 tampilan x 2 frame")


if __name__ == "__main__":
    main(sys.argv[1:])
