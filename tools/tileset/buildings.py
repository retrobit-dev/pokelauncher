"""Building parts, drawn as 32x32 sections so a house is built from pieces.

HeartGold houses read from the front: a triangular roof band, a plaster wall
with two windows, then a door. Splitting those into sections means the map
builder can make a 2x2 cottage or the wider lab without new art.
"""
from __future__ import annotations

from . import palette as P
from .pixels import Image, stamp

SIZE = 32


def roof() -> Image:
    """Roof band with tile shingles and a lit ridge."""
    img = Image(SIZE, SIZE, P.ROOF_2)
    for y in range(SIZE):
        for x in range(SIZE):
            # shingle rows: alternate the offset every 4 px
            row = y // 4
            offset = 0 if row % 2 == 0 else 4
            if (x + offset) % 8 == 0:
                img.dot(x, y, P.ROOF_3)
            if y % 4 == 3:
                img.dot(x, y, P.ROOF_DARK)
    img.hline(0, SIZE - 1, 0, P.ROOF_1)
    img.hline(0, SIZE - 1, 1, P.ROOF_1)
    img.rect(0, SIZE - 3, SIZE, 3, P.ROOF_DARK)
    # eave shadow
    img.hline(0, SIZE - 1, SIZE - 1, P.INK_SOFT)
    return img


def roof_edge(direction: str) -> Image:
    """Sloped end of a roof: the gable falls away on one side.

    The middle roof tile is a flat band, so the ends have to share the same
    eave line or a 3-wide cottage shows a step. Both ends keep the bottom two
    rows solid and only cut the upper slope.
    """
    img = Image(SIZE, SIZE, P.ROOF_2)
    # same shingle pattern as the middle section
    for y in range(SIZE):
        row = y // 4
        offset = 0 if row % 2 == 0 else 4
        for x in range(SIZE):
            if (x + offset) % 8 == 0:
                img.dot(x, y, P.ROOF_3)
            if y % 4 == 3:
                img.dot(x, y, P.ROOF_DARK)

    left = direction == "left"
    # A gable slopes down toward the outside: narrow at the ridge (top), wide
    # at the eave (bottom). Row 0 is the ridge, row SIZE-1 the eave.
    for y in range(SIZE):
        t = y / (SIZE - 1)
        cut = int(round(18 * t))          # 0 px cut at the ridge, 18 px at the eave
        for i in range(cut):
            x = i if left else SIZE - 1 - i
            img.dot(x, y, (0, 0, 0), 0)
        if 0 < cut < SIZE:
            x = cut if left else SIZE - 1 - cut
            img.dot(x, y, P.ROOF_1)
    # ridge highlight and eave shadow, drawn last so they stay crisp
    img.hline(0, SIZE - 1, 0, P.ROOF_1)
    img.hline(0, SIZE - 1, 1, P.ROOF_1)
    img.rect(0, SIZE - 3, SIZE, 3, P.ROOF_DARK)
    img.hline(0, SIZE - 1, SIZE - 1, P.INK_SOFT)
    return img


def wall() -> Image:
    """Plaster wall with a wooden skirt board along the bottom."""
    img = Image(SIZE, SIZE, P.WALL_1)
    # subtle vertical plaster grain
    for x in range(0, SIZE, 5):
        img.vline(x, 0, SIZE - 1, P.WALL_2)
    img.rect(0, SIZE - 5, SIZE, 5, P.WOOD_2)
    img.hline(0, SIZE - 1, SIZE - 5, P.WOOD_1)
    img.hline(0, SIZE - 1, SIZE - 1, P.WOOD_DARK)
    return img


def wall_window() -> Image:
    """Wall section with a window: the most common HG house facade."""
    img = wall()
    # frame
    img.rect(6, 7, 20, 16, P.WOOD_3)
    # glass with a diagonal sheen
    img.rect(7, 8, 18, 14, P.WINDOW_2)
    img.rect(7, 8, 18, 5, P.WINDOW_1)
    for i in range(12):
        img.dot(8 + i, 9 + i, P.WINDOW_1)
    # cross bars
    img.vline(15, 8, 21, P.WOOD_3)
    img.hline(7, 24, 14, P.WOOD_3)
    # sill
    img.rect(5, 22, 22, 2, P.WOOD_1)
    img.hline(5, 26, 24, P.WOOD_3)
    return img


def wall_door() -> Image:
    """Wall section with the front door, mat included."""
    img = wall()
    img.rect(9, 6, 14, 22, P.WOOD_3)      # frame
    img.rect(10, 7, 12, 20, P.DOOR_1)     # leaf
    img.rect(10, 7, 12, 2, P.DOOR_2)
    img.vline(10, 7, 26, P.DOOR_2)
    img.vline(21, 7, 26, P.DOOR_2)
    # panels
    img.rect(12, 10, 8, 6, P.DOOR_2)
    img.rect(12, 18, 8, 6, P.DOOR_2)
    # knob
    img.dot(19, 17, P.GOLD)
    img.dot(19, 18, P.PAPER_SHADE)
    # threshold mat
    img.rect(8, 27, 16, 3, P.PAPER_SHADE)
    img.hline(8, 23, 27, P.PAPER_DEEP)
    return img


def wall_plain() -> Image:
    """Blank wall filler, for corners and the side of a house."""
    return wall()


def lab_badge() -> Image:
    """A 16x16 sign plate reading ELM, hung beside the lab door."""
    img = Image(16, 16)
    img.rect(1, 3, 14, 11, P.WOOD_3)
    img.rect(2, 4, 12, 9, P.PAPER)
    stamp(img, [
        "###.#.#...#.#",
        "#...#.#.#.#.#",
        "###.#.#.#.#.#",
        "#...#.#.#.#.#",
        "###.#.#..#..#",
    ], 2, 6, {"#": P.INK})
    return img


BUILDING_PARTS: dict[str, tuple] = {
    "roof": (roof, 2, 2),
    "roof_left": (lambda: roof_edge("left"), 2, 2),
    "roof_right": (lambda: roof_edge("right"), 2, 2),
    "wall": (wall, 2, 2),
    "wall_plain": (wall_plain, 2, 2),
    "wall_window": (wall_window, 2, 2),
    "wall_door": (wall_door, 2, 2),
    "lab_badge": (lab_badge, 1, 1),
}
