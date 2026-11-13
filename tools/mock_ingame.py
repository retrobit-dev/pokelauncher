import sys, json
sys.path.insert(0,'tools')
from tileset.pixels import Image
from render_map import read_png

meta=json.load(open('docs/tileset/tileset.json')); T=meta['tiles']
doc=json.load(open('app/src/main/assets/tileset/map.json'))
atlas=read_png('docs/tileset/johto-tileset.png')
PX=16
WW,WH=doc['cols']*PX, doc['rows']*PX
world=Image(WW,WH)
for layer in ('ground','building','object'):
    for k,c in doc['cells'].items():
        name=c.get(layer)
        if not name: continue
        t=T.get(name)
        if not t: continue
        x,y=(int(v) for v in k.split(','))
        for yy in range(t['h']):
            for xx in range(t['w']):
                r,g,b,a=atlas.px(t['x']+xx,t['y']+yy)
                if a: world.dot(x*PX+xx,y*PX+yy,(r,g,b))

def rect(img,x,y,w,h,col):
    for yy in range(int(y),int(y+h)):
        for xx in range(int(x),int(x+w)):
            if 0<=xx<img.w and 0<=yy<img.h: img.dot(xx,yy,col)

sp=doc['spawn']; bx,by=sp['x']*PX, sp['y']*PX
for (dx,dy,w,h,col) in ((4,2,8,3,(0x2C,0x24,0x18)),(3,3,10,2,(0xC5,0x3A,0x2D)),
                        (5,5,6,3,(0xF2,0xC7,0x9A)),(4,8,8,5,(0x3E,0x5C,0x8A)),
                        (4,13,3,2,(0x2C,0x24,0x18)),(9,13,3,2,(0x2C,0x24,0x18)),
                        (6,6,1,1,(0x2C,0x24,0x18)),(9,6,1,1,(0x2C,0x24,0x18))):
    rect(world,bx+dx,by+dy,w,h,col)

# Show the world at 2x (a 1280x800 map is the test map; 2x reads like a tablet)
Z=2
scale=Image(WW*Z, WH*Z)
for y in range(WH*Z):
    for x in range(WW*Z):
        scale.buf[(y*WW*Z+x)*4:(y*WW*Z+x)*4+4]=world.buf[((y//Z)*WW+(x//Z))*4:((y//Z)*WW+(x//Z))*4+4]

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
panel(scale,28,28,470,236)
text(scale,56,52,'12:35',7,INK)
text(scale,332,58,'SIANG',3,GOLD)
for i in range(10): rect(scale,110+i*30,112,22,14,RED)
for i in range(10): rect(scale,110+i*30,140,22,14,GOLD if i<7 else SHADE)
rect(scale,56,172,380,2,SHADE)
text(scale,56,192,'1831',4,FAINT)

for i in range(3):
    panel(scale,28+i*250,H-148,224,120)
    rect(scale,60+i*250,H-108,160,10,INK)
    rect(scale,60+i*250,H-84,104,8,FAINT)

panel(scale,W-600,H-148,572,120)
rect(scale,W-572,H-126,76,76,(0x2C,0x24,0x18))
rect(scale,W-572,H-126,76,5,(0x56,0x84,0x8C))
rect(scale,W-470,H-116,340,14,INK)
rect(scale,W-470,H-88,240,9,FAINT)
rect(scale,W-470,H-66,300,9,FAINT)

scale.to_png('/tmp/ingame.png')
print('/tmp/ingame.png', scale.w,'x',scale.h)
