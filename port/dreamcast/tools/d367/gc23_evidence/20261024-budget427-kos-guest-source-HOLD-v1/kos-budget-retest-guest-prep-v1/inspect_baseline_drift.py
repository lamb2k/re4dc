"""Read-only exact path/stat drift; no repair, deletion or baseline refresh."""
from pathlib import Path
import json,sys,types
HERE=Path(__file__).resolve().parent
p=HERE/'common.py';c=types.ModuleType('guest_common');c.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),c.__dict__);k=c.context();b=k.read(c.MEDIA/'BASELINE.json');total,files,_=k.scan(b['roots']);before=b['members'];changes=[]
for path in sorted(set(files)|set(before)):
 old=before.get(path);now=files.get(path)
 if old is None or now is None or any(old[v]!=now[v] for v in ['size','dev','ino']):
  changes.append(dict(path=path,old=old,current=now,current_identity=None if now is None else c.row(path)))
c.fresh(HERE/'BASELINE-DRIFT.json',dict(status='HOLD_UNCHANGED_GUARD',baseline_unique=b['unique_bytes'],actual_unique=total,delta=total-b['unique_bytes'],changes=changes,no_mutation=True,SDK=0,guest=0))
print(json.dumps(dict(baseline_unique=b['unique_bytes'],actual_unique=total,changes=changes),indent=1))
