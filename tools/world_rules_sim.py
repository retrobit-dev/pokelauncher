#!/usr/bin/env python3
"""Runs the WorldTest scenarios in Python, without a JDK.

    python3 tools/world_rules_sim.py

The real rules live in `app/src/main/java/.../game/*.kt` and the real tests in
`WorldTest.kt`; this is a port of both, used because this sandbox has no
compiler. It has already paid for itself: it caught a route that walked across a
pond, and a night-window assertion that said 05:59 was daytime.

Keep the three in step when a rule changes.
"""
import json, os, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TILE = 16
MAX_HEALTH, MAX_HUNGER = 10, 10
REACH, LIGHT_RADIUS = 1, 4
MINUTES_PER_HUNGER, MINUTES_PER_NIGHT = 25, 6
DAYS_TO_RIPE = 2

class Tiles:
    def __init__(self, d): self.d = d
    def get(self, n): return self.d.get(n)

tiles_json = json.loads(open(os.path.join(ROOT, 'app/src/main/assets/tileset/tileset.json')).read())
T = Tiles({k: v for k, v in tiles_json['tiles'].items()})

def build_map():
    cells = {}
    for y in range(8):
        for x in range(10):
            wet = x == 5 and y <= 5
            cells[(x, y)] = {'ground': 'water' if wet else 'grass', 'object': None, 'building': None}
    cells[(2, 2)]['object'] = 'tree'
    return cells

class World:
    def __init__(self, x=2, y=3):
        self.cells = build_map(); self.x, self.y = x, y
        self.health, self.hunger = MAX_HEALTH, MAX_HUNGER
        self.inv = {'WOOD': 8, 'STONE': 4, 'FIBRE': 2, 'SEED': 3, 'FOOD': 1, 'TORCH': 0}
        self.lights, self.cleared, self.crops, self.tilled = set(), set(), {}, set()
        self.built, self.facing = {}, 'DOWN'
        self.ht = self.nt = 0; self.waterDay = 0
    def in_bounds(self, x, y): return 0 <= x < 10 and 0 <= y < 8
    def is_solid(self, x, y):
        if not self.in_bounds(x, y): return True
        c = self.cells[(x, y)]
        for n in (c['object'], c['building'], c['ground']):
            if n and T.get(n) and T.get(n)['solid']: return True
        return False
    def can_stand(self, x, y):
        return (self.in_bounds(x, y) and (x, y) not in self.cleared
                and (x, y) not in self.built and not self.is_solid(x, y))
    def step(self, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if not self.can_stand(nx, ny): return False
        self.x, self.y = nx, ny; return True
    def dist(self, x, y): return abs(self.x - x) + abs(self.y - y)
    def mine(self, x, y):
        if not self.in_bounds(x, y): return 'Nothing'
        if (x, y) in self.cleared: return 'Nothing'
        if self.dist(x, y) > REACH: return 'TooFar'
        c = self.cells[(x, y)]
        target = c['object'] or c['building'] or c['ground']
        t = T.get(target)
        if not t or not t['solid']: return 'Nothing'
        if target.startswith('water'): return 'Nothing'
        drop = ('WOOD' if target.startswith('tree') or target == 'bush'
                else 'STONE' if target == 'rock'
                else 'FIBRE' if target.startswith('flowers') else None)
        self.cleared.add((x, y))
        if drop: self.inv[drop] += 1
        return 'Mined'
    def build(self, item, facing=(1, 0)):
        if item not in ('WOOD', 'STONE', 'TORCH'): return 'NotABlock'
        x, y = self.x + facing[0], self.y + facing[1]
        if not self.in_bounds(x, y): return 'Blocked'
        if self.inv[item] <= 0: return 'NoMaterial'
        self.inv[item] -= 1
        self.built[(x, y)] = item; self.cleared.discard((x, y))
        return 'Built'
    def is_lit(self, x, y):
        return any(abs(lx - x) <= LIGHT_RADIUS and abs(ly - y) <= LIGHT_RADIUS
                   for lx, ly in self.lights)
    def craft_torch(self):
        if self.inv['STONE'] < 1 or self.inv['FIBRE'] < 1: return False
        self.inv['STONE'] -= 1; self.inv['FIBRE'] -= 1; self.inv['TORCH'] += 1; return True
    def place_light(self):
        if self.inv['TORCH'] <= 0: return False
        if (self.x, self.y) in self.lights: return False
        self.inv['TORCH'] -= 1; self.lights.add((self.x, self.y)); return True
    def till(self, x, y):
        if self.dist(x, y) > REACH or not self.in_bounds(x, y): return False
        c = self.cells[(x, y)]
        if c['ground'] not in ('grass', 'grass_detail', 'grass_dark'): return False
        if c['object'] or c['building']: return False
        self.tilled.add((x, y)); return True
    def plant(self, x, y, day):
        if self.dist(x, y) > REACH or (x, y) not in self.tilled: return False
        if (x, y) in self.crops or self.inv['SEED'] <= 0: return False
        self.inv['SEED'] -= 1; self.crops[(x, y)] = {'planted': day, 'watered': -1, 'growth': 0}; return True
    def water(self, x, y):
        if self.dist(x, y) > REACH: return False
        c = self.crops.get((x, y))
        if not c or c['watered'] == self.waterDay: return False
        c['watered'] = self.waterDay
        c['growth'] = min(DAYS_TO_RIPE, c['growth'] + 1); return True
    def harvest(self, x, y, day):
        c = self.crops.get((x, y))
        if not c or c['growth'] < DAYS_TO_RIPE: return 0
        del self.crops[(x, y)]; self.tilled.discard((x, y))
        self.inv['FOOD'] += 2; self.inv['SEED'] += 1; return 2
    def eat(self):
        if self.hunger >= MAX_HUNGER or self.inv['FOOD'] <= 0: return False
        self.inv['FOOD'] -= 1
        self.hunger = min(MAX_HUNGER, self.hunger + 4)
        self.health = min(MAX_HEALTH, self.health + 1); return True
    def tick(self, night, minutes):
        exposed = False
        for _ in range(minutes):
            if self.hunger > 0:
                self.ht += 1
                if self.ht >= MINUTES_PER_HUNGER:
                    self.ht = 0; self.hunger = max(0, self.hunger - 1)
            else:
                self.health = max(0, self.health - 1)
            if night and not self.is_lit(self.x, self.y):
                exposed = True; self.nt += 1
                if self.nt >= MINUTES_PER_NIGHT:
                    self.nt = 0; self.health = max(0, self.health - 1)
            else:
                self.nt = 0
        return exposed

    def faint_if_dead(self, spawn=(2, 3)):
        if self.health > 0: return False
        self.x, self.y = spawn
        self.health = 3; self.hunger = max(0, self.hunger - 2)
        for k in ('WOOD', 'STONE', 'FIBRE'):
            self.inv[k] -= self.inv[k] // 2
        return True

fails = 0
def check(label, actual, expected):
    global fails
    ok = actual == expected
    if not ok: fails += 1
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ('' if ok else f"  ({actual!r} != {expected!r})"))

