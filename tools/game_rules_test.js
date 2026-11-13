#!/usr/bin/env node
/**
 * Mirrors the Kotlin game core in JavaScript so the rules can be exercised in
 * this sandbox, where no JDK and no kotlinc exist.
 *
 * This is not the shipped code: `app/.../game/*.kt` is. It exists because the
 * rules below (walking, mining, building, farming, night damage, pathing) are
 * exactly the ones CI would only catch as a red build, and a red build says
 * "something broke", not "the player can walk through water".
 *
 * Keep this file in step with the Kotlin when a rule changes; tools/verify.py
 * checks that it still parses and that the numbers match.
 */
'use strict';

const TILE = 16;
const MAX_HEALTH = 10;
const MAX_HUNGER = 10;
const REACH = 1;
const LIGHT_RADIUS = 4;
const MINUTES_PER_HUNGER = 25;
const MINUTES_PER_NIGHT_DAMAGE = 6;
const DAYS_TO_RIPE = 2;

class TileSet {
  constructor(tile, columns, tiles) { this.tile = tile; this.columns = columns; this.tiles = tiles; }
  get(name) { return this.tiles[name]; }
}
class GameMap {
  constructor(cols, rows, cells, spawnX, spawnY) {
    this.cols = cols; this.rows = rows; this.cells = cells;
    this.spawnX = spawnX === undefined ? Math.floor(cols / 2) : spawnX;
    this.spawnY = spawnY === undefined ? Math.floor(rows / 2) : spawnY;
  }
  inBounds(x, y) { return x >= 0 && y >= 0 && x < this.cols && y < this.rows; }
  cell(x, y) { return this.cells.get(`${x},${y}`); }
  isSolid(x, y, tiles) {
    if (!this.inBounds(x, y)) return true;
    const c = this.cell(x, y);
    if (!c) return false;
    for (const n of [c.objectTile, c.building, c.ground]) {
      if (!n) continue;
      const t = tiles.get(n);
      if (t && t.solid) return true;
    }
    return false;
  }
}

class GameClock {
  constructor(minuteOfDay) { this.minuteOfDay = ((minuteOfDay % 1440) + 1440) % 1440; }
  get hour() { return Math.floor(this.minuteOfDay / 60); }
  get isNight() { return this.hour < 6 || this.hour >= 18; }
  get daylight() {
    const m = this.minuteOfDay;
    if (m <= 240) return 0;
    if (m < 360) return (m - 240) / 120;
    if (m < 1080) return 1;
    if (m < 1200) return 1 - (m - 1080) / 120;
    return 0;
  }
  static atMinute(m) { return new GameClock(m); }
}

