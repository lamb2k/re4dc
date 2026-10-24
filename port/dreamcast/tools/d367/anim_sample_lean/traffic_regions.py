#!/usr/bin/env python3
"""Attribute complete compiled sampler/pose data traffic by mapped region.

This reruns the target fixtures without a timing model. Regions are disjoint
byte ranges, but adjacent regions can share a 32-byte line: region line counts
must not be summed as a whole-call cache working set. Stack/literal reductions
are identified separately from key payload traffic. Actual addresses remain
synthetic; distinct lines and repeated visits are not cache-miss predictions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import target_run as sample
import pose_run as pose


def summarize(machine,regions):
    groups={name:[] for name in (*regions,'literal_or_other')}
    for event in machine.memory_events:
        address,size=event[3:5]
        matches=[name for name,(lo,hi) in regions.items() if lo<=address<hi]
        assert len(matches)<=1,(event,matches)
        name=matches[0] if matches else 'literal_or_other'
        if matches:assert address+size<=regions[name][1],('cross-region access',event,name)
        groups[name].append(event)
    return {name:dict(**sample.traffic(events,())['cached'],
        demand_line_visits=sample.traffic(events,())['demand_line_visits'],
        repeated_demand_line_visits=sample.traffic(events,())['repeated_demand_line_visits'])
        for name,events in groups.items()}


def sampler_case(build,case):
    rows={}
    for arm,meta in build['arms'].items():
        m,s,l=sample.load(Path(meta['elf']))
        raw=sample.payload(case['kind'],case['frames']);key=l[4]+case['alignment']
        m.map(key,raw)
        m.map(l[5],struct.pack('<ffIB3xI',case['frame'],case['max_frame'],case['flags'],case['kind'],key))
        m.map(l[6],struct.pack('<3f',17.25,-33.5,49.75));m.map(l[7],struct.pack('<3H',*case['history']))
        entry=s['_HermiteInterpolation'][0]
        if arm=='l1' and case['frame']>=case['max_frame'] and case['flags']&6!=4:
            entry=next(v[0] for n,v in s.items() if 'HermiteInterpolationClamped' in n)
        m.reg[5],m.reg[6]=l[6],l[7]
        m.observe_start();m.execute(entry,l[5]);m.observe_stop()
        regions={'parameters':(l[5],l[5]+20),'output':(l[6],l[6]+12),
            'history':(l[7],l[7]+6),'stack':(m.minimum_sp,m.initial_regs[15])}
        cursor=key;stride={0:12,5:6,6:4}[case['kind']]
        for axis,frames in enumerate(case['frames']):
            count=len(frames)
            regions[f'axis{axis}_count']=(cursor,cursor+2);cursor+=2
            regions[f'axis{axis}_frames']=(cursor,cursor+count*2);cursor+=count*2
            regions[f'axis{axis}_payload']=(cursor,cursor+count*stride);cursor+=count*stride
        assert cursor==key+len(raw)
        rows[arm]=summarize(m,regions)
    return dict(name=case['name'],regions=rows)


def pose_case(build,case):
    rows={}
    for arm,meta in build['arms'].items():
        m,s,d,l=pose.load(Path(meta['elf']));keybytes=pose.configure(m,d,l,case)
        m.observe_start();m.execute(s['_fixture_pose'][0]);m.observe_stop()
        regions={'keys':(l[4],l[4]+keybytes),'model':(d['model'],d['model']+d['model_bytes']),
            'parts':(d['parts'],d['parts']+case['joints']*d['model_bytes']),
            'work':(d['work'],d['work']+d['work_bytes']),
            'camera':(d['camera'],d['camera']+d['camera_bytes']),
            'key_table':(d['table'],d['table']+4*case['joints']),
            'kinds':(d['kinds'],d['kinds']+2*case['joints']),
            'numbers':(d['numbers'],d['numbers']+case['joints']),
            'stack':(m.minimum_sp,m.initial_regs[15])}
        rows[arm]=summarize(m,regions)
    return dict(name=case['name'],regions=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();build=json.loads(args.build.read_text())
    result=dict(status='PASS',scope=__doc__,
        target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        source_sha256={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in
            (Path(__file__),HERE/'target_run.py',HERE/'pose_run.py')},
        sampler=[sampler_case(build,c) for c in sample.cases(True)],
        pose=[pose_case(build,c) for c in pose.cases(False)])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',sampler_cases=len(result['sampler']),pose_cases=len(result['pose']))))


if __name__=='__main__':main()
