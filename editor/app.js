/* Johto map editor.
 *
 * The map is a grid of 16x16 cells. The canvas fills everything above the tool
 * bar; the view moves with the Geser tool (or middle/right drag, or the arrow
 * keys) and scales with the -/+/zoom buttons or the wheel.
 *
 * There is no pinch and no two-finger pan. Moving the map is a tool you pick,
 * like drawing: on a tablet it is one finger in the Geser tool, and on a desk it
 * is a middle drag if you would rather not change tools. Two fingers used to do
 * both, which meant every accidental second touch zoomed the map out from under
 * the stroke that was being drawn.
 *
 * Tools: pencil, eraser, picker, area fill, and Geser (move). The brush size
 * says how many cells one stroke touches.
 *
 * The dashed frame drawn over the map is the gameplay viewport: the cells that
 * `Mode gameplay` shows. It uses the same numbers as the game (zoom, 1/6 dead
 * zone, camera clamped to the map, panel 2560x1600), so the frame is a promise,
 * not a guess.
 */
'use strict';

const TILE = 16;                 // one grid cell, in map pixels
// 1 = exactly 16x16 px per cell. 0.5 is allowed (a cell becomes 8 px) because
// seeing the whole 160x100 panel map is worth the half pixels; above 1 only
// whole numbers, where snapping to whole pixels actually matters.
const ZOOM_STEPS = [0.5, 1, 2, 3, 4, 6, 8];

// The gameplay viewport, mirrored from the app. GameViewModel opens at
// TouchInput.DEFAULT (10x) and CameraRig keeps a sixth of the view still on
// each side; tools/verify.py checks these three numbers against the Kotlin.
const PANEL_PX = { w: 2560, h: 1600 };
const GAME_ZOOM = 10;
const DEAD_ZONE = 1 / 6;

// What one tablet screen shows, in cells. The game works in map pixels
// (2560/10 = 256 px), but the editor draws in cells, so converting once here
// keeps every use below in the same unit.
const FRAME_MAP = {
  w: PANEL_PX.w / GAME_ZOOM / TILE,     // 16 cells
  h: PANEL_PX.h / GAME_ZOOM / TILE,     // 10 cells
};
// The map is exactly the tablet panel at 1:1: 2560x1600 / 16 = 160x100 cells.
// That is why the grid "fills the screen": on the device it lines up pixel for
// pixel, and in a smaller browser window it simply zooms out to fit.
const DEFAULT_COLS = 160;
const DEFAULT_ROWS = 100;
const LAYERS = ['ground', 'building', 'object'];   // paint order: top layer drawn last

// Brush sizes, in cells. Square brushes only: a square of 1 is the old single
// cell, and a 4x4 square is a tree line in four strokes instead of sixteen.
const BRUSH_SIZES = [1, 2, 3, 4, 6, 8];

// How many edits can be taken back. A map is thousands of cells, so the limit
// is on *strokes*, not cells; 60 strokes is more than anyone undoes by hand.
const HISTORY_LIMIT = 60;

/**
 * A cell holds one tile per layer, so a tree stands on grass instead of
 * replacing it. The map is keyed "x,y|layer"; the saved file groups them back
 * into "x,y" cells.
 */
function layerKey(x, y, layer) {
  return `${x},${y}|${layer}`;
}

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ state
const state = {
  tileset: null,        // tileset.json
  atlas: null,          // HTMLImageElement of the atlas
  cells: new Map(),     // "x,y|layer" -> { name, layer, solid } | null
  camera: { x: 0, y: 0 },   // top-left of the view, in map pixels
  zoom: 1,          // 1 = one cell is exactly 16x16 screen pixels
  tool: 'pencil',
  brush: null,          // { name, layer, solid }
  brushSize: 1,         // cells per side, from BRUSH_SIZES
  tab: 'ground',
  hover: { x: 0, y: 0 },
  loadedMap: false,     // a saved map wins over the fresh sheet
  cols: DEFAULT_COLS,
  rows: DEFAULT_ROWS,
  spawn: null,          // the cell the player starts on, saved with the map
  painting: false,
  panning: false,
  panFrom: null,
  // undo/redo: snapshots of the painted cells, one per stroke
  undo: [],
  redo: [],
  // the stroke in progress, so a 40-cell drag is one undo step and not forty
  strokeOpen: false,
};

const key = (x, y) => x + ',' + y;

// ------------------------------------------------------------------ helpers
function toast(message, ms = 1400) {
  const el = $('toast');
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { el.hidden = true; }, ms);
}

function cellSize() { return TILE * state.zoom; }

function screenToCell(clientX, clientY) {
  const x = Math.floor((state.camera.x + clientX) / cellSize());
  const y = Math.floor((state.camera.y + clientY) / cellSize());
  return { x, y };
}

