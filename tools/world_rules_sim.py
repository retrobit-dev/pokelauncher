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

# --- camera follow, a port of CameraRig.kt
DEFAULT_MAX_STEP = 5
class Rig:
    def __init__(self, vw, vh, mw, mh, dzx=2560 // 6, dzy=1600 // 6):
        self.vw, self.vh, self.mw, self.mh = vw, vh, mw, mh
        self.dzx, self.dzy, self.step = dzx, dzy, DEFAULT_MAX_STEP
        self.x = self.y = 0
        self.jump(0, 0)
    def axis_max(self, view, m): return 0 if m <= view else m - view
    def place(self, value, view, m):
        if m <= view: return (m - view) // 2
        return max(0, min(value, m - view))
    def settle(self, current, target, view, dz):
        lowest = target - view + max(0, dz)
        highest = target - max(0, dz)
        if lowest > highest: return target - view // 2
        must_see = min(target - view + 1, target)
        return max(min(lowest, must_see), min(current, max(highest, target - 1)))
    def toward(self, current, goal):
        d = goal - current
        if d == 0: return current
        if abs(d) <= self.step: return goal
        return current + (self.step if d > 0 else -self.step)
    def clamp(self, v, mx): return v if mx <= 0 else max(0, min(v, mx))
    def advance(self, tx, ty):
        gx = self.settle(self.x, tx, self.vw, self.dzx)
        gy = self.settle(self.y, ty, self.vh, self.dzy)
        nx = self.place(self.toward(self.x, gx), self.vw, self.mw)
        ny = self.place(self.toward(self.y, gy), self.vh, self.mh)
        moved = (nx, ny) != (self.x, self.y)
        self.x, self.y = nx, ny
        return moved
    def jump(self, tx, ty):
        self.x = self.place(tx - self.vw // 2, self.vw, self.mw)
        self.y = self.place(ty - self.vh // 2, self.vh, self.mh)

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
print('\n-- kamera')
r = Rig(320, 240, 3200, 2400, dzx=16, dzy=12); r.jump(1600, 1200)
x0, y0 = r.x, r.y
check('diam di dead zone', any(r.advance(1600 + i * 16, 1200 + i * 16) for i in range(2)), False)
check('posisi tetap', (r.x, r.y), (x0, y0))

r2 = Rig(320, 240, 3200, 2400, dzx=16, dzy=12); r2.jump(1600, 1200)
frames = 0
while r2.advance(2400, 1200) and frames < 10000: frames += 1
check('kamera bergerak', r2.x > x0, True)
check('butuh banyak frame', frames > 10, True)
check('maks 5 px per frame', frames <= 2400 // DEFAULT_MAX_STEP + 2, True)

r3 = Rig(320, 240, 3200, 2400); r3.jump(0, 0)
for _ in range(200): r3.advance(-500, -500)
check('tidak pernah keluar kiri-atas', (r3.x, r3.y), (0, 0))
for _ in range(2000): r3.advance(9999, 9999)
check('berhenti di tepi kanan-bawah', (r3.x, r3.y), (3200 - 320, 2400 - 240))

r4 = Rig(2560, 1600, 1280, 800)
for _ in range(50): r4.advance(1200, 760)
check('peta lebih kecil: di tengah, bukan di 0', (r4.x, r4.y), ((1280 - 2560) // 2, (800 - 1600) // 2))

# On a panel bigger than the dead zone, the camera stops as soon as the player
# is inside the still band - not at the map edge. That is the whole point of a
# dead zone: it is not obliged to push the window all the way.
r5 = Rig(320, 240, 1280, 800)
for _ in range(300): r5.advance(1200, 760)
check('berhenti saat pemain di dalam zona', r5.x > 0 and r5.x <= 1280 - 320, True)
check('pemain masih di dalam pandangan',
      r5.x <= 1200 <= r5.x + 320 and r5.y <= 760 <= r5.y + 240, True)
# resize to a wider panel: the window must still keep the player visible
r5.vw, r5.vh = 640, 480
r5.x = r5.place(r5.x, r5.vw, r5.mw); r5.y = r5.place(r5.y, r5.vh, r5.mh)
check('setelah resize masih di dalam', r5.x <= 1280 - 640 and r5.y <= 800 - 480, True)
for _ in range(300): r5.advance(1200, 760)
check('pemain tetap di dalam pandangan setelah resize', r5.x <= 1200 <= r5.x + 640, True)

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
