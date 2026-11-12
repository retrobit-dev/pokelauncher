#!/usr/bin/env python3
"""Renders the launcher inside a Huawei MatePad Mini bezel, both orientations.

Device reference (Huawei MatePad Mini, 2025):
  8.8" flexible OLED, 2560 x 1600 px (16:10), 343 ppi, ~92% screen to body,
  body 198.6 x 127.3 x 5.2 mm -> ~4.4 mm bezel all round, 32 MP punch hole
  camera inside the display (top corner in portrait).

The UI follows the real Compose code path:

  landscape (853 dp wide -> wide layout)
      JohtoWallpaper + scrim, TopBar, PlayerCard wide branch (button right),
      PartyGrid with GridCells.Fixed(6) centred vertically, wide StatusCard
  portrait (533 dp wide -> phone layout)
      TopBar, PlayerCard stacked (full width button), PartyGrid with the
      default 3 columns, StatusCard with the hint under the title

Everything is pure Python (no Pillow) so the script runs anywhere.

Output: docs/preview-tablet.png and docs/preview-tablet-portrait.png
"""
from __future__ import annotations

import math
import os
import struct
import sys
import zlib

# ---------------------------------------------------------------- palette
def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


PAPER = rgb("FBF3DC")
PAPER_DEEP = rgb("F3E4BF")
INK = rgb("3B2F1E")
INK_SOFT = rgb("6B5B44")
INK_FAINT = rgb("9A8768")
GOLD = rgb("E0B84C")
RED = rgb("C53A2D")
RED_DEEP = rgb("9A2A20")
CREAM = rgb("FFFBF0")
SCREEN_INK = rgb("2C2418")
SKY_TOP = rgb("9FD4D2")
SKY_BOTTOM = rgb("F4E7BE")
SUN = rgb("F6E3A8")
HILL_FAR = rgb("AFC79A")
HILL_MID = rgb("8FAF74")
HILL_NEAR = rgb("7E9C63")
GRASS = rgb("5F7F4C")
BODY_TOP = rgb("E8EAE4")
BODY_BOTTOM = rgb("C6CCC4")
BODY_EDGE = rgb("979F97")
BEZEL_DARK = rgb("15181A")

CARTRIDGES = [
    (rgb("E0B84C"), rgb("C79A2E")),
    (rgb("C9CFD6"), rgb("A5ADB7")),
    (rgb("8FB6D8"), rgb("6F95B8")),
    (rgb("D08070"), rgb("B06152")),
    (rgb("9DBB86"), rgb("7D9B68")),
    (rgb("B7A0D4"), rgb("977FB4")),
]

DP = 3          # the MatePad Mini is 343 ppi: 1 dp == 3 px


def dp(value: float) -> float:
    return value * DP