/** Visible cell range, so painting never walks the whole infinite map. */
function visibleRange() {
  const w = window.innerWidth, h = window.innerHeight;
  return {
    x0: Math.floor(state.camera.x / cellSize()) - 1,
    y0: Math.floor(state.camera.y / cellSize()) - 1,
    x1: Math.ceil((state.camera.x + w) / cellSize()) + 1,
    y1: Math.ceil((state.camera.y + h) / cellSize()) + 1,
  };
}

// ------------------------------------------------------------------ history
/**
 * Snapshots are whole maps, on purpose.
 *
 * A diff-based undo would be smaller, but it also has to be right: one missed
 * case (fill, erase on a layer that is not there, a new map) and undo silently
 * corrupts the map. A 160x100 map is a few thousand cells, so a copy is cheap
 * and impossible to get subtly wrong. Only the first HISTORY_LIMIT strokes are
 * kept; older ones fall off the front.
 */
function snapshot() {
  return new Map(state.cells);
}

function remember() {
  state.undo.push(snapshot());
  if (state.undo.length > HISTORY_LIMIT) state.undo.shift();
  state.redo.length = 0;       // a new edit invalidates the redo branch
  state.strokeOpen = false;    // the next paint starts a fresh stroke
  updateHistoryButtons();
}

/**
 * One entry per stroke: the map as it was before the first cell of the drag.
 * Called from the first paint of a stroke, so dragging across 40 cells does not
 * bury everything else under 40 undo steps.
 */
function beginStroke() {
  if (state.strokeOpen) return;
  remember();
  state.strokeOpen = true;
}

function endStroke() {
  state.strokeOpen = false;
}

function undo() {
  if (!state.undo.length) { toast('Tidak ada yang bisa dibatalkan'); return false; }
  state.redo.push(snapshot());
  state.cells = state.undo.pop();
  state.strokeOpen = false;
  draw();
  updateHud();
  updateHistoryButtons();
  return true;
}

function redo() {
  if (!state.redo.length) { toast('Tidak ada yang bisa diulang'); return false; }
  state.undo.push(snapshot());
  state.cells = state.redo.pop();
  state.strokeOpen = false;
  draw();
  updateHud();
  updateHistoryButtons();
  return true;
}

function updateHistoryButtons() {
  if ($('undo')) {
    $('undo').disabled = state.undo.length === 0;
    $('redo').disabled = state.redo.length === 0;
  }
}

// ------------------------------------------------------------------ brush size
function setBrushSize(cells) {
  const allowed = BRUSH_SIZES.filter((v) => v <= cells);
  state.brushSize = allowed.length ? allowed[allowed.length - 1] : BRUSH_SIZES[0];
  updateHud();
  draw();
}

function brushUp() { setBrushSize(state.brushSize + 1); }
function brushDown() { setBrushSize(state.brushSize - 1); }

/** The cells one stroke touches: a square of brushSize centred on the cell. */
function brushCells(x, y) {
  const n = state.brushSize;
  const half = Math.floor((n - 1) / 2);
  const out = [];
  for (let dy = 0; dy < n; dy++) {
    for (let dx = 0; dx < n; dx++) {
      out.push({ x: x - half + dx, y: y - half + dy });
    }
  }
  return out;
}

// ------------------------------------------------------------------ drawing
function draw() {
  const canvas = $('map');
  const dpr = window.devicePixelRatio || 1;
  const w = window.innerWidth, h = window.innerHeight;

  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }

  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.imageSmoothingEnabled = false;

  // backdrop: the empty ground the game paints where a cell has no tile
  // (WorldCanvas.kt uses 0xFF5C7A45). Matching it means an empty map looks the
  // same in the editor and on the device, which is the whole point of the
  // frame being drawn here.
  ctx.fillStyle = '#5c7a45';
  ctx.fillRect(0, 0, w, h);

  const size = cellSize();
  const { x0, y0, x1, y1 } = visibleRange();

  // ground first, then buildings, then objects: same order as the game draws
  // them (WorldCanvas.drawMap), so a tall object overhangs exactly as it will
  // on the device. There is no grid: the app draws none, and an editor that
  // shows one is showing something the game cannot.
  for (const layer of LAYERS) {
    for (let y = y0; y <= y1; y++) {
      for (let x = x0; x <= x1; x++) {
        const cell = state.cells.get(layerKey(x, y, layer));
        if (!cell) continue;
        drawTile(ctx, cell.name, x, y, size);
      }
    }
  }

  drawGameFrame(ctx, size, w, h);
  drawCursor(ctx, size);
}