class World {
  constructor(map, tiles, startX, startY) {
    this.map = map; this.tiles = tiles;
    this.playerX = startX === undefined ? map.spawnX : startX;
    this.playerY = startY === undefined ? map.spawnY : startY;
    this.facing = 'DOWN';
    this.health = MAX_HEALTH; this.hunger = MAX_HUNGER;
    this.lights = new Set(); this.cleared = new Set(); this.crops = new Map();
    this.built = new Map(); this.tilled = new Set();
    this.inventory = { WOOD: 8, STONE: 4, FIBRE: 2, SEED: 3, FOOD: 1, TORCH: 0 };
    this.waterDay = 0; this.hungerTimer = 0; this.nightTimer = 0;
  }
  get wood() { return this.inventory.WOOD; }
  get stone() { return this.inventory.STONE; }
  get seeds() { return this.inventory.SEED; }
  get food() { return this.inventory.FOOD; }
  step(dir) {
    const d = { UP: [0, -1], DOWN: [0, 1], LEFT: [-1, 0], RIGHT: [1, 0] }[dir];
    this.facing = dir;
    const nx = this.playerX + d[0], ny = this.playerY + d[1];
    if (!this.canStand(nx, ny)) return false;
    this.playerX = nx; this.playerY = ny; return true;
  }
  craftTorch() {
    if (this.inventory.STONE < 1 || this.inventory.FIBRE < 1) return false;
    this.inventory.STONE--; this.inventory.FIBRE--; this.inventory.TORCH++; return true;
  }
  canStand(x, y) {
    if (!this.map.inBounds(x, y)) return false;
    if (this.built.has(`${x},${y}`)) return false;
    if (this.cleared.has(`${x},${y}`)) return false;
    return !this.map.isSolid(x, y, this.tiles);
  }
  distanceTo(x, y) { return Math.abs(this.playerX - x) + Math.abs(this.playerY - y); }
  mine(x, y) {
    if (!this.map.inBounds(x, y)) return { kind: 'Nothing' };
    const k = `${x},${y}`;
    if (this.cleared.has(k)) return { kind: 'Nothing' };
    if (this.distanceTo(x, y) > REACH) return { kind: 'TooFar' };
    const cell = this.map.cell(x, y);
    if (!cell) return { kind: 'Nothing' };
    const target = cell.objectTile || cell.building || cell.ground;
    const tile = target && this.tiles.get(target);
    if (!tile || !tile.solid) return { kind: 'Nothing' };
    if (tile.name.startsWith('water')) return { kind: 'Nothing' };
    let drop = null;
    if (tile.name.startsWith('tree') || tile.name === 'bush' || tile.name.startsWith('fence')) drop = 'WOOD';
    else if (tile.name === 'rock') drop = 'STONE';
    else if (tile.name.startsWith('flowers')) drop = 'FIBRE';
    this.cleared.add(k);
    if (drop) this.inventory[drop]++;
    return { kind: 'Mined', tile: tile.name, drop };
  }
  build(item) {
    if (!['WOOD', 'STONE', 'TORCH'].includes(item)) return { kind: 'NotABlock' };
    const d = { UP: [0, -1], DOWN: [0, 1], LEFT: [-1, 0], RIGHT: [1, 0] }[this.facing];
    const x = this.playerX + d[0], y = this.playerY + d[1];
    if (!this.map.inBounds(x, y)) return { kind: 'Blocked' };
    if (this.inventory[item] <= 0) return { kind: 'NoMaterial' };
    this.inventory[item]--;
    this.built.set(`${x},${y}`, item);
    this.cleared.delete(`${x},${y}`);
    return { kind: 'Built', item, x, y };
  }
  builtAt(x, y) { return this.built.get(`${x},${y}`) || null; }
  placeLight() {
    if (this.inventory.TORCH <= 0) return false;
    const k = `${this.playerX},${this.playerY}`;
    if (this.lights.has(k)) return false;
    this.inventory.TORCH--;
    this.lights.add(k); return true;
  }
  isLit(x, y) {
    for (const l of this.lights) {
      const [lx, ly] = l.split(',').map(Number);
      if (Math.abs(lx - x) <= LIGHT_RADIUS && Math.abs(ly - y) <= LIGHT_RADIUS) return true;
    }
    return false;
  }
  till(x, y) {
    if (this.distanceTo(x, y) > REACH) return false;
    if (!this.map.inBounds(x, y)) return false;
    const cell = this.map.cell(x, y);
    if (!cell) return false;
    const g = cell.ground;
    if (!['grass', 'grass_detail', 'grass_dark'].includes(g)) return false;
    if (cell.objectTile || cell.building) return false;
    this.tilled.add(`${x},${y}`); return true;
  }
  isTilled(x, y) { return this.tilled.has(`${x},${y}`); }
  plant(x, y, day) {
    if (this.distanceTo(x, y) > REACH) return false;
    if (!this.isTilled(x, y)) return false;
    if (this.crops.has(`${x},${y}`)) return false;
    if (this.inventory.SEED <= 0) return false;
    this.inventory.SEED--;
    this.crops.set(`${x},${y}`, { plantedDay: day, wateredDay: -1, growth: 0 });
    return true;
  }
  water(x, y) {
    if (this.distanceTo(x, y) > REACH) return false;
    const c = this.crops.get(`${x},${y}`);
    if (!c) return false;
    if (c.wateredDay === this.waterDay) return false;
    this.crops.set(`${x},${y}`, { ...c, wateredDay: this.waterDay,
      growth: Math.min(DAYS_TO_RIPE, c.growth + 1) });
    return true;
  }
  harvest(x, y, day) {
    if (this.distanceTo(x, y) > REACH) return 0;
    const c = this.crops.get(`${x},${y}`);
    if (!c) return 0;
    if (c.growth < DAYS_TO_RIPE) return 0;
    this.crops.delete(`${x},${y}`); this.tilled.delete(`${x},${y}`);
    this.inventory.FOOD += 2;
    return 2;
  }
  cropAt(x, y) { return this.crops.get(`${x},${y}`) || null; }
  eat() {
    if (this.hunger >= MAX_HUNGER) return false;
    if (this.inventory.FOOD <= 0) return false;
    this.inventory.FOOD--; this.hunger = Math.min(MAX_HUNGER, this.hunger + 4);
    this.health = Math.min(MAX_HEALTH, this.health + 1);
    return true;
  }
  tickSurvival(clock, minutes) {
    let starving = false, exposed = false;
    for (let i = 0; i < Math.max(0, minutes); i++) {
      if (this.hunger > 0) {
        if (++this.hungerTimer >= MINUTES_PER_HUNGER) { this.hungerTimer = 0; this.hunger = Math.max(0, this.hunger - 1); }
      } else { starving = true; this.health = Math.max(0, this.health - 1); }
      if (clock.isNight && !this.isLit(this.playerX, this.playerY)) {
        exposed = true;
        if (++this.nightTimer >= MINUTES_PER_NIGHT_DAMAGE) { this.nightTimer = 0; this.health = Math.max(0, this.health - 1); }
      } else { this.nightTimer = 0; }
    }
    return { health: this.health, hunger: this.hunger, starving, exposedAtNight: exposed };
  }
  sleep(hasShelter) {
    if (!hasShelter) return false;
    this.health = Math.min(MAX_HEALTH, this.health + 4);
    this.hunger = Math.max(0, this.hunger - 2);
    return true;
  }
  addItem(item, n) { this.inventory[item] += n; }
  countOf(item) { return this.inventory[item]; }
}

