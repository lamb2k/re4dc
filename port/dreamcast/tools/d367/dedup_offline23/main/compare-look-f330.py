from pathlib import Path
import sys, json, hashlib
import numpy as np
from PIL import Image
root=Path(sys.argv[1]); scene=sys.argv[2]
rows=[]
for arm in ('off','on'):
 cap=root/f'{scene}-{arm}-console-f330-r3'
 rr=json.loads((cap/'run-result.json').read_text())
 assert rr['emu']=='console' and rr.get('stopped')=='goal', rr
 log=(cap/'run-output.txt').read_text(errors='replace')
 assert 'warp: frozen at tick 330' in log
 ps=sorted((cap/'shots').glob('t*/frames/fb*.png'))[-4:]
 rows.append([(p,np.asarray(Image.open(p).convert('RGB'))) for p in ps])
best=None
for a,A in rows[0]:
 for b,B in rows[1]:
  assert A.shape==B.shape
  d=np.any(A!=B,axis=2); n=int(d.sum())
  if best is None or n<best['different_pixels']:
   ys,xs=np.where(d)
   best=dict(scene=scene,off=str(a),on=str(b),shape=list(A.shape),different_pixels=n,total_pixels=int(d.size),bounds=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())] if n else None,off_sha256=hashlib.sha256(a.read_bytes()).hexdigest(),on_sha256=hashlib.sha256(b.read_bytes()).hexdigest(),row_counts=[int(i) for i in d.sum(axis=1)],qualification='Exact frozen tick; diagnostic overlay differences are included. No masking.')
(root/f'look-{scene}-f330-r3.json').write_text(json.dumps(best,indent=2)+'\n')
print(json.dumps({k:v for k,v in best.items() if k!='row_counts'}))
