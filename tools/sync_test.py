#!/usr/bin/env python3
"""The editor and the game must draw the same map the same way.

The user's question was blunt: "are the editor and gameplay actually in sync?"
A screenshot cannot answer that - two renders can look similar and still place a
32x32 tree one cell down from where the app puts it, which is exactly the bug
that was here. So this test renders one map through both paths and compares
pixels:

  game path   tools/render_map.py, the same layer order and anchor rule the
              Compose renderer uses
  editor path editor/app.js itself, run in a small DOM shim, with its real
              draw() and its real drawImage rectangles recorded

A difference fails the test and prints where it is. Three things are excluded on
purpose, because they are overlays rather than map content:

  * the spawn marker the game paints over the map,
  * the editor's gameplay frame and cursor,
  * cells with no tile at all: the game leaves them transparent, the editor
    paints the app's ground colour (#5C7A45), which is what the device shows.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from render_map import read_png  # noqa: E402

TILE = 16
GROUND = (0x5C, 0x7A, 0x45)     # WorldCanvas.kt: the colour behind an empty cell
SPAWN = (197, 58, 45)           # the game's spawn marker, not map content

# A map that exercises the rules that can drift: a 2x2 tree (anchor + overhang),
# a single-cell ground tile, water, and a cell with nothing on it.
MAP = {
    "version": 1,
    "tile": TILE,
    "cols": 20,
    "rows": 12,
    "spawn": {"x": 5, "y": 6},
    "cells": {
        "5,6": {"ground": "path", "object": "tree"},
        "6,6": {"ground": "grass"},
        "7,6": {"ground": "water"},
        "9,7": {"ground": "path"},
    },
}

NODE_RUNNER = r"""
const fs = require('fs'), path = require('path');
const ROOT = process.argv[2];
const mapPath = process.argv[3];
const outPath = process.argv[4];
const src = fs.readFileSync(path.join(ROOT, 'editor/app.js'), 'utf8');

// Record every drawImage the editor asks for. The rectangles are the drawing
// itself: rasterising them here is the same picture the browser would paint.
const calls = [];
const ctx = {
  setTransform() {}, fillRect() {}, beginPath() {}, rect() {}, fill() {},
  strokeRect() {}, save() {}, restore() {}, moveTo() {}, lineTo() {}, stroke() {},
  arc() {}, clip() {},
  imageSmoothingEnabled: false, fillStyle: '', strokeStyle: '', lineWidth: 1,
  drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh) {
    calls.push({ sx, sy, sw, sh, dx, dy, dw, dh });
  },
  canvas: { width: 0, height: 0 },
};
class E {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.style = {}; this.dataset = {};
    this.hidden = false; this.textContent = ''; this.innerHTML = ''; this.disabled = false;
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
    this.children = [];
  }
  set id(v) { this._i = v; document._byId[v] = this; }
  get id() { return this._i; }
  appendChild(c) { this.children.push(c); return c; }
  setAttribute() {} getAttribute() {}
  addEventListener() {} removeEventListener() {} setPointerCapture() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: win.innerWidth, height: win.innerHeight }; }
  getContext() { return ctx; }
}
const document = {
  _byId: {},
  getElementById(id) { return this._byId[id] || (this._byId[id] = new E()); },
  createElement(t) { return new E(t); },
  body: new E(),
};
const win = {
  innerWidth: 320, innerHeight: 192, devicePixelRatio: 1,
  addEventListener() {}, setTimeout, clearTimeout,
};
const Image = class { set src(_v) { setTimeout(() => this.onload && this.onload(), 0); } };
const fetch = async (u) => {
  if (u.includes('tileset.json')) {
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/tileset/tileset.json'), 'utf8')) };
  }
  if (u.includes('map.json')) {
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(mapPath, 'utf8')) };
  }
  return { ok: true, json: async () => ({ ok: true }) };
};

const mod = new Function('document', 'window', 'Image', 'fetch', 'console', 'setTimeout', 'clearTimeout',
  src + '\nreturn { boot, state, draw };')(
  document, win, Image, fetch, console, setTimeout, clearTimeout);

