/* Johto map editor.
 *
 * The map is a grid of 16x16 cells. The canvas fills the whole window, so the
 * grid always covers the screen; the view scrolls with WASD, arrows, middle
 * drag or space drag. Cells outside the map are simply empty, which lets the
 * map grow as it is painted.
 *
 * Tools: pencil, eraser, picker, area fill. The + button opens the tileset.
 */
'use strict';

const TILE = 16;                 // one grid cell, in map pixels
const ZOOM_STEPS = [0.5, 1, 2, 3, 4, 6];   // 1 = exactly 16x16 px per cell
// The map is exactly the tablet panel at 1:1: 2560x1600 / 16 = 160x100 cells.
// That is why the grid "fills the screen": on the device it lines up pixel for
// pixel, and in a smaller browser window it simply zooms out to fit.
const DEFAULT_COLS = 160;
const DEFAULT_ROWS = 100;
const LAYERS = ['ground', 'building', 'object'];   // paint order: top layer drawn last

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
  cells: new Map(),     // "x,y" -> { name, layer, solid } | null
  camera: { x: 0, y: 0 },   // top-left of the view, in map pixels
  zoom: 1,          // 1 = one cell is exactly 16x16 screen pixels
  tool: 'pencil',
  brush: null,          // { name, layer, solid }
  tab: 'ground',
  hover: { x: 0, y: 0 },
  loadedMap: false,     // a saved map wins over the seeded lawn
  cols: DEFAULT_COLS,
  rows: DEFAULT_ROWS,
  painting: false,
  panning: false,
  panFrom: null,
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

  // backdrop: the empty field beyond the map edge
  ctx.fillStyle = '#5c7a45';
  ctx.fillRect(0, 0, w, h);

  const size = cellSize();
  const { x0, y0, x1, y1 } = visibleRange();

  // ground first, then objects, then buildings: same order as tileset.json
  for (const layer of LAYERS) {
    for (let y = y0; y <= y1; y++) {
      for (let x = x0; x <= x1; x++) {
        const cell = state.cells.get(layerKey(x, y, layer));
        if (!cell) continue;
        drawTile(ctx, cell.name, x * size - state.camera.x, y * size - state.camera.y, size);
      }
    }
  }

  drawGrid(ctx, w, h, size, x0, y0, x1, y1);
  drawCursor(ctx, size);
}

function drawTile(ctx, name, px, py, size) {
  const tile = state.tileset.tiles[name];
  if (!tile || !state.atlas) return;
  // A 2x2 piece (the tree) must cover four cells, not be squashed into one.
  // Its own w/h say how many cells it spans.
  ctx.drawImage(
    state.atlas,
    tile.x, tile.y, tile.w, tile.h,                                  // source rect
    px, py, (tile.w / TILE) * size, (tile.h / TILE) * size,          // destination
  );
}

function drawGrid(ctx, w, h, size, x0, y0, x1, y1) {
  // A faint grid only when a cell is big enough to see it; at zoom 1 it would
  // read as noise over the art.
  if (size < 24) return;
  ctx.save();
  ctx.strokeStyle = 'rgba(59, 47, 30, .13)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  const startX = (0 - state.camera.x % size + size) % size;
  const startY = (0 - state.camera.y % size + size) % size;
  for (let px = startX; px < w; px += size) {
    ctx.moveTo(Math.round(px) + .5, 0);
    ctx.lineTo(Math.round(px) + .5, h);
  }
  for (let py = startY; py < h; py += size) {
    ctx.moveTo(0, Math.round(py) + .5);
    ctx.lineTo(w, Math.round(py) + .5);
  }
  ctx.stroke();
  ctx.restore();
}

function drawCursor(ctx, size) {
  const { x, y } = state.hover;
  const px = x * size - state.camera.x;
  const py = y * size - state.camera.y;
  if (px < -size || py < -size) return;
  ctx.save();
  ctx.lineWidth = 2;
  ctx.strokeStyle = 'rgba(251, 243, 220, .95)';
  ctx.strokeRect(px + 1, py + 1, size - 2, size - 2);
  ctx.strokeStyle = 'rgba(59, 47, 30, .85)';
  ctx.strokeRect(px - .5, py - .5, size + 1, size + 1);
  ctx.restore();
}

// ------------------------------------------------------------------ editing
function paintAt(x, y) {
  if (!inBounds(x, y)) return;      // the map has a fixed edge
  if (state.tool === 'erase') {
    // Remove one layer, topmost first: deleting a tree keeps the lawn under it,
    // and a second erase on the same cell removes the lawn itself.
    for (const layer of ['object', 'building', 'ground']) {
      if (state.cells.delete(layerKey(x, y, layer))) return;
    }
    return;
  }
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
  if (!state.brush) {
    toast('Pilih tile dari + dulu');
    return;
  }
  // one tile per layer: painting ground under a tree keeps the tree
  state.cells.set(layerKey(x, y, state.brush.layer), { ...state.brush });
}

