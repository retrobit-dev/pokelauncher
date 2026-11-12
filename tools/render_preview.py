#!/usr/bin/env python3
"""Renders a preview of the launcher home screen from the real colour palette.

This is a design proof: it uses the exact colours defined in
ui/theme/Theme.kt (HgColors) and reproduces the layout described by
LauncherScreen.kt (top bar -> player card -> 2x3 party grid -> status card).
Output: docs/preview-home.png
"""
from __future__ import annotations

import os
import struct
import zlib

SCALE = 2
W, H = 412 * SCALE, 892 * SCALE


def hexrgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


PAPER = hexrgb("FBF3DC")
PAPER_DEEP = hexrgb("F3E4BF")
PAPER_SHADE = hexrgb("E9D7AE")
INK = hexrgb("3B2F1E")
INK_SOFT = hexrgb("6B5B44")
INK_FAINT = hexrgb("9A8768")
GOLD = hexrgb("E0B84C")
GOLD_DEEP = hexrgb("C79A2E")
RED = hexrgb("C53A2D")
RED_DEEP = hexrgb("9A2A20")
CREAM = hexrgb("FFFBF0")
SCREEN_INK = hexrgb("2C2418")

SKY_TOP = hexrgb("9FD4D2")
SKY_BOTTOM = hexrgb("F4E7BE")
SUN = hexrgb("F6E3A8")
HILL_FAR = hexrgb("AFC79A")
HILL_MID = hexrgb("8FAF74")
HILL_NEAR = hexrgb("7E9C63")
GRASS = hexrgb("5F7F4C")

CARTRIDGES = [
    (hexrgb("E0B84C"), hexrgb("C79A2E")),
    (hexrgb("C9CFD6"), hexrgb("A5ADB7")),
    (hexrgb("8FB6D8"), hexrgb("6F95B8")),
    (hexrgb("D08070"), hexrgb("B06152")),
    (hexrgb("9DBB86"), hexrgb("7D9B68")),
    (hexrgb("B7A0D4"), hexrgb("977FB4")),
]

# A 5x7 bitmap font for the few labels a mockup needs. Keeps the preview
# dependency free while still showing real text.
FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "11110", "10001", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
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
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "01110", "00001", "00001", "10001", "01110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
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

pixels = bytearray(W * H * 3)
for y in range(H):
    row = y * W * 3
    for x in range(W):
        pixels[row + x * 3: row + x * 3 + 3] = bytes(INK)


def put(x: int, y: int, colour: tuple[int, int, int]) -> None:
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        pixels[i:i + 3] = bytes(colour)


def rect(x: int, y: int, w: int, h: int, colour, radius: int = 0) -> None:
    x, y, w, h = int(x), int(y), int(w), int(h)
    for yy in range(max(0, y), min(H, y + h)):
        for xx in range(max(0, x), min(W, x + w)):
            if radius:
                dx = min(xx - x, x + w - 1 - xx)
                dy = min(yy - y, y + h - 1 - yy)
                if dx < radius and dy < radius:
                    if (radius - dx) ** 2 + (radius - dy) ** 2 > radius ** 2:
                        continue
            i = (yy * W + xx) * 3
            pixels[i:i + 3] = bytes(colour)


def ellipse(cx: float, cy: float, rx: float, ry: float, colour) -> None:
    for yy in range(int(cy - ry), int(cy + ry) + 1):
        for xx in range(int(cx - rx), int(cx + rx) + 1):
            if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0:
                put(xx, yy, colour)


def circle(cx: float, cy: float, r: float, colour) -> None:
    ellipse(cx, cy, r, r, colour)


def text(x: int, y: int, value: str, colour, scale: int = 2, spacing: int = 1) -> int:
    cx = x
    for ch in value.upper():
        glyph = FONT.get(ch, FONT["?"])
        for row_index, row in enumerate(glyph):
            for col_index, bit in enumerate(row):
                if bit == "1":
                    rect(cx + col_index * scale, y + row_index * scale, scale, scale, colour)
        cx += (len(glyph[0]) + spacing) * scale
    return cx


def panel(x: int, y: int, w: int, h: int, radius: int = 14 * SCALE, fill=PAPER) -> None:
    """Dark outline + paper fill, matching HgPanel's new default (no gold flood)."""
    rect(x + 3 * SCALE, y + 3 * SCALE, w, h, (150, 130, 100), radius)  # soft shadow
    rect(x, y, w, h, INK, radius)
    rect(x + 2 * SCALE, y + 2 * SCALE, w - 4 * SCALE, h - 4 * SCALE, fill, radius)


def pokeball(cx: int, cy: int, r: int) -> None:
    circle(cx, cy, r, INK)
    circle(cx, cy, r - 1.2 * SCALE, RED)
    # bottom half cream
    for yy in range(cy, cy + r):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= (r - 1.2 * SCALE) ** 2:
                put(xx, yy, CREAM)
    rect(cx - r, cy - SCALE, r * 2, 2 * SCALE, INK)
    circle(cx, cy, r * 0.36, INK)
    circle(cx, cy, r * 0.24, CREAM)