/**
 * The gameplay viewport: the cells `Mode gameplay` shows.
 *
 * Where it sits comes from the same rule the game uses, not from centring the
 * player on a screenshot:
 *
 *  - the camera is clamped to the map, so at the edges the frame stops at the
 *    edge instead of running past it;
 *  - if the map is smaller than the view, the whole map is centred;
 *  - inside that, CameraRig keeps the player inside a dead zone of a sixth of
 *    the view on each side, which is why the frame is drawn around the spawn
 *    and not always exactly centred on it.
 *
 * The player is drawn at the spawn cell: that is where the game starts, so it
 * is the one position the frame can be predicted for without running the game.
 */
function gameFrameRect() {
  const size = cellSize();
  // everything below is in screen pixels: cells * size
  const mapW = state.cols * size;
  const mapH = state.rows * size;
  const viewW = FRAME_MAP.w * size;
  const viewH = FRAME_MAP.h * size;

  const spawn = state.spawn || { x: Math.floor(state.cols / 2), y: Math.floor(state.rows / 2) };
  const targetX = spawn.x * size;
  const targetY = spawn.y * size;

  const clamp = (value, view, map) => (map <= view ? (map - view) / 2
    : Math.max(0, Math.min(map - view, value)));

  let x = clamp(targetX - viewW / 2, viewW, mapW);
  let y = clamp(targetY - viewH / 2, viewH, mapH);

  // dead zone: the camera only moves once the player leaves the middle band
  const dzx = viewW * DEAD_ZONE;
  const dzy = viewH * DEAD_ZONE;
  if (targetX > x + viewW - dzx) x = targetX - viewW + dzx;
  if (targetX < x + dzx) x = targetX - dzx;
  if (targetY > y + viewH - dzy) y = targetY - viewH + dzy;
  if (targetY < y + dzy) y = targetY - dzy;
  x = clamp(x, viewW, mapW);
  y = clamp(y, viewH, mapH);

  return { x, y, w: viewW, h: viewH, spawn, size };
}

function drawGameFrame(ctx, size, w, h) {
  const frame = gameFrameRect();
  const sx = frame.x - state.camera.x;
  const sy = frame.y - state.camera.y;

  ctx.save();
  // Dim everything the game will not show. Reading the frame is easier when the
  // inside is the only full-contrast part of the map.
  ctx.fillStyle = 'rgba(20, 28, 14, .34)';
  ctx.beginPath();
  ctx.rect(0, 0, w, h);
  ctx.rect(sx, sy, frame.w, frame.h);
  ctx.fill('evenodd');

  // the frame itself, plus corner ticks so it reads at any zoom
  ctx.strokeStyle = 'rgba(251, 243, 220, .95)';
  ctx.lineWidth = 2;
  ctx.strokeRect(sx + 1, sy + 1, frame.w - 2, frame.h - 2);
  ctx.strokeStyle = 'rgba(59, 47, 30, .9)';
  ctx.lineWidth = 1;
  ctx.strokeRect(sx + .5, sy + .5, frame.w - 1, frame.h - 1);

  // the player, at the spawn cell, inside the frame
  const px = frame.spawn.x * size - state.camera.x;
  const py = frame.spawn.y * size - state.camera.y;
  ctx.fillStyle = 'rgba(197, 58, 45, .95)';
  ctx.fillRect(px + size * 0.25, py + size * 0.25, size * 0.5, size * 0.5);
  ctx.strokeStyle = 'rgba(251, 243, 220, .95)';
  ctx.lineWidth = 1;
  ctx.strokeRect(px + size * 0.25 + .5, py + size * 0.25 + .5, size * 0.5 - 1, size * 0.5 - 1);

  ctx.restore();
}

function drawTile(ctx, name, cellX, cellY, size) {
  const tile = state.tileset.tiles[name];
  if (!tile || !state.atlas) return;
  // A 2x2 piece (the tree) must cover four cells, not be squashed into one, and
  // it hangs off its anchor cell: see tileOrigin().
  const origin = tileOrigin(tile, cellX, cellY);
  const px = origin.x * size - state.camera.x;
  const py = origin.y * size - state.camera.y;
  ctx.drawImage(
    state.atlas,
    tile.x, tile.y, tile.w, tile.h,                                  // source rect
    px, py, (tile.w / TILE) * size, (tile.h / TILE) * size,          // destination
  );
}

/** The brush footprint: one cell at size 1, a square of cells above that. */
function drawCursor(ctx, size) {
  const { x, y } = state.hover;
  if (!inBounds(x, y) && state.brushSize === 1) return;
  const half = Math.floor((state.brushSize - 1) / 2);
  const px = (x - half) * size - state.camera.x;
  const py = (y - half) * size - state.camera.y;
  const side = size * state.brushSize;
  if (px + side < 0 || py + side < 0) return;
  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = 'rgba(251, 243, 220, .95)';
  ctx.strokeRect(px + 1, py + 1, side - 2, side - 2);
  ctx.strokeStyle = 'rgba(59, 47, 30, .85)';
  ctx.strokeRect(px - .5, py - .5, side + 1, side + 1);
  ctx.restore();
}

