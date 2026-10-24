#!/usr/bin/env python3
"""Two additional complete poses using the regular 10.6 Seq.frame path.

This only changes the mapped frame-input fields of pose_run's existing T5/N16
fixture. The compiled MotionMoveCore and both samplers execute unchanged.
Offsets 0xAC (Seq.frame) and 0xB8 (Seq_frame) are the production MotionWork ABI;
the enclosing record size and Seq_frame offset are checked against the linked
header-derived layout. Original lookup/math costs remain typed fixture edges.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import pose_run as pose


original_configure=pose.configure


def configure(m,d,sampler,case):
    result=original_configure(m,d,sampler,case)
    assert d['work_bytes']==220 and d['work_seq_frame']==0xb8
    pose.setword(m,d['work']+d['work_attr'],0,2)
    pose.setword(m,d['work']+0xac,int((33. if case['clamped'] else 9.5)*64),2)
    return result


def cases(quick):
    for clamped in (False,True):
        yield dict(name='t5-n16-seq106-'+('clamped' if clamped else 'interior'),
            kind=5,joints=16,clamped=clamped,mode='normal',frame_source='Seq.frame 10.6')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--host-cc',default='gcc');parser.add_argument('--no-model',action='store_true')
    args=parser.parse_args();args.quick=False
    pose.configure=configure;pose.cases=cases
    result=pose.run(args)
    result['scope']=__doc__+'\n'+result['scope']
    for source in (Path(__file__),pose.ROOT/'include/model.h'):
        result['source_sha256'][str(source.relative_to(pose.ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
    (args.output/'pose-controls.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']))))


if __name__=='__main__':main()