# ------------------------------------------------------------ tiny canvas
class Canvas:
    """RGB canvas with flat byte storage and small AA helpers."""

    def __init__(self, w: int, h: int, fill: tuple[int, int, int]) -> None:
        self.w, self.h = w, h
        self.buf = bytearray(bytes(fill) * (w * h))

    def blend(self, x: int, y: int, colour: tuple[int, int, int], alpha: float) -> None:
        if alpha <= 0.0:
            return
        if alpha > 1.0:
            alpha = 1.0
        i = (y * self.w + x) * 3
        buf = self.buf
        if alpha >= 0.999:
            buf[i] = colour[0]
            buf[i + 1] = colour[1]
            buf[i + 2] = colour[2]
            return
        inv = 1.0 - alpha
        buf[i] = int(colour[0] * alpha + buf[i] * inv)
        buf[i + 1] = int(colour[1] * alpha + buf[i + 1] * inv)
        buf[i + 2] = int(colour[2] * alpha + buf[i + 2] * inv)

    def rect(self, x: float, y: float, w: float, h: float,
             colour: tuple[int, int, int], radius: float = 0.0,
             alpha: float = 1.0, mask=None) -> None:
        if w <= 0 or h <= 0:
            return
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.w, int(math.ceil(x + w))), min(self.h, int(math.ceil(y + h)))
        if radius > 0 or mask is not None:
            r = min(radius, w / 2, h / 2) if radius else 0.0
            for yy in range(y0, y1):
                cy = yy + 0.5
                dy = 0.0
                if r:
                    if cy < y + r:
                        dy = (y + r) - cy
                    elif cy > y + h - r:
                        dy = cy - (y + h - r)
                for xx in range(x0, x1):
                    cx = xx + 0.5
                    if r and dy:
                        dx = 0.0
                        if cx < x + r:
                            dx = (x + r) - cx
                        elif cx > x + w - r:
                            dx = cx - (x + w - r)
                        if dx and dx * dx + dy * dy > r * r:
                            continue
                    if mask is not None and not mask(cx, cy):
                        continue
                    self.blend(xx, yy, colour, alpha)
            return
        for yy in range(y0, y1):
            row = (yy * self.w + x0) * 3
            self.buf[row:row + (x1 - x0) * 3] = bytes(colour) * (x1 - x0)

    def disc(self, cx: float, cy: float, r: float, colour: tuple[int, int, int],
             alpha: float = 1.0) -> None:
        self.ellipse(cx, cy, r, r, colour, alpha)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float,
                colour: tuple[int, int, int], alpha: float = 1.0) -> None:
        if rx <= 0 or ry <= 0:
            return
        for yy in range(max(0, int(cy - ry)), min(self.h, int(math.ceil(cy + ry)))):
            dy = (yy + 0.5 - cy) / ry
            if abs(dy) >= 1.0:
                continue
            span = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            x_from, x_to = max(0, int(cx - span)), min(self.w, int(math.ceil(cx + span)))
            if x_to <= x_from:
                continue
            if alpha >= 0.999:
                row = (yy * self.w + x_from) * 3
                self.buf[row:row + (x_to - x_from) * 3] = bytes(colour) * (x_to - x_from)
            else:
                for xx in range(x_from, x_to):
                    self.blend(xx, yy, colour, alpha)

    def gradient_rect(self, y0: float, y1: float, top: tuple[int, int, int],
                      bottom: tuple[int, int, int]) -> None:
        for yy in range(max(0, int(y0)), min(self.h, int(y1))):
            t = (yy - y0) / max(1.0, y1 - y0)
            colour = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            row = yy * self.w * 3
            self.buf[row:row + self.w * 3] = bytes(colour) * self.w

    def to_png(self, path: str) -> int:
        raw = bytearray()
        stride = self.w * 3
        for yy in range(self.h):
            raw.append(0)
            raw.extend(self.buf[yy * stride:(yy + 1) * stride])

        def chunk(tag: bytes, data: bytes) -> bytes:
            payload = tag + data
            return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b"")
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(png)
        return len(png)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def round_rect_contains(px: float, py: float, x: float, y: float,
                        w: float, h: float, r: float) -> bool:
    if px < x or py < y or px > x + w or py > y + h:
        return False
    cx = min(max(px, x + r), x + w - r)
    cy = min(max(py, y + r), y + h - r)
    return (px - cx) ** 2 + (py - cy) ** 2 <= r * r


# -------------------------------------------------------------- 5x7 font
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
    "F": ["11111", "10000", "11110", "10000", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "11111", "10001", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "01110", "00001", "00001", "10001", "01110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    " ": ["00000"] * 7,
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
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "?": ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
}


def ts(base: float) -> int:
    """Font "scale" is a pixel size: derive it from the dp grid so a preview at
    any density keeps the same visual proportion as the Compose layout."""
    return max(2, int(round(base * DP / 2)))


def text_width(value: str, scale: int, spacing: int = 1) -> int:
    return max(0, len(value) * (5 + spacing) * scale - spacing * scale)


def draw_text(cv: Canvas, x: float, y: float, value: str, colour,
              scale: int, spacing: int = 1, alpha: float = 1.0) -> int:
    if alpha < 1.0:
        scale = max(1, scale)
    cx = x
    for ch in value.upper():
        glyph = FONT.get(ch, FONT["?"])
        for row_index, row in enumerate(glyph):
            for col_index, bit in enumerate(row):
                if bit == "1":
                    cv.rect(cx + col_index * scale, y + row_index * scale,
                            scale, scale, colour, alpha=alpha)
        cx += (5 + spacing) * scale
    return int(cx)


def fit_scale(value: str, available: float, maximum: int = 5) -> int:
    for scale in range(maximum, 1, -1):
        if text_width(value, scale) <= available:
            return scale
    return 2