/**
 * Where a tile is drawn, in cells, given the cell that was painted: exactly the
 * cell. A multi-cell tile grows down and right from the cell you click, and the
 * click lands on its top-left.
 *
 * That is not arbitrary. The 2x2 tree's art has its canopy in the lower half of
 * the 32x32 rect (the top 16 rows are empty), so a tree painted at (x, y) shows
 * bare cell at (x, y) and canopy over (x, y+1) and (x+1, y+1). This is also the
 * rule the game and both renderers already use, which is the point: the editor
 * has to place a tile exactly where the device will.
 */
function tileOrigin(tile, cellX, cellY) {
  return { x: cellX, y: cellY };
}

// ------------------------------------------------------------------ editing
/** Paints one cell, without touching the undo history. */
function paintCell(x, y) {
  if (!inBounds(x, y)) return false;      // the map has a fixed edge
  if (state.tool === 'erase') {
    // Remove one layer, topmost first: deleting a tree keeps the lawn under it,
    // and a second erase on the same cell removes the lawn itself.
    for (const layer of ['object', 'building', 'ground']) {
      if (state.cells.delete(layerKey(x, y, layer))) return true;
    }
    return false;
  }
  if (!state.brush) {
    toast('Pilih tile dari + dulu');
    return false;
  }
  // one tile per layer: painting ground under a tree keeps the tree
  state.cells.set(layerKey(x, y, state.brush.layer), { ...state.brush });
  return true;
}

/** Applies the brush footprint, remembering the stroke once. */
function paintAt(x, y) {
  if (state.tool === 'pick') {
    // topmost painted layer wins: that is what the eye sees
    let picked = null;
    for (const layer of ['object', 'building', 'ground']) {
      const cell = state.cells.get(layerKey(x, y, layer));
      if (cell) { picked = cell; break; }
    }
    if (picked) {
      state.brush = { ...picked };
      showBrush();
    } else {
      toast('Sel kosong');
    }
    return;
  }
  // Any real change is one undo step, and the whole footprint is one change.
  const cells = brushCells(x, y);
  const touched = cells.some((c) => inBounds(c.x, c.y)
    && (state.tool === 'erase'
      ? ['object', 'building', 'ground'].some((l) => state.cells.has(layerKey(c.x, c.y, l)))
      : state.brush));
  if (!touched) return;
  beginStroke();
  for (const cell of cells) paintCell(cell.x, cell.y);
}

function fillFrom(x, y) {
  if (!state.brush) {
    toast('Pilih tile dari + dulu');
    return;
  }
  const target = state.cells.get(layerKey(x, y, state.brush.layer)) || null;
  const targetName = target ? target.name : null;
  if (target && target.layer === state.brush.layer && target.name === state.brush.name) return;

  // flood fill across empty cells is unbounded, so cap the work
  const limit = 20000;
  const queue = [[x, y]];
  const seen = new Set();
  let painted = 0;
  beginStroke();
  while (queue.length && seen.size < limit) {
    const [cx, cy] = queue.pop();
    const k = key(cx, cy);
    if (seen.has(k)) continue;
    seen.add(k);
    if (!inBounds(cx, cy)) continue;
    const cell = state.cells.get(layerKey(cx, cy, state.brush.layer)) || null;
    const same = (cell ? cell.name : null) === targetName;
    if (!same) continue;
    paintCell(cx, cy);
    painted++;
    queue.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
  }
  endStroke();
  if (!painted) state.undo.pop();      // nothing changed: do not leave a step
  if (seen.size >= limit) toast('Isi area dihentikan: terlalu luas');
  updateHistoryButtons();
}

// ------------------------------------------------------------------ tools
function setTool(tool) {
  state.tool = tool;
  const map = $('map');
  // the Geser tool is the one tool that does not draw, so the cursor says so
  map.style.cursor = tool === 'move' ? 'grab' : 'crosshair';
  updateHud();
  draw();
}

// ------------------------------------------------------------------ palette
function tilesOfTab() {
  const out = [];
  for (const [name, tile] of Object.entries(state.tileset.tiles)) {
    if (tile.layer === state.tab) out.push([name, tile]);
  }
  out.sort((a, b) => a[0].localeCompare(b[0]));
  return out;
}

