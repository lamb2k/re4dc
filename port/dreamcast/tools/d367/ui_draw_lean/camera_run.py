#!/usr/bin/env python3
"""Run complete compiled messageCamera and unchanged production math/GX code.

OFF constructor and ON immutable template are compared in all 16 matrix words
at GXSetProjection entry and all seven resulting compact GX state words.
Only observable GX state must match: removed GX identity-load/current-matrix
calls are actual no-op functions in gx_stub.cpp. FP exception status is outside
the scalar interpreter; the compile-time template is qualified for normal RN.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import target_common as c


def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    interpreter_controls=c.controls()
    build=json.loads(args.build.read_text());arms={};states=[]
    expected=[0x3f800000,0x3b800000,0xbf800000,0xbbaaaaab,0x3f800000,0x3c23d70a,0xbf800000]
    for name,info in build['arms'].items():
        path=Path(info['elf']);assert hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256']
        m,s=c.load(path);captures=[]
        m.hooks[s['_GXSetProjection'][0]]=lambda x:captures.append([x.reg[5],x.bytes_at(x.reg[4],64).hex()])
        m.observe_start();m.execute(s['_messageCamera'][0]);m.observe_stop()
        state=[m.word(s['_re4dc_gxf_projection'][0]+4*i) for i in range(7)]
        assert state==expected,(name,state)
        assert len(captures)==1 and captures[0][0]==1,captures
        observed=dict(matrix=captures[0][1],compact_words=state);states.append(observed)
        row=c.row(m);row.update(observed)
        model=c.pipeline_cost.Model(out/('model-'+name),path,args.host_cc)
        row.update(c.price(model,'message-camera',m));row['model']=model.metadata();arms[name]=row
    assert states[0]==states[1],states
    result=dict(status='PASS',scope=__doc__,arms=arms,interpreter_controls=interpreter_controls,
        camera_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),HERE/'target_common.py')})
    (out/'camera-controls.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--host-cc',default='gcc');r=run(p.parse_args())
    print(json.dumps(dict(status=r['status'],arms={n:dict(cycles=a['model_cycles'],traffic=a['traffic']['cached']) for n,a in r['arms'].items()})))


if __name__=='__main__':main()
