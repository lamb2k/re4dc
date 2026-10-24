"""Opaque graph potential only. No asset/runtime/pixel admission or timing claim."""
import argparse,json,struct,sys
from collections import Counter
from pathlib import Path
from estimate_loaded import estimate,groups,pin,sha,SOURCE,HERE
from graph_strip import graph_partition,tie_risks,topology_bound

def candidates(mesh,policy,sg=None):
 p,ordered,base=estimate(mesh,policy,sg)
 modes={k:[] for k in ('fixed_provoking','gouraud_cyclic','guarded_cyclic')};risks=Counter();totals=Counter()
 for li,l in enumerate(p.lets):
  old=l['strips'];corners=p.decoded(l);ends=groups(p,sg,li);start=0;bounds=[];rows={k:[] for k in modes};counts={k:[] for k in modes}
  for end in ends:
   ss=old[start:end];rr=tie_risks(ss,corners) if ordered[li]['admitted'] else {};totals['groups']+=1
   bound=topology_bound(ss,corners) if ordered[li]['admitted'] else dict(min_corners=sum(map(len,ss)))
   bounds.append(bound['min_corners']);totals['optimistic_min_corners']+=bound['min_corners']
   for k in rr:risks[k]+=1
   for k in modes:
    allow=ordered[li]['admitted'] and (k!='guarded_cyclic' or not rr)
    out=graph_partition(ss,corners,k!='fixed_provoking') if allow and ss else ss
    rows[k].extend(out);counts[k].append(len(rows[k]))
   start=end
  assert start==len(old)
  for k in modes:modes[k].append(dict(strips=rows[k],group_ends=counts[k],admitted=ordered[li]['admitted'],optimistic_group_min_corners=bounds))
 result={}
 for k,lets in modes.items():
  pool=bytearray();seen=set();oldc=sum(sum(map(len,l['strips'])) for l in p.lets);newc=sum(sum(map(len,l['strips'])) for l in lets)
  for l,out in zip(p.lets,lets):
   raw=(mesh[p.h[14]+l['fs']:p.h[14]+l['fs']+2*l['n']] if l['ix'] else b'')+b''.join(bytes([len(s)])+bytes(s) for s in out['strips'])
   if raw not in seen:
    if len(pool)&1:pool.append(0)
    seen.add(raw);pool.extend(raw)
  size=((p.h[14]+len(pool)+31)&~31)+len(mesh)-p.h[15]
  result[k]=dict(corners_before=oldc,corners_after=newc,reduction_percent=100*(1-newc/oldc),changed_meshlets=sum(a['strips']!=b['strips'] for a,b in zip(p.lets,lets)),estimated_physical_bytes=size,physical_byte_delta=size-len(mesh))
 return p,modes,dict(base=base,modes=result,risk_groups=dict(risks),group_count=totals['groups'],optimistic_all_loaded_min_corners=totals['optimistic_min_corners'],scope='All loaded LODs, not camera gate. Unguarded modes retain known tie/degenerate risks; guarded mode still lacks near-equal depth/FP clipping proof. No assets written.')

def require_pin(path,row):
 if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:raise ValueError('input pin mismatch: '+str(path))
def frozen_variants():
 frozen=json.loads((HERE.parent/'strip-share-private-pins.json').read_text())
 return {Path(v['output_directory']).name.split('-')[0]:v for v in frozen['variants']}
def checked_inputs(inputs,assets):
 r=json.loads(inputs.read_text())
 if r['source']!=SOURCE:raise ValueError('wrong runtime source')
 frozen=frozen_variants()
 for room,row in r['rooms'].items():
  files={k:Path(v['path']) for k,v in row['files'].items()}
  for k,path in files.items():require_pin(path,row['files'][k])
  mesh=assets/(room+'-stripshare-v1')/'ps2-dd3.re4mesh';sg=mesh.with_suffix('.r4sg') if room=='r101' else None
  for path in [mesh]+([sg] if sg else []):require_pin(path,frozen[room]['files'][path.name])
  p,modes,stats=candidates(mesh.read_bytes(),files['r4pw'].read_bytes(),sg.read_bytes() if sg else None)
  oh=struct.unpack_from('<4s19I',files['re4mesh'].read_bytes())
  if p.h[18]!=oh[3] or (p.h[17] or len(p.data))!=oh[2]:raise ValueError('baseline CRC/extent binding')
  yield room,p,modes,dict(input=pin(mesh),policy=pin(files['r4pw']),groups=pin(sg) if sg else None,**stats)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--assets',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 out={}
 for room,p,modes,stats in checked_inputs(a.inputs,a.assets):
  out[room]=stats;print(room,json.dumps(stats['modes']),flush=True)
 a.output.write_text(json.dumps(dict(source=SOURCE,status='OFFLINE_GRAPH_POTENTIAL_NOT_ADMISSION',inputs_sha256=sha(a.inputs),helper_files={p.name:sha(p) for p in HERE.glob('*.py')},rooms=out),indent=2)+'\n')
if __name__=='__main__':main()