function buildTabs() {
  const tabs = $('tabs');
  tabs.innerHTML = '';
  const labels = { ground: 'TANAH', object: 'OBJEK', building: 'BANGUNAN' };
  for (const layer of LAYERS) {
    const button = document.createElement('button');
    button.className = 'tab';
    button.textContent = labels[layer] || layer;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-selected', String(layer === state.tab));
    button.addEventListener('click', () => {
      state.tab = layer;
      buildTabs();
      buildPalette();
    });
    tabs.appendChild(button);
  }
}

function buildPalette() {
  const palette = $('palette');
  palette.innerHTML = '';

  const entries = tilesOfTab();
  if (!entries.length) {
    // No tiles yet is a legitimate state: the world is being rebuilt from
    // scratch. Say what to do instead of showing an empty white panel.
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = state.atlas
      ? 'Belum ada tile di lapisan ini. Tambahkan lewat tools/tileset/build.py, '
        + 'lalu muat ulang halaman.'
      : 'Atlas tileset belum termuat.';
    palette.appendChild(empty);
    return;
  }

  for (const [name, tile] of entries) {
    const cell = document.createElement('button');
    cell.className = 'cell';
    cell.type = 'button';
    cell.setAttribute('aria-pressed', String(state.brush && state.brush.name === name));

    const canvas = document.createElement('canvas');
    canvas.width = 48;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    if (state.atlas) {
      // 3x so a 16px tile is readable while picking
      ctx.drawImage(state.atlas, tile.x, tile.y, tile.w, tile.h, 0, 0, 48, 48);
    }
    cell.appendChild(canvas);

    const label = document.createElement('span');
    label.textContent = name.replace(/_/g, ' ');
    cell.appendChild(label);

    if (tile.solid) {
      const tag = document.createElement('span');
      tag.className = 'tag';
      tag.textContent = 'solid';
      cell.appendChild(tag);
    }

    cell.addEventListener('click', () => {
      state.brush = { name, layer: tile.layer, solid: tile.solid };
      buildPalette();
      showBrush();
    });
    cell.addEventListener('mouseenter', () => {
      $('drawer-info').textContent = `${name} · ${tile.w}x${tile.h} px · ${tile.solid ? 'tidak bisa dilewati' : 'bisa dilewati'}`;
    });

    palette.appendChild(cell);
  }
}

function showBrush() {
  if (!state.brush) return;
  $('drawer-info').textContent = `Kuas: ${state.brush.name}`;
  updateHud();
}

// ------------------------------------------------------------------ hud
const TOOL_LABEL = { pencil: 'Pensil', erase: 'Hapus', pick: 'Ambil', fill: 'Isi', move: 'Geser' };

function updateHud() {
  $('hud-tool').textContent = TOOL_LABEL[state.tool] + (state.brush ? ` · ${state.brush.name}` : '');
  $('hud-brush').textContent = `kuas ${state.brushSize}×${state.brushSize}`;
  $('hud-cell').textContent = `${state.hover.x}, ${state.hover.y}`;
  $('hud-size').textContent =
    `${state.cols}×${state.rows} sel · ${state.cells.size} terpakai · ${cellSize()} px`;
  $('hud-frame').textContent = `bingkai ${FRAME_MAP.w}×${FRAME_MAP.h} sel`;
  $('zoom-value').textContent = `${state.zoom}×`;
  if ($('size-value')) $('size-value').textContent = String(state.brushSize);
  for (const id of ['pencil', 'erase', 'pick', 'fill', 'move']) {
    const button = $('tool-' + id);
    if (!button) continue;
    const on = state.tool === id;
    button.classList.toggle('active', on);
    // aria-pressed, so the active tool is not conveyed by colour alone
    button.setAttribute('aria-pressed', String(on));
  }
  updateHistoryButtons();
}

/** Steps the zoom by one and keeps the point under (atX, atY) fixed. */
function zoomTo(step, atX, atY) {
  const next = ZOOM_STEPS[Math.max(0, Math.min(ZOOM_STEPS.length - 1, step))];
  if (next === state.zoom) return false;
  const cx = atX === undefined ? window.innerWidth / 2 : atX;
  const cy = atY === undefined ? window.innerHeight / 2 : atY;
  const before = screenToCell(cx, cy);
  state.zoom = next;
  state.camera.x = before.x * cellSize() - cx;
  state.camera.y = before.y * cellSize() - cy;
  return true;
}

function zoomIn(atX, atY) {
  return zoomTo(ZOOM_STEPS.indexOf(state.zoom) + 1, atX, atY);
}

function zoomOut(atX, atY) {
  return zoomTo(ZOOM_STEPS.indexOf(state.zoom) - 1, atX, atY);
}

// ------------------------------------------------------------------ drawer
function toggleDrawer(force) {
  const drawer = $('drawer');
  const open = force === undefined ? drawer.hidden : force;
  drawer.hidden = !open;
  $('add').setAttribute('aria-expanded', String(open));
  if (open) buildPalette();
}