def cartridge(x: int, y: int, w: int, h: int, body, shade) -> None:
    cut = w * 0.10
    notch = w * 0.14
    for yy in range(h):
        for xx in range(w):
            in_body = True
            if yy < cut and (xx < cut - yy or xx > w - (cut - yy)):
                in_body = False
            lower = yy > h * 0.60
            if lower:
                # taper towards the notch
                inset_left = notch + (cut * 0.7 - notch) * ((yy - h * 0.6) / (h * 0.4))
                if xx < inset_left or xx > w - inset_left:
                    in_body = False
            if in_body:
                colour = shade if yy > h * 0.74 else body
                put(x + xx, y + yy, colour)
    # outline pass
    for yy in range(h):
        for xx in range(w):
            if 0 <= x + xx < W and 0 <= y + yy < H:
                inside = (x + xx, y + yy)
    # simple outline: redraw border pixels darker
    rect(x + int(cut), y, int(w - cut * 2), SCALE, INK)
    # screen inset
    sw = int(w * 0.78)
    sx = x + (w - sw) // 2
    sy = y + 16 * SCALE
    sh = int(sw * 0.87)
    rect(sx, sy, sw, sh, INK, 6 * SCALE)
    rect(sx + 2 * SCALE, sy + 2 * SCALE, sw - 4 * SCALE, sh - 4 * SCALE, SCREEN_INK, 5 * SCALE)


