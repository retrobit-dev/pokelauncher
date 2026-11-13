#!/usr/bin/env python3
"""Renders the launcher inside a Huawei MatePad Mini bezel, landscape only.

Device reference (Huawei MatePad Mini, 2025):
  8.8" flexible OLED, 2560 x 1600 px (16:10), 343 ppi, ~92% screen to body,
  body 198.6 x 127.3 x 5.2 mm -> ~4.4 mm bezel all round, 32 MP punch hole
  camera inside the display.

The screen itself is empty: a clean home screen filled with the launcher's
paper colour, no clock, cards, cartridges or wallpaper - exactly what
LauncherScreen's HomeSurface draws now. The frame is a flat black bezel: no
aluminium, no keys, no shadow, no labels.

Everything is pure Python (no Pillow) so the script runs anywhere.

Output: docs/preview-tablet.png
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


# Same colour as HgColors.Paper in Theme.kt: the clean home screen fill.
PAPER = rgb("FBF3DC")

# Punch hole: 32 MP selfie camera. In portrait the hole sits in the top right
# corner of the 1600 x 2560 panel; turning the tablet the usual way for
# landscape (counter clockwise, keys on top) brings that corner to the top
# LEFT of the screen, which is where hands-on photos of the device show it.
# Measured off orthographic product photography: the hole is ~5.4% of the
# 1600 px short side, i.e. ~86 px / ~28 dp across, with a rim gap of ~12 dp to
# the two nearest panel edges.
CAMERA_INSET_DP = 12.0    # rim gap between the hole edge and the panel edge
CAMERA_RADIUS_DP = 14.0   # 28 dp diameter, matching the 86 px hole on device

BEZEL_BLACK = rgb("101112")   # flat black surround
BEZEL_RIM = rgb("2A2C2E")     # hairline where the glass meets the panel
BEZEL_DARK = rgb("15181A")

DP = 3          # the MatePad Mini is 343 ppi: 1 dp == 3 px


def dp(value: float) -> float:
    return value * DP


# ------------------------------------------------------------ tiny canvas
class Canvas:
    """RGBA canvas with flat storage and small anti aliasing helpers.

    The alpha channel matters for the published shot: the body corners are
    transparent, so the rounded black bezel is visible against any page
    background instead of merging into a black rectangle.
    """

    def __init__(self, w: int, h: int, fill: tuple[int, int, int],
                 alpha: int = 0) -> None:
        self.w, self.h = w, h
        self.buf = bytearray(bytes((*fill, alpha)) * (w * h))

    def blend(self, x: int, y: int, colour: tuple[int, int, int], alpha: float) -> None:
        """Source-over blend. Painting also makes the pixel opaque, so the
        frame covers the transparent background exactly where it is drawn."""
        if alpha <= 0.0:
            return
        if alpha > 1.0:
            alpha = 1.0
        i = (y * self.w + x) * 4
        buf = self.buf
        dest_alpha = buf[i + 3] / 255.0
        out_alpha = alpha + dest_alpha * (1.0 - alpha)
        if out_alpha <= 0.0:
            return
        if alpha >= 0.999:
            buf[i] = colour[0]
            buf[i + 1] = colour[1]
            buf[i + 2] = colour[2]
            buf[i + 3] = 255
            return
        inv = 1.0 - alpha
        for channel in range(3):
            buf[i + channel] = int(
                (colour[channel] * alpha + buf[i + channel] * dest_alpha * inv) / out_alpha)
        buf[i + 3] = int(out_alpha * 255)

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
            row = (yy * self.w + x0) * 4
            self.buf[row:row + (x1 - x0) * 4] = bytes((*colour, 255)) * (x1 - x0)

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
                row = (yy * self.w + x_from) * 4
                self.buf[row:row + (x_to - x_from) * 4] = bytes((*colour, 255)) * (x_to - x_from)
            else:
                for xx in range(x_from, x_to):
                    self.blend(xx, yy, colour, alpha)

    def gradient_rect(self, y0: float, y1: float, top: tuple[int, int, int],
                      bottom: tuple[int, int, int]) -> None:
        for yy in range(max(0, int(y0)), min(self.h, int(y1))):
            t = (yy - y0) / max(1.0, y1 - y0)
            colour = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            row = yy * self.w * 4
            self.buf[row:row + self.w * 4] = bytes((*colour, 255)) * self.w

    def to_png(self, path: str) -> int:
        raw = bytearray()
        stride = self.w * 4
        for yy in range(self.h):
            raw.append(0)
            raw.extend(self.buf[yy * stride:(yy + 1) * stride])

        def chunk(tag: bytes, data: bytes) -> bytes:
            payload = tag + data
            return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
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


# ------------------------------------------------------------------- device
class Device:
    """One MatePad Mini in landscape, screen inside a black bezel."""

    BEZEL = 34
    CORNER = 62
    SCREEN_CORNER = 30

    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h            # display size in px
        self.outer_w = w + 2 * self.BEZEL
        self.outer_h = h + 2 * self.BEZEL
        self.cv = Canvas(self.outer_w, self.outer_h, BEZEL_BLACK, alpha=0)

    # -- screen content ------------------------------------------------
    def draw_screen(self) -> Canvas:
        """Clean home screen: the launcher's paper colour and nothing else.

        Mirrors HomeSurface() in LauncherScreen.kt, which now paints a single
        flat fill - no wallpaper, clock, party cards or status strip.

        The fill must be opaque: Canvas defaults to alpha 0 so the bezel
        corners stay transparent, and a screen that nothing else paints over
        would otherwise be copied in as a fully transparent rectangle.
        """
        cv = Canvas(self.w, self.h, PAPER, alpha=255)

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
        """Uniform black bezel around the panel, nothing else.

        No aluminium back, no keys, no drop shadow: the preview is the screen
        inside the frame, so the frame stays a flat black surround with the
        same rounded corners as the tablet.
        """
        cv = self.cv
        ow, oh = self.outer_w, self.outer_h

        # the frame is a single flat colour, clipped to the body corner radius
        for yy in range(oh):
            cv.rect(0, yy, ow, 1, BEZEL_BLACK,
                    mask=lambda px, py, yy=yy: round_rect_contains(
                        px, py, 0, 0, ow, oh, self.CORNER))

        # black glass around the lit panel, with a hairline so the edge of the
        # screen reads as an edge instead of a colour change
        cv.rect(self.BEZEL - dp(1.6), self.BEZEL - dp(1.6),
                self.w + dp(3.2), self.h + dp(3.2), BEZEL_RIM,
                self.SCREEN_CORNER + dp(1.6), alpha=0.55)

    def draw_hardware(self) -> None:
        """Only what is visible from the front: the punch hole camera.

        The camera sits in the top right corner of the portrait panel. The
        tablet is normally turned counter clockwise to landscape (volume keys
        on top), which carries that corner over to the top LEFT of the screen,
        exactly where hands-on photos of the MatePad Mini show the hole.
        """
        cv = self.cv
        radius = dp(CAMERA_RADIUS_DP)
        cam_x = self.BEZEL + dp(CAMERA_INSET_DP) + radius
        cam_y = self.BEZEL + dp(CAMERA_INSET_DP) + radius

        # dark rim, then the lens barrel, then the glass reflection
        ring = radius + dp(0.6)
        cv.disc(cam_x, cam_y, ring, rgb("070A0C"), alpha=0.9)
        cv.disc(cam_x, cam_y, radius, rgb("04060A"))
        cv.disc(cam_x - dp(0.4), cam_y - dp(0.4), radius * 0.66, rgb("141F27"))
        cv.disc(cam_x - dp(2.2), cam_y - dp(2.2), radius * 0.24, rgb("6F8A96"), alpha=0.9)

    def render(self) -> Canvas:
        # body first (opaque bezel, transparent outside the rounded corners),
        # then the screen is copied in, then the camera sits on top of the UI
        self.draw_body()
        screen = self.draw_screen()
        for yy in range(self.h):
            src = yy * self.w * 4
            dst = ((yy + self.BEZEL) * self.outer_w + self.BEZEL) * 4
            self.cv.buf[dst:dst + self.w * 4] = screen.buf[src:src + self.w * 4]
        self.draw_hardware()
        return self.cv


def main(argv: list[str] | None = None) -> None:
    """Renders the single landscape preview. No arguments, one output."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 2560 x 1600: the MatePad Mini panel in landscape.
    device = Device(2560, 1600)
    png = device.render().to_png(os.path.join(root, "docs", "preview-tablet.png"))
    print(f"docs/preview-tablet.png ({png // 1024} KB, {device.outer_w}x{device.outer_h})")


if __name__ == "__main__":
    main(sys.argv[1:])