class Camera {
  constructor(x, y, viewWidth, viewHeight, mapWidth, mapHeight) {
    Object.assign(this, { x, y, viewWidth, viewHeight, mapWidth, mapHeight });
  }
  follow(tx, ty) {
    const maxX = this.mapWidth - this.viewWidth, maxY = this.mapHeight - this.viewHeight;
    const nx = maxX <= 0 ? Math.trunc((this.mapWidth - this.viewWidth) / 2)
      : Math.min(Math.max(tx - Math.floor(this.viewWidth / 2), 0), maxX);
    const ny = maxY <= 0 ? Math.trunc((this.mapHeight - this.viewHeight) / 2)
      : Math.min(Math.max(ty - Math.floor(this.viewHeight / 2), 0), maxY);
    return new Camera(nx, ny, this.viewWidth, this.viewHeight, this.mapWidth, this.mapHeight);
  }
}

function cellAt(touchX, touchY, camera) {
  return [Math.floor((camera.x + Math.trunc(touchX)) / TILE), Math.floor((camera.y + Math.trunc(touchY)) / TILE)];
}

function findPath(sx, sy, gx, gy, walkable) {
  if (sx === gx && sy === gy) return [];
  let target = [gx, gy];
  if (!walkable(gx, gy)) {
    // pick the walkable neighbour nearest the player, so tapping an adjacent
    // tree does not walk around the pond first
    const cand = [[gx, gy + 1], [gx, gy - 1], [gx - 1, gy], [gx + 1, gy]]
      .filter(([x, y]) => walkable(x, y))
      .sort((a, b) => (Math.abs(a[0] - sx) + Math.abs(a[1] - sy)) - (Math.abs(b[0] - sx) + Math.abs(b[1] - sy)));
    if (!cand.length) return [];
    target = cand[0];
  }
  const key = (x, y) => `${x},${y}`;
  const came = new Map(); const seen = new Set([key(sx, sy)]);
  const q = [[sx, sy]];
  let head = 0;
  while (head < q.length) {
    const [cx, cy] = q[head++];
    if (cx === target[0] && cy === target[1]) {
      const path = []; let cur = key(cx, cy);
      while (cur !== key(sx, sy)) { const [x, y] = cur.split(',').map(Number); path.unshift([x, y]); cur = came.get(cur); }
      return path;
    }
    for (const [nx, ny] of [[cx, cy + 1], [cx, cy - 1], [cx - 1, cy], [cx + 1, cy]]) {
      if (!walkable(nx, ny) || seen.has(key(nx, ny))) continue;
      seen.add(key(nx, ny)); came.set(key(nx, ny), key(cx, cy)); q.push([nx, ny]);
    }
  }
  return [];
}

// ------------------------------------------------------------------ fixtures
const TILES = new TileSet(16, 8, {
  grass: { name: 'grass', solid: false }, path: { name: 'path', solid: false },
  water: { name: 'water', solid: true }, tree: { name: 'tree', solid: true },
  bush: { name: 'bush', solid: true }, rock: { name: 'rock', solid: true },
  flowers_gold: { name: 'flowers_gold', solid: false }, fence_h: { name: 'fence_h', solid: true },
});

function buildMap() {
  const cells = new Map();
  for (let y = 0; y < 8; y++) for (let x = 0; x < 10; x++) {
    // a pond on x=5 from y=0..5 only: rows 6 and 7 are the way around it
    const wet = x === 5 && y <= 5;
    cells.set(`${x},${y}`, { ground: wet ? 'water' : 'grass', objectTile: null, building: null });
  }
  cells.get('2,2').objectTile = 'tree';
  return new GameMap(10, 8, cells, 2, 3);
}

let failures = 0;
function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  if (!ok) failures++;
  console.log(`  ${ok ? 'ok  ' : 'FAIL'}  ${label}${ok ? '' : `  (${JSON.stringify(actual)} != ${JSON.stringify(expected)})`}`);
}

// ------------------------------------------------------------------ scenarios
const w = new World(buildMap(), TILES, 2, 3);