def main() -> None:
    # Sky gradient
    for y in range(H):
        t = min(1.0, y / (H * 0.82))
        colour = tuple(
            int(SKY_TOP[i] + (SKY_BOTTOM[i] - SKY_TOP[i]) * t) for i in range(3)
        )
        rect(0, y, W, 1, colour)

    # Sun + clouds
    circle(int(W * 0.78), int(H * 0.19), int(W * 0.085), SUN)
    for cx, cy, w in ((0.14, 0.13, 0.20), (0.60, 0.09, 0.16), (0.42, 0.24, 0.12)):
        ellipse(int(W * cx), int(H * cy), w * W * 0.5, w * W * 0.22, CREAM)

    # Hills
    import math

    for base, amp, colour, phase in (
        (0.74, 0.10, HILL_FAR, 0.4),
        (0.80, 0.12, HILL_MID, 2.1),
        (0.87, 0.09, HILL_NEAR, 4.2),
    ):
        for x in range(W):
            angle = (x / W) * 2 * math.pi + phase
            y = int(H * base + math.sin(angle) * H * amp)
            rect(x, y, 1, H - y, colour)
    rect(0, int(H * 0.93), W, H - int(H * 0.93), GRASS)

    margin = 16 * SCALE
    y = 16 * SCALE

    # ---- top bar: clock badge + settings button
    clock_w, clock_h = 118 * SCALE, 44 * SCALE
    panel(margin, y, clock_w, clock_h, radius=12 * SCALE)
    pokeball(margin + 18 * SCALE, y + clock_h // 2, 9 * SCALE)
    text(margin + 34 * SCALE, y + clock_h // 2 - 7 * SCALE, "09:41", INK, scale=2 * SCALE)

    gear_size = 46 * SCALE
    gx = W - margin - gear_size
    rect(gx, y, gear_size, gear_size, INK, gear_size // 2)
    rect(gx + 2 * SCALE, y + 2 * SCALE, gear_size - 4 * SCALE, gear_size - 4 * SCALE, PAPER, gear_size // 2)
    circle(gx + gear_size // 2, y + gear_size // 2, 9 * SCALE, INK)
    circle(gx + gear_size // 2, y + gear_size // 2, 5 * SCALE, PAPER)
    for i in range(8):
        a = math.radians(i * 45)
        px = gx + gear_size // 2 + math.cos(a) * 12 * SCALE
        py = y + gear_size // 2 + math.sin(a) * 12 * SCALE
        circle(px, py, 2.4 * SCALE, INK)

    # ---- player card: info row, then a full width action button
    y += clock_h + 10 * SCALE
    card_h = 132 * SCALE
    panel(margin, y, W - margin * 2, card_h)
    diorama_w, diorama_h = 84 * SCALE, 50 * SCALE
    dx, dy = margin + 10 * SCALE, y + 10 * SCALE
    rect(dx, dy, diorama_w, diorama_h, CREAM, 6 * SCALE)
    rect(dx + SCALE, dy + SCALE, diorama_w - 2 * SCALE, int(diorama_h * 0.62), hexrgb("BFE3E0"), 5 * SCALE)
    circle(dx + diorama_w * 0.72, dy + diorama_h * 0.30, diorama_h * 0.16, SUN)
    for xx in range(diorama_w):
        t = xx / diorama_w
        hill_y = dy + int(diorama_h * (0.66 - 0.18 * math.sin(t * math.pi)))
        rect(dx + xx, hill_y, 1, diorama_h - (hill_y - dy) - SCALE, HILL_MID)
        front_y = dy + int(diorama_h * (0.82 - 0.12 * math.cos(t * math.pi * 1.4)))
        rect(dx + xx, front_y, 1, diorama_h - (front_y - dy) - SCALE, HILL_NEAR)

    text(dx + diorama_w + 10 * SCALE, y + 14 * SCALE, "JOHTO REGION", RED_DEEP, scale=SCALE)
    text(dx + diorama_w + 10 * SCALE, y + 26 * SCALE, "PARTY KAMU", INK, scale=2 * SCALE)
    for i in range(6):
        bx = dx + diorama_w + 10 * SCALE + i * 14 * SCALE
        by = y + 52 * SCALE
        if i < 4:
            pokeball(bx, by, 5 * SCALE)
        else:
            circle(bx, by, 5 * SCALE, INK_FAINT)

    btn_w, btn_h = W - margin * 2 - 20 * SCALE, 40 * SCALE
    bx, by = margin + 10 * SCALE, y + card_h - btn_h - 10 * SCALE
    panel(bx, by, btn_w, btn_h, radius=10 * SCALE, fill=PAPER_DEEP)
    label = "APLIKASI"
    label_w = len(label) * 6 * SCALE * 2
    text(bx + (btn_w - label_w) // 2, by + btn_h // 2 - 7 * SCALE, label, INK, scale=2 * SCALE)

    # ---- party grid (3 columns)
    y += card_h + 12 * SCALE
    gap = 12 * SCALE
    card_w = (W - margin * 2 - gap * 2) // 3
    card_hh = int(card_w / 0.92) + 26 * SCALE
    names = ["KAMERA", "MUSIK", "KOMPAS", "KALKULATOR", "", ""]
    for index in range(6):
        row, col = divmod(index, 3)
        cx = margin + col * (card_w + gap)
        cy = y + row * (card_hh + 26 * SCALE)
        if index >= 4:
            # empty slot: dashed-ish outline
            rect(cx, cy, card_w, int(card_w / 0.92), INK_FAINT, 10 * SCALE)
            rect(cx + SCALE, cy + SCALE, card_w - 2 * SCALE, int(card_w / 0.92) - 2 * SCALE, PAPER, 10 * SCALE)
            plus_cx = cx + card_w // 2
            plus_cy = cy + int(card_w / 0.92) // 2
            rect(plus_cx - 2 * SCALE, plus_cy - 10 * SCALE, 4 * SCALE, 20 * SCALE, INK_FAINT)
            rect(plus_cx - 10 * SCALE, plus_cy - 2 * SCALE, 20 * SCALE, 4 * SCALE, INK_FAINT)
            continue
        body, shade = CARTRIDGES[index]
        cart_h = int(card_w / 0.92)
        cartridge(cx, cy, card_w, cart_h, body, shade)
        # icon glyph inside the screen
        sx = cx + card_w // 2
        sy = cy + 16 * SCALE + int(card_w * 0.78 * 0.43)
        if index == 0:
            rect(sx - 10 * SCALE, sy - 7 * SCALE, 20 * SCALE, 14 * SCALE, PAPER, 3 * SCALE)
            circle(sx, sy, 4 * SCALE, body)
        elif index == 1:
            circle(sx, sy, 6 * SCALE, PAPER)
            circle(sx - 4 * SCALE, sy - 4 * SCALE, 2 * SCALE, body)
        elif index == 2:
            for i in range(3):
                rect(sx - 9 * SCALE, sy - 6 * SCALE + i * 6 * SCALE, 18 * SCALE - i * 3 * SCALE, 3 * SCALE, PAPER)
        else:
            rect(sx - 8 * SCALE, sy - 8 * SCALE, 16 * SCALE, 16 * SCALE, PAPER, 3 * SCALE)
        # level + ball row
        text(cx + 8 * SCALE, cy + 4 * SCALE, "LV3", INK, scale=SCALE)
        pokeball(cx + card_w - 14 * SCALE, cy + 9 * SCALE, 5 * SCALE)
        # label inset
        label_y = cy + cart_h + 4 * SCALE
        rect(cx, label_y, card_w, 22 * SCALE, PAPER_DEEP, 7 * SCALE)
        text(cx + 9 * SCALE, label_y + 6 * SCALE, names[index], INK, scale=SCALE)

    # ---- status card
    y = H - 78 * SCALE
    panel(margin, y, W - margin * 2, 58 * SCALE)
    pokeball(margin + 26 * SCALE, y + 29 * SCALE, 11 * SCALE)
    text(margin + 46 * SCALE, y + 16 * SCALE, "PARTY 4/6 TERISI", INK, scale=2 * SCALE)
    text(margin + 46 * SCALE, y + 36 * SCALE, "TAHAN KARTU UNTUK OPSI", INK_SOFT, scale=SCALE)

    # ---- encode PNG
    raw = bytearray()
    for yy in range(H):
        raw.append(0)
        raw.extend(pixels[yy * W * 3:(yy + 1) * W * 3])

    def chunk(tag: bytes, data: bytes) -> bytes:
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    out = os.path.join(ROOT, "docs", "preview-home.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(png)
    print(f"wrote {out} ({len(png) // 1024} KB)")


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    main()