# ----------------------------------------------------------- Hg primitives
def panel(cv: Canvas, x: float, y: float, w: float, h: float, radius: float,
          fill=PAPER) -> None:
    """HgPanel: soft shadow, ink outline, paper face."""
    cv.rect(x + dp(1.3), y + dp(1.7), w, h, (150, 130, 100), radius, alpha=0.55)
    cv.rect(x, y, w, h, INK, radius)
    cv.rect(x + dp(0.7), y + dp(0.7), w - dp(1.4), h - dp(1.4), fill, radius - 1)


def inset_panel(cv: Canvas, x: float, y: float, w: float, h: float, radius: float) -> None:
    """HgInset: the recessed label strip under a cartridge."""
    cv.rect(x, y, w, h, INK_SOFT, radius)
    cv.rect(x + dp(0.5), y + dp(0.5), w - dp(1.0), h - dp(1.0), PAPER_DEEP, radius - 1)


def button(cv: Canvas, x: float, y: float, w: float, h: float, label: str,
           text_scale: int = 5) -> None:
    """HgButton: shadow, ink body, paper face, gold inner rule, centred label."""
    r = dp(10)
    cv.rect(x, y + dp(1), w, h, (120, 100, 70), r, alpha=0.35)
    cv.rect(x, y, w, h - dp(1), INK, r)
    cv.rect(x + dp(0.7), y + dp(0.7), w - dp(1.4), h - dp(2.7), PAPER_DEEP, r - 1)
    rule = dp(1)
    cv.rect(x + dp(1.7), y + dp(1.7), w - dp(3.4), rule, GOLD, alpha=0.95)
    cv.rect(x + dp(1.7), y + h - dp(4.2), w - dp(3.4), rule, GOLD, alpha=0.95)
    cv.rect(x + dp(1.7), y + dp(1.7), rule, h - dp(5.9), GOLD, alpha=0.95)
    cv.rect(x + w - dp(2.7), y + dp(1.7), rule, h - dp(5.9), GOLD, alpha=0.95)
    draw_text(cv, x + (w - text_width(label, text_scale)) / 2,
              y + (h - dp(1) - 7 * text_scale) / 2, label, INK, text_scale)


def pokeball(cv: Canvas, cx: float, cy: float, r: float) -> None:
    cv.disc(cx, cy, r, INK)
    cv.disc(cx, cy, r - dp(0.6), RED)
    inner = r - dp(0.6)
    for yy in range(int(cy), int(cy + inner) + 1):
        dy = (yy + 0.5 - cy) / inner
        if abs(dy) >= 1:
            continue
        span = inner * math.sqrt(max(0.0, 1 - dy * dy))
        cv.rect(cx - span, yy, span * 2, 1, CREAM)
    cv.rect(cx - r, cy - r * 0.13, r * 2, max(dp(0.8), r * 0.26), INK)
    cv.disc(cx, cy, r * 0.38, INK)
    cv.disc(cx, cy, r * 0.25, CREAM)


def cartridge_outline(x: float, y: float, w: float, h: float):
    """Returns spans(ly) for the silhouette used by cartridgePath() in Kotlin."""
    cut = w * 0.10
    notch = w * 0.075

    def spans(ly: float):
        if ly < 0 or ly > h:
            return None
        if ly < cut:
            inset = cut - ly
            return x + inset, x + w - inset
        if ly < h * 0.70:
            return x, x + w
        if ly < h * 0.78:
            t = (ly - h * 0.70) / (h * 0.08)
            inset = notch * t
            return x + inset, x + w - inset
        if ly < h * 0.92:
            return x + notch, x + w - notch
        t = (ly - h * 0.92) / (h * 0.08)
        inset = notch + (notch * 0.45 - notch) * t
        return x + inset, x + w - inset

    return spans


def cartridge(cv: Canvas, x: float, y: float, w: float, h: float, body, shade) -> None:
    """GBA cartridge: clipped top corners, shallow notch at 70%, ridge at the base."""
    spans = cartridge_outline(x, y, w, h)
    for yy in range(int(y), int(y + h) + 1):
        span = spans(yy + 0.5 - y)
        if span is None or span[1] - span[0] <= 0:
            continue
        x0, x1 = span
        colour = shade if (yy + 0.5 - y) > h * 0.74 else body
        cv.rect(x0, yy, x1 - x0, 1, colour)
        edge = min(dp(0.6), (x1 - x0) / 2)
        cv.rect(x0, yy, edge, 1, INK)
        cv.rect(x1 - edge, yy, edge, 1, INK)

    top = spans(1.0)
    bottom = spans(h - 1.0)
    if top:
        cv.rect(top[0], y, top[1] - top[0], dp(0.6), INK)
    if bottom:
        cv.rect(bottom[0], y + h - dp(0.6), bottom[1] - bottom[0], dp(0.6), INK)

    # glossy highlight band near the top and the grip lines at the base
    cv.rect(x + w * 0.16, y + h * 0.030, w * 0.68, h * 0.020, CREAM, alpha=0.38)
    for i in range(2):
        cv.rect(x + w * 0.42, y + h * 0.945 + i * dp(0.9), w * 0.16, dp(0.4), INK, alpha=0.40)


