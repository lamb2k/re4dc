#!/usr/bin/env python3
"""Price full compiled public re4dc_draw_id_quad with fixed typed service edges.

The fixture observes all 104 output bytes and mask submissions. Inputs use the
actual target IdUnit/TPL/GX layouts. The bridge's arithmetic executes normally;
the unchanged matrix edge is an identity-screen copy, and texture/camera/native
enqueue services use typed adapters. Adapter instructions are retained, their
original game/service costs are not claimed. Normal RN/DN scalar arithmetic
and bounded finite color conversions only; no hardware frame-time prediction.
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
import target_common as c


def put(m,address,fmt,*values):m.map(address,struct.pack('<'+fmt,*values))


def fixture(path,case):
    m,s=c.load(path);a=s['_ui_fixture_bridge_layout'][0];v=[m.word(a+4*i) for i in range(20)]
    (version,usz,wsz,tsz,csz,psz,dsz,qsz,unit,wks,tpls,descs,tex,clut,ptpl,mat,vtx,col,uv,maskresult)=v
    assert [version,usz,wsz,tsz,csz,psz,dsz,qsz]==[1,312,84,36,12,12,8,104],v
    identity=(1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.)
    put(m,s['__ZN8IDSystem10m_scrn_matE'][0],'12f',*identity)
    m.map(unit,bytes(usz));put(m,unit+mat,'12f',*identity)
    put(m,unit+2,'2B',2,3)
    put(m,unit+108,'4B',0x0a if case.get('mask') else 4,0x12,0,0)
    put(m,unit+127,'B',int(case.get('mask',False)));put(m,unit+132,'B',1)
    put(m,unit+vtx,'12f',-16.,-8.,-40.,48.,-8.,-40.,48.,24.,-40.,-16.,24.,-40.)
    put(m,unit+col,'4f',35.,129.,254.,187.)
    put(m,unit+uv,'4f',-.125,1.125,.25,.875)
    for i in range(2):
        m.map(wks+wsz*i,bytes(wsz));put(m,wks+wsz*i+ptpl,'I',tpls+psz*i)
        put(m,tpls+psz*i,'3I',1,1,descs+dsz*i)
        put(m,descs+dsz*i,'2I',tex+tsz*i,clut+csz*i if i or case.get('palette') else 0)
        m.map(tex+tsz*i,bytes(tsz));put(m,tex+tsz*i,'2H2I',32,64,5,0x400000+i*0x10000)
        put(m,tex+tsz*i+20,'2I',1,1)
        put(m,clut+csz*i,'H2x2I',16,1,0x480000+i*0x1000)
    put(m,maskresult,'I',int(case.get('mask',False)))
    projection=(0.,1.25,.125,1.5,-.25,1.,-2.) if case.get('perspective') else (1.,1./256,-1.,-1./192,1.,.01,-1.)
    put(m,s['_re4dc_gxf_projection'][0],'7f',*projection)
    put(m,s['_re4dc_gxf_viewport'][0],'6f',8.,6.,640.,480.,0.,1.)
    put(m,s['_re4dc_res_vjitter'][0],'f',case.get('jitter',0.))
    observations=[]
    def submit(x):observations.append(('quad',x.bytes_at(x.reg[4],104).hex()))
    def mask(x):observations.append(('mask',x.bytes_at(x.reg[4],104).hex(),x.bytes_at(x.reg[5],28).hex()))
    m.hooks[s['_re4dc_ui_submit'][0]]=submit
    m.hooks[s['_re4dc_ui_hud_mask_submit'][0]]=mask
    before=m.bytes_at(unit,usz)
    m.observe_start();m.execute(s['_re4dc_draw_id_quad'][0],argument=unit);m.observe_stop()
    assert m.bytes_at(unit,usz)==before,'input modified'
    assert len(observations)==1 and observations[0][0]==('mask' if case.get('mask') else 'quad'),observations
    return m,observations


def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    interpreter_controls=c.controls()
    build=json.loads(args.build.read_text());arms={};expected={}
    cases=[dict(name='ortho'),dict(name='ortho-palette',palette=True),
        dict(name='perspective-jitter',perspective=True,jitter=1./960),dict(name='mask',mask=True)]
    for name,info in build['arms'].items():
        path=Path(info['elf']);assert hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256']
        model=c.pipeline_cost.Model(out/('model-'+name),path,args.host_cc);rows={}
        for case in cases:
            m,observations=fixture(path,case)
            if case['name'] in expected:assert observations==expected[case['name']],(name,case['name'],'output differs')
            else:expected[case['name']]=observations
            row=c.row(m);row.update(c.price(model,case['name'],m));row.update(input=case,observations=observations)
            rows[case['name']]=row
        arms[name]=dict(cases=rows,model=model.metadata())
    result=dict(status='PASS',scope=__doc__,arms=arms,interpreter_controls=interpreter_controls,
        build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),HERE/'target_common.py')})
    (out/'bridge-controls.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--host-cc',default='gcc')
    r=run(p.parse_args());print(json.dumps(dict(status=r['status'],arms={n:{k:dict(cycles=v['model_cycles'],traffic=v['traffic']['cached'])
        for k,v in a['cases'].items()} for n,a in r['arms'].items()})))


if __name__=='__main__':main()
