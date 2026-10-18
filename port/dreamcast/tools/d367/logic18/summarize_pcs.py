#!/usr/bin/env python3
"""Read existing PCS1 samples using exact ELF extents; no nearest-symbol guessing."""
import argparse,bisect,collections,json,struct
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--pcs',type=Path,required=True);p.add_argument('--symbols',type=Path,required=True)
p.add_argument('--frames',required=True,help='inclusive first:last:stride matching trace samples')
p.add_argument('--out',type=Path,required=True);a=p.parse_args()
first,last,stride=map(int,a.frames.split(':'));wanted=set(range(first,last+1,stride))
s=json.loads(a.symbols.read_text())['symbols'];starts=[r['start'] for r in s]
data=a.pcs.read_bytes();h=struct.unpack('<32I',data[:128]);assert h[:3]==(0x31534350,1,32)
assert (len(data)-128)%8==0
counts=collections.Counter();tids=collections.Counter();perframe=collections.Counter();seen=set();closed=set();frame=None;lost=late=foreign=0
for w0,w1 in struct.iter_unpack('<II',data[128:]):
 if w1==0xffffffff:
  if frame in wanted:lost+=w0
  continue
 if w1&0x80000000:
  if frame in wanted:closed.add(frame)
  frame=w0
  if frame in wanted:seen.add(frame)
  continue
 if frame not in wanted:continue
 perframe[frame]+=1;tids[w0>>23]+=1
 late+=bool(w1&0x40000000)
 if w1&0x10000000:foreign+=1;counts['FOREIGN']+=1;continue
 pc=0x8c000000+((w0&0x7fffff)<<1);i=bisect.bisect_right(starts,pc)-1
 name=s[i]['name'] if i>=0 and pc<s[i]['end'] else 'UNKNOWN'
 counts[name]+=1
assert seen==wanted and closed==wanted,(sorted(wanted-seen),sorted(wanted-closed))
assert not lost, f'{lost} records lost inside selected window'
ms_each=h[5]*80e-6
result=dict(frames=sorted(wanted),samples=sum(counts.values()),samples_by_frame=dict(perframe),samples_by_thread=dict(tids),lost=lost,late=late,foreign=foreign,nominal_period_ms=ms_each,units='Flycast guest TMU statistical samples converted with nominal period; not host wall time or hardware measurement',resolution_ms_per_frame=ms_each/len(wanted),flat_self=[dict(name=k,samples=v,ms_per_frame=v*ms_each/len(wanted)) for k,v in counts.most_common()],limitations=['Statistical sample counts have sampling error and 1ms nominal period; low-count functions are not precise timings.','Includes explicit wait/idle time; do not interpret total as useful logic work.','No inclusive or owner attribution is inferred from sampled PC/PR.'])
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='flat_self'},indent=2));print(json.dumps(result['flat_self'][:15],indent=2))
