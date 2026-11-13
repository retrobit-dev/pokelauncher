#!/usr/bin/env python3
"""Writes the starter map that ships inside the app.

    python3 tools/starter_map.py

`app/src/main/assets/tileset/map.json` is what the home screen loads on first
run: a small village with a house, a field, a pond, trees and — the point of the
whole thing — the launcher machine beside the house.

The format is the one the editor saves, so opening this file in the editor and
saving over it is the normal way to change the starting world.
"""
from __future__ import annotations

import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "app", "src", "main", "assets", "tileset", "map.json")
COLS, ROWS = 80, 50          # 1280x800 px: roomy on the tablet at 3x, small enough to walk
CELLS: dict[str, dict] = {}


def put(x: int, y: int, name: str, layer: str, solid: bool) -> None:
    """One tile per layer: a tree sits *on* the grass, it does not replace it."""
    cell = CELLS.setdefault(f"{x},{y}", {})
    cell[layer] = name


def fill(x0: int, y0: int, x1: int, y1: int, name: str, layer: str, solid: bool) -> None:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, name, layer, solid)


def main() -> None:
    rnd = random.Random(11)

    # ground: a lawn with a little texture, never a flat green rectangle
    for y in range(ROWS):
        for x in range(COLS):
            roll = rnd.random()
            name = "grass_detail" if roll < 0.10 else ("grass_dark" if roll < 0.18 else "grass")
            put(x, y, name, "ground", False)

    # a pond in the north-east
    fill(58, 8, 72, 20, "water", "ground", True)
    fill(60, 10, 70, 18, "water_shallow", "ground", True)
    for y in range(7, 22):
        for x in range(57, 74):
            cell = CELLS.get(f"{x},{y}")
            if cell and cell.get("ground", "").startswith("grass"):
                near = any(CELLS.get(f"{x + dx},{y + dy}", {}).get("ground", "").startswith("water")
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if near:
                    put(x, y, "water_foam", "ground", True)

    # the main path: east-west through the village, then north to the house
    fill(0, 30, COLS - 1, 31, "path", "ground", False)
    fill(38, 22, 39, 29, "path", "ground", False)

    # a house at the end of the north path: 9 wide, 2 roof rows over 2 wall rows
    # (the wall component already carries its own eave, so 2 rows reads as a
    # proper HG cottage instead of a kiosk)
    for x in range(35, 44):
        put(x, 18, "roof_left" if x == 35 else ("roof_right" if x == 43 else "roof"), "building", True)
        put(x, 19, "roof", "building", True)
        put(x, 20, "wall_window" if x in (36, 42) else "wall_plain", "building", True)
    put(39, 21, "wall_door", "building", True)
    fill(37, 22, 41, 22, "path", "ground", False)

    # the launcher machine, waiting by the front door
    put(41, 22, "machine_left", "object", True)
    put(42, 22, "machine_right", "object", True)

    # a fenced field to the west: soil the player can till
    for x in range(8, 22):
        put(x, 24, "fence_h", "object", True)
        put(x, 35, "fence_h", "object", True)
    for y in range(24, 36):
        put(7, y, "fence_v", "object", True)
        put(22, y, "fence_v", "object", True)
    put(14, 35, "stairs", "object", False)
    for y in range(25, 35):
        for x in range(8, 22):
            put(x, y, "grass_dark", "ground", False)

    # trees and flowers, kept clear of the paths and the field
    spawn = (39, 33)
    keep_clear = {spawn, (spawn[0], spawn[1] - 1), (spawn[0] - 1, spawn[1]), (spawn[0] + 1, spawn[1])}

    def free(x: int, y: int) -> bool:
        if (x, y) in keep_clear:
            return False
        cell = CELLS.get(f"{x},{y}")
        if not cell:
            return False
        ground = cell.get("ground", "")
        if not ground.startswith("grass"):
            return False
        if "object" in cell or "building" in cell:
            return False
        if 28 <= y <= 32:
            return False
        if 6 <= x <= 23 and 23 <= y <= 36:
            return False
        if 33 <= x <= 44 and 18 <= y <= 23:
            return False
        return True

    for _ in range(140):
        x, y = rnd.randrange(1, COLS - 1), rnd.randrange(1, ROWS - 1)
        if not free(x, y):
            continue
        put(x, y, "tree", "object", True)

    for _ in range(90):
        x, y = rnd.randrange(COLS), rnd.randrange(ROWS)
        if not free(x, y):
            continue
        # flowers are walkable in the atlas, bush is not: keep the flags in step
        name = rnd.choice(["flowers_gold", "flowers_red", "flowers_white", "bush"])
        put(x, y, name, "object", name == "bush")

    for (x, y) in ((30, 29), (46, 32), (20, 42)):
        put(x, y, "sign", "object", True)

    doc = {
        "version": 1,
        "tile": 16,
        "cols": COLS,
        "rows": ROWS,
        "spawn": {"x": 39, "y": 33},
        "cells": CELLS,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"), sort_keys=True)
    size = os.path.getsize(OUT)
    print(f"{os.path.relpath(OUT, ROOT)}  {COLS}x{ROWS} sel  {len(CELLS)} sel  {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
