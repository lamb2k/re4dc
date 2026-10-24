#!/usr/bin/env python3
"""Price complete public native UI emit functions with typed unchanged edges.

Production ui_draw_quad/glyph code and begin_pvr_packet execute unchanged.
Cached headers contain all eight defined seeded words. The metadata lookup
edge supplies a real Texture and live Header; stream_send is an observed,
zero-cost transport edge. Actual transport, allocation, upload and GPU costs
are excluded. Scalar RN/DN execution is bounded fixture evidence, not general
hardware FP conformance. Demand lines are touches, never measured misses.
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
    m,s=c.load(path)
    at=s['_ui_fixture_layout'][0]
    v=[m.word(at+4*i) for i in range(23)]
    assert v[0]==1 and v[3:5]==[104,16],v
    (_,entry_bytes,package_bytes,_,_,entries,quads,handles,drawn,header,texture,
        header_offset,key_offset,cells,glyphs,nglyph,glyph_headers,ready,glyph_drawn,
        autosort,layer,sx,sy)=v
    # Only Package::header() reads this synthetic object; the typed descriptor
    # access edges use the real Texture below. Every aligned package word maps
    # to live Header storage, avoiding any fixture dependence on private layout.
    for offset in range(0,package_bytes,4):put(m,entries+offset,'I',header)
    m.map(header,bytes(48));put(m,header+44,'I',case.get('cover',0))
    m.map(texture,bytes(96));put(m,texture+64,'3I',64,64,0)
    put(m,entries+key_offset,'I',1)
    put(m,entries+header_offset,'8I',*[0x80840000+i*0x101 for i in range(8)])
    put(m,drawn,'I',2);put(m,glyph_drawn,'I',0);put(m,layer,'I',7)
    put(m,autosort,'B',case.get('autosort',1))
    put(m,sx,'f',case.get('sx',1.0));put(m,sy,'f',case.get('sy',1.0))
    count=case.get('glyphs',0)
    if count:
        put(m,handles,'I',cells)
        m.map(quads,bytes(104));put(m,quads+8,'2I',0,count)
        put(m,nglyph,'I',count)
        for i in range(count):
            bank=(i//3)%8 if case.get('bank_changes') else 2
            put(m,glyphs+16*i,'4h4BI',-31+19*i,45+3*i,83+19*i,139+3*i,
                (i*7+3)%64,19+(i%13),17+(i%15),bank,0xa3d48e22+i)
        for bank in range(8):
            put(m,glyph_headers+32*bank,'8I',*[0x80840000+bank*0x10000+i*0x101 for i in range(8)])
        m.map(ready,bytes([1]*8))
    else:
        put(m,handles,'I',entries)
        put(m,quads,'7I16f3I',0x410000,0,64,64,0,0,0,
            -12.25,34.5,64.25,34.5,64.25,87.75,-12.25,87.75,
            .125,.25,.875,.25,.875,.75,.125,.75,0xb7ae6d43,1,0)
    output=[]
    stream=[value[0] for name,value in s.items() if 'stream_send' in name]
    assert len(stream)==1,stream
    def send(x):
        assert 0<x.reg[5]<=65*32 and x.reg[5]%32==0,x.reg[5]
        output.append(x.bytes_at(x.reg[4],x.reg[5]))
        return x.pr
    m.hooks[stream[0]]=send
    entry=s['__ZL12ui_draw_quadj'][0]
    m.observe_start();m.execute(entry,argument=0);m.observe_stop()
    state=dict(drawn=m.word(drawn),glyph_drawn=m.word(glyph_drawn),overlay_layer=m.word(layer))
    assert state['drawn']==(2 if count else 3),state
    assert state['glyph_drawn']==count,state
    assert state['overlay_layer']==7+((count or 1) if case.get('autosort',1) else 0),state
    return m,output,state


def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    interpreter_controls=c.controls()
    build=json.loads(args.build.read_text());arms={};expected={}
    cases=[dict(name='quad'),dict(name='glyph1',glyphs=1),dict(name='glyph16',glyphs=16)]
    if args.extended:
        cases += [dict(name='glyph17-bank-scale',glyphs=17,bank_changes=True,sx=.5,sy=2.),
            dict(name='glyph32-bank-fixed',glyphs=32,bank_changes=True,autosort=0,sx=2.,sy=.5),
            dict(name='quad-cover-scale',sx=.5,sy=2.,cover=0x80000000|(32<<11)|48),
            dict(name='quad-fixed',autosort=0,sx=2.,sy=.5)]
    for name,info in build['arms'].items():
        path=Path(info['elf']);assert hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256']
        model=c.pipeline_cost.Model(out/('model-'+name),path,args.host_cc)
        rows={}
        for case in cases:
            m,packets,state=fixture(path,case)
            signature=(packets,state)
            if case['name'] in expected:assert signature==expected[case['name']],(name,case['name'],'output differs')
            else:expected[case['name']]=signature
            payload=b''.join(packets);(out/(name+'-'+case['name']+'.bin')).write_bytes(payload)
            row=c.row(m);row.update(c.price(model,case['name'],m))
            row.update(state=state,packet_sizes=[len(x) for x in packets],ta_words=len(payload)//4,
                output_sha256=hashlib.sha256(payload).hexdigest(),input=case)
            rows[case['name']]=row
        arms[name]=dict(cases=rows,model=model.metadata())
    result=dict(status='PASS',scope=__doc__,arms=arms,interpreter_controls=interpreter_controls,
        build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),HERE/'target_common.py')})
    (out/'native-controls.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--host-cc',default='gcc');p.add_argument('--extended',action='store_true')
    r=run(p.parse_args());print(json.dumps(dict(status=r['status'],arms={n:{k:dict(cycles=v['model_cycles'],traffic=v['traffic']['cached'])
        for k,v in a['cases'].items()} for n,a in r['arms'].items()})))


if __name__=='__main__':main()
