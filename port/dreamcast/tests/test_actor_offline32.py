#!/usr/bin/env python3
"""Synthetic FE3 fixtures for the real configured offline producer and actor TU.

Pass explicit owner-local producer paths. Private producer source and original
assets are never copied into this public fixture or its generated synthetic data.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
DC = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


helper = load('offline32', DC/'tools/d367/ps2leon/actor_format32.py')
decoder = load('blob32', DC/'tools/d367/charbake/cb_blob.py')
runtime = load('runtime32', DC/'tools/cloud/build32/actor_runtime_host.py')
checks = 0


def check(value):
    global checks
    checks += 1
    assert value


def refused(fn):
    try:
        fn()
    except (ValueError, AssertionError, IndexError, struct.error):
        check(True)
    else:
        raise AssertionError('malformed source unexpectedly accepted')


def oriented(strip):
    return [tuple(strip[k:k+3]) if not k & 1 else (strip[k+1], strip[k], strip[k+2]) for k in range(len(strip)-2)]


def index_triangles(data):
    result, run = [], []
    for value in data:
        run.append(value & 127)
        if value & 128:
            result.extend(oriented(run)); run = []
    check(not run)
    return result


def synthetic(path, n=4, near=False, small=False):
    path.mkdir()
    pos = [(100*(i%2), 160*i, -48 if near and i==0 else -9600, 0) for i in range(n)]
    normal = [(0, 0, 60 if small else 16000, 0)]
    uv = [(i%7, (i*3)%11) for i in range(n)] + [(65535, 65535)] # explicitly unreferenced allocation
    corners = [(v, 0, v) for tri in oriented(list(range(n))) for v in tri]
    data = dict(gx=bytes([144])+struct.pack('>H',len(corners))+b''.join(struct.pack('>3H',*c) for c in corners),
                pos=b''.join(struct.pack('<3hH',*p) for p in pos),
                nrm=b''.join(struct.pack('<3bB' if small else '<3hH',*p) for p in normal),
                uv=b''.join(struct.pack('<2H',*p) for p in uv))
    for suffix, payload in data.items(): (path/('info0.'+suffix)).write_bytes(payload)
    return data, corners


def source_cases(data):
    helper.source(data['gx'],data['pos'],data['nrm'],data['uv'])
    for suffix in data:
        bad=dict(data);bad[suffix]=bad[suffix][:-1]
        refused(lambda bad=bad:helper.source(bad['gx'],bad['pos'],bad['nrm'],bad['uv']))
    padded=data['gx']+bytes((-len(data['gx']))%32)
    check(helper.source(padded,data['pos'],data['nrm'],data['uv'])['stream_bytes']==len(padded))
    refused(lambda:helper.source(padded+b'\0',data['pos'],data['nrm'],data['uv']))


def malformed(blob,data):
    validate=lambda b=blob,p=len(data['pos']),n=len(data['nrm']),u=data['uv']:helper.validate(b,p,n,u)
    check(validate()['certificate'] is not None)
    refused(lambda:validate(p=65536*8))
    for p,n,u in ((len(data['pos'])-1,len(data['nrm']),data['uv']),
                  (len(data['pos']),len(data['nrm'])-1,data['uv']),
                  (len(data['pos']),len(data['nrm']),data['uv'][:-1])):
        refused(lambda p=p,n=n,u=u:validate(p=p,n=n,u=u))
    for end in (0,31,39,len(blob)-4): refused(lambda end=end:validate(blob[:end]))
    for flag in (1,2,128):
        b=bytearray(blob);b[2]|=flag;refused(lambda b=b:validate(b))
    for code in range(16):
        b=bytearray(blob);b[2]=code<<2;check(validate(b)['certificate'] is None)
    b=bytearray(blob);b[2]=16<<2;refused(lambda:validate(b))
    # Every stored LOD is checked, including a nonselected malformed prefix.
    for broken in range(4):
        b=bytearray(blob);b[3]=3;at=(len(b)+3)&~3;b.extend(bytes(at-len(b)));struct.pack_into('<H',b,12,at//4)
        b.extend(bytes(24));next_at=len(b)
        for level in range(3):
            struct.pack_into('<fHH',b,at+level*8,float(level),next_at//4,(next_at+8)//4)
            b.extend(struct.pack('<IHH',3|(3<<8)|(1<<20),0,0));b.extend(bytes((0,1,130,0)));next_at+=12
        if broken: struct.pack_into('<I',b,at+24+(broken-1)*12,5|(3<<8)|(1<<20))
        if broken: refused(lambda b=b:validate(b))
        else: check(validate(b)['levels']==3)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fastpath',type=Path,required=True)
    parser.add_argument('--legacy-producer',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    bb=load('real_offline32',args.fastpath/'build_blob.py')
    old=load('original_offline32',args.legacy_producer)
    for length in (63,64,65,66,127,128,129,1000):
        strip=[i%128 for i in range(length)];split=helper.split_strips(strip[:-1]+[strip[-1]|128])
        check(index_triangles(split)==oriented(strip))
    refused(lambda:helper.split_strips([0,1,2]));refused(lambda:helper.split_strips([128]))
    rows=[]
    for name,n,near,small in (('short',4,False,False),('near',4,True,False),('long',70,False,False),('small',4,False,True)):
        src=out/(name+'-source');data,corners=synthetic(src,n,near,small)
        if name=='short':source_cases(data)
        c=bb.load_chunk(src,0,small,helper);ch=bb.Chunk(c);metas=bb.build(ch,'boundary',0.0,8)
        before=old.assemble(old.Chunk(old.load_chunk(src,0,small)),metas)
        legacy=bb.assemble(ch,metas);check(legacy==before)
        blob=bb.assemble(ch,metas,format32_helper=helper)
        check(bb.assemble(ch,metas)==legacy) # opt-in assembly never mutates a legacy input/plan
        info=helper.validate(blob,len(data['pos']),len(data['nrm']),data['uv'],small)
        check(info['indices']==decoder.Blob(blob).stats()['indices'])
        check(info['strips']==decoder.Blob(blob).stats()['strips'])
        check(info['certificate']<31) # unused 65535 must not manufacture the bound
        got=decoder.Blob(blob).triangles()
        check(Counter(decoder.canon(t) for t in got)==Counter(decoder.canon(tuple(corners[k:k+3])) for k in range(0,len(corners),3)))
        if name=='long':check(decoder.Blob(blob).stats()['indices']>sum(len(m['idx']) for m in metas));check(index_triangles(metas[0]['idx'])==index_triangles(helper.split_strips(metas[0]['idx'])))
        if name=='short':
            malformed(blob,data)
            bad=[dict(rec=metas[0]['rec'][:3],idx=[i%3 for i in range(1023)]+[128],ntri=1022)]
            refused(lambda:bb.assemble(ch,bad,format32_helper=helper))
        for arm,payload in (('legacy',legacy),('on',blob)):
            directory=out/(name+'-'+arm);directory.mkdir()
            for suffix,content in data.items():(directory/('info0.'+suffix)).write_bytes(content)
            (directory/'info0.meshlets').write_bytes(payload)
        if name in ('short','near','small'):
            cmd=[sys.executable,str(args.fastpath/'verify_blob.py'),str(out/(name+'-legacy')),str(out/(name+'-on')),
                 '--format32-helper',str(DC/'tools/d367/ps2leon/actor_format32.py')]
            if small:cmd.append('--small-normals')
            run=subprocess.run(cmd,capture_output=True);(out/(name+'-verify.log')).write_bytes(run.stdout+run.stderr);check(run.returncode==0)
        rows.append(dict(case=name,stats=info,legacy_bytes=len(legacy),new_bytes=len(blob),default_identity=True))
    # Exhaustively compare the Python producer's magnitude tags with C++ runtime
    # arithmetic, then execute freshly produced short/near blobs in the actor TU.
    expected=bytes(helper.certificate(((v,0),)) for v in range(65536))+bytes(helper.certificate(((v,0),),True) for v in range(-32768,32768))
    (out/'certificate-oracle.bin').write_bytes(expected)
    (out/'host/dc').mkdir(parents=True);(out/'host/dc/pvr.h').write_text(runtime.adapter.PVR);(out/'host/dc/sq.h').write_text(runtime.adapter.SQ)
    source,adaptations=runtime.adapter.host_source(runtime.adapter.ACTOR.read_text());(out/'native_actor_host.inc').write_text(source)
    fixture=runtime.fixture();fixture=fixture[:fixture.rfind('int main(){')]
    fixture+='\nextern "C" unsigned re4dc_actor_stream_begin(const void*,unsigned){return 0;}\nextern "C" void re4dc_actor_stream_end(unsigned,const void*,unsigned){}\n'
    fixture+=Path(__file__).with_suffix('.cpp.in').read_text();(out/'fixture.cpp').write_text(fixture)
    defs=dict(RE4DC_ACTOR_SOURCE_SPAN=1,RE4DC_ACTOR_TRANSACTION=1,RE4DC_ACTOR_FORMAT32=1,RE4DC_ACTOR_LIGHT_FAST_ONLY=1,
        RE4DC_ACTOR_UV16=1,RE4DC_ACTOR_BACKFACE_CONE=2,RE4DC_ACTOR_DIRECT=1,RE4DC_COARSE_ONE_SUBMIT=1,
        RE4DC_ACTOR_VTX_KERNEL=1,RE4DC_ACTOR_ASM=0,RE4DC_AVK_RIGID6=1,RE4DC_ACTOR_LIGHT_N16=0,
        RE4DC_ACTOR_NO_CLEAR=1,RE4DC_ACTOR_MOVCA=0,RE4DC_ACTOR_LOD_BUDGET=0,RE4DC_NATIVE_ACTOR_SKIN=1,
        RE4DC_NATIVE_ACTOR_SKIN_LAZY=1,RE4DC_ACTOR_SETUP_LEAN=1)
    cmd=['g++','-std=c++20','-O1','-g','-fno-fast-math','-ffp-contract=off','-ffunction-sections','-fdata-sections',
         *['-D'+k+'='+str(v) for k,v in defs.items()],'-I'+str(out/'host'),'-I'+str(DC/'game/platform'),
         '-I'+str(DC/'game/platform/include'),'-I'+str(DC/'room'),str(out/'fixture.cpp'),
         str(DC/'room/pvr_geometry.cpp'),str(DC/'room/source_lighting.cpp'),'-Wl,--gc-sections','-o',str(out/'consumer')]
    if args.sanitize:cmd[1:1]=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
    built=subprocess.run(cmd,capture_output=True);(out/'consumer-compile.log').write_bytes(built.stdout+built.stderr);check(built.returncode==0)
    environment=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')
    run=subprocess.run([str(out/'consumer'),str(out)],capture_output=True,env=environment)
    (out/'consumer.stdout').write_bytes(run.stdout);(out/'consumer.stderr').write_bytes(run.stderr);check(run.returncode==0)
    report=dict(status='PASS',checks=checks,producer_sha256=hashlib.sha256((args.fastpath/'build_blob.py').read_bytes()).hexdigest(),
        validator_sha256=hashlib.sha256((args.fastpath/'verify_blob.py').read_bytes()).hexdigest(),
        helper_sha256=hashlib.sha256((DC/'tools/d367/ps2leon/actor_format32.py').read_bytes()).hexdigest(),
        runtime_source_sha256=hashlib.sha256(runtime.adapter.ACTOR.read_bytes()).hexdigest(),
        fixture_sha256=hashlib.sha256(Path(__file__).with_suffix('.cpp.in').read_bytes()).hexdigest(),
        cases=rows,consumer=json.loads(run.stdout),command=cmd,adaptations=adaptations)
    (out/'offline32.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['consumer']));print('PASS producer checks',checks)


if __name__=='__main__':main()
