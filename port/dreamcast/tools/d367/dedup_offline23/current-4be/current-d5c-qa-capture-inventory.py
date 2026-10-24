from pathlib import Path
import hashlib,json,struct
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
rows={}
for arm in ('off','on'):
 for kind in ('boot','warp','h2'):
  cap=E/f'qa-{arm}-{kind}-console-r1';g=json.loads((cap/'qa-gate.json').read_text());assert g['status']=='PASS'
  shots=[]
  for p in sorted((cap/'shots').glob('*/frames/*.png')):
   with p.open('rb') as f:h=f.read(24)
   assert h[:8]==b'\x89PNG\r\n\x1a\n'
   shots.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),size=list(struct.unpack('>II',h[16:24]))))
  rows[arm+'-'+kind]=dict(gate_sha256=sha(cap/'qa-gate.json'),screenshots=shots)
out=E/'qa-capture-inventory-r1.json';assert not out.exists()
out.write_text(json.dumps(dict(source='4be08e0110592510e3630c01fa9f49b3ac2fed3d',kind='INVENTORY_ONLY_NO_WALL_TIME_PIXEL_IDENTITY',captures=rows,limits='Inventory of actual PNG files; no arbitrary wall-time frame equality or complete actor/material visibility claim. Clean boot fb0 images inspected once per arm; standard held-frame comparison is a separate receipt.'),indent=2)+'\n')
print('QA_CAPTURE_INVENTORY',sum(len(x['screenshots']) for x in rows.values()))

