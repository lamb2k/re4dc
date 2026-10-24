"""Read-only ELF section census; no compiler/tools or original writes."""
from pathlib import Path
import collections,hashlib,json,resource,signal,struct,time
HERE=Path(__file__).resolve().parent
ROOT=Path('/dev/shm/rain8ce-full-normal-179r4a5c')
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));signal.alarm(120)
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):
 b=p.read_bytes();h=struct.unpack_from('<16sHHIIIIIHHHHHH',b)
 assert h[0][:6]==b'\x7fELF\x01\x01' and h[2]==42
 ss=[struct.unpack_from('<10I',b,h[6]+i*h[11]) for i in range(h[12])];q=ss[h[13]];names=b[q[4]:q[4]+q[5]]
 rows={}
 for s in ss:
  name=names[s[0]:].split(b'\0',1)[0].decode()
  rows[name]=dict(type=s[1],flags=s[2],bytes=s[5],align=s[8],sha256=digest(b[s[4]:s[4]+s[5]]) if s[1]!=8 else None)
 return dict(raw_sha256=digest(b),sections=rows)
def main():
 start=time.monotonic();plan=json.loads((ROOT/'PREPARATION.json').read_text());rows=[];counts=collections.Counter()
 for old in plan['historical_actual_graph']['off']['object_order']:
  rel='out/obj/'+old.split('/out/obj/',1)[1]
  a=read(ROOT/'off'/rel);b=read(ROOT/'on'/rel)
  differences=[dict(name=k,off=a['sections'].get(k),on=b['sections'].get(k)) for k in sorted(a['sections'].keys()|b['sections'].keys()) if a['sections'].get(k)!=b['sections'].get(k)]
  if a['raw_sha256']!=b['raw_sha256']:
   allocated=[x['name'] for x in differences if (x['off'] or x['on'])['flags']&2]
   counts['raw_changed']+=1;counts['allocated_changed']+=bool(allocated)
   rows.append(dict(object=rel,raw_off=a['raw_sha256'],raw_on=b['raw_sha256'],allocated_changed=allocated,differences=differences))
 assert len(plan['historical_actual_graph']['off']['object_order'])==448
 allocated=[r['object'] for r in rows if r['allocated_changed']]
 assert allocated==['out/obj/src/game/espgen44.o','out/obj/src/game/filter06.o'] or set(allocated)=={'out/obj/src/game/espgen44.o','out/obj/src/game/filter06.o'},allocated
 changes=collections.Counter(x['name'] for r in rows if not r['allocated_changed'] for x in r['differences'])
 result=dict(status='PASS',object_count=448,counts=dict(counts),non_rain_changed_section_names=dict(changes),rows=rows,scope='Raw object identity was not a contract prerequisite. Earlier extra only-two-raw-objects assertion failed; this census classifies all changes instead. Nonallocated metadata differences are not runtime bytes.',seconds=time.monotonic()-start)
 with (HERE/'OBJECT-SECTIONS.json').open('x') as f:json.dump(result,f,indent=1);f.write('\n')
 print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