check('pohon menghalangi langkah', w.step('UP'), false);
check('pemain tetap di tempat', [w.playerX, w.playerY], [2, 3]);
w.step('RIGHT'); w.step('RIGHT');
check('air menghalangi langkah', w.step('RIGHT'), false);
check('pemain berhenti sebelum air', [w.playerX, w.playerY], [4, 3]);

const m1 = new World(buildMap(), TILES, 2, 3);
check('menebang dari jauh ditolak', new World(buildMap(), TILES, 8, 6).mine(2, 2).kind, 'TooFar');
check('awal di bawah pohon', [m1.playerX, m1.playerY], [2, 3]);
check('jarak ke pohon satu sel', m1.distanceTo(2, 2), 1);
const woodBefore = m1.wood;
check('menebang pohon dapat kayu', m1.mine(2, 2).kind, 'Mined');
check('kayu bertambah', m1.wood, woodBefore + 1);
check('bekas tambang jadi lubang', m1.canStand(2, 2), false);

const b = new World(buildMap(), TILES, 2, 3);
check('membangun tanpa bahan ditolak', b.build('TORCH').kind, 'NoMaterial');
check('makanan bukan blok', b.build('FOOD').kind, 'NotABlock');
b.addItem('STONE', 1);
const stoneBefore = b.stone;
check('membangun batu berhasil', b.build('STONE').kind, 'Built');
check('bahan berkurang', b.stone, stoneBefore - 1);

const dark = new World(buildMap(), TILES);
const cold = dark.tickSurvival(GameClock.atMinute(1380), 12);
check('malam tanpa lampu kehilangan nyawa', cold.health < MAX_HEALTH, true);
const lit = new World(buildMap(), TILES);
lit.addItem('TORCH', 1); lit.placeLight();
const warm = lit.tickSurvival(GameClock.atMinute(1380), 12);
check('malam dengan lampu aman', warm.exposedAtNight, false);
check('nyawa utuh di dekat lampu', warm.health, MAX_HEALTH);
const noon = new World(buildMap(), TILES).tickSurvival(GameClock.atMinute(720), 30);
check('siang hari aman', noon.health, MAX_HEALTH);

const f = new World(buildMap(), TILES);
check('membajak rumput', f.till(2, 3), true);
check('membajak air ditolak', f.till(5, 3), false);
check('menanam butuh tanah', new World(buildMap(), TILES).plant(2, 3, 0), false);
const seedsBefore = f.seeds;
check('menanam dengan tanah & bibit', f.plant(2, 3, 0), true);
check('bibit berkurang', f.seeds, seedsBefore - 1);
check('belum matang hari itu', f.harvest(2, 3, 0), 0);
const foodBefore = f.food;
check('menunggu tidak mematangkan', f.harvest(2, 3, 99), 0);
f.waterDay = 40; check('siraman pertama', f.water(2, 3), true);
f.waterDay = 41; check('siraman kedua', f.water(2, 3), true);
check('panen setelah 2 siraman', f.harvest(2, 3, 41), 2);
check('makanan bertambah', f.food, foodBefore + 2);

const c = new Camera(0, 0, 320, 240, 1600, 1600);
check('kamera di tepi kiri', c.follow(0, 0).x, 0);
check('kamera di tepi kanan', c.follow(1590, 1590).x, 1600 - 320);
const small = new Camera(0, 0, 640, 480, 320, 240);
check('peta kecil di tengah', small.follow(10, 10).x, Math.trunc((320 - 640) / 2));

check('ketuk 40px = 2 sel', cellAt(40, 40, new Camera(160, 64, 640, 480, 2560, 1600)), [160 / 16 + 2, 64 / 16 + 2]);

const routeMap = buildMap();
const walkable = (x, y) => routeMap.inBounds(x, y) && !routeMap.isSolid(x, y, TILES);
const p = findPath(2, 3, 8, 3, walkable);
check('jalur memutari kolam', p.length > 6, true);
check('jalur berakhir di tujuan', p[p.length - 1], [8, 3]);
const nearTree = findPath(2, 3, 2, 2, walkable);
// standing beside the tree already: the walk is zero steps, which is correct
check('ketuk pohon saat sudah di sebelahnya = tanpa langkah', nearTree.length, 0);
const farTree = findPath(8, 6, 2, 2, walkable);
check('ketuk pohon dari jauh berhenti di sebelahnya', farTree.length > 0 &&
  Math.abs(farTree[farTree.length - 1][0] - 2) + Math.abs(farTree[farTree.length - 1][1] - 2) === 1, true);
check('jam 07:00 bukan malam', GameClock.atMinute(420).isNight, false);
check('daylight tengah hari', GameClock.atMinute(720).daylight, 1);
check('daylight sebelum fajar', GameClock.atMinute(120).daylight, 0);

console.log(failures ? `\n${failures} uji gagal` : '\nsemua uji mesin game lulus');
process.exit(failures ? 1 : 0);
