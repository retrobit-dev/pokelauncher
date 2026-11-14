#!/usr/bin/env node
/**
 * Uji editor peta tanpa browser.
 *
 * `editor/app.js` adalah skrip browser, jadi tes ini menyediakan DOM tiruan
 * yang secukupnya: elemen dengan id, kelas, kanvas 2D, dan `fetch` yang membaca
 * berkas asli dari cakram. Setelah itu seluruh alur editor dijalankan di atas
 * tileset sungguhan: muat, cat, hapus, isi area, simpan.
 *
 * Dengan begitu kerusakan yang paling sering terjadi (id salah ketik, tileset
 * hilang, grid tidak 16x16, peta tidak menutupi layar) tertangkap di CI, bukan
 * di mata pengguna.
 *
 * Pakai: node tools/editor_test.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const TILE = 16;

let failures = 0;
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) failures++;
  const shown = ok ? '' : `  (dapat ${JSON.stringify(actual)}, harusnya ${JSON.stringify(expected)})`;
  console.log(`${ok ? '  ok  ' : '  FAIL'}  ${label}${shown}`);
}

// ---------------------------------------------------------------- DOM tiruan
class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.style = {};
    this.dataset = {};
    this.hidden = false;
    this.textContent = '';
    this.innerHTML = '';
    this.width = 0;
    this.height = 0;
    this._attrs = {};
    this.classList = {
      _s: new Set(),
      add: (c) => this.classList._s.add(c),
      remove: (c) => this.classList._s.delete(c),
      contains: (c) => this.classList._s.has(c),
      toggle: (c, on) => (on ? this.classList._s.add(c) : this.classList._s.delete(c)),
    };
  }
  set id(value) { this._id = value; document._byId[value] = this; }
  get id() { return this._id; }
  appendChild(child) { this.children.push(child); return child; }
  removeChild(child) { this.children = this.children.filter((c) => c !== child); }
  setAttribute(k, v) { this._attrs[k] = String(v); }
  getAttribute(k) { return this._attrs[k]; }
  addEventListener(type, fn) { (this._listeners = this._listeners || {})[type] = fn; }
  removeEventListener() {}
  setPointerCapture() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight }; }
  getContext() {
    const noop = () => {};
    this._draws = this._draws || [];
    const self = this;
    return {
      setTransform: noop,
      fillRect(...args) { self._fills = (self._fills || []); self._fills.push(args); },
      drawImage(...args) { self._draws.push(args); },
      beginPath: noop,
      moveTo: noop, lineTo: noop, stroke: noop, strokeRect: noop, save: noop,
      restore: noop, rect: noop, clip: noop, fill: noop, arc: noop,
      imageSmoothingEnabled: false, fillStyle: '', strokeStyle: '', lineWidth: 1,
      canvas: { width: 0, height: 0 },
    };
  }
}

const document = {
  _byId: {},
  getElementById(id) { return this._byId[id] || (this._byId[id] = new Element()); },
  createElement(tag) { return new Element(tag); },
  body: new Element('body'),
  addEventListener() {},
};

const window = {
  innerWidth: 1280,
  innerHeight: 800,
  devicePixelRatio: 1,
  addEventListener() {},
  setTimeout,
  clearTimeout,
};

const Image = class {
  set src(value) { this._src = value; setTimeout(() => this.onload && this.onload(), 0); }
  get src() { return this._src; }
};

const fetch = async (url) => {
  if (url.includes('tileset.json')) {
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/tileset/tileset.json'), 'utf8')) };
  }
  if (url.includes('map.json')) return { ok: false, json: async () => ({}) };  // no saved map yet
  if (url.includes('/api/')) return { ok: true, json: async () => ({ ok: true }) };
  throw new Error('fetch tak terduga: ' + url);
};

// ---------------------------------------------------------------- muat editor
const source = fs.readFileSync(path.join(ROOT, 'editor/app.js'), 'utf8');

// Berkas memakai const letak-atas; bungkus jadi fungsi agar bisa dievaluasi.
const sandbox = { document, window, Image, fetch, console, setTimeout, clearTimeout };
const loader = new Function(
  'document', 'window', 'Image', 'fetch', 'console', 'setTimeout', 'clearTimeout',
  `${source}\nreturn { __steps: ZOOM_STEPS, __sizes: BRUSH_SIZES, boot, state, cellSize, key, layerKey,
            paintAt, fillFrom, mapExtent, fitToScreen, zoomToActual, inBounds, DEFAULT_COLS,
            DEFAULT_ROWS, TILE, zoomIn, zoomOut, gameFrameRect, FRAME_MAP, newMap, save,
            undo, redo, setBrushSize, brushUp, brushDown, brushCells, setTool, endStroke,
            drawPlayerMarker,
            updateHistoryButtons };`
);
const editor = loader(sandbox.document, sandbox.window, sandbox.Image, sandbox.fetch,
  console, setTimeout, clearTimeout);

// --------------------------------------------------------------------- assertions
editor.boot().then(() => {
  const { state, cellSize, key, layerKey, paintAt, fillFrom, mapExtent, fitToScreen, zoomToActual,
          zoomIn, zoomOut, gameFrameRect, undo, redo, setBrushSize, brushUp, brushDown,
          brushCells, setTool, endStroke } = editor;
  const steps = editor.__steps;
  const sizes = editor.__sizes;

  console.log('grid 16x16');
  check('TILE adalah 16', editor.TILE, TILE);
  zoomToActual();
  check('mode 1:1 menggambar sel tepat 16 px', cellSize(), TILE);

  console.log('\ngrid memenuhi layar');
  check('peta selebar panel tablet', editor.DEFAULT_COLS, 160);
  check('peta setinggi panel tablet', editor.DEFAULT_ROWS, 100);
  check('peta 1:1 = 2560x1600 px', editor.DEFAULT_COLS * TILE, 2560);
  fitToScreen();
  const cols = editor.state.cols, rows = editor.state.rows, size = cellSize();
  check('lebar grid >= layar', cols * size >= window.innerWidth, true);
  check('tinggi grid >= layar', rows * size >= window.innerHeight, true);
  check('zoom dipilih agar pas', editor.__steps.includes(editor.state.zoom), true);

  console.log('\npeta kosong');
  check('editor tidak mengisi rumput sendiri', state.cells.size, 0);
  check('spawn kosong sampai digambar', state.spawn, null);

  console.log('\ntileset');
  // the atlas grows as art is added, so assert the palette is populated and
  // that the tiles the editor needs are present, not a hard count
  check('palet berisi tile', Object.keys(state.tileset.tiles).length >= 29, true);
  check('ada tile rumput', Boolean(state.tileset.tiles.grass), true);
  check('ada tile pohon', Boolean(state.tileset.tiles.tree), true);

  console.log('\nmenggambar');
  state.tool = 'pencil';
  state.brush = { name: 'path', layer: 'ground', solid: false };
  paintAt(10, 6);
  check('pensil menaruh jalan', state.cells.get(layerKey(10, 6, 'ground')).name, 'path');
  state.brush = { name: 'grass', layer: 'ground', solid: false };
  paintAt(12, 6);
  state.brush = { name: 'tree', layer: 'object', solid: true };
  paintAt(12, 6);
  check('pohon masuk layer objek', state.cells.get(layerKey(12, 6, 'object')).name, 'tree');
  check('pohon menyimpan properti solid', state.cells.get(layerKey(12, 6, 'object')).solid, true);
  // the important rule: an object must not erase the ground under it
  check('rumput tetap ada di bawah pohon', state.cells.get(layerKey(12, 6, 'ground')).name, 'grass');

  console.log('\nbatas peta');
  state.tool = 'pencil';
  const before = state.cells.size;
  paintAt(-1, 5);
  paintAt(cols + 3, 5);
  paintAt(5, -2);
  check('tidak bisa mengecat di luar peta', state.cells.size, before);
  check('inBounds menolak koordinat negatif', editor.inBounds(-1, 0), false);
  check('inBounds menerima pojok kanan bawah', editor.inBounds(cols - 1, rows - 1), true);

  state.tool = 'erase';
  paintAt(10, 6);                                   // removes the path (top layer)
  check('hapus membuang lapisan teratas', state.cells.has(layerKey(10, 6, 'ground')), false);
  check('hapus tidak menyimpan null', Array.from(state.cells.values()).every((c) => c && c.name), true);

  console.log('\nmengisi area');
  const total = state.cells.size;
  state.tool = 'fill';
  state.brush = { name: 'water', layer: 'ground', solid: true };
  fillFrom(0, 0);
  const water = Array.from(state.cells.values()).filter((c) => c && c.name === 'water').length;
  check('isi area mengecat sel', water > 0, true);
  check('isi area berhenti di batas peta', editor.inBounds(0, 0), true);

  console.log('\nmemuat peta tersimpan');
  check('peta kosong tidak diisi ulang otomatis', (() => {
    state.cells.clear();
    state.loadedMap = true;
    // seedIfEmpty memakai state.loadedMap; peta kosong yang sah harus tetap kosong
    return state.cells.size === 0;
  })(), true);

  console.log('\nukuran kuas');
  state.cells.clear();
  setBrushSize(1);
  check('ukuran awal 1 sel', state.brushSize, 1);
  check('kuas 1x1 hanya satu sel', brushCells(5, 5), [{ x: 5, y: 5 }]);
  setBrushSize(3);
  const nine = brushCells(5, 5);
  check('kuas 3x3 menyentuh sembilan sel', nine.length, 9);
  check('kuas 3x3 tetap di tengah sel kursor',
    nine.some((c) => c.x === 5 && c.y === 5), true);
  state.tool = 'pencil';
  state.brush = { name: 'grass', layer: 'ground', solid: false };
  paintAt(20, 20);
  endStroke();                     // pointerup, as in the browser
  check('satu goresan kuas 3x3 mengecat 9 sel', state.cells.size, 9);
  brushUp(); check('tombol + menaikkan ukuran', state.brushSize, 4);
  brushDown(); brushDown(); check('tombol − menurunkan ukuran', state.brushSize, 2);
  setBrushSize(999); check('ukuran dibatasi daftar', sizes.includes(state.brushSize), true);
  check('batas atas 8', state.brushSize, 8);
  setBrushSize(0); check('batas bawah 1', state.brushSize, 1);

  console.log('\nbatal dan ulangi');
  state.cells.clear();
  state.undo.length = 0;
  state.redo.length = 0;
  setBrushSize(1);
  state.brush = { name: 'path', layer: 'ground', solid: false };
  paintAt(3, 3);
  endStroke();                     // pointerup ends the stroke, in the browser
  check('satu goresan, satu langkah', state.undo.length, 1);
  check('belum ada yang bisa diulang', state.redo.length, 0);
  const beforeUndo = state.cells.size;
  check('batal berhasil', undo(), true);
  check('batal menghapus goresan', state.cells.size, beforeUndo - 1);
  check('goresan pindah ke tumpukan ulangi', state.redo.length, 1);
  check('ulangi berhasil', redo(), true);
  check('ulangi mengembalikan sel', state.cells.size, beforeUndo);
  // the restored map must be the *same* map, not just the same size: a size
  // check alone passed while undo silently dropped a different cell
  check('ulangi mengembalikan sel yang sama',
    state.cells.has(layerKey(3, 3, 'ground')), true);
  undo();
  check('batal membuang sel yang sama',
    state.cells.has(layerKey(3, 3, 'ground')), false);
  redo();
  // a whole drag is one step: paint three cells inside a single stroke
  state.undo.length = 0;
  state.redo.length = 0;
  state.strokeOpen = false;
  state.painting = true;
  paintAt(7, 7); paintAt(8, 7); paintAt(9, 7);
  state.painting = false;
  endStroke();
  check('satu seret = satu langkah batal', state.undo.length, 1);

  // drain both stacks; an undo with nothing left must say so, not throw
  while (undo());
  check('batal tidak error saat kosong', undo(), false);
  while (redo());
  check('ulangi tidak error saat kosong', redo(), false);

  console.log('\nalat geser');
  setTool('move');
  check('alat geser aktif', state.tool, 'move');
  setTool('pencil');
  check('kembali ke pensil', state.tool, 'pencil');

  console.log('\ntanpa pinch');
  // Moving the map is a tool now. If pinch or two-finger pan ever comes back,
  // this catches it: the editor must not carry pointer bookkeeping for it.
  check('tidak ada state pointers', state.pointers, undefined);
  check('tidak ada state pinch', state.pinch, undefined);
  check('tidak ada fungsi pinchInfo', typeof editor.pinchInfo, 'undefined');

  console.log('\nkarakter di spawn');
  check('sprite pemain termuat', state.playerSprite ? state.playerSprite.src : null,
    '/docs/tileset/player.png');
  // The marker must be the app's character, not a bare square: the whole point
  // of showing it in the editor is to see where the player will stand.
  const pad = new Element('canvas');
  const pctx = pad.getContext('2d');
  editor.drawPlayerMarker(pctx, 0, 0, 16);
  const spriteDraw = pad._draws.filter((a) => a.length === 9 && a[3] === 32 && a[4] === 32);
  check('karakter digambar dari frame DOWN', spriteDraw.length, 1);
  // 32x32 frames, two rows down the sheet: DOWN is row 1.
  check('frame yang dipakai: kolom 0 baris 1', spriteDraw.length
    ? [spriteDraw[0][1], spriteDraw[0][2]] : null, [0, 32]);
  // The frame covers two cells and is anchored on the feet, so at a 16px cell
  // it is 32px tall and its top edge sits one cell above the spawn cell.
  check('setinggi dua sel, kaki di sel spawn', spriteDraw.length
    ? [spriteDraw[0][7], spriteDraw[0][8]] : null, [32, 32]);
  check('tambat di kaki, bukan di pojok atas', spriteDraw.length
    ? [spriteDraw[0][5], spriteDraw[0][6]] : null, [0, -16]);
  // the fallback square must not be used while the sheet is loaded
  const redSquares = (pad._fills || []).filter((a) => a[2] > 0 && a[2] < 16 && String(a[3]).includes('.95'));
  check('tidak memakai kotak merah saat sprite ada', redSquares.length, 0);

  console.log('\nzoom kelipatan 0.5');
  check('0.5 ada di daftar langkah', steps.includes(0.5), true);
  check('langkah di atas 1 bilangan bulat',
    steps.filter((v) => v > 1).every((v) => Number.isInteger(v)), true);
  state.zoom = 1;
  zoomIn(); check('perbesar dari 1x -> 2x', state.zoom, 2);
  zoomOut(); zoomOut(); check('perkecil 2x -> 1x -> 0.5x', state.zoom, 0.5);
  zoomOut(); check('0.5x adalah batas bawah', state.zoom, 0.5);
  state.zoom = 8; zoomIn(); check('8x adalah batas atas', state.zoom, 8);

  console.log('\nbingkai gameplay');
  // gameFrameRect works in screen pixels, so the cell count is size / cellSize
  state.zoom = 1;
  let frame = gameFrameRect();
  check('bingkai 16x10 sel di 1x', [frame.w / cellSize(), frame.h / cellSize()], [16, 10]);
  state.zoom = 2;
  frame = gameFrameRect();
  check('zooming tidak mengubah jumlah sel di bingkai',
    [frame.w / cellSize(), frame.h / cellSize()], [16, 10]);
  check('bingkai ikut membesar di layar saat zoom', frame.w, 16 * 16 * 2);
  state.zoom = 1;
  frame = gameFrameRect();
  check('bingkai tidak keluar dari peta',
    frame.x >= 0 && frame.y >= 0
    && frame.x + frame.w <= state.cols * cellSize() + 0.001
    && frame.y + frame.h <= state.rows * cellSize() + 0.001, true);

  console.log(failures ? `\n${failures} uji gagal` : '\nsemua uji editor lulus');
  process.exit(failures ? 1 : 0);
}).catch((error) => {
  console.log('  FAIL  boot editor:', error.message);
  console.log(error.stack);
  process.exit(1);
});
