#!/usr/bin/env python3
"""Builds the Johto tileset: one atlas PNG plus a review sheet.

    python3 tools/tileset/build.py

Outputs
  docs/tileset/johto-tileset.png    the atlas a game engine would load
  docs/tileset/johto-tileset@6x.png the same atlas, nearest-neighbour, to review
  docs/tileset/johto-world.png      a small composed scene, to judge the pieces
  docs/tileset/tileset.json         tile names, grid position and collision

The art is generated, not copied: every pixel is written by the modules in this
package, so the tileset stays original while keeping the flat, warm, paper-like
look of HeartGold. Nothing here ships Nintendo's artwork.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tileset import buildings as B          # noqa: E402
from tileset import ground as G             # noqa: E402
from tileset import objects as O            # noqa: E402
from tileset import palette as P            # noqa: E402
from tileset.pixels import Image            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "tileset")

TILE = 16
COLUMNS = 8


def ground_tiles() -> list[tuple[str, object, bool]]:
    """(name, factory, solid) for the 16x16 ground layer."""
    return [
        ("grass", G.grass_plain, False),
        ("grass_detail", G.grass_detail, False),
        ("grass_dark", G.grass_dark, False),
        ("path", G.path_stone, False),
        ("path_n", lambda: G.path_edge("n"), False),
        ("path_s", lambda: G.path_edge("s"), False),
        ("path_w", lambda: G.path_edge("w"), False),
        ("path_e", lambda: G.path_edge("e"), False),
        ("water", lambda: G.water(False), True),
        ("water_shallow", lambda: G.water(True), True),
        ("water_foam", G.water_foam, True),
        ("cliff_face", G.cliff_face, True),
        ("cliff_top", G.cliff_top, True),
    ]


def object_tiles() -> list[tuple[str, object, bool]]:
    """(name, factory, solid) for everything that sits on the ground."""
    return [
        ("flowers_gold", lambda: O.flowers("gold"), False),
        ("flowers_red", lambda: O.flowers("red"), False),
        ("flowers_white", lambda: O.flowers("white"), False),
        ("bush", O.bush, True),
        ("rock", O.rock, True),
        ("fence_h", O.fence_h, True),
        ("fence_v", O.fence_v, True),
        ("sign", O.sign, True),
        ("stairs", O.stairs, False),
    ]


def building_parts() -> list[tuple[str, object, bool]]:
    return [
        ("wall_plain", B.wall_plain, True),
        ("wall_window", B.wall_window, True),
        ("wall_door", B.wall_door, True),
        ("roof", B.roof, True),
        ("roof_left", lambda: B.roof_edge("left"), True),
        ("roof_right", lambda: B.roof_edge("right"), True),
    ]


def build_atlas(out_dir: str) -> dict:
    """Packs the 16x16 tiles into a grid and records where each one landed."""
    entries: list[tuple[str, Image, bool, str]] = []
    for name, factory, solid in ground_tiles():
        entries.append((name, factory(), solid, "ground"))
    for name, factory, solid in object_tiles():
        entries.append((name, factory(), solid, "object"))
    for name, factory, solid in building_parts():
        entries.append((name, factory(), solid, "building"))

    rows = (len(entries) + COLUMNS - 1) // COLUMNS
    atlas = Image(COLUMNS * TILE, rows * TILE)
    index: dict[str, dict] = {}
    for i, (name, img, solid, layer) in enumerate(entries):
        col, row = i % COLUMNS, i // COLUMNS
        atlas.blit(img, col * TILE, row * TILE)
        index[name] = {
            "x": col * TILE,
            "y": row * TILE,
            "w": TILE,
            "h": TILE,
            "solid": solid,
            "layer": layer,
        }

    # the tree is the one multi-tile piece: a 2x2 footprint in its own spot
    tree = O.tree_canopy()
    tree_y = rows * TILE + TILE
    atlas_h = rows * TILE + TILE + tree.h
    tall = Image(atlas.w, atlas_h)
    tall.blit(atlas, 0, 0)
    tall.blit(tree, 0, rows * TILE + TILE)
    index["tree"] = {
        "x": 0,
        "y": rows * TILE + TILE,
        "w": tree.w,
        "h": tree.h,
        "solid": True,
        "layer": "object",
        "footprint": [2, 2],
    }

    os.makedirs(out_dir, exist_ok=True)
    size = tall.to_png(os.path.join(out_dir, "johto-tileset.png"))
    tall.scaled(6).to_png(os.path.join(out_dir, "johto-tileset@6x.png"))

    meta = {
        "tile": TILE,
        "columns": COLUMNS,
        "atlas": "johto-tileset.png",
        "tiles": index,
        "generated_by": "tools/tileset/build.py",
    }
    with open(os.path.join(out_dir, "tileset.json"), "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)
        handle.write("\n")
    return {"atlas_size": (tall.w, tall.h), "bytes": size, "count": len(index)}


def compose_world(out_dir: str) -> None:
    """A tiny scene: grass, a path, a cottage, a tree line and water.

    This is not the game map; it exists so a reviewer can see the tiles working
    together, including the seams between them.
    """
    cols, rows = 20, 13
    scene = Image(cols * TILE, rows * TILE)

    grass = [G.grass_plain(), G.grass_detail(), G.grass_dark()]

    def scatter(x: int, y: int, salt: int, mod: int) -> int:
        """Cheap hash: a linear formula lays the flowers out in diagonal rows,
        which reads as polka dots. Mixing the coordinates first scatters them
        the way a hand-placed lawn looks."""
        n = x * 73856093 ^ y * 19349663 ^ salt * 83492791
        return (n >> 4) % mod

    for y in range(rows):
        for x in range(cols):
            pick = grass[1] if scatter(x, y, 7, 17) == 0 else grass[0]
            scene.blit(pick, x * TILE, y * TILE)

    # a path running down the middle and turning east
    for y in range(3, rows):
        scene.blit(G.path_stone(), 8 * TILE, y * TILE)
    for x in range(9, 14):
        scene.blit(G.path_stone(), x * TILE, 9 * TILE)

    # a pond in the lower left; the top edge steps in and out so the shore is
    # not a ruler-straight line
    for x in range(0, 6):
        top = 10 if x % 3 else 11
        for y in range(top, rows):
            tile = G.water_foam() if y == top else G.water(False)
            scene.blit(tile, x * TILE, y * TILE)

    # a cottage: roof band, wall with a window, door at the bottom
    scene.blit(B.roof(), 2 * TILE, 1 * TILE)
    scene.blit(B.roof(), 4 * TILE, 1 * TILE)
    scene.blit(B.wall_window(), 2 * TILE, 3 * TILE)
    scene.blit(B.wall_door(), 4 * TILE, 3 * TILE)

    # trees along the top, bushes and flowers scattered on the lawn
    for x in (0, 6, 12, 14, 16, 18):
        scene.blit(O.tree_canopy(), min(x, cols - 2) * TILE, 0)
    for (x, y) in ((1, 8), (6, 7), (11, 4), (13, 7), (16, 8)):
        scene.blit(O.bush(), x * TILE, y * TILE)
    for (x, y, kind) in ((5, 6, "gold"), (7, 5, "red"), (12, 5, "white"),
                         (10, 8, "gold"), (15, 6, "red")):
        scene.blit(O.flowers(kind), x * TILE, y * TILE)
    scene.blit(O.rock(), 18 * TILE, 10 * TILE)
    scene.blit(O.sign(), 9 * TILE, 8 * TILE)

    os.makedirs(out_dir, exist_ok=True)
    scene.to_png(os.path.join(out_dir, "johto-world.png"))
    scene.scaled(4).to_png(os.path.join(out_dir, "johto-world@4x.png"))


def main() -> int:
    result = build_atlas(OUT)
    compose_world(OUT)
    w, h = result["atlas_size"]
    print(f"docs/tileset/johto-tileset.png  {w}x{h}  {result['count']} tiles  "
          f"{result['bytes'] // 1024} KB")
    print("docs/tileset/johto-world.png   scene check")
    print("docs/tileset/tileset.json      index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
