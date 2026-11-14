"""The launcher machine: the in-world terminal that opens the app list.

Two 16x16 halves on purpose. The editor's grid is one tile per cell, so a
32x32 machine would need a footprint feature it does not have yet; two tiles
side by side give a wide terminal that reads correctly at 16px and can be
placed with the tools that already exist.

Art direction: the same warm paper body as the buildings, a dark screen so it
looks powered on, and a small red light so it is findable at a glance.
"""
from __future__ import annotations

from tileset.palette import shade
from tileset.pixels import Image

BODY = (222, 210, 184)
BODY_DARK = (188, 173, 145)
BODY_EDGE = (150, 134, 108)
SCREEN = (44, 62, 74)
SCREEN_GLOW = (86, 132, 140)
SCREEN_LIGHT = (176, 214, 200)
ACCENT = (197, 58, 45)


def _base() -> Image:
    img = Image(16, 16)
    # cabinet: a chunky upright with a rounded top edge
    img.rect(2, 1, 12, 14, BODY)
    img.rect(2, 1, 12, 1, shade(BODY, 1.08))
    img.rect(2, 13, 12, 2, BODY_DARK)
    img.rect(1, 2, 1, 12, BODY_DARK)
    img.rect(14, 2, 1, 12, BODY_EDGE)
    img.rect(2, 15, 12, 1, BODY_EDGE)
    # a soft shadow under the right edge sells the bulk
    for y in range(3, 14):
        img.dot(15, y, BODY_EDGE)
    return img


def machine_left() -> Image:
    img = _base()
    # screen glass, inset from the frame
    img.rect(4, 3, 10, 7, SCREEN)
    for x in range(4, 14):
        img.dot(x, 3, SCREEN_GLOW)
    img.rect(5, 5, 4, 1, SCREEN_GLOW)
    img.rect(5, 7, 6, 1, SCREEN_LIGHT)
    # keyboard strip: tiny keys, unreadable on purpose at 16px
    for x in range(4, 14, 2):
        img.rect(x, 11, 1, 2, BODY_DARK)
    img.dot(14, 12, ACCENT)
    return img


def machine_right() -> Image:
    img = _base()
    img.rect(2, 3, 8, 7, SCREEN)
    for x in range(2, 10):
        img.dot(x, 3, SCREEN_GLOW)
    # a party-ball sigil: the launcher's mark, not Nintendo's exact sprite
    cx, cy = 6, 6
    img.rect(cx - 2, cy - 2, 4, 1, ACCENT)
    img.rect(cx - 2, cy - 1, 4, 1, (250, 246, 232))
    img.rect(cx - 2, cy, 4, 1, (250, 246, 232))
    img.rect(cx - 2, cy + 1, 4, 1, ACCENT)
    img.dot(cx, cy - 1, SCREEN)
    # vent slats on the lower cabinet
    for y in (11, 13):
        img.rect(3, y, 9, 1, BODY_DARK)
    return img
