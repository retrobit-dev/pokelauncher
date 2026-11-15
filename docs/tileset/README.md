# Johto tileset (original art)

A 16x16 tile set for the top-down Johto world, drawn pixel by pixel by
`tools/tileset/`. The look follows the flat, warm, paper-like palette of the
launcher (`HgColors`), not a copy of Nintendo's artwork.

## Build

```bash
python3 tools/tileset/build.py
```

## Files

| file | what it is |
| --- | --- |
| `johto-tileset.png` | the atlas an engine loads, 16 px tiles |
| `johto-tileset@6x.png` | the same atlas at 6x, for eyeballing each tile |
| `johto-world.png` | a composed scene to judge the pieces together |
| `johto-world@4x.png` | that scene at 4x |
| `tileset.json` | every tile: atlas position, size, collision, layer |

## Tiles

**Ground** `grass`, `grass_detail`, `grass_dark`, `path`, `path_n/s/e/w`,
`water`, `water_shallow`, `water_foam`, `cliff_face`, `cliff_top`

**Objects** `tree` (2x2), `bush`, `flowers_gold/red/white`, `rock`,
`fence_h`, `fence_v`, `sign`, `stairs`

**Buildings** `roof`, `roof_left`, `roof_right`, `wall`, `wall_plain`,
`wall_window`, `wall_door`, `lab_badge`

`solid` in the index is what the map collision uses; `layer` says whether a
tile belongs under the player (`ground`) or over it (`object`, `building`).

## Rules the tiles follow

- 16x16, no anti-aliasing, no gradients: flat colour and a short ramp per
  material, so they scale crisply on the 343 ppi panel.
- Ground tiles are seamless; `verify.py` and the build check the wrap-around
  edges so a repeated lawn never shows a grid.
- Decorative variation (flowers, tufts) lives in separate tiles and is placed
  with a coordinate hash, so a lawn scatters instead of forming a pattern.