mod.boot().then(() => {
  const st = mod.state;
  // 1:1, camera at the top-left: the frame render_map.py draws
  st.zoom = 1; st.camera.x = 0; st.camera.y = 0;
  calls.length = 0;
  mod.draw();
  // keep only tile draws; the frame and cursor are editor decorations
  const tiles = calls.filter((c) => (c.dw === 16 || c.dw === 32) && (c.dh === 16 || c.dh === 32));
  fs.writeFileSync(outPath, JSON.stringify({ cells: st.cells.size, tiles }));
}).catch((e) => {
  console.error('editor boot failed:', e.message);
  process.exit(1);
});
"""


def main() -> int:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        map_path = os.path.join(tmp, "map.json")
        game_png = os.path.join(tmp, "game.png")
        calls_json = os.path.join(tmp, "calls.json")
        runner = os.path.join(tmp, "runner.js")
        with open(map_path, "w", encoding="utf-8") as handle:
            json.dump(MAP, handle)
        with open(runner, "w", encoding="utf-8") as handle:
            handle.write(NODE_RUNNER)

        # 1. the game's own renderer
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "render_map.py"),
             map_path, game_png, "1"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("  FAIL  render_map.py gagal")
            print(result.stderr.strip()[:400])
            return 1

        # 2. the editor's real draw path
        result = subprocess.run(["node", runner, ROOT, map_path, calls_json],
                                capture_output=True, text=True)
        if result.returncode != 0:
            print("  FAIL  editor tidak bisa dijalankan")
            print((result.stderr or result.stdout).strip()[:400])
            return 1

        with open(calls_json, encoding="utf-8") as handle:
            payload = json.load(handle)
        tiles = payload["tiles"]

        # 3. the editor must have actually loaded the map. This is the bug that
        #    was here: seedIfEmpty() cleared the cells right after loadMap(), so
        #    the editor opened empty and every pixel comparison trivially
        #    matched nothing.
        expected_cells = len(MAP["cells"])
        if payload["cells"] < expected_cells:
            print(f"  FAIL  editor memuat {payload['cells']} sel, padahal peta berisi "
                  f"{expected_cells}: peta tersimpan tidak sampai ke editor")
            return 1
        print(f"  ok    editor memuat {payload['cells']} sel dari peta")

        if not tiles:
            print("  FAIL  editor tidak menggambar satu tile pun")
            return 1

        # 4. compare every tile pixel against the game render
        atlas = read_png(os.path.join(ROOT, "docs", "tileset", "johto-tileset.png"))
        game = read_png(game_png)
        seen = set()
        same = diff = skipped = 0
        first = None
        for call in tiles:
            spot = (call["sx"], call["sy"], call["dx"], call["dy"])
            if spot in seen:
                continue              # the editor draws once; guard anyway
            seen.add(spot)
            for yy in range(call["sh"]):
                for xx in range(call["sw"]):
                    r, g, b, a = atlas.px(call["sx"] + xx, call["sy"] + yy)
                    if not a:
                        continue          # transparent: the cell shows through
                    x, y = call["dx"] + xx, call["dy"] + yy
                    if not (0 <= x < game.w and 0 <= y < game.h):
                        continue
                    actual = tuple(game.buf[(y * game.w + x) * 4:(y * game.w + x) * 4 + 3])
                    if max(abs(actual[i] - SPAWN[i]) for i in range(3)) <= 12:
                        skipped += 1  # the game's spawn marker, not map content
                        continue
                    if actual == (r, g, b):
                        same += 1
                    else:
                        diff += 1
                        if first is None:
                            first = (x, y, (r, g, b), actual)

        total = same + diff
        if total == 0:
            print("  FAIL  tidak ada piksel yang bisa dibandingkan")
            return 1
        if diff:
            share = 100.0 * diff / total
            print(f"  FAIL  {diff} dari {total} piksel ({share:.1f}%) berbeda; "
                  f"pertama di {first[0]},{first[1]}: editor {first[2]}, game {first[3]}")
            problems.append("editor dan game menggambar peta dengan cara berbeda")
        else:
            print(f"  ok    {same} piksel identik antara editor dan game "
                  f"({skipped} piksel penanda spawn dilewati)")

        # 5. the 2x2 tree must start at the cell that carries it and cover four
        #    cells from there. A tile drawn at the wrong offset still looks like
        #    a tree, so this checks the rectangle, not the picture: anchored at
        #    (5,6) it is a 32x32 rect at (80,96), i.e. it reaches cell (6,7).
        tree_rects = [c for c in tiles if c["dw"] == 32 and c["dh"] == 32]
        if not tree_rects:
            problems.append("pohon 2x2 tidak digambar sama sekali")
            print("  FAIL  pohon 2x2 tidak digambar")
        else:
            ok = all(
                call["dx"] == 5 * TILE and call["dy"] == 6 * TILE
                for call in tree_rects
            )
            if not ok:
                problems.append("pohon 2x2 tidak mulai di sel anchor-nya (5,6)")
                print(f"  FAIL  pohon mulai di "
                      f"({tree_rects[0]['dx'] // TILE},{tree_rects[0]['dy'] // TILE}) "
                      f"bukan (5,6)")
            else:
                print("  ok    pohon 2x2 mulai di selnya, menutup 2x2 sel ke kanan-bawah")

    if problems:
        print(f"\n{len(problems)} problem(s)")
        return 1
    print("\neditor dan gameplay menggambar peta yang sama")
    return 0


if __name__ == "__main__":
    sys.exit(main())