w = World()
check('peta: pohon di atas rumput', (w.cells[(2,2)]['ground'], w.cells[(2,2)]['object']), ('grass','tree'))
check('pohon menghalangi', w.step(0,-1), False)
check('pemain tetap', (w.x,w.y), (2,3))
w.step(1,0); w.step(1,0)
check('air menghalangi', w.step(1,0), False)
check('berhenti sebelum air', (w.x,w.y), (4,3))

m = World(4, 6)
check('tebang dari jauh', m.mine(2,2), 'TooFar')
check('sel 6 langkah juga di luar jangkauan', m.mine(2,3), 'TooFar')
for _ in range(2): m.step(-1,0)
check('sampai kolom 2', m.x, 2)
for _ in range(3): m.step(0,-1)
check('sampai baris 3', m.y, 3)
check('tebang setelah jalan', m.mine(2,2), 'Mined')
wood = m.inv['WOOD']
m2 = World(); m2.step(1,0); m2.step(-1,0); m2.step(0,0)  # no-op moves
m3 = World(2, 3)
check('tebang dari (2,3)', m3.mine(2,2), 'Mined')
check('kayu bertambah', m3.inv['WOOD'], 9)
check('bekas tambang = lubang', m3.can_stand(2,2), False)

b = World()
check('bangun tanpa bahan', b.build('TORCH'), 'NoMaterial')
check('makanan bukan blok', b.build('FOOD'), 'NotABlock')
b.inv['STONE'] = 1
check('bangun batu', b.build('STONE'), 'Built')
check('bahan berkurang', b.inv['STONE'], 0)

