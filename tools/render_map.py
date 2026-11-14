#!/usr/bin/env python3
"""Renders a map.json to a PNG for review, the way the game would draw it.

    python3 tools/render_map.py app/src/main/assets/tileset/map.json out.png [scale]

Layers are drawn ground -> building -> object, transparent pixels are skipped
(so a tree's canopy sits on the grass instead of punching a black hole), and a
2x2 piece is drawn once at its top-left cell. This is the same rule the Compose
renderer follows, which is what makes the output worth looking at before
shipping a map.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from tileset.pixels import Image  # noqa: E402


def read_png(path: str) -> Image:
    blob = open(path, "rb").read()
    pos, idat = 8, b""
    while pos + 8 <= len(blob):
        length = struct.unpack(">I", blob[pos:pos + 4])[0]
        tag = blob[pos + 4:pos + 8]
        body = blob[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 4
    img = Image(width, height)
    prev = bytearray(stride)
    o = 0
    for y in range(height):
        f = raw[o]; o += 1
        line = bytearray(raw[o:o + stride]); o += stride
        if f == 1:
            for i in range(4, stride):
                line[i] = (line[i] + line[i - 4]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - 4] if i >= 4 else 0
                b = prev[i]
                c = prev[i - 4] if i >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        img.buf[y * stride:(y + 1) * stride] = line
        prev = line
    return img


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    map_path = argv[0]
    out_path = argv[1]
    scale = int(argv[2]) if len(argv) > 2 else 1

    meta = json.load(open(os.path.join(ROOT, "docs/tileset/tileset.json"), encoding="utf-8"))
    tiles = meta["tiles"]
    atlas = read_png(os.path.join(ROOT, "docs/tileset/johto-tileset.png"))
    doc = json.load(open(map_path, encoding="utf-8"))
    cols, rows = doc["cols"], doc["rows"]

    img = Image(cols * 16, rows * 16)
    # ground first for every cell: an object's overhang must never be covered
    # by a neighbour's ground tile
    for layer in ("ground", "building", "object"):
        for key, cell in doc["cells"].items():
            # new format: one name per layer; old format: a single name+layer
            name = cell.get(layer)
            if name is None and cell.get("layer") == layer:
                name = cell.get("name")
            tile = tiles.get(name)
            if not tile:
                continue
            x, y = (int(v) for v in key.split(","))
            for yy in range(tile["h"]):
                for xx in range(tile["w"]):
                    r, g, b, a = atlas.px(tile["x"] + xx, tile["y"] + yy)
                    if a == 0:
                        continue
                    if 0 <= x * 16 + xx < img.w and 0 <= y * 16 + yy < img.h:
                        img.dot(x * 16 + xx, y * 16 + yy, (r, g, b))

    spawn = doc.get("spawn")
    if spawn:
        for i in range(16):
            img.dot(spawn["x"] * 16 + i, spawn["y"] * 16, (197, 58, 45))
            img.dot(spawn["x"] * 16 + i, spawn["y"] * 16 + 15, (197, 58, 45))

    if scale > 1:
        img = img.scaled(scale)
    img.to_png(out_path)
    print(f"{out_path}  {img.w}x{img.h}  ({cols}x{rows} sel, skala {scale}x)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
