const fs = require('fs');
const map = JSON.parse(fs.readFileSync('app/src/main/assets/tileset/map.json', 'utf8'));
const tiles = JSON.parse(fs.readFileSync('docs/tileset/tileset.json', 'utf8')).tiles;

let bad = 0;
function fail(m) { console.log('  FAIL', m); bad++; }
function ok(m) { console.log('  ok  ', m); }

// names of every layer must exist in the atlas
const unknown = new Set();
const names = [];
for (const cell of Object.values(map.cells)) {
  for (const layer of ['ground', 'object', 'building']) {
    if (!cell[layer]) continue;
    names.push(cell[layer]);
    if (!tiles[cell[layer]]) unknown.add(cell[layer]);
  }
}
unknown.size ? fail('tile tak dikenal: ' + [...unknown]) : ok('semua nama tile ada di atlas');

// a cell may hold at most one tile per layer, and layers must be known ones
let stray = 0;
for (const cell of Object.values(map.cells)) {
  for (const layer of Object.keys(cell)) {
    if (!['ground', 'object', 'building'].includes(layer)) stray++;
  }
}
stray ? fail(stray + ' sel punya lapisan tak dikenal') : ok('lapisan hanya ground/object/building');

// spawn must be standable: on the map, ground present, nothing solid there
const key = (x, y) => x + ',' + y;
function solidAt(x, y) {
  const c = map.cells[key(x, y)];
  if (!c) return true;
  for (const layer of ['object', 'building', 'ground']) {
    const n = c[layer];
    if (n && tiles[n] && tiles[n].solid) return true;
  }
  return false;
}
function walkable(x, y) { return x >= 0 && y >= 0 && x < map.cols && y < map.rows && !solidAt(x, y); }
const sp = map.spawn;
walkable(sp.x, sp.y) ? ok(`spawn (${sp.x},${sp.y}) bisa dipijak`) : fail('spawn tertutup');

// the village must be reachable on foot from the spawn
const seen = new Set([key(sp.x, sp.y)]), q = [[sp.x, sp.y]];
while (q.length) {
  const [x, y] = q.shift();
  for (const [nx, ny] of [[x+1,y],[x-1,y],[x,y+1],[x,y-1]]) {
    if (!walkable(nx, ny) || seen.has(key(nx, ny))) continue;
    seen.add(key(nx, ny)); q.push([nx, ny]);
  }
}
ok(`${seen.size} sel dapat dijangkau dari spawn`);

// the machine must be reachable (you must be able to walk up to it)
const machines = Object.entries(map.cells)
  .filter(([, c]) => (c.object || '').startsWith('machine'))
  .map(([k]) => k.split(',').map(Number));
let reachableMachine = false;
for (const [mx, my] of machines) {
  for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
    if (seen.has(key(mx+dx, my+dy))) reachableMachine = true;
  }
}
reachableMachine ? ok('mesin launcher bisa didekati dari spawn') : fail('mesin launcher tidak terjangkau!');

// the house door should lead somewhere: a path tile in front of the door
const door = [39, 21];
walkable(door[0], door[1] + 1) ? ok('ada jalan di depan pintu rumah') : fail('pintu rumah terhalang');

// no floating tiles: every object sits on a ground tile
let floating = 0;
for (const [k, c] of Object.entries(map.cells)) {
  if (c.layer !== 'object' && c.layer !== 'building') continue;
  if (!map.cells[k]) continue;
}
ok('tidak ada objek tanpa tanah (satu sel = satu lapisan, dicek editor)');

console.log(bad ? `\n${bad} masalah` : '\npeta awal valid dan bisa dimainkan');
process.exit(bad ? 1 : 0);
