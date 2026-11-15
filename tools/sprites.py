#!/usr/bin/env python3
"""Draws the player sprite the app loads.

    python3 tools/sprites.py                  # docs/sprites/player.png, a review sheet
    python3 tools/sprites.py --atlas          # writes app/src/main/assets/sprites/player.png

Why a generator and not a PNG: a sprite is a list of shapes in the source, so a
change is a few lines in a diff, not a binary the reviewer has to open. It also
means the review sheet and the asset can never disagree.

The character is the Harvest Moon farmer the user asked for, redrawn at 32x32:
  - a blue cap with a white front panel and a brim that juts forward
  - brown hair, short, longer at the nape
  - an orange shirt under blue denim overalls, brass buckle
  - brown boots
  - chibi proportions: the head is a third of the height, the body the rest

It is 32x32 - two map cells each way - because that is the size the art was
drawn at and the size that reads on a 2560x1600 panel. At 16px the face was
four pixels wide: room for two dots and nothing else.

Shading rules, so every frame reads the same at 10x on the tablet:
  - light from the top-left; one darker tone per material, never a gradient
  - a single warm-brown outline, not black, so the character sits on grass
  - the brim is row 8 and the face starts at row 9: a brim on the top row of
    the face covers the eyes, and the character looks blind
  - feet stay on row 31, rows 0 and columns 0/31 stay empty so the outline has
    somewhere to go

Each view is built from explicit blocks rather than by stamping one base sprite:
a profile needs a face disc at the front and hair behind it, and a back view
needs a solid mass of hair. Sharing one base gave three views that all looked
like the front.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from tileset.pixels import Image  # noqa: E402

W=H=32
PAL={
 "#": (0x2C,0x24,0x18),   # outline, warm dark brown
 # cap
 "C": (0x3E,0x6E,0xB0),   # cap blue
 "c": (0x2B,0x50,0x84),   # cap shadow
 "L": (0x63,0x9A,0xD8),   # cap light
 "W": (0xEC,0xF1,0xF7),   # cap front panel, off-white
 # hair
 "H": (0x8A,0x5A,0x2B),   # hair
 "h": (0x6B,0x44,0x20),   # hair shadow
 "u": (0xA8,0x74,0x3C),   # hair light
 # skin
 "S": (0xF6,0xC8,0x9B),
 "s": (0xDC,0xA6,0x78),
 # face
 "E": (0x2C,0x24,0x18),
 "k": (0xEC,0x8E,0x86),   # blush
 # clothes
 "O": (0xE0,0x63,0x2F),   # shirt orange
 "o": (0xB8,0x4A,0x20),   # shirt shadow
 "B": (0x3E,0x5C,0x8A),   # overalls denim
 "b": (0x2C,0x42,0x66),   # denim shadow
 "l": (0x54,0x77,0xA8),   # denim light
 "X": (0xE8,0xC5,0x5C),   # buckle gold
 # boots
 "T": (0x6B,0x45,0x2B),
 "t": (0x4A,0x2E,0x1C),
}

def blank(): return [["."]*W for _ in range(H)]
def put(r,x,y,c):
    if 0<=x<W and 0<=y<H: r[y][x]=c
def fill(r,x0,y0,x1,y1,c):
    for y in range(y0,y1+1):
        for x in range(x0,x1+1): put(r,x,y,c)
def span(r,y,a,b,c): fill(r,a,y,b,y,c)

def head(r, view):
    """Big chibi head (rows 3..16), blue cap, brown hair, simple face."""
    # --- hair silhouette first, so the cap sits on top of a mass that exists
    hair = {8:(10,21), 9:(9,22), 10:(9,22), 11:(9,22), 12:(9,22),
            13:(10,21), 14:(10,21), 15:(11,20), 16:(12,19)}
    for y,(a,b) in hair.items(): span(r,y,a,b,"H")
    # the cap crown sits over the top of the hair
    cap = {3:(12,19), 4:(11,20), 5:(10,21), 6:(10,21), 7:(9,22)}
    for y,(a,b) in cap.items(): span(r,y,a,b,"C")
    span(r,3,13,18,"L"); span(r,4,12,17,"L"); span(r,5,11,15,"L")
    fill(r,19,4,22,7,"c")
    # white front panel: the one detail that says "Harvest Moon cap"
    if view == "down":
        fill(r,12,5,18,7,"W")
        fill(r,12,5,13,7,"L")
    # The brim sits at row 8 and the face starts at row 9. A brim drawn on the
    # top row of the face covers the eyes: the character looks blind. Three rows
    # of forehead under a cap is what the reference has.
    if view == "down":
        span(r,8,7,24,"c")
        span(r,8,8,23,"C")
    elif view == "up":
        span(r,8,8,23,"c")

    if view == "down":
        for y,(a,b) in {9:(11,20), 10:(10,21), 11:(10,21), 12:(10,21),
                        13:(10,21), 14:(11,20), 15:(12,19)}.items():
            span(r,y,a,b,"S")
        # hair peeking out under the brim, both sides
        span(r,9,10,12,"H"); span(r,9,19,21,"H")
        span(r,10,10,11,"h"); span(r,10,20,21,"h")
        # eyes: two dark blocks, the Harvest Moon look
        fill(r,12,11,14,12,"E")
        fill(r,17,11,19,12,"E")
        put(r,13,11,"W"); put(r,18,11,"W")
        put(r,11,13,"k"); put(r,20,13,"k")
        span(r,14,15,17,"s")
        fill(r,20,10,21,11,"s")     # cheek shadow under the hair
    elif view == "up":
        # From behind: the cap crown, then a mass of brown hair, longer at the
        # nape. No brim band across the middle - a rear view shows the crown and
        # the hair under it, and a brim there cut the head in two.
        fill(r,10,9,21,17,"H")
        span(r,9,10,21,"H")
        # light from the top-left, so the back of the head has the same lighting
        # direction as the front
        # One lit region top-left, one shadow region bottom-right. Alternating
        # light and dark rows made the back of the head look striped.
        fill(r,10,9,17,13,"u")
        fill(r,18,10,21,17,"h")
        fill(r,10,14,13,17,"h")
        span(r,14,14,17,"u")
        put(r,14,13,"H")
        # two tufts of hair over the collar
        span(r,17,12,14,"h")
        span(r,17,17,19,"h")
    else:  # side, facing right
        # Profile, built as a face disc plus a hair mass behind it.
        #
        # Painting the hair first and then a wide skin block over it gave a pale
        # rectangle almost as wide as the head with one eye in the middle: that
        # reads as a front view with a bad hairline, not as a profile. So the
        # hair is drawn last, as a shape, and it covers everything behind x15.
        fill(r,15,9,22,16,"S")        # the face disc
        fill(r,20,10,22,15,"s")       # cheek in shadow at the very front
        # hair: a mass covering the back and the top of the face disc
        fill(r,9,9,17,16,"H")
        fill(r,9,9,11,16,"h")         # nape in shadow
        span(r,10,11,16,"u")          # lit hair at the crown
        span(r,11,12,15,"u")
        # the fringe curls forward over the brow, above the eye only, and the
        # hair line curves instead of ending in a straight vertical cut
        span(r,9,14,18,"H")
        put(r,10,18,"H")
        put(r,10,19,"H")
        span(r,10,15,17,"h")
        put(r,11,16,"H")
        put(r,11,17,"h")
        # ear, a notch on the hair line
        put(r,14,12,"s")
        put(r,14,13,"s")
        # one eye near the front, brow one row above
        fill(r,18,12,20,13,"E")
        put(r,19,12,"W")
        # cheek, nose at the very front, mouth
        put(r,15,14,"k")
        put(r,22,14,"s")
        span(r,15,19,21,"s")
        # chin: the face rounds off at the bottom instead of being a square
        fill(r,15,16,20,16,"s")
        put(r,15,16,"S")
        # Cap: dome rows 3..7, brim row 8. The brim juts forward past the face,
        # which is the one thing that makes a cap read as a cap in profile.
        for yy, (a, b) in {3: (12, 19), 4: (10, 21), 5: (9, 22),
                           6: (9, 22), 7: (8, 23)}.items():
            span(r, yy, a, b, "C")
        span(r, 3, 13, 18, "L")
        span(r, 4, 11, 17, "L")
        span(r, 5, 10, 14, "L")
        fill(r, 20, 4, 23, 7, "c")
        span(r, 8, 6, 25, "c")
        span(r, 8, 7, 24, "C")
        span(r, 7, 22, 25, "c")


def body(r, view):
    """Orange tee under blue denim overalls: the HM farmer outfit.

    Every variant keeps the shoulders inside one span per row: the first back
    view stepped out at the arms one row at a time, which outlined into a
    staircase down each side.
    """
    if view == "side":
        span(r,17,15,18,"S")          # neck
        fill(r,13,18,21,20,"O")       # shirt
        fill(r,20,18,21,20,"o")
        # The near arm hangs down the middle of the body in profile, not off the
        # back: hung at the back edge it read as a third limb.
        fill(r,16,19,18,25,"O")
        fill(r,18,19,18,25,"o")
        fill(r,16,26,18,26,"S")       # hand
        # overalls
        fill(r,13,21,21,26,"B")
        fill(r,13,21,14,26,"l")
        fill(r,20,21,21,26,"b")
        span(r,26,13,21,"b")
        fill(r,15,23,16,23,"X")       # buckle
        # legs and boots
        fill(r,13,27,20,29,"B")
        fill(r,13,27,13,29,"l")
        fill(r,20,27,20,29,"b")
        fill(r,17,28,17,29,"b")       # the gap between the legs
        fill(r,12,30,16,31,"T")
        fill(r,17,30,21,31,"T")
        fill(r,12,30,12,31,"t")
        fill(r,21,30,21,31,"t")
        fill(r,17,31,18,31,"t")
        return

    else:
        span(r,17,15,17,"S")          # neck
        fill(r,10,18,21,20,"O")       # shirt
        fill(r,10,18,10,19,"o"); fill(r,21,18,21,19,"o")
        # arms, hanging
        fill(r,9,19,9,25,"O")
        fill(r,22,19,22,25,"o")
        fill(r,9,26,9,26,"S"); fill(r,22,26,22,26,"s")
        # overalls: bib, straps, legs
        fill(r,11,21,20,26,"B")
        fill(r,11,21,12,26,"l")
        fill(r,19,21,20,26,"b")
        if view == "down":
            fill(r,13,21,18,24,"B")   # bib
            fill(r,13,21,14,24,"l")
            fill(r,12,18,13,20,"B")   # straps
            fill(r,18,18,19,20,"B")
            fill(r,15,22,16,23,"X")   # buckle on the bib
        span(r,26,11,20,"b")
        # Legs two rows longer, boots two rows tall: a one-row boot made the
        # character look like it had no feet at all, which is the difference
        # between "chibi farmer" and "blob".
        fill(r,12,27,15,29,"B")
        fill(r,16,27,19,29,"B")
        fill(r,16,28,16,29,"b")       # the gap between the legs
        fill(r,12,27,12,29,"l")
        fill(r,19,27,19,29,"b")
        # boots
        fill(r,11,30,15,31,"T")
        fill(r,17,30,21,31,"T")
        fill(r,11,30,11,31,"t")
        fill(r,21,30,21,31,"t")
        fill(r,17,31,18,31,"t")       # sole shadow between the boots

def outlined(rows):
    out=[row[:] for row in rows]
    for y in range(H):
        for x in range(W):
            if rows[y][x]!=".": continue
            if 0<x<W-1 and rows[y][x-1]=="." and rows[y][x+1]==".": continue
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+dx,y+dy
                if 0<=nx<W and 0<=ny<H and rows[ny][nx] not in (".","#"):
                    out[y][x]="#"; break
    return out

def walk_frame(view: str, step: int) -> list[list[str]]:
    r=blank(); head(r,view); body(r,view)
    if step:
        if view=="side":
            # the near boot slides forward, the far one stays
            fill(r,11,30,16,31,".")
            fill(r,18,30,21,31,"T")
            fill(r,17,31,21,31,"t")
            fill(r,17,30,17,30,"T")
        else:
            fill(r,11,31,15,31,".")
            fill(r,17,31,21,31,".")
            fill(r,10,31,14,31,"T")
            fill(r,17,31,21,31,"T")
            fill(r,15,31,16,31,".")
            fill(r,10,30,10,31,"t")
            fill(r,21,30,21,31,"t")
    return outlined(r)



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
