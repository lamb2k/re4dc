"""Label and assemble already-rendered Blender comparisons; no new visual content."""
import argparse
import json
from pathlib import Path
import shutil
from PIL import Image,ImageDraw,ImageFont,ImageStat

ap=argparse.ArgumentParser();ap.add_argument('--dir',type=Path,required=True);ap.add_argument('--mirror',type=Path);ap.add_argument('--encoded',action='store_true')
a=ap.parse_args();root=a.dir
try:font=ImageFont.truetype('arial.ttf',19)
except OSError:font=ImageFont.load_default(size=19)
count=json.loads((root/'BLENDER-BAKE-RECEIPT.json').read_text())['target_triangles']
labels=['A: PS2 source core | 407 triangles',f'Plain C9 shell | {count} triangles',f'Baked C9 shell | {count} triangles']
names=['A_PS2_SOURCE','PLAIN_C9','BAKED_C9']
prefix='BLENDER-'
if a.encoded:labels[2]=f'Baked shell | {count} triangles | native UV / decoded VQ';names[2]='VQ_BAKED_C9';prefix='BLENDER-VQ-'
def row(frame):
    im=Image.new('RGB',(1920,530),'#1c1c1c');d=ImageDraw.Draw(im)
    for i,(name,label) in enumerate(zip(names,labels)):
        im.paste(Image.open(root/(name+'-%02d.png'%frame)).convert('RGB'),(i*640,50));d.text((i*640+15,13),label,font=font,fill='white')
    return im
sheet=Image.new('RGB',(1920,1110),'#1c1c1c');sheet.paste(row(0),(0,50));sheet.paste(row(4),(0,580));d=ImageDraw.Draw(sheet)
d.text((15,13),'BLENDER CORE ONLY: unchanged dormer/other materials omitted in every column. No Flycast, console or acceptance.',font=font,fill='#f1d89a')
sheet.save(root/(prefix+'COMPARISON.png'))
frames=[]
for frame in range(12):
    im=row(frame);d=ImageDraw.Draw(im);d.text((1200,510),'BLENDER preview / unaccepted',font=font,fill='#f1d89a');frames.append(im)
frames[0].save(root/(prefix+'ORBIT.gif'),save_all=True,append_images=frames[1:],duration=180,loop=0,optimize=True)
checks={}
for role in ('wall','roof'):
    image=Image.open(root/(role+'-baked.png')).convert('RGB');colors=image.getcolors(512*512)
    checks[role]={'dimensions':list(image.size),'unique_rgb_colors':len(colors),'channel_extrema':image.getextrema()}
    assert image.size==(512,512) and len(colors)>256,'flat/missing bake'
(root/'IMAGE-CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
if a.mirror:
    a.mirror.mkdir(parents=True,exist_ok=True)
    for name in (prefix+'COMPARISON.png',prefix+'ORBIT.gif'):
        shutil.copy2(root/name,a.mirror/name);assert (root/name).read_bytes()==(a.mirror/name).read_bytes()
print(json.dumps(checks,indent=2))