def empty_slot(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """EmptySlotCard(): 40% paper fill, faint ink hairline and a centred plus."""
    spans = cartridge_outline(x, y, w, h)

    def covered(px: float, py: float) -> bool:
        span = spans(py - y)
        return span is not None and span[0] <= px <= span[1]

    for yy in range(int(y), int(y + h) + 1):
        span = spans(yy + 0.5 - y)
        if span is None:
            continue
        cv.rect(span[0], yy, span[1] - span[0], 1, PAPER_DEEP, alpha=0.40)
        for xx in range(int(span[0]), int(span[1]) + 1):
            if not (covered(xx + 0.5 - dp(0.5), yy + 0.5) and covered(xx + 0.5 + dp(0.5), yy + 0.5)
                    and covered(xx + 0.5, yy + 0.5 - dp(0.5)) and covered(xx + 0.5, yy + 0.5 + dp(0.5))):
                cv.blend(xx, yy, INK_FAINT, 0.70)

    plus_cx, plus_cy = x + w / 2, y + h / 2
    arm, thick = dp(7), dp(1.6)
    cv.rect(plus_cx - thick / 2, plus_cy - arm, thick, arm * 2, INK_FAINT)
    cv.rect(plus_cx - arm, plus_cy - thick / 2, arm * 2, thick, INK_FAINT)


def app_icon(cv: Canvas, cx: float, cy: float, size: float, kind: int, tint) -> None:
    """Stand-in for the real app icon, drawn in the launcher's own style."""
    half = size / 2
    cv.rect(cx - half, cy - half, size, size, CREAM, size * 0.22)
    if kind == 0:      # camera
        cv.rect(cx - size * 0.34, cy - size * 0.20, size * 0.68, size * 0.46, SCREEN_INK, size * 0.10)
        cv.disc(cx, cy + size * 0.03, size * 0.15, tint)
        cv.disc(cx, cy + size * 0.03, size * 0.08, CREAM)
        cv.rect(cx - size * 0.10, cy - size * 0.30, size * 0.20, size * 0.10, SCREEN_INK, size * 0.03)
    elif kind == 1:    # music note
        cv.disc(cx - size * 0.10, cy + size * 0.22, size * 0.13, tint)
        cv.rect(cx + size * 0.01, cy - size * 0.30, size * 0.06, size * 0.52, tint)
        cv.rect(cx + size * 0.01, cy - size * 0.30, size * 0.24, size * 0.08, tint)
    elif kind == 2:    # compass: needle over a dial
        cv.disc(cx, cy, size * 0.29, CREAM)
        cv.disc(cx, cy, size * 0.29, tint, alpha=0.25)
        cv.rect(cx - size * 0.035, cy - size * 0.20, size * 0.07, size * 0.28, tint, size * 0.03)
        cv.rect(cx - size * 0.20, cy - size * 0.035, size * 0.28, size * 0.07, tint, size * 0.03)
        cv.disc(cx, cy, size * 0.05, CREAM)
    elif kind == 3:    # calculator
        cv.rect(cx - size * 0.26, cy - size * 0.30, size * 0.52, size * 0.60, tint, size * 0.08)
        cv.rect(cx - size * 0.19, cy - size * 0.24, size * 0.38, size * 0.16, CREAM, size * 0.04)
        for row in range(2):
            for col in range(3):
                cv.disc(cx - size * 0.14 + col * size * 0.14,
                        cy + size * 0.06 + row * size * 0.13, size * 0.035, CREAM)
    elif kind == 4:    # gallery
        cv.rect(cx - size * 0.28, cy - size * 0.24, size * 0.56, size * 0.48, tint, size * 0.08)
        cv.disc(cx + size * 0.10, cy - size * 0.08, size * 0.07, CREAM)
        for i in range(3):
            cv.rect(cx - size * 0.24 + i * size * 0.16, cy + size * 0.08,
                    size * 0.13, size * 0.12, CREAM, size * 0.03)
    else:              # maps: folded map with a pin
        cv.rect(cx - size * 0.28, cy - size * 0.22, size * 0.56, size * 0.44, tint, size * 0.06)
        cv.rect(cx - size * 0.06, cy - size * 0.22, size * 0.02, size * 0.44, CREAM)
        cv.disc(cx + size * 0.08, cy - size * 0.02, size * 0.07, CREAM)
        cv.rect(cx + size * 0.06, cy + size * 0.02, size * 0.04, size * 0.10, CREAM)


def gear(cv: Canvas, cx: float, cy: float, r: float) -> None:
    for i in range(8):
        angle = math.radians(i * 45)
        cv.disc(cx + math.cos(angle) * r * 0.80, cy + math.sin(angle) * r * 0.80, r * 0.20, INK)
    cv.disc(cx, cy, r * 0.66, INK)
    cv.disc(cx, cy, r * 0.34, PAPER)


# ------------------------------------------------------------------- device
class Device:
    """One MatePad Mini, drawn in the requested orientation."""

    BEZEL = 34
    CORNER = 62
    SCREEN_CORNER = 30

    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h            # display size in px
        self.wide = w >= dp(700)         # same rule as LauncherScreen.kt
        self.outer_w = w + 2 * self.BEZEL
        self.outer_h = h + 2 * self.BEZEL
        self.cv = Canvas(self.outer_w, self.outer_h, BODY_BOTTOM)

    # -- screen content ------------------------------------------------
    def wallpaper(self, cv: Canvas) -> None:
        cv.gradient_rect(0, self.h, SKY_TOP, SKY_BOTTOM)
        sun_x, sun_y = self.w * 0.80, self.h * 0.42
        cv.disc(sun_x, sun_y, self.w * 0.16, SUN, alpha=0.22)
        cv.disc(sun_x, sun_y, self.w * 0.09, SUN, alpha=0.45)
        cv.disc(sun_x, sun_y, self.w * 0.055, SUN)
        for cx, cy, w in ((0.16, 0.22, 0.22), (0.52, 0.15, 0.16),
                          (0.88, 0.30, 0.13), (0.34, 0.34, 0.10)):
            cv.ellipse(self.w * cx, self.h * cy, self.w * w * 0.5, self.w * w * 0.17, CREAM, alpha=0.75)
            cv.ellipse(self.w * cx - self.w * w * 0.20, self.h * cy + self.w * w * 0.03,
                       self.w * w * 0.28, self.w * w * 0.14, CREAM, alpha=0.75)
            cv.ellipse(self.w * cx + self.w * w * 0.22, self.h * cy + self.w * w * 0.02,
                       self.w * w * 0.26, self.w * w * 0.13, CREAM, alpha=0.75)
        for base, amp, length, colour, phase in (
            (0.74, 0.055, 1.15, HILL_FAR, 0.4),
            (0.82, 0.070, 0.85, HILL_MID, 2.1),
            (0.90, 0.050, 0.62, HILL_NEAR, 4.2),
        ):
            points = []
            for xx in range(0, self.w + 1, 8):
                angle = (xx / self.w) * 2 * math.pi * length + phase
                points.append((xx, self.h * base + math.sin(angle) * self.h * amp))
            for index in range(len(points) - 1):
                (xa, ya), (xb, yb) = points[index], points[index + 1]
                steps = max(1, int(xb - xa))
                for step in range(steps):
                    t = step / steps
                    yy = ya + (yb - ya) * t
                    cv.rect(xa + step, yy, 1, self.h - yy, colour)
            cv.rect(self.w - 8, points[-1][1], 8, self.h - points[-1][1], colour)
        cv.rect(0, self.h * 0.965, self.w, self.h * 0.035, GRASS)
        for i in range(160):
            gx = (i * 149.0) % self.w
            for gi in range(6 + (i % 3) * 3):
                h = dp(2) + (gi * dp(1.2)) % dp(3.4)
                cv.rect(gx + gi * dp(1), self.h * 0.975 - h, dp(0.8), h, GRASS, alpha=0.85)

    def scrim(self, cv: Canvas) -> None:
        """Paper scrim from HomeSurface: white at the top, paper at the bottom."""
        for yy in range(self.h):
            t = yy / self.h
            if t < 0.42:
                alpha = 0.28 * (1 - t / 0.42)
                colour = (255, 255, 255)
            elif t < 0.74:
                continue
            else:
                k = (t - 0.74) / 0.26
                alpha = 0.22 + (0.60 - 0.22) * k
                colour = PAPER
            cv.rect(0, yy, self.w, 1, colour, alpha=alpha)

    # -- composables ---------------------------------------------------
    def top_bar(self, cv: Canvas, margin: float, y: float) -> float:
        clock_w, clock_h = dp(118), dp(44)
        panel(cv, margin, y, clock_w, clock_h, dp(12))
        pokeball(cv, margin + dp(18), y + clock_h / 2, dp(9))
        draw_text(cv, margin + dp(34), y + clock_h / 2 - 7 * ts(4) / 2, "09:41", INK, ts(4))

        size = dp(46)
        bx = self.w - margin - size
        cv.rect(bx, y, size, size, INK, size / 2)
        cv.rect(bx + dp(0.7), y + dp(0.7), size - dp(1.4), size - dp(1.4), PAPER, size / 2 - 1)
        gear(cv, bx + size / 2, y + size / 2, dp(4.3))
        return clock_h

    def party_copy(self, cv: Canvas, x: float, y: float, height: float) -> None:
        micro, body = ts(2), ts(4)
        gap = dp(2)
        block = 7 * micro + gap + 7 * body + dp(3) + dp(3)
        top = y + (height - block) / 2
        draw_text(cv, x, top, "JOHTO REGION", RED_DEEP, micro)
        draw_text(cv, x, top + 7 * micro + gap, "PARTY KAMU", INK, body)
        ball_y = top + 7 * micro + gap + 7 * body + dp(3) + dp(1.5)
        for i in range(6):
            bx = x + dp(1.5) + i * dp(4)
            if i < 5:
                pokeball(cv, bx, ball_y, dp(1.5))
            else:
                cv.disc(bx, ball_y, dp(1.5), INK_FAINT, alpha=0.22)

    def player_card(self, cv: Canvas, x: float, y: float, width: float) -> float:
        diorama_w, diorama_h = dp(84), dp(50)
        if self.wide:
            # wide branch: one line, action button on the right
            height = diorama_h + dp(20)
            panel(cv, x, y, width, height, dp(14))
            dx, dy = x + dp(10), y + (height - diorama_h) / 2
            self.diorama(cv, dx, dy, diorama_w, diorama_h)
            self.party_copy(cv, dx + diorama_w + dp(12), dy, diorama_h)
            action_w, action_h = dp(230), dp(44)
            button(cv, x + width - dp(10) - action_w, dy + (diorama_h - action_h) / 2 + dp(1),
                   action_w, action_h, "APLIKASI", ts(5))
            return height

        # phone branch: copy row, then a full width action button
        height = dp(10) + diorama_h + dp(9) + dp(40) + dp(10)
        panel(cv, x, y, width, height, dp(14))
        dx, dy = x + dp(10), y + dp(10)
        self.diorama(cv, dx, dy, diorama_w, diorama_h)
        self.party_copy(cv, dx + diorama_w + dp(10), dy, diorama_h)
        button(cv, x + dp(10), y + height - dp(10) - dp(40),
               width - dp(20), dp(40), "APLIKASI", ts(4))
        return height

    def diorama(self, cv: Canvas, x: float, y: float, w: float, h: float) -> None:
        cv.rect(x, y, w, h, CREAM, dp(6))
        cv.rect(x + dp(0.7), y + dp(0.7), w - dp(1.4), h * 0.62, rgb("BFE3E0"), dp(5))
        cv.disc(x + w * 0.72, y + h * 0.30, h * 0.15, SUN)
        for xx in range(int(w) - 6):
            t = xx / w
            hill_y = y + h * (0.64 - 0.16 * math.sin(t * math.pi))
            cv.rect(x + dp(0.7) + xx, hill_y, 1, h - (hill_y - y) - dp(1), HILL_MID)
            front_y = y + h * (0.80 - 0.10 * math.cos(t * math.pi * 1.4))
            cv.rect(x + dp(0.7) + xx, front_y, 1, h - (front_y - y) - dp(1), HILL_NEAR)

    def party_grid(self, cv: Canvas, x: float, y: float, width: float,
                   top: float, bottom: float) -> None:
        names = ["KAMERA", "MUSIK", "KOMPAS", "KALKULATOR", "GALERI", "PETA"]
        cols = 6 if self.wide else 3
        gap = dp(12)
        grid_w = min(width, dp(1100)) if self.wide else width
        grid_x = x + (width - grid_w) / 2
        card_w = (grid_w - gap * (cols - 1)) / cols
        cart_h = card_w / 0.92
        label_h = dp(6) * 3
        card_hh = cart_h + dp(5) + label_h
        status_h = dp(19) * 3
        rows = (6 + cols - 1) // cols
        block_h = rows * card_hh + (rows - 1) * dp(14) + dp(22) + status_h

        if self.wide and bottom - y > block_h:
            y += (bottom - y - block_h) / 2

        for index in range(6):
            row, col = divmod(index, cols)
            cx = grid_x + col * (card_w + gap)
            cy = y + row * (card_hh + dp(14))
            strip_y = cy + cart_h + dp(5)

            if index >= 5:
                empty_slot(cv, cx, cy, card_w, cart_h)
                inset_panel(cv, cx, strip_y, card_w, label_h, dp(7))
                empty = "- KOSONG -"
                draw_text(cv, cx + (card_w - text_width(empty, ts(2))) / 2,
                          strip_y + (label_h - 7 * ts(2)) / 2, empty, INK_FAINT, ts(2))
                continue

            body, shade = CARTRIDGES[index]
            cartridge(cv, cx, cy, card_w, cart_h, body, shade)

            # screen inset with the app glyph
            sw = card_w * 0.78
            sx = cx + (card_w - sw) / 2
            sy = cy + dp(16)
            sh = sw / 1.15
            cv.rect(sx, sy, sw, sh, SCREEN_INK, dp(6))
            cv.rect(sx + dp(0.5), sy + dp(0.5), sw - dp(1), sh - dp(1), CREAM, dp(6), alpha=0.85)
            app_icon(cv, sx + sw / 2, sy + sh / 2, min(sw, sh) * 0.62, index, body)

            draw_text(cv, cx + dp(8), cy + dp(4), f"LV{3 + index}", INK, ts(2))
            pokeball(cv, cx + card_w - dp(12), cy + dp(10), dp(4.5))

            inset_panel(cv, cx, strip_y, card_w, label_h, dp(7))
            label = names[index]
            scale = fit_scale(label, card_w - dp(16), maximum=ts(3))
            draw_text(cv, cx + (card_w - text_width(label, scale)) / 2,
                      strip_y + (label_h - 7 * scale) / 2, label, INK, scale)

        # StatusCard: on wide screens the hint sits on the right edge
        status_y = y + rows * card_hh + (rows - 1) * dp(14) + dp(22) - card_hh
        status_y = y + rows * card_hh + (rows - 1) * dp(14) + dp(8)
        panel(cv, grid_x, status_y, grid_w, status_h, dp(14))
        pokeball(cv, grid_x + dp(26), status_y + status_h / 2, dp(11))
        title = "PARTY 5/6 TERISI"
        hint = "TAHAN KARTU UNTUK OPSI - BACK MENUTUP PANEL"
        if self.wide:
            draw_text(cv, grid_x + dp(46), status_y + (status_h - 7 * ts(4)) / 2,
                      title, INK, ts(4))
            draw_text(cv, grid_x + grid_w - dp(20) - text_width(hint, ts(2)),
                      status_y + (status_h - 7 * ts(2)) / 2, hint, INK_SOFT, ts(2))
        else:
            draw_text(cv, grid_x + dp(46), status_y + dp(8), title, INK, ts(4))
            draw_text(cv, grid_x + dp(46), status_y + dp(8) + 7 * ts(4) + dp(2),
                      hint, INK_SOFT, ts(2))

    def draw_screen(self) -> Canvas:
        cv = Canvas(self.w, self.h, SKY_TOP)
        self.wallpaper(cv)
        self.scrim(cv)

        margin = dp(16)
        y = dp(10)
        y += self.top_bar(cv, margin, y) + dp(10)
        y += self.player_card(cv, margin, y, self.w - margin * 2) + dp(10)
        self.party_grid(cv, margin, y, self.w - margin * 2, y, self.h - dp(10))

        # round the panel corners, like the real OLED cut
        corner = self.SCREEN_CORNER
        for cx, cy in ((0, 0), (self.w - corner, 0), (0, self.h - corner),
                       (self.w - corner, self.h - corner)):
            for yy in range(int(cy), int(cy) + corner):
                for xx in range(int(cx), int(cx) + corner):
                    if not round_rect_contains(xx + 0.5, yy + 0.5, 0, 0, self.w, self.h, corner):
                        cv.blend(xx, yy, BEZEL_DARK, 1.0)
        return cv

    # -- hardware ------------------------------------------------------
    def draw_body(self) -> None:
        cv = self.cv
        ow, oh = self.outer_w, self.outer_h
        # drop shadow
        cv.rect(dp(8), oh - dp(7), ow - dp(16), dp(6), (0, 0, 0), self.CORNER, alpha=0.28)
        # aluminium body with a soft vertical gradient, clipped to the corners
        for yy in range(oh):
            t = yy / oh
            colour = mix(BODY_TOP, BODY_BOTTOM, t)
            cv.rect(0, yy, ow, 1, colour,
                    mask=lambda px, py, yy=yy: round_rect_contains(px, py, 0, 0, ow, oh, self.CORNER))
        # thin edge line
        frame = dp(1)
        for yy in range(oh):
            for xx in range(0, ow):
                if not round_rect_contains(xx + 0.5, yy + 0.5, 0, 0, ow, oh, self.CORNER):
                    continue
                if not round_rect_contains(xx + 0.5, yy + 0.5, frame, frame,
                                           ow - 2 * frame, oh - 2 * frame,
                                           self.CORNER - frame):
                    cv.blend(xx, yy, BODY_EDGE, 0.9)
        # black glass ring around the panel
        cv.rect(self.BEZEL - dp(2.7), self.BEZEL - dp(2.7),
                self.w + dp(5.4), self.h + dp(5.4), BEZEL_DARK, self.SCREEN_CORNER + dp(2.7))

    def draw_hardware(self) -> None:
        """Only what is visible from the front: the punch hole camera.

        Side keys and speakers sit on the 5.2 mm back edge and are invisible
        head on, so drawing them would just add noise.
        """
        cv = self.cv
        if self.wide:
            cam_x, cam_y = self.BEZEL + dp(9), self.BEZEL + dp(44)
        else:
            cam_x, cam_y = self.BEZEL + dp(44), self.BEZEL + dp(9)
        cv.disc(cam_x, cam_y + dp(0.5), dp(4.6), (0, 0, 0), alpha=0.30)
        cv.disc(cam_x, cam_y, dp(3.9), rgb("0B0F11"))
        cv.disc(cam_x - dp(0.3), cam_y - dp(0.3), dp(2.4), rgb("1B2A33"))
        cv.disc(cam_x - dp(1.1), cam_y - dp(1.1), dp(0.8), rgb("6E8A96"), alpha=0.9)

    def render(self) -> Canvas:
        screen = self.draw_screen()
        self.draw_body()
        for yy in range(self.h):
            src = yy * self.w * 3
            dst = ((yy + self.BEZEL) * self.outer_w + self.BEZEL) * 3
            self.cv.buf[dst:dst + self.w * 3] = screen.buf[src:src + self.w * 3]
        self.draw_hardware()
        return self.cv


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orientation", choices=("landscape", "portrait"), default=None,
                       help="render a single orientation (default: both)")
    args = parser.parse_args(argv)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.orientation in (None, "landscape"):
        # 2560 x 1600 -> 853 dp wide, the wide layout.
        landscape = Device(2560, 1600)
        png = landscape.render().to_png(os.path.join(root, "docs", "preview-tablet.png"))
        print(f"docs/preview-tablet.png ({png // 1024} KB, {landscape.outer_w}x{landscape.outer_h})")

    if args.orientation in (None, "portrait"):
        # 1600 x 2560 -> 533 dp wide, the phone layout.
        portrait = Device(1600, 2560)
        png = portrait.render().to_png(os.path.join(root, "docs", "preview-tablet-portrait.png"))
        print(f"docs/preview-tablet-portrait.png ({png // 1024} KB, {portrait.outer_w}x{portrait.outer_h})")


if __name__ == "__main__":
    main(sys.argv[1:])