// ------------------------------------------------------------------ persistence
async function save() {
  // group the per-layer keys back into one cell object per position
  const cells = {};
  for (const [k, cell] of state.cells) {
    if (!cell || !cell.name || !state.tileset.tiles[cell.name]) continue;
    const xy = k.split('|')[0];
    (cells[xy] = cells[xy] || {})[cell.layer || 'object'] = cell.name;
  }
  const cellsArr = Object.entries(cells);
  if (!cellsArr.length && !confirm('Peta kosong. Tetap simpan?')) return;

  const document = {
    version: 1,
    tile: TILE,
    cols: state.cols,
    rows: state.rows,
    // The game reads this too, so the spawn has to survive a round trip. It
    // is the cell the editor opens on, and the only place the player may
    // start: without it the game falls back to its own default.
    spawn: state.spawn || { x: Math.floor(state.cols / 2), y: Math.floor(state.rows / 2) },
    cells: Object.fromEntries(cellsArr),
  };

  try {
    const response = await fetch('/api/map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(document),
    });
    const result = await response.json();
    if (!result.ok) {
      toast(`Gagal: ${result.error}`);
      return;
    }
    // The game loads the map from the app assets, not from the editor's
    // working file: publishing is what makes "Mode gameplay" show this map.
    const published = await fetch('/api/publish', { method: 'POST' });
    const report = await published.json();
    toast(report.ok
      ? `Tersimpan & dipakai game (${cellsArr.length} sel)`
      : `Tersimpan, tapi game gagal dimuat: ${report.error}`);
  } catch (error) {
    toast('Gagal menyimpan: ' + error.message);
  }
}

async function loadMap() {
  try {
    const response = await fetch('/docs/tileset/map.json', { cache: 'no-store' });
    if (!response.ok) return;
    const doc = await response.json();
    state.loadedMap = true;
    state.cols = doc.cols || DEFAULT_COLS;
    state.rows = doc.rows || DEFAULT_ROWS;
    state.spawn = doc.spawn || null;
    state.cells.clear();
    for (const [xy, value] of Object.entries(doc.cells || {})) {
      // current format: {ground,object,building}; older files: one {name,layer}
      if (value && typeof value.name === 'string') {
        if (state.tileset.tiles[value.name]) {
          state.cells.set(layerKey(...xy.split(',').map(Number), value.layer || 'object'), { ...value });
        }
        continue;
      }
      if (!value) continue;
      const [cx, cy] = xy.split(',').map(Number);
      for (const layer of LAYERS) {
        const name = value[layer];
        if (!name || !state.tileset.tiles[name]) continue;
        // layerKey(x, y, layer): the layer has to be the third argument, not
        // the last item of a spread, or every cell is stored under the wrong key
        // and the map loads "successfully" as empty.
        state.cells.set(layerKey(cx, cy, layer),
          { name, layer, solid: !!state.tileset.tiles[name].solid });
      }
    }
    toast(`Peta dimuat (${state.cells.size} sel)`);
  } catch {
    /* no saved map yet: start from the default sheet */
  }
}

/**
 * A blank sheet for a first run, and nothing at all for a loaded map.
 *
 * It used to fill the map with grass on first run. That hid a real question
 * ("what is the world made of?") behind a default nobody chose, and it made an
 * empty map impossible to author on purpose.
 *
 * It also used to clear the cells unconditionally, which ran right after
 * loadMap() and quietly threw away every saved cell: the editor opened on an
 * empty map whether or not one had been drawn. The guard is the whole function
 * now: a map that was loaded, or that the user deliberately made blank, is
 * never touched.
 */
function seedIfEmpty() {
  if (state.loadedMap) return;      // a loaded map is the map, not a default
  state.cells.clear();
  state.spawn = null;
}

/**
 * Starts a new, empty map at a chosen size.
 *
 * Size is asked for rather than guessed: a map that is too small to hold the
 * gameplay frame (16x10 cells) cannot be explored, and that is worth saying out
 * loud instead of letting the paint tools silently refuse.
 */
