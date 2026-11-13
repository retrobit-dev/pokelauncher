"""Tiny pixel-art primitives and a PNG writer, shared by every tile.

Why not Pillow: the repo already renders its preview with a hand written PNG
encoder (tools/render_tablet.py) so the tooling runs anywhere without extra
installs. The tileset keeps the same rule.

Everything works on an RGBA bytearray so a tile can be blitted with or without
transparency (grass is opaque, a flower is not).
"""
from __future__ import annotations

import struct
import zlib

RGB = tuple[int, int, int]


class Image:
    """An RGBA pixel buffer with the few operations tile art needs."""

    __slots__ = ("w", "h", "buf")

    def __init__(self, w: int, h: int, fill: RGB | None = None) -> None:
        self.w, self.h = w, h
        if fill is None:
            self.buf = bytearray(w * h * 4)
        else:
            self.buf = bytearray(bytes((*fill, 255)) * (w * h))

    # -- reads ---------------------------------------------------------
    def px(self, x: int, y: int) -> tuple[int, int, int, int]:
        x, y = int(x), int(y)
        if not (0 <= x < self.w and 0 <= y < self.h):
            return (0, 0, 0, 0)
        i = (y * self.w + x) * 4
        b = self.buf
        return b[i], b[i + 1], b[i + 2], b[i + 3]

    # -- writes --------------------------------------------------------
    def dot(self, x: int, y: int, colour: RGB, alpha: int = 255) -> None:
        x, y = int(x), int(y)
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        i = (y * self.w + x) * 4
        self.buf[i] = colour[0]
        self.buf[i + 1] = colour[1]
        self.buf[i + 2] = colour[2]
        self.buf[i + 3] = alpha

    def fill(self, colour: RGB, x0: int = 0, y0: int = 0,
             x1: int | None = None, y1: int | None = None) -> None:
        x1 = self.w if x1 is None else x1
        y1 = self.h if y1 is None else y1
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.dot(x, y, colour)

    def rect(self, x: int, y: int, w: int, h: int, colour: RGB,
             alpha: int = 255) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.dot(xx, yy, colour, alpha)

    def hline(self, x0: int, x1: int, y: int, colour: RGB) -> None:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.dot(x, y, colour)

    def vline(self, x: int, y0: int, y1: int, colour: RGB) -> None:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.dot(x, y, colour)

    def blit(self, src: "Image", x: int, y: int) -> None:
        """Copies src over this image, skipping fully transparent pixels."""
        for sy in range(src.h):
            for sx in range(src.w):
                r, g, b, a = src.px(sx, sy)
                if a:
                    self.dot(x + sx, y + sy, (r, g, b), a)

    def scaled(self, factor: int) -> "Image":
        """Nearest-neighbour upscale, for the published preview only."""
        out = Image(self.w * factor, self.h * factor)
        for y in range(out.h):
            for x in range(out.w):
                out.dot(x, y, self.px(x // factor, y // factor)[:3])
        return out

    # -- output --------------------------------------------------------
    def to_png(self, path: str) -> int:
        raw = bytearray()
        stride = self.w * 4
        for y in range(self.h):
            raw.append(0)  # filter: none
            raw.extend(self.buf[y * stride:(y + 1) * stride])
        data = zlib.compress(bytes(raw), 9)

        def chunk(tag: bytes, payload: bytes) -> bytes:
            return (struct.pack(">I", len(payload)) + tag + payload
                    + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
        png += chunk(b"IDAT", data)
        png += chunk(b"IEND", b"")
        with open(path, "wb") as handle:
            handle.write(png)
        return len(png)


def stamp(img: Image, pattern: list[str], x: int, y: int,
          colours: dict[str, RGB]) -> None:
    """Draws ASCII art onto a tile.

    One character per pixel; '.' and ' ' are transparent. The pattern is a list
    of equal length strings so the art can be reviewed in the source itself -
    a flower is readable as a flower, not as a pile of coordinates.
    """
    for dy, row in enumerate(pattern):
        for dx, ch in enumerate(row):
            if ch in (".", " "):
                continue
            colour = colours.get(ch)
            if colour is None:
                raise KeyError(f"stamp(): no colour for {ch!r} in row {row!r}")
            img.dot(x + dx, y + dy, colour)