function fillFrom(x, y) {
  const target = state.brush
    ? state.cells.get(layerKey(x, y, state.brush.layer)) || null
    : null;
  const targetName = target ? target.name : null;
  if (!state.brush) {
    toast('Pilih tile dari + dulu');
    return;
  }
  if (target && target.layer === state.brush.layer && target.name === state.brush.name) return;

  // flood fill across empty cells is unbounded, so cap the work
  const limit = 20000;
  const queue = [[x, y]];
  const seen = new Set();
  while (queue.length && seen.size < limit) {
    const [cx, cy] = queue.pop();
    const k = key(cx, cy);
    if (seen.has(k)) continue;
    seen.add(k);
    if (!inBounds(cx, cy)) continue;
    const cell = state.cells.get(layerKey(cx, cy, state.brush.layer)) || null;
    const same = (cell ? cell.name : null) === targetName;
    if (!same) continue;
    paintAt(cx, cy);
    queue.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
  }
  if (seen.size >= limit) toast('Isi area dihentikan: terlalu luas');
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
  for (const [name, tile] of tilesOfTab()) {
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
const TOOL_LABEL = { pencil: 'Pensil', erase: 'Hapus', pick: 'Ambil', fill: 'Isi' };

function updateHud() {
  $('hud-tool').textContent = TOOL_LABEL[state.tool] + (state.brush ? ` · ${state.brush.name}` : '');
  $('hud-cell').textContent = `${state.hover.x}, ${state.hover.y}`;
  $('hud-size').textContent = `${state.cells.size} sel · ${cellSize()}×${cellSize()} px · zoom ${state.zoom}x`;
  for (const id of ['pencil', 'erase', 'pick', 'fill']) {
    $('tool-' + id).classList.toggle('active', state.tool === id);
  }
}

function setTool(tool) {
  state.tool = tool;
  updateHud();
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

  try {
    const response = await fetch('/api/map', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        version: 1,
        tile: TILE,
        cols: state.cols,
        rows: state.rows,
        cells: Object.fromEntries(cellsArr),
      }),
    });
    const result = await response.json();
    toast(result.ok ? `Tersimpan (${cellsArr.length} sel)` : `Gagal: ${result.error}`);
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
      for (const layer of LAYERS) {
        const name = value[layer];
        if (!name || !state.tileset.tiles[name]) continue;
        state.cells.set(layerKey(...xy.split(',').map(Number), layer),
          { name, layer, solid: !!state.tileset.tiles[name].solid });
      }
    }
    toast(`Peta dimuat (${state.cells.size} sel)`);
  } catch {
    /* no saved map yet: start from the default lawn */
  }
}

function seedIfEmpty() {
  if (state.cells.size || state.loadedMap) return;
  for (let y = 0; y < state.rows; y++) {
    for (let x = 0; x < state.cols; x++) {
      state.cells.set(layerKey(x, y, 'ground'), { name: 'grass', layer: 'ground', solid: false });
    }
  }
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

    // middle mouse, or space held, pans the map
    if (event.button === 1 || event.button === 2 || event.altKey) {
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
      fillFrom(cell.x, cell.y);
    } else {
      state.painting = true;
      paintAt(cell.x, cell.y);
    }
    draw();
    updateHud();
  });

  const stop = () => {
    state.painting = false;
    state.panning = false;
    state.panFrom = null;
    $('map').style.cursor = 'crosshair';
  };
  canvas.addEventListener('pointerup', stop);
  canvas.addEventListener('pointercancel', stop);
  canvas.addEventListener('pointerleave', () => { state.hover = { x: -1, y: -1 }; });

  // right click never opens a menu: it is a pan gesture here
  canvas.addEventListener('contextmenu', (event) => event.preventDefault());

  // zoom with the wheel, anchored at the cursor
  canvas.addEventListener('wheel', (event) => {
    event.preventDefault();
    const before = screenToCell(event.clientX, event.clientY);
    const index = ZOOM_STEPS.indexOf(state.zoom);
    const next = ZOOM_STEPS[Math.min(ZOOM_STEPS.length - 1,
      Math.max(0, index + (event.deltaY < 0 ? 1 : -1)))];
    if (next === state.zoom) return;
    state.zoom = next;
    state.camera.x = before.x * cellSize() - event.clientX;
    state.camera.y = before.y * cellSize() - event.clientY;
    draw();
    updateHud();
  }, { passive: false });
}

function bindKeys() {
  window.addEventListener('keydown', (event) => {
    if (event.target instanceof HTMLInputElement) return;
    const k = event.key.toLowerCase();

    if (k === 'escape') { toggleDrawer(false); return; }
    if (k === 'b') { setTool('pencil'); return; }
    if (k === 'e') { setTool('erase'); return; }
    if (k === 'i') { setTool('pick'); return; }
    if (k === 'g') { setTool('fill'); return; }
    if (k === '+') { toggleDrawer(); return; }
    if (k === 'f') { fitToScreen(); draw(); updateHud(); return; }
    if (k === '1') { zoomToActual(); draw(); updateHud(); return; }
    if (k === 's' && (event.ctrlKey || event.metaKey)) {
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
  $('add').addEventListener('click', () => toggleDrawer());
  $('close').addEventListener('click', () => toggleDrawer(false));
  $('view-fit').addEventListener('click', () => { fitToScreen(); draw(); updateHud(); });
  $('view-1x').addEventListener('click', () => { zoomToActual(); draw(); updateHud(); });

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