function newMap() {
  const minCols = FRAME_MAP.w;
  const minRows = FRAME_MAP.h;
  const colsText = window.prompt('Lebar peta (sel, 16 px per sel):', String(state.cols));
  if (colsText === null) return;
  const rowsText = window.prompt('Tinggi peta (sel):', String(state.rows));
  if (rowsText === null) return;

  const cols = Math.round(Number(colsText));
  const rows = Math.round(Number(rowsText));
  if (!Number.isFinite(cols) || !Number.isFinite(rows) || cols < 1 || rows < 1) {
    toast('Ukuran tidak valid');
    return;
  }
  if (cols < minCols || rows < minRows) {
    toast(`Terlalu kecil: minimal ${minCols}x${minRows} sel agar bingkai gameplay muat`);
    return;
  }
  if (state.cells.size && !window.confirm('Buang semua sel dan mulai peta baru?')) return;

  remember();                 // a new map is undoable too
  state.cols = cols;
  state.rows = rows;
  state.cells.clear();
  state.spawn = { x: Math.floor(cols / 2), y: Math.floor(rows / 2) };
  state.loadedMap = true;      // a deliberate blank map must not be re-seeded
  fitToScreen();
  draw();
  updateHud();
  toast(`Peta baru ${cols}x${rows} sel — kosong`);
}

/** True when the cell is on the map; painting outside it is a no-op. */
function inBounds(x, y) {
  return x >= 0 && y >= 0 && x < state.cols && y < state.rows;
}

// ------------------------------------------------------------------ input
function mapExtent() {
  return { minX: 0, minY: 0, maxX: state.cols - 1, maxY: state.rows - 1 };
}

/** Frames the map so the grid fills the window at an exact 16px cell if it can. */
function fitToScreen() {
  const { minX, minY, maxX, maxY } = mapExtent();
  const cols = maxX - minX + 1;
  const rows = maxY - minY + 1;
  const fit = Math.min(window.innerWidth / (cols * TILE),
                       window.innerHeight / (rows * TILE));
  // The grid exists to be edited at 16x16 px. If the whole map fits in the
  // window at 1:1, that is the answer; only zoom in when it would otherwise be
  // unreadably small, and only zoom out when the map does not fit.
  let zoom;
  if (fit >= 1) {
    zoom = 1;                                    // 1:1: one cell is 16x16 px
  } else {
    // not enough room: smallest step that still covers the window
    const covering = ZOOM_STEPS.filter((step) => step >= fit);
    zoom = covering.length ? covering[0] : ZOOM_STEPS[ZOOM_STEPS.length - 1];
  }
  state.zoom = zoom;
  const size = cellSize();
  state.camera.x = minX * size - (window.innerWidth - cols * size) / 2;
  state.camera.y = minY * size - (window.innerHeight - rows * size) / 2;
}

/** Shrinks the view until the window is the grid: cells are exactly TILE px. */
function zoomToActual() {
  // 1:1 with the tablet panel: 16px cells, scrolled to the top-left.
  state.zoom = 1;
  state.camera.x = 0;
  state.camera.y = 0;
}

function bindCanvas() {
  const canvas = $('map');

  canvas.addEventListener('pointermove', (event) => {
    // Geser is the move tool: one finger drags the map, like a hand tool. It is
    // a tool rather than a gesture so that a stroke can never pan by accident,
    // and so that a touch screen needs no second finger to scroll.
    if (state.panning && state.panFrom) {
      state.camera.x = state.panFrom.cx - (event.clientX - state.panFrom.x);
      state.camera.y = state.panFrom.cy - (event.clientY - state.panFrom.y);
      draw();
      return;
    }

    const cell = screenToCell(event.clientX, event.clientY);
    if (cell.x !== state.hover.x || cell.y !== state.hover.y) {
      state.hover = cell;
      updateHud();
      draw();
    }
    if (state.painting) paintAt(cell.x, cell.y);
  });

  canvas.addEventListener('pointerdown', (event) => {
    canvas.setPointerCapture(event.pointerId);

    // middle mouse, right mouse or alt-drag pans without leaving the tool
    if (event.button === 1 || event.button === 2 || event.altKey || state.tool === 'move') {
      state.panning = true;
      state.panFrom = {
        x: event.clientX, y: event.clientY,
        cx: state.camera.x, cy: state.camera.y,
      };
      canvas.style.cursor = 'grabbing';
      return;
    }

    const cell = screenToCell(event.clientX, event.clientY);
    state.hover = cell;
    if (state.tool === 'fill') {
      state.strokeOpen = false;
      fillFrom(cell.x, cell.y);
    } else {
      state.painting = true;
      state.strokeOpen = false;    // a press always starts a new undo step
      paintAt(cell.x, cell.y);
    }
    draw();
    updateHud();
  });

  const stop = () => {
    state.painting = false;
    state.panning = false;
    state.panFrom = null;
    endStroke();
    canvas.style.cursor = state.tool === 'move' ? 'grab' : 'crosshair';
  };
  canvas.addEventListener('pointerup', stop);
  canvas.addEventListener('pointercancel', stop);
  canvas.addEventListener('pointerleave', () => { state.hover = { x: -1, y: -1 }; });

  // right click never opens a menu: it is a pan gesture here
  canvas.addEventListener('contextmenu', (event) => event.preventDefault());

  // zoom with the wheel, anchored at the cursor. ctrl+wheel is the trackpad
  // pinch gesture, which browsers report as a wheel event.
  canvas.addEventListener('wheel', (event) => {
    event.preventDefault();
    const changed = event.deltaY < 0
      ? zoomIn(event.clientX, event.clientY)
      : zoomOut(event.clientX, event.clientY);
    if (changed) { draw(); updateHud(); }
  }, { passive: false });
}