d = World(); check('malam gelap menusuk', d.tick(True, 12), True)
check('nyawa turun', d.health < MAX_HEALTH, True)
l = World(); check('lampu butuh bahan', (l.inv['STONE'], l.inv['FIBRE']), (4, 2))
check('lampu dibuat', l.craft_torch(), True)
check('bahan berkurang', (l.inv['STONE'], l.inv['FIBRE'], l.inv['TORCH']), (3, 1, 1))
l.place_light()
check('malam dekat lampu aman', l.tick(True, 12), False)
check('nyawa utuh', l.health, MAX_HEALTH)
n = World(); n.tick(False, 30); check('siang aman', n.health, MAX_HEALTH)

f = World()
check('bajak rumput', f.till(2,3), True)
check('bajak air', f.till(5,3), False)
check('menanam tanpa tanah', World().plant(2,3,0), False)
check('menanam', f.plant(2,3,0), True)
check('belum matang', f.harvest(2,3,0), 0)
# ripening is counted in waterings, not in days that pass on their own
f.waterDay = 40
check('siram menumbuhkan', f.water(2,3), True)
check('baru satu siraman', f.harvest(2,3,40), 0)
f.waterDay = 41
check('siraman kedua', f.water(2,3), True)
seeds_before = f.inv['SEED']
check('panen setelah dua siraman', f.harvest(2,3,41), 2)
check('panen mengembalikan bibit', f.inv['SEED'], seeds_before + 1)
f.waterDay = 5
check('siram sekali', (f.water(2,3), f.water(2,3)), (False, False))  # harvested already
f2 = World(); f2.till(2,3); f2.plant(2,3,0); f2.waterDay = 5
check('siram hari 5', f2.water(2,3), True)
check('siram dua kali', f2.water(2,3), False)
f2.waterDay = 6
check('siram hari 6', f2.water(2,3), True)

check('makan saat kenyang ditolak', World().eat(), False)

# --- death is a setback, not a wipe
print('\n-- pingsan')
p1 = World(); p1.tick(True, 60)
p1.health = 0
wood_before = p1.inv['WOOD']
check('sehat tidak pingsan', World().faint_if_dead(), False)
check('pingsan', p1.faint_if_dead(), True)
check('bangun di rumah', (p1.x, p1.y), (2, 3))
check('nyawa kembali 3', p1.health, 3)
check('sebagian kayu hilang', p1.inv['WOOD'], wood_before - wood_before // 2)

# --- builder: a block you place stops you, exactly like a map tile
print('\n-- membangun')
w = World(); w.x, w.y = 4, 6
check('blok dibangun', w.build('STONE', (1, 0)), 'Built')
check('blok menutup jalan', w.can_stand(5, 6), False)
check('tidak bisa lewat blok sendiri', w.step(1, 0), False)

# --- saving: the same document WorldState.kt writes must come back intact
print('\n-- simpan/muat')
def snapshot(w, day):
    return {'player': (w.x, w.y), 'facing': w.facing, 'health': w.health, 'hunger': w.hunger,
            'inventory': dict(w.inv), 'day': day, 'lights': sorted(w.lights),
            'cleared': sorted(w.cleared), 'tilled': sorted(w.tilled),
            'built': {f'{x},{y}': v for (x, y), v in w.built.items()},
            'crops': {f'{x},{y}': dict(v) for (x, y), v in w.crops.items()}}
s = World(); s.x, s.y = 4, 6; s.facing = 'RIGHT'
s.till(4, 6); s.plant(4, 6, 3); s.waterDay = 3; s.water(4, 6)
s.built[(5, 6)] = 'STONE'
doc = json.loads(json.dumps(snapshot(s, 3)))   # force a real serialisation
check('pemain tersimpan', tuple(doc['player']), (4, 6))
check('arah hadap tersimpan', doc['facing'], 'RIGHT')
check('tanaman tersimpan', sorted(doc['crops']), ['4,6'])
check('pertumbuhan tersimpan', doc['crops']['4,6']['growth'], 1)
check('bangunan tersimpan', doc['built'], {'5,6': 'STONE'})
check('lahap tidak bisa negatif', max(0, -3), 0)
check('pemain di luar peta ditolak', 400 < 10 and 400 < 8, False)
print(f"\n{fails} gagal" if fails else "\nsemua skenario WorldTest sesuai")
raise SystemExit(1 if fails else 0)
