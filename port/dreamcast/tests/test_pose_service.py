#!/usr/bin/env python3
"""Host contract tests for phase 1B; optional real EDCL corpus differential.

These prove bounded codec/closure behavior, not game equivalence or speed.
The Python oracle uses the existing baker's q48/dq48/nlerp math.
"""
import argparse
import ctypes as C
import importlib.util
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('edemo_baker', ROOT/'port/dreamcast/tools/enginebake/bake_clips.py')
baker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baker)

class Local(C.Structure):
    _fields_ = [('q', C.c_float*4), ('t', C.c_float*3), ('s', C.c_float*3)]
class Matrix(C.Structure):
    _fields_ = [('m', C.c_float*12)]
class Track(C.Structure):
    _fields_ = [('rotation', C.c_void_p), ('translation', C.c_void_p), ('scale', C.c_void_p),
                ('translation_scale', C.c_float), ('rotation_keys', C.c_uint16),
                ('translation_keys', C.c_uint16), ('rotation_shift', C.c_uint8),
                ('translation_shift', C.c_uint8), ('translation_mode', C.c_uint8)]
class Skeleton(C.Structure):
    _fields_ = [('bone_count', C.c_uint32), ('parent', C.POINTER(C.c_int32)),
                ('rest_translation', C.POINTER(C.c_float))]
class Clip(C.Structure):
    _fields_ = [('bone_count', C.c_uint32), ('frames', C.c_uint32),
                ('tracks', C.POINTER(Track)), ('root_track', C.c_void_p), ('root_scale', C.c_float),
                ('pose_stage', C.c_uint8)]
class Dependency(C.Structure):
    _fields_ = [('destination', C.c_uint32), ('source', C.c_uint32)]
class Layer(C.Structure):
    _fields_ = [('clip', C.POINTER(Clip)), ('frame', C.c_float), ('weight', C.c_float),
                ('bone_mask', C.POINTER(C.c_uint8))]

def skeleton(n):
    parents = (C.c_int32*n)(-1, *range(n-1))
    rest = (C.c_float*(3*n))(*([0, 10, 0]*n))
    return Skeleton(n, parents, rest)

def record(n=3, nf=5, scaled=True):
    out = bytearray(struct.pack('<HBB', nf, n, 0))
    for _ in range(n):
        out += bytes([1 | 6 | (3<<3) | (3<<5) | (0x80 if scaled else 0)])
        # A final shortened segment (frame 0 -> 4 with stride 8).
        out += baker.q48((0,0,0,1)) + baker.q48((0,0,1,0))
        out += struct.pack('<f6h', .25, 0, 0, 0, 8, 16, 24)
        if scaled:
            for f in range(nf): out += struct.pack('<3h', 4096-f*1024, 4096, 4096+f*512)
    out += bytes((-len(out))%4)
    out += struct.pack('<f', 1) + bytes(12*nf)
    return bytes(out)

def file_image(records):
    head = struct.pack('<4sHH', b'EDCL', 1, len(records))
    at = 8+8*len(records); table = bytearray(); body = bytearray()
    for entry, rec in records:
        table += struct.pack('<HHI', entry, struct.unpack_from('<H',rec)[0], at)
        body += rec; at += len(rec)
    return head+table+body

