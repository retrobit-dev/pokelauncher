#!/usr/bin/env python3
"""Draws the player sprite the app loads.

    python3 tools/sprites.py                  # docs/sprites/player.png, a review sheet
    python3 tools/sprites.py --atlas          # writes app/src/main/assets/sprites/player.png

Why a generator and not a PNG: a sprite is a list of shapes in the source, so a
change is a few lines in a diff, not a binary the reviewer has to open. It also
means the review sheet and the asset can never disagree.

The character is 32x32 - two map cells wide and two tall - because the art has
to read on a 2560x1600 panel used at arm's length. At 16px the face was four
pixels wide: there was room for two dots and nothing else. Two cells give a
face with brows, a mouth, blush, and hair with highlights, which is what makes
it look like a person rather than a marker.

Design, from the reference the user drew:
  - magenta hair, swooping, longer on the left, with light streaks
  - green vest with a plum lining at the shoulders
  - plum trousers, a dark belt with a gold buckle
  - pink boots
  - pale skin, one relaxed eye line, a small mouth

Shading rules, so every frame reads the same at 10x on the tablet:
  - light from the top-left; the shadow side is one darker tone, never a gradient
  - the outline is a single deep-plum colour, not black, so the character sits on
    grass and on stone without looking cut out
  - shapes are defined as horizontal spans, so the silhouette is a table you can
    read and edit; there are no floating single pixels to fall out of sync
  - feet stay on the bottom row; the top row stays empty so the outline always
    has somewhere to go
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from tileset.pixels import Image  # noqa: E402

# The frame is 32x32: see the module docstring. Kept as one constant because the
# atlas, the review sheet and the Kotlin reader all have to agree on it.
W = H = 32

PAL = {
    "#": (0x2E, 0x17, 0x27),   # outline, deep plum (never pure black)
    "H": (0xC9, 0x50, 0x82),   # hair, lit
    "h": (0xA3, 0x38, 0x64),   # hair, mid
    "j": (0x7D, 0x25, 0x4E),   # hair, shadow
    "l": (0xDE, 0x6C, 0x98),   # hair highlight streak
    "S": (0xF4, 0xCB, 0xA2),   # skin
    "s": (0xD9, 0xA6, 0x7C),   # skin shadow
    "E": (0x2E, 0x17, 0x27),   # eye and brow
    "k": (0xEC, 0x86, 0x8E),   # blush
    "G": (0x4E, 0x8C, 0x53),   # vest
    "g": (0x33, 0x60, 0x38),   # vest shadow
    "F": (0xEC, 0xAE, 0xDD),   # pink lining at the shoulders
    "P": (0x6E, 0x35, 0x5D),   # trousers
    "p": (0x4E, 0x23, 0x43),   # trousers shadow
    "B": (0x5C, 0x2B, 0x4C),   # belt
    "X": (0xE9, 0xB6, 0x4C),   # buckle, gold
    "W": (0xEC, 0x9C, 0xB6),   # boots, pink
    "w": (0xC6, 0x72, 0x90),   # boot shadow
    "T": (0x9C, 0x4C, 0x6C),   # wrist cuff
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


def span(rows, y, a, b, ch) -> None:
    fill(rows, a, y, b, y, ch)


# The head is a rounded mass of hair with a window of face in it. Written as
# spans rather than as a bitmap so the shape is legible: each row says how wide
# the hair is there, which is the whole silhouette.
HAIR = {
    3: (13, 18), 4: (11, 21), 5: (10, 22), 6: (9, 23), 7: (9, 23), 8: (8, 24),
    9: (8, 24), 10: (8, 24), 11: (8, 24), 12: (9, 23), 13: (9, 23), 14: (10, 22),
    15: (11, 21), 16: (12, 20), 17: (14, 19),
}
FACE = {7: (13, 19), 8: (12, 20), 9: (12, 20), 10: (12, 20),
        11: (12, 20), 12: (12, 20), 13: (12, 20)}


def head(rows, view: str) -> None:
    """Hair, then the face, then the two or three pixels that make it a face."""
    for y, (a, b) in HAIR.items():
        span(rows, y, a, b, "h")
    # lit from the top-left: a wedge of the lighter tone
    span(rows, 3, 14, 17, "H")
    span(rows, 4, 12, 18, "H")
    span(rows, 5, 10, 15, "H")
    span(rows, 6, 9, 13, "H")
    span(rows, 7, 9, 11, "H")
    span(rows, 8, 8, 10, "H")
    span(rows, 9, 8, 9, "H")
    # highlight streaks, angled down to the right like the reference
    span(rows, 5, 13, 16, "l")
    span(rows, 4, 16, 19, "l")
    span(rows, 6, 17, 19, "l")
    span(rows, 7, 20, 22, "l")
    # the shadow side, and the shadow under the fringe
    fill(rows, 21, 9, 24, 13, "j")
    fill(rows, 19, 13, 23, 16, "j")
    fill(rows, 10, 14, 12, 16, "j")

    if view == "down":
        for y, (a, b) in FACE.items():
            span(rows, y, a, b, "S")
        # fringe: two points of hair dipping over the forehead
        span(rows, 7, 13, 15, "h")
        span(rows, 7, 18, 20, "h")
        put(rows, 16, 7, "h")
        put(rows, 17, 7, "S")
        # brows and eyes: two pixels each, one row, relaxed
        span(rows, 9, 13, 14, "E")
        span(rows, 9, 18, 19, "E")
        put(rows, 13, 8, "E")
        put(rows, 18, 8, "E")
        # blush, and the cheek in shadow on the far side
        put(rows, 12, 12, "k")
        put(rows, 20, 12, "k")
        span(rows, 13, 18, 19, "s")
        # the mouth is a short line, not a smile: this character is calm
        span(rows, 13, 15, 17, "s")
        put(rows, 14, 12, "s")
        put(rows, 18, 12, "s")
        span(rows, 17, 15, 17, "S")            # neck
    elif view == "up":
        # From behind: all hair. The mass follows the same spans as the front,
        # so the two views share a silhouette and the head does not change size
        # when the player turns around.
        for y, (a, b) in FACE.items():
            span(rows, y, a, b, "h")
        fill(rows, 10, 10, 21, 17, "h")
        span(rows, 9, 13, 18, "H")
        span(rows, 10, 12, 16, "H")
        span(rows, 11, 11, 14, "H")
        fill(rows, 20, 11, 22, 16, "j")
        fill(rows, 11, 13, 13, 17, "j")
        span(rows, 11, 15, 19, "l")
        span(rows, 12, 12, 15, "l")
        # a parting line, so the back reads as hair with a direction rather
        # than as a smooth dome: two dark strokes leaving the crown
        for i, y in enumerate(range(10, 16)):
            put(rows, 17 + (i // 3), y, "j")
        span(rows, 14, 11, 20, "j")
        # the ends of the hair flick out over the shoulders
        put(rows, 9, 15, "j")
        put(rows, 22, 15, "j")
        # the nape sits on the collar
        span(rows, 17, 14, 16, "j")
        span(rows, 17, 18, 20, "j")
    else:  # side, facing right
        # The profile is a single column of face at the front of the head, with
        # hair covering everything behind it. Fill the whole face block first
        # and carve the hair out of it: leaving the two routines to overlap was
        # what punched holes in the cheek.
        fill(rows, 12, 7, 22, 16, "S")
        fill(rows, 12, 7, 16, 16, "h")         # the back half is hair
        fill(rows, 21, 8, 22, 15, "s")         # cheek in shadow
        fill(rows, 9, 3, 19, 9, "H")           # lit crown, over the top
        fill(rows, 9, 4, 12, 12, "j")          # deep shadow at the back
        span(rows, 5, 12, 17, "l")
        span(rows, 6, 17, 19, "l")
        # the fringe hangs over the temple, in front of the hair mass
        fill(rows, 16, 7, 18, 9, "h")
        span(rows, 10, 16, 17, "l")
        # one eye, forward of centre
        span(rows, 11, 18, 19, "E")
        put(rows, 20, 10, "E")
        # a calm brow
        span(rows, 9, 18, 19, "j")
        put(rows, 22, 13, "s")                 # nose
        span(rows, 14, 18, 20, "s")            # mouth
        put(rows, 13, 17, "k")                 # blush
        span(rows, 17, 15, 17, "S")            # neck


def body(rows, view: str) -> None:
    """Vest, belt, trousers, boots. Grown-up proportions: head to body is 1:1."""
    if view == "side":
        fill(rows, 11, 18, 20, 19, "G")
        fill(rows, 11, 19, 20, 25, "G")
        fill(rows, 11, 19, 12, 25, "F")        # lining down the back
        fill(rows, 19, 20, 20, 24, "g")
        span(rows, 17, 16, 18, "S")
        span(rows, 25, 11, 20, "g")
        fill(rows, 11, 26, 20, 27, "B")
        fill(rows, 18, 26, 19, 27, "X")
        fill(rows, 11, 28, 20, 30, "P")
        fill(rows, 11, 28, 12, 30, "p")
        span(rows, 31, 11, 16, "W")
        span(rows, 31, 18, 20, "W")
        put(rows, 11, 31, "w")
        put(rows, 20, 31, "w")
    else:
        fill(rows, 11, 18, 20, 18, "G")
        fill(rows, 10, 19, 21, 19, "G")
        fill(rows, 10, 20, 21, 25, "G")
        fill(rows, 10, 18, 11, 21, "F")        # lining at both shoulders
        fill(rows, 20, 18, 21, 21, "F")
        span(rows, 18, 15, 17, "S")
        # arms: one column outside the vest, the far one in shadow
        fill(rows, 10, 22, 10, 25, "S")
        fill(rows, 21, 22, 21, 25, "s")
        put(rows, 10, 26, "T")
        put(rows, 21, 26, "T")
        span(rows, 25, 11, 20, "g")
        if view == "down":
            fill(rows, 15, 21, 16, 24, "g")    # centre seam
        fill(rows, 10, 26, 21, 27, "B")
        fill(rows, 15, 26, 17, 27, "X")
        fill(rows, 11, 28, 20, 30, "P")
        fill(rows, 11, 28, 12, 30, "p")
        fill(rows, 19, 28, 20, 30, "p")
        if view == "down":
            fill(rows, 15, 29, 16, 30, "p")    # the gap between the legs
        span(rows, 31, 11, 15, "W")
        span(rows, 31, 18, 20, "W")
        put(rows, 11, 31, "w")
        put(rows, 20, 31, "w")


def outlined(rows: list[list[str]]) -> list[list[str]]:
    """Puts a one pixel outline around the silhouette.

    Drawn by code rather than by hand: a hand drawn outline is the first thing
    to break when a limb moves, and it is invisible until the sprite is on a
    dark tile.
    """
    out = [row[:] for row in rows]
    for y in range(H):
        for x in range(W):
            if rows[y][x] != ".":
                continue
            # A pixel in a one wide vertical gap (between the legs) is inside
            # the silhouette. Outlining it turns a pair of legs into a comb.
            if 0 < x < W - 1 and rows[y][x - 1] == "." and rows[y][x + 1] == ".":
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and rows[ny][nx] not in (".", "#"):
                    out[y][x] = "#"
                    break
    return out


def walk_frame(view: str, step: int) -> list[list[str]]:
    """One frame. Step 1 is a stride: the boots shift and one lifts."""
    rows = blank()
    head(rows, view)
    body(rows, view)
    if step:
        if view == "side":
            fill(rows, 11, 31, 16, 31, ".")
            fill(rows, 18, 31, 20, 31, "W")
            put(rows, 17, 31, ".")
            put(rows, 16, 30, "W")
            put(rows, 19, 30, "P")
        else:
            fill(rows, 11, 31, 15, 31, ".")
            fill(rows, 18, 31, 20, 31, ".")
            fill(rows, 10, 31, 14, 31, "W")
            fill(rows, 18, 31, 21, 31, "W")
            fill(rows, 15, 31, 16, 31, ".")
            put(rows, 10, 30, "W")
            put(rows, 21, 30, "W")
    return outlined(rows)


def frames() -> dict[str, list[list[str]]]:
    return {
        f"{view}_{step}": walk_frame(view, step)
        for view in ("down", "up", "side")
        for step in (0, 1)
    }


def mirror(rows: list[list[str]]) -> list[list[str]]:
    """Flip a side-facing frame, so one drawn direction serves both ways."""
    return [list(reversed(row)) for row in rows]


def draw(rows: list[list[str]]) -> Image:
    img = Image(W, H)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            img.dot(x, y, PAL[ch])
    return img


# Atlas row order. The Kotlin sheet indexes it by Direction.ordinal, so the two
# must stay in the same order as the enum: UP, DOWN, LEFT, RIGHT.
ATLAS_ROWS = ("up", "down", "left", "right")


def atlas_frames(all_frames: dict[str, list[list[str]]]) -> dict[str, list[list[str]]]:
    return {
        "up": [all_frames["up_0"], all_frames["up_1"]],
        "down": [all_frames["down_0"], all_frames["down_1"]],
        "left": [mirror(all_frames["side_0"]), mirror(all_frames["side_1"])],
        "right": [all_frames["side_0"], all_frames["side_1"]],
    }


def atlas() -> Image:
    """The sheet the game loads: four rows by two frames, 32x32 each.

    Left is the mirror of right rather than hand-drawn: one drawn direction
    cannot drift out of sync with the other, and the mirror is free.
    """
    packed = atlas_frames(frames())
    img = Image(2 * W, len(ATLAS_ROWS) * H)
    for row, key in enumerate(ATLAS_ROWS):
        for col, rows in enumerate(packed[key]):
            art = draw(rows)
            for y in range(H):
                for x in range(W):
                    r, g, b, a = art.px(x, y)
                    if a:
                        img.dot(col * W + x, row * H + y, (r, g, b))
    return img


def review_sheet(scale: int = 8) -> Image:
    """Both walk frames of all four directions, on grass, for review.

    The rows are in atlas order, so this doubles as a picture of the sheet: what
    you see at row 0 is what the game draws when the player faces up.
    """
    packed = atlas_frames(frames())
    pad = 8
    cell = W * scale
    img = Image(2 * (cell + pad) + pad, len(ATLAS_ROWS) * (cell + pad) + pad,
                fill=(0x5C, 0x7A, 0x45))       # grass, so the outline can be judged
    for row, key in enumerate(ATLAS_ROWS):
        for col, rows in enumerate(packed[key]):
            art = draw(rows)
            x0 = pad + col * (cell + pad)
            y0 = pad + row * (cell + pad)
            for y in range(H):
                for x in range(W):
                    r, g, b, a = art.px(x, y)
                    if not a:
                        continue
                    for dy in range(scale):
                        for dx in range(scale):
                            img.dot(x0 + x * scale + dx, y0 + y * scale + dy, (r, g, b))
    return img


def main(argv: list[str]) -> None:
    if "--atlas" in argv:
        # written to the app assets, not docs: this file is what the APK loads
        img = atlas()
        path = os.path.join(ROOT, "app", "src", "main", "assets", "sprites",
                            "player.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.to_png(path)
        print(f"{path}  {img.w}x{img.h}  4 arah x 2 frame, {W}x{H} px per frame")
        return

    out_dir = os.path.join(ROOT, "docs", "sprites")
    os.makedirs(out_dir, exist_ok=True)
    img = review_sheet()
    path = os.path.join(out_dir, "player.png")
    img.to_png(path)
    print(f"{path}  {img.w}x{img.h}  4 arah x 2 frame, {W}x{H} px per frame")


if __name__ == "__main__":
    main(sys.argv[1:])
