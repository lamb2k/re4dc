#!/usr/bin/env python3
"""Summarize disjoint costs and validated owner coverage; never add inclusive rows."""
import argparse, csv, json
from array import array
from collections import Counter
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix',type=Path,required=True)
p.add_argument('--symbols',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--model',default='nominal')
a=p.parse_args()
symbols=json.loads(a.symbols.read_text())['symbols']; names={r['symbol']:r['name'] for r in symbols}; names[0]='UNKNOWN'
explicit={r['symbol']:r['owner'] for r in symbols if r['owner']}
flat=Counter(); inclusive=Counter(); calls=Counter(); owner_raw=Counter(); owner_valid=Counter(); root_counts=Counter(); valid_roots=Counter(); cov=Counter(); samples=set()
with Path(str(a.prefix)+'.function_frames.tsv').open() as f:
 for r in csv.DictReader(f,delimiter='\t'):
  flat[int(r['symbol'])]+=int(r['cycles16']);samples.add(int(r['sample']))
last=None
with Path(str(a.prefix)+'.contexts.tsv').open() as f:
 for row in csv.DictReader(f,delimiter='\t'):
  sample,n,parent,symbol,kind,owner,complete,invalid,self16,inc16=map(int,row.values())
  if sample!=last:
   roots=array('i'); owners=array('B'); valid=array('B');last=sample
  assert n==len(roots)
  # Explicit named roots, owner-changing exact-tail entries and IRQ roots establish a span.
  newroot=bool(owner and (n==0 or parent>=n or owners[parent]!=owner or explicit.get(symbol)==owner or kind==2))
  root=n if newroot else (roots[parent] if parent<n else -1)
  roots.append(root);owners.append(owner);valid.append(bool(complete and not invalid))
  if newroot:
   root_counts[owner]+=1
   if valid[n]:valid_roots[owner]+=1
  owner_raw[owner]+=self16
  if root>=0 and valid[root]:owner_valid[owner]+=self16
  cov['total16']+=self16
  if invalid:cov['invalid_invocation_self16']+=self16
  if complete and not invalid:
   cov['complete_valid_invocation_self16']+=self16
   if symbol:inclusive[symbol]+=inc16;calls[symbol]+=1
N=len(samples);scale=16*200000*N
rows=lambda counter:[dict(name=names[k],symbol=k,ms_per_sample=v/scale,total16=v,complete_valid_calls=calls[k]) for k,v in counter.most_common()]
result=dict(samples=N,units=f'MODELLED {a.model} milliseconds per captured physical iteration; scheduler count must be qualified independently',flat_self=rows(flat),complete_valid_inclusive=rows(inclusive),coverage=dict(cov),owners=[dict(owner=k,raw_ms=v/scale,validated_root_ms=owner_valid[k]/scale,observed_roots=root_counts[k],validated_roots=valid_roots[k]) for k,v in sorted(owner_raw.items())],limitations=['Owner raw includes incomplete roots; validated-root cost is partial coverage, not an extrapolated owner total.','Named inclusive rows overlap and must not be summed.','IRQ is an independent explicit execution owner; IRQ roots do not complete through ordinary returns.','Unknown tail functions are excluded from named inclusive ranks.'])
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('flat_self','complete_valid_inclusive')},indent=2))