def oracle(rec, rest, f):
    nf,n,_ = struct.unpack_from('<HBB',rec)
    f=max(0,min(f,nf-1)); at=4; out=[]
    def at_key(keys, shift, is_q=False):
        if len(keys)==1: return keys[0]
        k=min(int(f)//(1<<shift),len(keys)-2)
        a=min(k<<shift,nf-1); b=min((k+1)<<shift,nf-1)
        t=0 if a==b else (f-a)/(b-a)
        return baker.nlerp(keys[k],keys[k+1],t) if is_q else tuple(x+(y-x)*t for x,y in zip(keys[k],keys[k+1]))
    for i in range(n):
        flags=rec[at]; at+=1
        rs=(flags>>3)&3; ts=(flags>>5)&3; tm=flags&6
        count=((nf-1+(1<<rs)-1)>>rs)+1 if flags&1 else 1
        qs=[baker.dq48(rec[at+6*k:at+6*k+6]) for k in range(count)]; at+=6*count
        if tm:
            scale=struct.unpack_from('<f',rec,at)[0]; at+=4
            count=1 if tm==2 else ((nf-1+(1<<ts)-1)>>ts)+1
            vals=[tuple(x*scale for x in struct.unpack_from('<3h',rec,at+6*k)) for k in range(count)]
            at+=6*count
            tr=at_key(vals,ts)
        else: tr=rest[3*i:3*i+3]
        sc=(1,1,1)
        if flags&0x80:
            vals=[tuple(x/4096 for x in struct.unpack_from('<3h',rec,at+6*k)) for k in range(nf)]
            at+=6*nf; sc=at_key(vals,0)
        out.append((at_key(qs,rs,True), tr, sc))
    return out

def configure(lib):
    lib.re4ps_open_edcl.argtypes=[C.POINTER(Clip), C.POINTER(Track), C.c_size_t,C.c_void_p,C.c_size_t,C.c_uint16,C.POINTER(Skeleton)]
    lib.re4ps_required.argtypes=[C.POINTER(Skeleton),C.POINTER(C.c_uint8),C.POINTER(Dependency),C.c_size_t,C.POINTER(C.c_uint8),C.c_size_t]
    lib.re4ps_sample.argtypes=[C.POINTER(Skeleton),C.POINTER(Clip),C.c_float,C.POINTER(C.c_uint8),C.POINTER(Local),C.c_size_t]
    lib.re4ps_layers.argtypes=[C.POINTER(Skeleton),C.POINTER(Layer),C.c_size_t,C.POINTER(C.c_uint8),C.POINTER(Local),C.c_size_t]
    lib.re4ps_compose.argtypes=[C.POINTER(Skeleton),C.POINTER(Local),C.POINTER(C.c_uint8),C.POINTER(Matrix),C.POINTER(Matrix),C.c_size_t]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--edcl',type=Path); ap.add_argument('--output',type=Path)
    args=ap.parse_args(); checks=0; max_error=0; clips=0
    with tempfile.TemporaryDirectory(prefix='re4-pose-test-') as tmp:
        so=Path(tmp)/'pose.so'
        subprocess.run(['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Werror',
                        '-shared','-fPIC',str(ROOT/'port/dreamcast/engine/pose_service.c'),'-lm','-o',str(so)],check=True)
        lib=C.CDLL(str(so)); configure(lib)
        s=skeleton(3); tracks=(Track*3)(); clip=Clip(); data=file_image([(11,record())]); buf=C.create_string_buffer(data)
        fixture=Path(tmp)/'probe.edcl'; fixture.write_bytes(data)
        bounds=Path(tmp)/'bounds'
        subprocess.run(['cc','-std=c11','-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined',
                        str(ROOT/'port/dreamcast/tests/pose_service_bounds.c'),
                        str(ROOT/'port/dreamcast/engine/pose_service.c'),'-lm','-o',str(bounds)],check=True)
        subprocess.run([str(bounds),str(fixture)],check=True)
        assert lib.re4ps_open_edcl(C.byref(clip),tracks,3,buf,len(data),11,C.byref(s))==0
        assert clip.pose_stage==0
        version2=bytearray(data); version2[4]=2; version2[19]=1
        v2buf=C.create_string_buffer(bytes(version2))
        assert lib.re4ps_open_edcl(C.byref(clip),tracks,3,v2buf,len(data),11,C.byref(s))==0
        assert clip.pose_stage==1
        unchanged=(Local*3)(); C.memset(unchanged,0x3d,C.sizeof(unchanged)); saved=bytes(unchanged)
        assert lib.re4ps_sample(C.byref(s),C.byref(clip),.5,None,unchanged,3)==-6
        assert bytes(unchanged)==saved
        bad_layers=(Layer*2)(Layer(C.pointer(clip),0,1,None),Layer(C.pointer(clip),.5,.5,None))
        assert lib.re4ps_layers(C.byref(s),bad_layers,2,None,unchanged,3)==-6
        assert bytes(unchanged)==saved
        assert lib.re4ps_sample(C.byref(s),C.byref(clip),2,None,unchanged,3)==0
        for version,stage in ((1,1),(2,0),(2,2),(3,1)):
            invalid_stage=bytearray(data); invalid_stage[4]=version; invalid_stage[19]=stage
            badbuf=C.create_string_buffer(bytes(invalid_stage))
            assert lib.re4ps_open_edcl(C.byref(clip),tracks,3,badbuf,len(data),11,C.byref(s))==-2
            assert clip.frames==0
        assert lib.re4ps_open_edcl(C.byref(clip),tracks,3,buf,len(data),11,C.byref(s))==0
        checks+=13
        # Every truncation refuses. Output clip is not published after failure.
        for size in range(len(data)):
            bad=Clip()
            assert lib.re4ps_open_edcl(C.byref(bad),tracks,3,buf,size,11,C.byref(s))!=0
            assert bad.frames==0; checks+=1
        assert lib.re4ps_open_edcl(C.byref(clip),tracks,2,buf,len(data),11,C.byref(s))==-3
        assert lib.re4ps_open_edcl(C.byref(clip),tracks,3,buf,len(data),11,C.byref(s))==0
        mask=(C.c_uint8*3)(0,0,1); required=(C.c_uint8*3)()
        assert lib.re4ps_required(C.byref(s),mask,None,0,required,3)==0 and list(required)==[1,1,1]
        s.parent[2]=-1
        deps=(Dependency*2)(Dependency(0,2),Dependency(2,0)); mask[:]=[1,0,0]
        assert lib.re4ps_required(C.byref(s),mask,deps,2,required,3)==0 and list(required)==[1,0,1]
        out=(Local*3)(); C.memset(out,0x3d,C.sizeof(out)); before=bytes(out[1])
        assert lib.re4ps_sample(C.byref(s),C.byref(clip),2,required,out,3)==0
        assert bytes(out[1])==before
        matrices=(Matrix*3)(); root=Matrix((C.c_float*12)(1,0,0,100,0,1,0,200,0,0,1,300))
        assert lib.re4ps_compose(C.byref(s),out,required,C.byref(root),matrices,3)==0
        assert abs(matrices[0].m[3]-101)<1e-5
        invalid=(C.c_uint8*3)(0,1,0)
        assert lib.re4ps_compose(C.byref(s),out,invalid,None,matrices,3)==-4
        assert lib.re4ps_sample(C.byref(s),C.byref(clip),float('nan'),None,out,3)==-5
        layers=(Layer*2)(Layer(C.pointer(clip),0,1,None),Layer(C.pointer(clip),4,.5,required))
        assert lib.re4ps_layers(C.byref(s),layers,2,None,out,3)==0
        assert abs(out[0].t[0]-1)<1e-5 and abs(out[1].t[0])<1e-5
        assert abs(out[0].s[0]-.5)<1e-5
        # Skeleton/closure API is not fixed to the demo's 34 bones or 8-bit IDs.
        large=skeleton(512); lr=(C.c_uint8*512)(); lm=(C.c_uint8*512)(); lm[511]=1
        assert lib.re4ps_required(C.byref(large),lm,None,0,lr,512)==0 and sum(lr)==512
        large.parent[400]=401
        assert lib.re4ps_required(C.byref(large),lm,None,0,lr,512)==-4
        checks+=12
        corpus=[data]
        if args.edcl: corpus.append(args.edcl.read_bytes())
        for data in corpus:
            count=struct.unpack_from('<H',data,6)[0]; buf=C.create_string_buffer(data)
            for k in range(count):
                entry,nf,offset=struct.unpack_from('<HHI',data,8+8*k)
                end=struct.unpack_from('<I',data,8+8*(k+1)+4)[0] if k+1<count else len(data)
                rec=data[offset:end]; n=rec[2]; s=skeleton(n); tracks=(Track*n)(); clip=Clip(); out=(Local*n)()
                assert lib.re4ps_open_edcl(C.byref(clip),tracks,n,buf,len(data),entry,C.byref(s))==0,entry
                clips+=1
                # Endpoints, fractional positions, shortened final segments and clamp behavior.
                for f in sorted(set([-1.,0.,.5,1.,nf/3,nf-1.5,float(nf-1),float(nf+1)])):
                    f=C.c_float(f).value
                    if clip.pose_stage==1 and 0<f<nf-1 and f!=math.floor(f):
                        before=bytes(out)
                        assert lib.re4ps_sample(C.byref(s),C.byref(clip),f,None,out,n)==-6
                        assert bytes(out)==before
                        checks+=1
                        continue
                    assert lib.re4ps_sample(C.byref(s),C.byref(clip),f,None,out,n)==0
                    expected=oracle(rec,list(s.rest_translation[:3*n]),f)
                    for i,(q,t,scale) in enumerate(expected):
                        qerr=min(max(abs(a-b) for a,b in zip(out[i].q,q)),max(abs(a+b) for a,b in zip(out[i].q,q)))
                        err=max(qerr,max(abs(a-b) for a,b in zip(out[i].t,t)),max(abs(a-b) for a,b in zip(out[i].s,scale)))
                        max_error=max(max_error,err)
                        assert err<.002,(entry,f,i,err)
                        checks+=1
    result=dict(checks=checks, clips=clips, max_component_error=max_error, result='PASS',
                scope='Host codec, masks, hierarchy, layers and real EDCL decode parity; no game or console acceptance.')
    if args.output: args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
