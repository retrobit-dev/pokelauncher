#!/usr/bin/env python3
"""Renders the launcher inside a Huawei MatePad Mini bezel, landscape only.

Device reference (Huawei MatePad Mini, 2025):
  8.8" flexible OLED, 2560 x 1600 px (16:10), 343 ppi, ~92% screen to body,
  body 198.6 x 127.3 x 5.2 mm -> ~4.4 mm bezel all round, 32 MP punch hole
  camera inside the display.

The screen starts empty: a clean paper canvas, ready to be built up step by
step. Pass `--world` to fill it with the in-game mockup from
`tools/mock_ingame.py`; that path is kept so the world can come back without
rewriting the renderer.

The frame is a flat black bezel: no aluminium, no keys, no shadow.

The page around the device is a bright sky blue, so the black bezel reads as a
device floating on a light desk rather than a black rectangle on a black page.
The padding inside the PNG is what `/device` shows as that bright surround.

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


# Same colour as HgColors.Paper in Theme.kt, used when no render is available.
PAPER = rgb("FBF3DC")

# The bright surround for the published shot: a clear morning sky, close to the
# daylight palette of the tileset so the device sits on a light page.
PAGE = rgb("BFE3F2")
PAGE_EDGE = rgb("9FD2E6")
SHADOW = rgb("7FB6CC")

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


class Rgba:
    """Just enough of an image: width, height and flat RGBA bytes."""

    def __init__(self, w: int, h: int, buf: bytearray) -> None:
        self.w, self.h, self.buf = w, h, buf


def read_png(path: str) -> Rgba:
    """Decodes an 8-bit RGBA PNG, all five row filters.

    Written out rather than imported because the whole preview pipeline is
    standard library only; a PNG reader that only handles filter 0 would fail
    on any file a real encoder wrote.
    """
    blob = open(path, "rb").read()
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, width, height = 8, b"", 0, 0
    while pos + 8 <= len(blob):
        length = struct.unpack(">I", blob[pos:pos + 4])[0]
        tag = blob[pos + 4:pos + 8]
        body = blob[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, colour = struct.unpack(">IIBB", body[:10])
            if depth != 8 or colour != 6:
                raise ValueError("only 8-bit RGBA PNGs are supported")
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 4
    out = bytearray(stride * height)
    prev = bytearray(stride)
    o = 0
    for y in range(height):
        kind = raw[o]
        o += 1
        line = bytearray(raw[o:o + stride])
        o += stride
        if kind == 1:      # Sub
            for i in range(4, stride):
                line[i] = (line[i] + line[i - 4]) & 255
        elif kind == 2:    # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif kind == 3:    # Average
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif kind == 4:    # Paeth
            for i in range(stride):
                a = line[i - 4] if i >= 4 else 0
                b = prev[i]
                c = prev[i - 4] if i >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return Rgba(width, height, out)


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
    """One MatePad Mini in landscape, screen inside a black bezel.

    `PAD` is the bright margin around the device. It exists so the published
    PNG is a light page with a tablet on it, not a black slab that merges with
    a dark browser. A short soft shadow makes it sit on the page.
    """

    BEZEL = 34                       # black glass around the panel, in px
    CORNER = 62
    SCREEN_CORNER = dp(10.0)         # panel corner radius: dp, like the device
    PAD = 72

    def __init__(self, w: int, h: int, show_world: bool = False,
                 show_grid: bool = False) -> None:
        self.w, self.h = w, h            # display size in px
        self.show_world = show_world     # False: a blank screen to build on
        self.show_grid = show_grid       # True: draw the design grid on top
        self.body_w = w + 2 * self.BEZEL
        self.body_h = h + 2 * self.BEZEL
        self.outer_w = self.body_w + 2 * self.PAD
        self.outer_h = self.body_h + 2 * self.PAD
        self.cv = Canvas(self.outer_w, self.outer_h, PAGE, alpha=255)
        self.world: Canvas | None = None

    # -- screen content ------------------------------------------------
    def draw_grid(self, panel: Canvas) -> None:
        """The design grid, in the same cells as `ui/DesignGrid.kt`.

        40 dp at 3x is 120 px, so the panel holds 21.33 x 13.33 cells and the
        last column/row is partial - which is exactly what the tablet shows,
        and worth seeing instead of being surprised by later.
        """
        cell = 120                     # 40 dp * 3 px
        line = rgb("3F5D74")           # every 5th cell: the main measure
        soft = rgb("6E8AA0")           # 8 dp helper rhythm
        cool = rgb("5F7F97")           # ordinary cell edges
        x = 0
        col = 0
        while x <= self.w:
            every = col % 5 == 0
            panel.rect(x, 0, 3 if every else 2, self.h,
                       line if every else cool, alpha=0.9 if every else 0.5)
            x += cell
            col += 1
        y = 0
        row = 0
        while y <= self.h:
            every = row % 5 == 0
            panel.rect(0, y, self.w, 3 if every else 2,
                       line if every else cool, alpha=0.9 if every else 0.5)
            y += cell
            row += 1
        # 8 dp rhythm, faint
        step = 24
        x = 0
        while x <= self.w:
            panel.rect(x, 0, 1, self.h, soft, alpha=0.22)
            x += step
        y = 0
        while y <= self.h:
            panel.rect(0, y, self.w, 1, soft, alpha=0.22)
            y += step
        # camera danger box, 64 dp = 192 px
        panel.rect(0, 0, 192, 192, rgb("C53A2D"), alpha=0.16)
        panel.rect(0, 0, 192, 192, rgb("C53A2D"), alpha=0.85)
        panel.rect(2, 2, 188, 4, page := rgb("C53A2D"), alpha=0.85)
        panel.rect(2, 2, 4, 188, page, alpha=0.85)
        panel.rect(2, 186, 188, 4, page, alpha=0.85)
        panel.rect(186, 2, 4, 188, page, alpha=0.85)
        # Labels every five cells. Numbers are drawn with the 5x7 font, so a
        # cell can be named ("C3") instead of pointed at.
        def glyph(text: str, x0: int, y0: int, scale: int, colour) -> None:
            cx = x0
            for ch in text:
                rows_ = FONT.get(ch, FONT[" "])
                for gy, bits in enumerate(rows_):
                    for gx, bit in enumerate(bits):
                        if bit == "1":
                            panel.rect(cx + gx * scale, y0 + gy * scale,
                                       scale, scale, colour, alpha=0.95)
                cx += 6 * scale

        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for col in range(len(letters)):
            gx = col * cell + 8
            if gx + 18 > self.w:
                break
            glyph(letters[col], gx, 212, 3, rgb("3F5D74"))
        for row in range(40):
            gy = row * cell + 8
            if gy + 48 > self.h:
                break
            glyph(str(row + 1), 8, gy, 3, rgb("3F5D74"))

        # centre crosshair
        cx, cy, arm = self.w // 2, self.h // 2, 72
        panel.rect(cx - arm, cy, 2 * arm, 2, line, alpha=0.9)
        panel.rect(cx, cy - arm, 2, 2 * arm, line, alpha=0.9)

    def draw_blank(self) -> None:
        """A clean, empty screen: the paper colour and nothing else.

        This is the starting point for building the world back up one piece at
        a time. No HUD, no field, no title: an empty canvas makes each step
        visible on its own, instead of hiding a new element inside a busy shot.
        """
        panel = Canvas(self.w, self.h, PAPER, alpha=255)
        if self.show_grid:
            self.draw_grid(panel)
        self.round_panel(panel)
        self.world = panel

    def draw_world(self) -> None:
        """Copies the in-game mockup onto the panel, scaling to fit.

        `tools/mock_ingame.py` owns the picture. Loading it instead of copying
        the layout here means the preview cannot drift from the mockup the
        README publishes: one renderer, one truth.

        The picture is fitted, not stretched: a 16:10 render fills the panel
        exactly, and anything else would be letterboxed on the page colour
        rather than distorted. The camera punches through afterwards, so the
        parts of the HUD the app itself keeps clear of the cutout are hidden
        here too - the render tells the truth about the device.
        """
        here = os.path.dirname(os.path.abspath(__file__))
        source = os.path.join(here, "..", "docs", "editor", "ingame.png")
        image = None
        if os.path.exists(source):
            try:
                image = read_png(source)
            except (OSError, ValueError, zlib.error):
                image = None
        if image is None or image.w == 0 or image.h == 0:
            self.world = self.draw_screen()
            return

        panel = Canvas(self.w, self.h, PAGE_EDGE, alpha=255)
        scale = min(self.w / image.w, self.h / image.h)
        out_w, out_h = max(1, int(image.w * scale)), max(1, int(image.h * scale))
        off_x, off_y = (self.w - out_w) // 2, (self.h - out_h) // 2
        for yy in range(out_h):
            sy = min(image.h - 1, yy * image.h // out_h)
            row = sy * image.w
            dst_y = (off_y + yy) * self.w
            for xx in range(out_w):
                sx = min(image.w - 1, xx * image.w // out_w)
                i = (row + sx) * 4
                o = (dst_y + off_x + xx) * 4
                panel.buf[o] = image.buf[i]
                panel.buf[o + 1] = image.buf[i + 1]
                panel.buf[o + 2] = image.buf[i + 2]
        self.round_panel(panel)
        self.world = panel

    def round_panel(self, cv: Canvas) -> None:
        """Rounds the OLED corners, like the real panel cut."""
        corner = int(self.SCREEN_CORNER)
        for cx, cy in ((0, 0), (self.w - corner, 0), (0, self.h - corner),
                       (self.w - corner, self.h - corner)):
            for yy in range(int(cy), int(cy) + corner):
                for xx in range(int(cx), int(cx) + corner):
                    if not round_rect_contains(xx + 0.5, yy + 0.5, 0, 0, self.w, self.h, corner):
                        cv.blend(xx, yy, BEZEL_DARK, 1.0)

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
        corner = int(self.SCREEN_CORNER)
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
        ow, oh = self.body_w, self.body_h
        ox, oy = self.PAD, self.PAD

        # soft drop shadow: three passes, widest and faintest last, so the
        # tablet lifts off the page without a blur filter we do not have
        for spread, alpha in ((dp(16), 0.10), (dp(9), 0.12), (dp(4), 0.16)):
            cv.rect(ox - spread + dp(2), oy - spread + dp(6),
                    ow + 2 * spread, oh + 2 * spread, SHADOW,
                    self.CORNER + spread, alpha=alpha)

        # the frame is a single flat colour, clipped to the body corner radius
        for yy in range(oh):
            cv.rect(ox, oy + yy, ow, 1, BEZEL_BLACK,
                    mask=lambda px, py, yy=yy: round_rect_contains(
                        px, py, ox, oy, ow, oh, self.CORNER))

        # black glass around the lit panel, with a hairline so the edge of the
        # screen reads as an edge instead of a colour change
        cv.rect(ox + self.BEZEL - dp(1.6), oy + self.BEZEL - dp(1.6),
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
        cam_x = self.PAD + self.BEZEL + dp(CAMERA_INSET_DP) + radius
        cam_y = self.PAD + self.BEZEL + dp(CAMERA_INSET_DP) + radius

        # dark rim, then the lens barrel, then the glass reflection
        ring = radius + dp(0.6)
        cv.disc(cam_x, cam_y, ring, rgb("070A0C"), alpha=0.9)
        cv.disc(cam_x, cam_y, radius, rgb("04060A"))
        cv.disc(cam_x - dp(0.4), cam_y - dp(0.4), radius * 0.66, rgb("141F27"))
        cv.disc(cam_x - dp(2.2), cam_y - dp(2.2), radius * 0.24, rgb("6F8A96"), alpha=0.9)

    def render(self) -> Canvas:
        # screen first, then the frame is painted around it. The bezel has to go
        # on top because the page is already laid down: drawing the screen after
        # the body is what used to leave the panel showing the page colour.
        self.world = None
        # `--world` restores the full in-game mockup. The default is the empty
        # canvas: the screen is being rebuilt step by step, and the renderer
        # keeps the machinery for the moment the world comes back.
        if self.show_world:
            self.draw_world()
        else:
            self.draw_blank()
        self.draw_body()
        if self.world is not None:
            for yy in range(self.h):
                src = yy * self.w * 4
                dst = ((yy + self.PAD + self.BEZEL) * self.outer_w + self.PAD + self.BEZEL) * 4
                self.cv.buf[dst:dst + self.w * 4] = self.world.buf[src:src + self.w * 4]
        self.draw_hardware()
        return self.cv


def main(argv: list[str] | None = None) -> None:
    """Renders the landscape preview: an empty screen unless --world is passed."""
    argv = list(argv or [])
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 2560 x 1600: the MatePad Mini panel in landscape.
    device = Device(2560, 1600, show_world="--world" in argv,
                    show_grid="--grid" in argv)
    png = device.render().to_png(os.path.join(root, "docs", "preview-tablet.png"))
    print(f"docs/preview-tablet.png ({png // 1024} KB, {device.outer_w}x{device.outer_h})")


if __name__ == "__main__":
    main(sys.argv[1:])
