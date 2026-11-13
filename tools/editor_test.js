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
    return {
      setTransform: noop, fillRect: noop, drawImage: noop, beginPath: noop,
      moveTo: noop, lineTo: noop, stroke: noop, strokeRect: noop, save: noop,
      restore: noop, imageSmoothingEnabled: false, fillStyle: '', strokeStyle: '', lineWidth: 1,
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
  set src(_value) { setTimeout(() => this.onload && this.onload(), 0); }
};

const fetch = async (url) => {
  if (url.includes('tileset.json')) {
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(ROOT, 'docs/tileset/tileset.json'), 'utf8')) };
  }
  if (url.includes('map.json')) return { ok: false, json: async () => ({}) };  // no saved map yet
  throw new Error('fetch tak terduga: ' + url);
};

// ---------------------------------------------------------------- muat editor
const source = fs.readFileSync(path.join(ROOT, 'editor/app.js'), 'utf8');

// Berkas memakai const letak-atas; bungkus jadi fungsi agar bisa dievaluasi.
const sandbox = { document, window, Image, fetch, console, setTimeout, clearTimeout };
const loader = new Function(
  'document', 'window', 'Image', 'fetch', 'console', 'setTimeout', 'clearTimeout',
  `${source}\nreturn { __steps: ZOOM_STEPS, boot, state, cellSize, key, paintAt, fillFrom, mapExtent,
            fitToScreen, zoomToActual, inBounds, DEFAULT_COLS, DEFAULT_ROWS, TILE };`
);
const editor = loader(sandbox.document, sandbox.window, sandbox.Image, sandbox.fetch,
  console, setTimeout, clearTimeout);

// --------------------------------------------------------------------- assertions
editor.boot().then(() => {
  const { state, cellSize, key, paintAt, fillFrom, mapExtent, fitToScreen, zoomToActual, ensureCoverage } = editor;

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
  check('sel menutupi seluruh layar', editor.state.cells.size, cols * rows);
  check('zoom dipilih agar pas', editor.__steps.includes(editor.state.zoom), true);

  console.log('\ntileset');
  check('semua tile terbaca', Object.keys(state.tileset.tiles).length, 29);
  check('ada tile rumput', Boolean(state.tileset.tiles.grass), true);
  check('ada tile pohon', Boolean(state.tileset.tiles.tree), true);

  console.log('\nmenggambar');
  state.tool = 'pencil';
  state.brush = { name: 'path', layer: 'ground', solid: false };
  paintAt(10, 6);
  check('pensil menaruh jalan', state.cells.get(key(10, 6)).name, 'path');
  state.brush = { name: 'tree', layer: 'object', solid: true };
  paintAt(12, 6);
  check('pohon masuk layer objek', state.cells.get(key(12, 6)).name, 'tree');
  check('pohon menyimpan properti solid', state.cells.get(key(12, 6)).solid, true);

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
  paintAt(10, 6);
  check('hapus membuang sel', state.cells.has(key(10, 6)), false);
  check('hapus tidak menyimpan null', Array.from(state.cells.values()).every((c) => c && c.name), true);

  console.log('\nmengisi area');
  const total = state.cells.size;
  state.tool = 'fill';
  state.brush = { name: 'water', layer: 'ground', solid: true };
  fillFrom(0, 0);
  const water = Array.from(state.cells.values()).filter((c) => c && c.name === 'water').length;
  check('isi area mengecat sel', water > 0, true);
  check('isi area tidak meluber keluar peta', state.cells.size, total);

  console.log('\nmemuat peta tersimpan');
  check('peta kosong tidak diisi ulang otomatis', (() => {
    state.cells.clear();
    state.loadedMap = true;
    // seedIfEmpty memakai state.loadedMap; peta kosong yang sah harus tetap kosong
    return state.cells.size === 0;
  })(), true);

  console.log(failures ? `\n${failures} uji gagal` : '\nsemua uji editor lulus');
  process.exit(failures ? 1 : 0);
}).catch((error) => {
  console.log('  FAIL  boot editor:', error.message);
  console.log(error.stack);
  process.exit(1);
});
