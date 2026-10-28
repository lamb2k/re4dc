#!/usr/bin/env python3
"""Keep reviewable Build29 proofs and production deltas from passing raw gates.

Reject stale source hashes. Raw commands, ELF files and traces remain generated
outputs; their digests plus deterministic reproduction tools are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
SIZE=('executable_bytes','allocated_bytes','zero_fill_bytes')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):
    data=json.loads(path.read_text());assert data['status']=='PASS',path
    for name,digest in data.get('source_sha256',{}).items():
        assert sha(ROOT/name)==digest,(path,name,'stale gate input')
    return data
def write(directory,name,data):
    (directory/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def frame_map(rows):
    return {re.sub(r'^.*?:\d+:\d+:','',r['function']):r['bytes'] for r in rows}
def phase(row):
    return {k:row[k] for k in ('instructions','peak_stack_bytes','model_cycles','trace_sha256','first_argb') if k in row}|dict(
        cold_icache={k:row['cold_icache'][k] for k in ('model_cycles','instruction_fills','scope')},
        traffic={k:row['traffic'][k] for k in ('cached','store_queue','uncached','demand_line_visits','repeated_demand_line_visits','prefetch','scope')})

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('output','off','on','actor','light','actor-host'):
        ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    off,on=load(a.off),load(a.on)
    assert off['baseline']==on['baseline'] and off['off_identity_comparisons']==192
    assert len(on['enabled_compiles'])==5
    target={k:off[k] for k in ('status','scope','baseline','knobs','compiler','compiler_sha256','linker','kos','sdk',
        'pinned_executable_sha256','off_identity_comparisons','disabled_identity','validation_only_overrides')}
    target.update(raw_sha256=dict(off=sha(a.off),on=sha(a.on)),source_sha256=off['source_sha256']|on['source_sha256'],
        enabled_compiles=on['enabled_compiles'],partial_links=on['partial_links'],
        make_rejections=[{k:v for k,v in r.items() if k in ('knob','value','missing','returncode')} for r in on['make_rejections']],
        artifacts={name:{unit:{kind:{k:v for k,v in obj.items() if k!='stack_usage'} for kind,obj in record.items()}
                   for unit,record in rows.items()} for name,rows in (off['artifacts']|on['artifacts']).items()})
    write(a.output,'target-controls.json',target)
    metrics=[]
    for name,control in (('audit','audit'),('scan','plain'),('all','composed')):
        baseline=off['artifacts'][control+'-baseline'];candidate=on['artifacts']['on-'+name]
        units=[]
        for unit,artifacts in candidate.items():
            before=baseline.get(unit,{}).get('o',{});after=artifacts['o']
            oldframes=frame_map(before.get('stack_usage',[]));newframes=frame_map(after['stack_usage'])
            changes=[dict(function=f,before=oldframes.get(f),after=newframes.get(f))
                     for f in sorted(oldframes.keys()|newframes.keys()) if oldframes.get(f)!=newframes.get(f)]
            units.append(dict(unit=unit,delta={k:after[k]-before.get(k,0) for k in SIZE},
                before={k:before.get(k,0) for k in SIZE},after={k:after[k] for k in SIZE},
                max_compiler_local_frame=dict(before=max(oldframes.values(),default=0),after=max(newframes.values(),default=0)),
                changed_local_frames=changes))
        metrics.append(dict(profile=name,baseline_profile=control,
            total_delta={k:sum(r['delta'][k] for r in units) for k in SIZE},units=units))
    write(a.output,'production-metrics.json',dict(status='PASS',baseline=off['baseline'],profiles=metrics,
        scope='Complete selected production TU sections before final link/GC. Allocated includes code/rodata/data/BSS; do not add BSS again. Local compiler frames are not call-chain or IRQ watermarks.',
        raw_target_sha256=dict(off=sha(a.off),on=sha(a.on))))
    for name,path in (('actor-cost',a.actor),('light-cost',a.light)):
        raw=load(path)
        record={k:v for k,v in raw.items() if k not in ('profile_receipt','cases','local_frames','model','flags','options')}
        record['raw_receipt_sha256']=sha(path)
        record['profile_receipt_sha256']=hashlib.sha256(json.dumps(raw['profile_receipt'],sort_keys=True).encode()).hexdigest()
        record['cases']=[{k:v for k,v in c.items() if k!='phases'}|dict(phases={k:phase(v) for k,v in c['phases'].items()}) for c in raw['cases']]
        write(a.output,name+'.json',record)
    host=load(a.actor_host);host['raw_receipt_sha256']=sha(a.actor_host);write(a.output,'actor-attribution.json',host)
    print(json.dumps(dict(status='PASS',profiles={r['profile']:r['total_delta'] for r in metrics})))
if __name__=='__main__':main()
