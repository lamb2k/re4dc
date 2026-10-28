#!/usr/bin/env python3
"""Actual actor clip-strip controls: four OFF/ON x reuse arms, synthetic only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
DC=ROOT/'port/dreamcast'
ACTOR=DC/'game/platform/native_actor_fast.cpp'

def decode(data):
    rows=[];at=0
    while at<len(data):
        ident,okay,output,used,clipped,rebuilt,style=struct.unpack_from('<7I',data,at);at+=28
        size=used*32;packet=data[at:at+size];at+=size
        assert len(packet)==size
        rows.append(dict(id=ident,okay=okay,output=output,used=used,clipped=clipped,rebuilt=rebuilt,style=style,
                         packet=hashlib.sha256(packet).hexdigest()))
    assert at==len(data) and len(rows)==3940
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sanitize',action='store_true')
    args=p.parse_args();arms=[];all_rows={}
    with tempfile.TemporaryDirectory(prefix='re4dc-clip26-') as name:
        d=Path(name);(d/'dc').mkdir()
        (d/'dc/pvr.h').write_text('#pragma once\n#include <cstddef>\n#include <cstdint>\n'
            'struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n'
            'struct pvr_poly_hdr_t{std::uint32_t words[8];};\n'
            '#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n'
            'inline int pvr_prim(const void*,std::size_t){return 0;}\n')
        fixture=d/'model.cpp';fixture.write_text((HERE/'model_clip_cases.cpp.in').read_text().replace('ACTOR_IMPLEMENTATION',str(ACTOR)))
        for reuse in (0,1):
            for front in (0,1):
                exe=d/f'model-reuse{reuse}-front{front}'
                cmd=['g++','-std=c++20','-O2','-fno-fast-math','-ffp-contract=off',
                     '-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
                     '-DRE4DC_DRAW_FALLBACK_AUDIT=1','-DRE4DC_ACTOR_PLAN=1',f'-DRE4DC_ACTOR_CLIP_REUSE={reuse}',
                     f'-DRE4DC_ACTOR_CLIP_FRONT26={front}',
                     '-I'+str(d),'-I'+str(DC/'game/platform'),'-I'+str(DC/'game/platform/include'),
                     str(fixture),str(DC/'room/pvr_geometry.cpp'),'-o',str(exe)]
                if args.sanitize:cmd[1:1]=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
                done=subprocess.run(cmd,capture_output=True)
                if done.returncode:raise RuntimeError(done.stderr.decode())
                env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0'
                done=subprocess.run([str(exe)],capture_output=True,env=env)
                if done.returncode:raise RuntimeError(done.stderr.decode())
                rows=decode(done.stdout);all_rows[reuse,front]=rows
                arms.append(dict(reuse=reuse,front=front,cases=len(rows),output_sha256=hashlib.sha256(done.stdout).hexdigest(),
                                 clipped_triangles=sum(r['clipped'] for r in rows),reconstructed_corners=sum(r['rebuilt'] for r in rows),
                                 emitted_vertices=sum(r['used'] for r in rows)))
                print(exe.name+': '+done.stderr.decode().strip(),flush=True)
        for reuse in (0,1):
            before=all_rows[reuse,0];after=all_rows[reuse,1]
            for a,b in zip(before,after):
                for key in ('id','okay','output','used','packet','style'):
                    assert a[key]==b[key],(reuse,a['id'],key,a[key],b[key])
                assert b['rebuilt']<=a['rebuilt'],(reuse,a['id'],'rebuild count increased')
            assert sum(r['rebuilt'] for r in after)<sum(r['rebuilt'] for r in before)
        for front in (0,1):
            for a,b in zip(all_rows[0,front],all_rows[1,front]):
                for key in ('id','okay','output','used','packet','clipped','style'):
                    assert a[key]==b[key],(front,a['id'],'reuse',key)
    paths=[ACTOR,DC/'game/platform/include/actor_clip_front26.hpp',DC/'game/platform/include/actor_clip_reuse.hpp',
           DC/'game/platform/include/draw_fallback_model.def',DC/'room/pvr_geometry.cpp',DC/'room/pvr_geometry.hpp',
           HERE/'model_clip_cases.cpp.in',Path(__file__)]
    receipt=dict(status='PASS',scope=__doc__,sanitizer='address,undefined' if args.sanitize else None,
                 leak_detection=False if args.sanitize else None,arms=arms,
                 meaning='Synthetic cache populated through actual world_of/project; exact TA/output/capacity equality on these inputs. Real FTRV/reciprocal rounding remains an authorized render approximation.',
                 source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths})
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS front/cache shortcut preserves synthetic TA, strip parity, cull, alpha, UV16 and failure boundaries')

if __name__=='__main__':main()
