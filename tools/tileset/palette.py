"""Johto-flavoured palette, derived from HgColors in ui/theme/Theme.kt.

Every colour is 8-bit sRGB and deliberately hand-picked: flat, slightly warm,
low saturation on purpose. HeartGold's tiles read as painted paper, not as
glossy 3D, so the ramp for each material is short (3-4 steps) and the darkest
step is close to the ink colour, never pure black.
"""
from __future__ import annotations

RGB = tuple[int, int, int]

# ---------------------------------------------------------------- paper / UI
PAPER: RGB = (0xFB, 0xF3, 0xDC)
PAPER_DEEP: RGB = (0xF3, 0xE4, 0xBF)
PAPER_SHADE: RGB = (0xE9, 0xD7, 0xAE)
INK: RGB = (0x3B, 0x2F, 0x1E)
INK_SOFT: RGB = (0x6B, 0x5B, 0x44)
INK_FAINT: RGB = (0x9A, 0x87, 0x68)

# ---------------------------------------------------------------- grass
GRASS_1: RGB = (0x7C, 0xA9, 0x5E)
GRASS_2: RGB = (0x6B, 0x9A, 0x4F)
GRASS_3: RGB = (0x59, 0x86, 0x41)
GRASS_DARK: RGB = (0x46, 0x6C, 0x34)
GRASS_LIGHT: RGB = (0x92, 0xBD, 0x71)

# ---------------------------------------------------------------- dirt / path
DIRT_1: RGB = (0xD6, 0xBC, 0x92)
DIRT_2: RGB = (0xC7, 0xA9, 0x7C)
DIRT_3: RGB = (0xB4, 0x93, 0x66)
DIRT_DARK: RGB = (0x99, 0x78, 0x4F)

# ---------------------------------------------------------------- wood
WOOD_1: RGB = (0xB6, 0x82, 0x52)
WOOD_2: RGB = (0x9C, 0x6B, 0x3F)
WOOD_3: RGB = (0x7E, 0x53, 0x2F)
WOOD_DARK: RGB = (0x5C, 0x3B, 0x21)

# ---------------------------------------------------------------- stone
STONE_1: RGB = (0xC9, 0xC4, 0xB4)
STONE_2: RGB = (0xAB, 0xA5, 0x94)
STONE_3: RGB = (0x8D, 0x87, 0x78)
STONE_DARK: RGB = (0x6E, 0x69, 0x5C)

# ---------------------------------------------------------------- water
WATER_1: RGB = (0x7E, 0xB6, 0xC9)
WATER_2: RGB = (0x63, 0x9F, 0xB6)
WATER_3: RGB = (0x4C, 0x86, 0xA0)
WATER_DARK: RGB = (0x3A, 0x6A, 0x82)
WATER_FOAM: RGB = (0xDF, 0xF1, 0xF3)

# ---------------------------------------------------------------- foliage
LEAF_1: RGB = (0x4E, 0x82, 0x3F)
LEAF_2: RGB = (0x3C, 0x69, 0x31)
LEAF_3: RGB = (0x2C, 0x51, 0x25)
LEAF_LIGHT: RGB = (0x6E, 0xA0, 0x52)

# ---------------------------------------------------------------- roof / house
ROOF_1: RGB = (0xC0, 0x5E, 0x4C)
ROOF_2: RGB = (0xA6, 0x4A, 0x3B)
ROOF_3: RGB = (0x87, 0x39, 0x2D)
ROOF_DARK: RGB = (0x66, 0x2A, 0x21)

WALL_1: RGB = (0xF0, 0xE6, 0xCB)
WALL_2: RGB = (0xDC, 0xCE, 0xAC)
WALL_3: RGB = (0xC2, 0xB1, 0x8C)

WINDOW_1: RGB = (0x8F, 0xC4, 0xD6)
WINDOW_2: RGB = (0x5F, 0x97, 0xAD)
WINDOW_DARK: RGB = (0x3E, 0x6C, 0x80)

DOOR_1: RGB = (0x8A, 0x5C, 0x35)
DOOR_2: RGB = (0x6E, 0x46, 0x27)

# ---------------------------------------------------------------- flowers
FLOWER_PETAL: RGB = (0xF2, 0xE0, 0x9A)
FLOWER_CORE: RGB = (0xE0, 0xB8, 0x4C)
FLOWER_RED: RGB = (0xD1, 0x6D, 0x5E)
FLOWER_WHITE: RGB = (0xFA, 0xF6, 0xE8)

# ---------------------------------------------------------------- accent
GOLD: RGB = (0xE0, 0xB8, 0x4C)
RED: RGB = (0xC5, 0x3A, 0x2D)
RED_DEEP: RGB = (0x9A, 0x2A, 0x20)

TRANSPARENT: RGB = (0, 0, 0)


def shade(colour: RGB, amount: float) -> RGB:
    """Mixes a colour toward the ink tone, for a flat hand-picked shadow."""
    t = max(0.0, min(1.0, amount))
    return tuple(  # type: ignore[return-value]
        int(round(colour[i] * (1 - t) + INK[i] * t)) for i in range(3)
    )


def tint(colour: RGB, amount: float) -> RGB:
    """Mixes a colour toward warm white, for a flat highlight."""
    t = max(0.0, min(1.0, amount))
    return tuple(  # type: ignore[return-value]
        int(round(colour[i] * (1 - t) + 255 * t)) for i in range(3)
    )
