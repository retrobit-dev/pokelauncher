"""Ground tiles: grass, dirt path, water and cliffs.

Every tile is 16x16 and tileable: the edges line up with their neighbours so a
map builder can repeat them without seams. The variation tiles exist so a lawn
does not look like wallpaper - the map builder picks them by a hash of the tile
coordinates.
"""
from __future__ import annotations

from . import palette as P
from .pixels import Image, stamp

SIZE = 16


def grass_plain() -> Image:
    """Base lawn: flat mid green with a few darker tufts."""
    img = Image(SIZE, SIZE, P.GRASS_1)
    # a sparse, deterministic scatter keeps the tile readable but not busy
    tufts = [
        "................",
        "................",
        "....##..........",
        "..#.##....##....",
        "..####....##....",
        "..........##....",
        "................",
        ".......##.......",
        ".......##....#..",
        ".............##.",
        "................",
        "....##..........",
        "....##...##.....",
        ".........##.....",
        "................",
        "................",
    ]
    stamp(img, tufts, 0, 0, {"#": P.GRASS_2})
    return img


def grass_detail() -> Image:
    """Same lawn with one small four-petal bloom: breaks up long green runs."""
    img = grass_plain()
    # 5x5 bloom, dark outline so it reads at 16 px even on a bright lawn
    stamp(img, [
        "..#..",
        ".###.",
        "##.##",
        ".###.",
        "..#..",
    ], 6, 5, {"#": P.FLOWER_WHITE})
    stamp(img, [
        ".....",
        "..#..",
        ".#.#.",
        "..#..",
        ".....",
    ], 6, 5, {"#": P.FLOWER_CORE})
    # a couple of leaves under it, so it is planted rather than floating
    img.dot(8, 10, P.LEAF_2)
    img.dot(7, 10, P.GRASS_3)
    img.dot(9, 10, P.GRASS_3)
    img.dot(8, 11, P.LEAF_2)
    return img


def grass_dark() -> Image:
    """Taller, shaded grass used along a tree line."""
    img = Image(SIZE, SIZE, P.GRASS_2)
    stamp(img, [
        "..##....##......",
        ".####..####.....",
        ".####..####..##.",
        "..##....##..####",
        ".............###",
        "................",
        "....##....##....",
        "...####..####...",
        "....##....##....",
        "................",
        ".##....##.......",
        "####..####......",
        ".##....##....##.",
        ".............###",
        "................",
        "................",
    ], 0, 0, {"#": P.GRASS_3})
    return img


def path_stone() -> Image:
    """Packed-earth path, the colour of the roads in New Bark Town."""
    img = Image(SIZE, SIZE, P.DIRT_1)
    # speckle so a long path has texture without visible repetition
    stamp(img, [
        "................",
        "..##............",
        "..##.......###..",
        "...........###..",
        ".......##.......",
        ".......##.......",
        "................",
        ".....##.........",
        "..##.##....##...",
        "..##.......##...",
        "................",
        ".##.............",
        ".##.......##....",
        "..........##....",
        "................",
        "................",
    ], 0, 0, {"#": P.DIRT_3})
    # a lighter pebble or two
    stamp(img, [
        "..",
        "..",
    ], 12, 5, {".": P.DIRT_1})
    return img


def path_edge(direction: str) -> Image:
    """Grass along one side, path on the other, with a soft boundary.

    direction is the side the GRASS is on: 'n', 's', 'e' or 'w'.
    """
    img = path_stone()
    band = 3
    for i in range(SIZE):
        for depth in range(band):
            if depth >= band:
                break
            if direction == "n":
                x, y = i, depth
            elif direction == "s":
                x, y = i, SIZE - 1 - depth
            elif direction == "w":
                x, y = depth, i
            else:  # 'e'
                x, y = SIZE - 1 - depth, i
            # jagged edge: the last row of grass dips in and out
            wobble = 1 if (i * 7 + depth * 3) % 5 < 2 else 0
            if depth < band - 1 - wobble:
                img.dot(x, y, P.GRASS_1 if depth < band - 2 else P.GRASS_2)
    return img


def water(shallow: bool = False) -> Image:
    """Open water with horizontal ripples, seamless on every side.

    Two ripple bands and a darker shift near the bottom give a large pond some
    depth without any gradient dithering.
    """
    base = P.WATER_2 if shallow else P.WATER_3
    img = Image(SIZE, SIZE, base)
    ripple = P.WATER_1 if shallow else P.WATER_2
    for y in (3, 4, 10, 11):
        for x in range(SIZE):
            if (x + y * 3) % 8 < 5:
                img.dot(x, y, ripple)
    for y in (7, 14):
        for x in range(SIZE):
            if (x + y) % 8 < 2:
                img.dot(x, y, P.WATER_DARK if not shallow else P.WATER_3)
    # lower half a touch deeper
    for y in range(9, SIZE):
        for x in range(SIZE):
            if (x + y) % 3 == 0:
                img.dot(x, y, P.WATER_DARK if not shallow else P.WATER_3)
    return img


def water_foam() -> Image:
    """Water meeting land along the TOP edge: sand, foam, then open water.

    A hard water line looks like a blue rectangle pasted on the lawn; the sand
    strip and the wavy foam make the shore read as a shore.
    """
    img = water(True)
    # sand, two rows, with a ragged lower boundary
    for x in range(SIZE):
        img.dot(x, 0, P.DIRT_1)
        img.dot(x, 1, P.DIRT_2)
        if (x * 3) % 5 < 3:
            img.dot(x, 2, P.DIRT_3)
    # foam where the sand meets the water
    for x in range(SIZE):
        if (x * 5 + 1) % 7 < 4:
            img.dot(x, 2, P.WATER_FOAM)
            img.dot(x, 3, P.WATER_FOAM)
    for x in range(SIZE):
        if (x * 7) % 6 < 2:
            img.dot(x, 4, P.WATER_1)
    return img


def cliff_face() -> Image:
    """The rock wall of a small ledge, used to separate two grass levels."""
    img = Image(SIZE, SIZE, P.STONE_2)
    stamp(img, [
        "################",
        "#..............#",
        "#.####..###....#",
        "#.#..#..#.#....#",
        "#.####..###....#",
        "#..............#",
        "#....####......#",
        "#....#..#......#",
        "#....####......#",
        "#..............#",
        "#..###....####.#",
        "#..#......#..#.#",
        "#..###....####.#",
        "#..............#",
        "################",
        "................",
    ], 0, 0, {"#": P.STONE_3})
    # top lit edge, bottom shaded edge
    img.hline(0, SIZE - 1, 0, P.STONE_1)
    img.hline(0, SIZE - 1, SIZE - 1, P.STONE_DARK)
    return img


def cliff_top() -> Image:
    """The lip of a ledge: grass with a stone rim along the bottom."""
    img = grass_plain()
    img.hline(0, SIZE - 1, SIZE - 1, P.STONE_2)
    img.hline(0, SIZE - 1, SIZE - 2, P.STONE_3)
    return img
