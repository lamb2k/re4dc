import json, math, os
d=json.load(open('/root/probe/lanes-20261016/ch2/k/route1.json'))['rooms']
D='/root/probe/lanes-20261016/ch2/tree/port/dreamcast/tools/d367/ch2/warps'
CH2=('r118','r112','r111','r113','r11c','r11d','r11e','r10f','r11f')
def doors(a): return d[a]['doors']
def back(a,b):  # the door record in b leading to a = arrival point in a next to a's door to b
    for x in doors(b):
        if x['dst']==a: return x
def hop(a,b,frame0):
    x=back(a,b)
    if not x: return None
    p=x['pos']; ang=x['angle']+math.pi
    if ang>math.pi: ang-=2*math.pi
    # step 600 units through the doorway (towards the door = facing ang), Ashley beside, then A presses
    gx=p[0]+600*math.sin(ang); gz=p[2]+600*math.cos(ang)
    lines=['goto %d %d %d %d %.4f sub'%(frame0,gx,p[1],gz,ang)]
    for i in range(4): lines.append('act %d a 4'%(frame0+60+80*i))
    lines.append('act %d fwd 30'%(frame0+400))
    return lines,p,x['angle']
pairs=[]
for a in CH2:
    for x in doors(a):
        b=x['dst']
        if b in CH2:
            k=tuple(sorted((a,b)))
            if k not in [tuple(sorted(q)) for q in pairs]: pairs.append((a,b))
made=[]
for a,b in pairs:
    h1=hop(a,b,60)
    if not h1: print('no back door',a,b); continue
    lines1,p,ang=h1
    h2=hop(b,a,240) if b!='r200' else None
    txt=['name ch2-door-%s-%s'%(a,b),'# lane ch2code16: door %s -> %s%s (arrival points from stage_route.py; Ashley beside: goto sub)'%(a,b,' -> back' if h2 else ''),
         'room 0x%s'%a[1:],'pos %d %d %d'%tuple(p),'ang %.4f'%ang,'find 0x00100000','status 3 0x04000000','inv default','god']+lines1
    if h2: txt+=['entry 2']+h2[0]
    open('%s/d-%s-%s.txt'%(D,a,b),'w').write('\n'.join(txt)+'\n'); made.append('%s-%s'%(a,b))
print(made)
