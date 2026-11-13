"""Props: trees, bushes, flowers, rocks, fences, signs and stairs.

A tree is 2x2 tiles (32x32) because a 16px canopy reads as a dot, not a tree;
the map builder places it by its top-left tile and marks all four cells solid.
Everything else fits one tile.
"""
from __future__ import annotations

from . import palette as P
from .pixels import Image, stamp

SIZE = 16


def tree_canopy() -> Image:
    """32x32 tree, trunk included, with a soft drop shadow at the base."""
    img = Image(32, 32)

    # --- trunk (behind the canopy so the canopy always wins) -----------
    img.rect(14, 20, 5, 10, P.WOOD_3)
    img.rect(15, 20, 3, 10, P.WOOD_2)
    img.vline(15, 21, 28, P.WOOD_1)
    # root flare
    img.rect(12, 28, 9, 2, P.WOOD_3)

    # --- canopy: three overlapping blobs, darkest at the bottom --------
    blobs = [
        (16, 12, 13),   # centre
        (8, 15, 9),     # left
        (24, 15, 9),    # right
        (16, 6, 8),     # top
    ]
    for cx, cy, r in blobs:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img.dot(x, y, P.LEAF_2)

    # lighter top-left mass to fake a light source
    for cx, cy, r in ((13, 10, 8), (8, 14, 5), (19, 7, 5)):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img.dot(x, y, P.LEAF_1)

    # highlight speckles
    stamp(img, [
        "......####......",
        "....########....",
        "...#.##..####...",
        "..#...##..###...",
        ".......##.......",
    ], 5, 5, {"#": P.LEAF_LIGHT})

    # dark outline of the canopy bottom, so the tree sits on the ground
    for y in range(20, 27):
        for x in range(3, 29):
            r, g, b, a = img.px(x, y)
            below = img.px(x, y + 1)
            if a and (below[3] == 0 or (y > 24 and r == P.LEAF_2[0])):
                img.dot(x, y, P.LEAF_3)
    return img


def bush() -> Image:
    """A single-tile shrub, walkable around but solid itself."""
    img = Image(SIZE, SIZE)
    for cx, cy, r in ((8, 10, 6), (5, 11, 4), (11, 11, 4)):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img.dot(x, y, P.LEAF_2)
    stamp(img, [
        "....####....",
        "..########..",
        ".##..##..##.",
        ".##.####.##.",
        "..########..",
        "....####....",
    ], 2, 5, {"#": P.LEAF_1})
    stamp(img, [
        "....##....",
        "..........",
        "..##......",
    ], 5, 6, {"#": P.LEAF_LIGHT})
    return img


def flowers(kind: str = "gold") -> Image:
    """Small flower cluster: gold, red or white petals."""
    petal = {"gold": P.FLOWER_CORE, "red": P.FLOWER_RED, "white": P.FLOWER_WHITE}[kind]
    img = Image(SIZE, SIZE)
    art = [
        "..##......##....",
        ".#..#....#..#...",
        ".#..#....#..#...",
        "..##......##....",
        "................",
        "........##......",
        ".......#..#.....",
        ".......#..#.....",
        "........##......",
        "................",
        "..##............",
        ".#..#.....##....",
        "..##.....#..#...",
        "..........##....",
        "................",
        "................",
    ]
    stamp(img, art, 0, 0, {"#": petal})
    # a green sprig under each bloom so they are planted, not floating
    for (x, y) in ((3, 4), (10, 4), (8, 9), (2, 13), (6, 9)):
        img.dot(x, y, P.GRASS_3)
        img.dot(x, y + 1, P.LEAF_2)
    return img


def rock() -> Image:
    """Boulder: solid, and the classic way to block a shortcut."""
    img = Image(SIZE, SIZE)
    for cx, cy, r in ((8, 9, 6), (5, 11, 4), (11, 11, 4)):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    img.dot(x, y, P.STONE_2)
    stamp(img, [
        "...####...",
        "..######..",
        ".##...##..",
        ".#.....##.",
        "........#.",
        "........#.",
        "........#.",
        ".#.....##.",
        "..#####...",
    ], 3, 4, {"#": P.STONE_3})
    stamp(img, [
        "..####",
        ".###..",
        ".##...",
    ], 4, 4, {"#": P.STONE_1})
    img.hline(4, 11, 14, P.STONE_DARK)
    return img


def fence_h() -> Image:
    """Horizontal fence rail (top/bottom run of a pen)."""
    img = Image(SIZE, SIZE)
    img.rect(0, 6, SIZE, 4, P.WOOD_2)
    img.hline(0, SIZE - 1, 6, P.WOOD_1)
    img.hline(0, SIZE - 1, 9, P.WOOD_3)
    img.rect(3, 4, 3, 9, P.WOOD_3)
    img.rect(11, 4, 3, 9, P.WOOD_3)
    img.vline(3, 4, 12, P.WOOD_1)
    img.vline(11, 4, 12, P.WOOD_1)
    return img


def fence_v() -> Image:
    """Vertical fence rail."""
    img = Image(SIZE, SIZE)
    img.rect(6, 0, 4, SIZE, P.WOOD_2)
    img.vline(6, 0, SIZE - 1, P.WOOD_1)
    img.vline(9, 0, SIZE - 1, P.WOOD_3)
    img.rect(4, 3, 9, 3, P.WOOD_3)
    img.rect(4, 11, 9, 3, P.WOOD_3)
    img.hline(4, 12, 3, P.WOOD_1)
    img.hline(4, 12, 11, P.WOOD_1)
    return img


def sign() -> Image:
    """A wooden notice board; the map builder attaches the text."""
    img = Image(SIZE, SIZE)
    img.rect(7, 10, 3, 6, P.WOOD_3)
    img.rect(2, 3, 13, 8, P.WOOD_1)
    img.rect(2, 3, 13, 1, P.PAPER)
    img.rect(2, 10, 13, 1, P.WOOD_3)
    stamp(img, [
        "##########",
        "..#....#..",
        "......#...",
        "..#.......",
        "......#...",
    ], 3, 5, {"#": P.INK_SOFT})
    return img


def stairs() -> Image:
    """Three stone steps that connect two grass levels."""
    img = Image(SIZE, SIZE, P.STONE_2)
    for i, y in enumerate((4, 8, 12)):
        img.rect(0, y, SIZE, 4 if i < 2 else 3, P.STONE_1 if i % 2 == 0 else P.STONE_2)
        img.hline(0, SIZE - 1, y, P.STONE_1)
        img.hline(0, SIZE - 1, y + 3, P.STONE_3)
    img.vline(0, 0, SIZE - 1, P.STONE_3)
    img.vline(SIZE - 1, 0, SIZE - 1, P.STONE_DARK)
    return img


# ---------------------------------------------------------------- registry
# name -> (image factory, solid?, tiles wide, tiles tall)
PROPS: dict[str, tuple] = {
    "tree": (tree_canopy, True, 2, 2),
    "bush": (bush, True, 1, 1),
    "flowers_gold": (lambda: flowers("gold"), False, 1, 1),
    "flowers_red": (lambda: flowers("red"), False, 1, 1),
    "flowers_white": (lambda: flowers("white"), False, 1, 1),
    "rock": (rock, True, 1, 1),
    "fence_h": (fence_h, True, 1, 1),
    "fence_v": (fence_v, True, 1, 1),
    "sign": (sign, True, 1, 1),
    "stairs": (stairs, False, 1, 1),
}
