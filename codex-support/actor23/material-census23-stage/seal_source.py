"""Seal only source and small metadata. Does not approve or execute anything."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
def seal(root):
 files={}
 for p in sorted(root.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.name not in ('SOURCE-SEAL.json','HOST-TEST-RESULTS.json','STATUS.md','HANDBACK.md'):
   files[p.relative_to(root).as_posix()]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 out=dict(status='MATERIAL_CENSUS23_SOURCE_ONLY_PENDING_EXTERNAL_REVIEWS',source='f2405bb06ebaff6e2a7681479d5308ec5d3b988a',runtime_admitted=False,files=files)
 (root/'SOURCE-SEAL.json').write_text(json.dumps(out,indent=2)+'\n')
 return hashlib.sha256((root/'SOURCE-SEAL.json').read_bytes()).hexdigest()
if __name__=='__main__':
 run=P.parent/'material-census23-run';runpin=seal(run)
 path=P/'contracts.py';text=path.read_text();import re
 text=re.sub(r"CENSUS_SHA='[^']+'", "CENSUS_SHA='"+runpin+"'",text);path.write_text(text)
 print(json.dumps(dict(run_seal_sha256=runpin,stage_seal_sha256=seal(P))))
