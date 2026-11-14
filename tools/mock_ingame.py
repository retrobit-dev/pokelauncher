#!/usr/bin/env python3
"""Draws the in-game screen: the starter village, the trainer, and the HUD.

    python3 tools/mock_ingame.py [--night] [out.png]

This is a mockup, not the app: the HUD labels here are blocks of colour rather
than text, because the real labels live in Compose. Its job is to keep an
honest picture of the layout and the palette in the repo, so a change that makes
the HUD cover the field is visible without a tablet.
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from tileset.pixels import Image
from render_map import read_png

NIGHT = '--night' in sys.argv
# --field draws only what is on the screen: the map and the player, no HUD.
# That is what the app's home screen shows right now (SHOW_WORLD is off, so the
# HUD has not been rebuilt yet), and it is what the tablet preview publishes.
FIELD = '--field' in sys.argv
_default = ('field.png' if FIELD else
            ('ingame-night.png' if NIGHT else 'ingame.png'))
OUT = next((a for a in sys.argv[1:] if a.endswith('.png')),
           os.path.join(HERE, '..', 'docs', 'editor', _default))

meta=json.load(open(os.path.join(ROOT,'docs/tileset/tileset.json'))); T=meta['tiles']
# One map file, the one the app loads. The editor used to keep a separate
# working copy under docs/, and the tablet shot could be built from a map the
# game never saw; drawing from the asset removes that gap by construction.
_map = os.path.join(ROOT,'app/src/main/assets/tileset/map.json')
doc=json.load(open(_map))
atlas=read_png(os.path.join(ROOT,'docs/tileset/johto-tileset.png'))
PX=16
WW,WH=doc['cols']*PX, doc['rows']*PX
# Empty ground: the same moss green the app paints behind the tiles
# (WorldCanvas.kt), so an undrawn map looks the same here as on the device.
world=Image(WW,WH,(0x5C,0x7A,0x45))
for layer in ('ground','building','object'):
    for k,c in doc['cells'].items():
        name=c.get(layer)
        if not name: continue
        t=T.get(name)
        if not t: continue
        x,y=(int(v) for v in k.split(','))
        # a multi-cell tile grows down and right from its cell (see render_map.py)
        for yy in range(t['h']):
            for xx in range(t['w']):
                r,g,b,a=atlas.px(t['x']+xx,t['y']+yy)
                if a: world.dot(x*PX+xx,y*PX+yy,(r,g,b))

def night(world, lights, radius=6):
    """Blue dusk everywhere, with a soft warm pool around each torch.

    The app draws this per cell in Compose; here it is per pixel so the mockup
    reads the way the real screen does: brightest at the torch, fading out.
    """
    out=Image(world.w, world.h)
    out.buf[:]=world.buf
    darkness=0.62
    for y in range(world.h):
        cy=y/PX
        for x in range(world.w):
            cx=x/PX
            best=0.0
            for (lx,ly) in lights:
                d=max(abs(cx-(lx+0.5)), abs(cy-(ly+0.5)))
                if d<radius:
                    best=max(best, 1.0-(d/radius))
            a=darkness-(darkness-0.06)*best
            i=(y*world.w+x)*4
            for c,base in enumerate((0x0C,0x15,0x33)):
                out.buf[i+c]=int(out.buf[i+c]*(1-a)+base*a)
    return out

def rect(img,x,y,w,h,col):
    for yy in range(int(y),int(y+h)):
        for xx in range(int(x),int(x+w)):
            if 0<=xx<img.w and 0<=yy<img.h: img.dot(xx,yy,col)

# The player, from the same sheet the app loads: row 1 is DOWN, frame 0 is
# standing. Drawn from the asset rather than by hand, so the mockup cannot
# disagree with the game about what the player looks like.
sp=doc['spawn']; bx,by=sp['x']*PX, sp['y']*PX
player=read_png(os.path.join(ROOT,'app/src/main/assets/sprites/player.png'))
# 32x32 frames, row 1 is DOWN, and the frame is anchored on the feet: the bottom
# of the frame sits on the bottom of the spawn cell, so the head rises one cell.
FRAME=32
for yy in range(FRAME):
    for xx in range(FRAME):
        r,g,b,a=player.px(xx,FRAME+yy)
        if a: world.dot(bx+xx,by+yy+ (PX-FRAME), (r,g,b))

# No crops, no torches, no invented scenery.
#
# This block used to draw a planted field and three torches next to the player,
# gated on the map having *any* cells. That is why the tablet render showed a
# garden that the map editor never had: crops and torches are runtime state in
# the app, and the mock was making them up. A picture of the home screen is only
# worth looking at if it shows what the map file actually contains, so the field
# is gone. When crops exist in a save, drawing them belongs here as real data
# read from that save, not as decoration invented at render time.
#
# The one thing worth keeping is the night pass: it darkens the real map.
torches = ()

if NIGHT:
    world = night(world, torches)

# What the panel actually shows: the camera window at the app's default zoom,
# not the whole map shrunk to fit. Rendering all 80x50 cells at 2x made the
# world look tiny and was the reason the tablet shot read as a map rather than
# a place. DEFAULT_ZOOM must match TouchInput.DEFAULT, and
# tools/verify.py fails if the two drift apart.
DEFAULT_ZOOM = 10
PANEL_W, PANEL_H = 2560, 1600
Z = DEFAULT_ZOOM
view_w, view_h = PANEL_W // Z, PANEL_H // Z      # 320 x 200 map px

# centre on the player, then clamp so the window never leaves the map
x0 = max(0, min(WW - view_w, sp['x'] * PX - view_w // 2)) if WW > view_w else (WW - view_w) // 2
y0 = max(0, min(WH - view_h, sp['y'] * PX - view_h // 2)) if WH > view_h else (WH - view_h) // 2

scale = Image(PANEL_W, PANEL_H)
for y in range(PANEL_H):
    sy = y0 + y // Z
    for x in range(PANEL_W):
        sx = x0 + x // Z
        if 0 <= sx < WW and 0 <= sy < WH:
            src = (sy * WW + sx) * 4
            dst = (y * PANEL_W + x) * 4
            scale.buf[dst:dst + 4] = world.buf[src:src + 4]

# Night: the same scene, one blue overlay, with the lit cells left clear.
PAPER=(251,243,220); INK=(59,47,30); FAINT=(154,135,104)
RED=(197,58,45); GOLD=(224,184,76); SHADE=(233,215,174)
def panel(img,x,y,w,h):
    rect(img,x,y,w,h,INK); rect(img,x+4,y+4,w-8,h-8,PAPER)
G={'0':'111,101,101,101,111','1':'010,110,010,010,111','2':'111,001,111,100,111',
   '3':'111,001,111,001,111','4':'101,101,111,001,001','5':'111,100,111,001,111',
   '6':'111,100,111,101,111','7':'111,001,010,010,010','8':'111,101,111,101,111',
   '9':'111,101,111,001,111',':':'000,010,000,010,000'}
def text(img,x,y,s,k,col):
    cx=x
    for ch in s:
        for ry,row in enumerate(G.get(ch,'000,000,000,000,000').split(',')):
            for rx,bit in enumerate(row):
                if bit=='1': rect(img,cx+rx*k,y+ry*k,k,k,col)
        cx+=4*k

W,H=scale.w,scale.h

# The move pad, bottom-left: the same disc and knob the app draws, from the same
# numbers (Joystick.kt: 76 dp radius, 30 dp knob, 20% dead zone). Drawn here
# because the pad is part of the screen, and a tablet shot that omits a control
# the player uses every few seconds is a picture of a different app.
PAD_R = 76
def draw_pad():
    cx, cy = PAD_R + 18, H - PAD_R - 18
    for y in range(-PAD_R, PAD_R + 1):
        for x in range(-PAD_R, PAD_R + 1):
            if x * x + y * y <= PAD_R * PAD_R:
                # paper at 55% over the grass, like Compose draws it
                gx, gy = cx + x, cy + y
                if 0 <= gx < W and 0 <= gy < H:
                    r0, g0, b0, _ = scale.px(gx, gy)
                    scale.dot(gx, gy, (
                        int(r0 * 0.45 + PAPER[0] * 0.55),
                        int(g0 * 0.45 + PAPER[1] * 0.55),
                        int(b0 * 0.45 + PAPER[2] * 0.55),
                    ))
    # rim, drawn as a ring of ink
    for i in range(360 * 2):
        import math
        a = i / 2 * math.pi / 180
        for w in (0, 1):
            x = int(cx + (PAD_R - w) * math.cos(a))
            y = int(cy + (PAD_R - w) * math.sin(a))
            if 0 <= x < W and 0 <= y < H:
                scale.dot(x, y, INK)
    # the knob, resting at the centre
    for y in range(-30, 31):
        for x in range(-30, 31):
            if x * x + y * y <= 900:
                gx, gy = cx + x, cy + y
                if 0 <= gx < W and 0 <= gy < H:
                    scale.dot(gx, gy, PAPER)
    for i in range(360):
        import math
        a = i * math.pi / 180
        x = int(cx + 30 * math.cos(a)); y = int(cy + 30 * math.sin(a))
        if 0 <= x < W and 0 <= y < H:
            scale.dot(x, y, INK)


def draw_hud():
  # Unused: the home screen has no HUD (see the call site). Kept while the HUD
  # branch behind SHOW_WORLD still exists, so turning it on has a picture to
  # compare against; delete both together.
  # The MatePad Mini camera sits inside the panel, top-left. GameHud applies
  # WindowInsets.displayCutout, so everything here starts to its right.
  CUTOUT = 116
  panel(scale,CUTOUT,28,470,236)
  text(scale,CUTOUT+28,52,'20:41' if NIGHT else '12:35',7,INK)
  text(scale,CUTOUT+304,58,'MALAM' if NIGHT else 'SIANG',3,RED if NIGHT else GOLD)
  for i in range(10): rect(scale,CUTOUT+82+i*30,112,22,14,RED)
  for i in range(10): rect(scale,CUTOUT+82+i*30,140,22,14,GOLD if i<7 else SHADE)
  rect(scale,CUTOUT+28,172,380,2,SHADE)
  text(scale,CUTOUT+28,192,'1831',4,FAINT)

  for i in range(3):
      panel(scale,250+i*250,H-148,224,120)
      rect(scale,282+i*250,H-108,160,10,INK)
      rect(scale,282+i*250,H-84,104,8,FAINT)

  # top-right: the menu button that opens settings and the app list
  rect(scale,W-116,28,88,88,INK)
  rect(scale,W-112,32,80,80,PAPER)
  for i in range(3):
      rect(scale,W-94,54+i*18,44,5,INK)

  panel(scale,W-600,H-148,572,120)
  rect(scale,W-572,H-126,76,76,(0x2C,0x24,0x18))
  rect(scale,W-572,H-126,76,5,(0x56,0x84,0x8C))
  rect(scale,W-470,H-116,340,14,INK)
  rect(scale,W-470,H-88,240,9,FAINT)
  rect(scale,W-470,H-66,300,9,FAINT)


# The home screen shows the map, the character and the pad - no clock, no
# vitals, no verb buttons. That is the screen the app actually draws
# (LauncherScreen: SHOW_WORLD = false), so the tablet shot draws the same thing;
# a mock with a HUD the device does not have would be a picture of another app.
# --field is the same picture with no controls at all.
if not FIELD:
    draw_pad()

scale.to_png(OUT)
print(OUT, scale.w,'x',scale.h)