function bindKeys() {
  window.addEventListener('keydown', (event) => {
    if (event.target instanceof HTMLInputElement) return;
    const k = event.key.toLowerCase();

    // undo/redo first: ctrl+z must not fall through to a tool shortcut
    if ((event.ctrlKey || event.metaKey) && k === 'z' && !event.shiftKey) {
      event.preventDefault();
      undo();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && (k === 'y' || (k === 'z' && event.shiftKey))) {
      event.preventDefault();
      redo();
      return;
    }

    if (k === 'escape') { toggleDrawer(false); return; }
    if (k === 'b') { setTool('pencil'); return; }
    if (k === 'e') { setTool('erase'); return; }
    if (k === 'i') { setTool('pick'); return; }
    if (k === 'g') { setTool('fill'); return; }
    if (k === 'v') { setTool('move'); return; }
    if (k === 'f') { fitToScreen(); draw(); updateHud(); return; }
    if (k === '1') { zoomToActual(); draw(); updateHud(); return; }
    if (k === 'n') { newMap(); return; }
    if (k === '[') { brushDown(); return; }
    if (k === ']') { brushUp(); return; }
    // + and - already work on most layouts; the zoom buttons carry the same
    // actions for touch, where there is no keyboard at all.
    if (k === '=' || k === '+') { if (zoomIn()) { draw(); updateHud(); } return; }
    if (k === '-' || k === '_') { if (zoomOut()) { draw(); updateHud(); } return; }
    if (k === 's') {
      // Plain "s" as well as ctrl+s: the bar has a visible Simpan button, and a
      // button you can see should have a key you can press.
      event.preventDefault();
      save();
      return;
    }

    // pan with the keyboard
    const step = cellSize();
    if (k === 'arrowleft' || k === 'a') state.camera.x -= step;
    else if (k === 'arrowright' || k === 'd') state.camera.x += step;
    else if (k === 'arrowup' || k === 'w') state.camera.y -= step;
    else if (k === 'arrowdown') state.camera.y += step;
    else return;
    event.preventDefault();
    draw();
  });
}

function bindChrome() {
  $('tool-pencil').addEventListener('click', () => setTool('pencil'));
  $('tool-erase').addEventListener('click', () => setTool('erase'));
  $('tool-pick').addEventListener('click', () => setTool('pick'));
  $('tool-fill').addEventListener('click', () => setTool('fill'));
  $('tool-move').addEventListener('click', () => setTool('move'));
  $('undo').addEventListener('click', () => undo());
  $('redo').addEventListener('click', () => redo());
  $('size-up').addEventListener('click', () => brushUp());
  $('size-down').addEventListener('click', () => brushDown());
  $('add').addEventListener('click', () => toggleDrawer());
  $('close').addEventListener('click', () => toggleDrawer(false));
  $('save').addEventListener('click', () => save());
  $('new').addEventListener('click', () => newMap());
  $('view-in').addEventListener('click', () => { if (zoomIn()) { draw(); updateHud(); } });
  $('view-out').addEventListener('click', () => { if (zoomOut()) { draw(); updateHud(); } });
  $('view-zoom').addEventListener('click', () => { zoomToActual(); draw(); updateHud(); });
  $('view-fit').addEventListener('click', () => { fitToScreen(); draw(); updateHud(); });

  window.addEventListener('resize', () => { draw(); updateHud(); });
  window.addEventListener('beforeunload', () => { /* no silent writes */ });
}

// ------------------------------------------------------------------ boot
async function boot() {
  const [indexResponse, atlas] = await Promise.all([
    fetch('/docs/tileset/tileset.json', { cache: 'no-store' }),
    new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = '/docs/tileset/johto-tileset.png';
    }),
  ]);
  if (!indexResponse.ok) throw new Error('tileset.json tidak ditemukan');
  state.tileset = await indexResponse.json();
  state.atlas = atlas;

  await loadMap();
  seedIfEmpty();
  fitToScreen();

  buildTabs();
  buildPalette();
  bindChrome();
  bindCanvas();
  bindKeys();
  updateHud();
  draw();
}

boot().catch((error) => {
  document.body.innerHTML =
    `<pre style="padding:24px;color:#fbf3dc;font:14px monospace">Gagal memuat editor:\n${error.message}</pre>`;
});
