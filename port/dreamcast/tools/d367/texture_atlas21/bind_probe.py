#!/usr/bin/env python3
"""Compile the uninstalled adapter against actual plan types and sealed arrays."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct
import sys
import atlas_split as atlas

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--consumers',type=Path)
    ap.add_argument('--runtime-data',type=Path)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('preserve existing checks')
    sums=a.candidate/'SHA256SUMS'
    if sha(sums)!='9b524ee573753dcb640cb561ba7966e56c5d57e53200c5dcbd8683f0796ad2a2':raise ValueError('v2 candidate seal')
    for line in sums.read_text().splitlines():
        digest,name=line.split('  ',1)
        if sha(a.candidate/name)!=digest:raise ValueError('candidate changed: '+name)
    manifest=json.loads((a.candidate/'source-inputs.json').read_text())
    if sha(a.source_root/'SHA256SUMS-actors-v2')!=atlas.SOURCE_SEAL:raise ValueError('actor source seal')
    for name,digest in manifest['selected'].items():
        if sha(a.source_root/name)!=digest:raise ValueError('source changed: '+name)
    dynamic=[]
    neck=None
    consumer_seal=None
    if a.consumers:
        consumer_seal=sha(a.consumers/'SHA256SUMS')
        if consumer_seal!='6adc079fb9b5559f749acf272443b26ce63154c5e0ff322f14f846cd8513e9c6':raise ValueError('consumer seal')
        for line in (a.consumers/'SHA256SUMS').read_text().splitlines():
            digest,name=line.split('  ',1)
            if sha(a.consumers/name)!=digest:raise ValueError('consumer changed: '+name)
        neck=atlas.hands_pack.arrays((a.consumers/'inputs/ps2leon_neck.h').read_text())['n']
        hands=(a.consumers/'inputs/leon_hands_pl00.re4hp').read_bytes()
        h=struct.unpack_from('<8I',hands)
        for i in range(h[2]&65535):
            e=struct.unpack_from('<BB11H',hands,32+(h[1]>>16)*12+i*24)
            at=e[12]*32;parts={}
            for name,size in zip(('pos','nrm','uv','gx','weights'),e[6:11]):
                parts[name]=hands[at:at+size];at+=atlas.r32(size)
            dynamic.append((e[0],e[5],parts))
    own=Path(__file__).resolve().parent
    include=own.parents[2]/'game/platform/include'
    a.out.mkdir(parents=True)
    results=[]
    for actor,cohort,appearance,role in [('standard','leon-v1',0x100,1),('pl08','leon-extra-v1',0x108,0),('pl08-headless','leon-extra-v1',0x109,0)]:
        folder=a.out/actor;folder.mkdir()
        candidate_actor='pl08' if actor=='pl08-headless' else actor
        report=json.loads((a.candidate/candidate_actor/'report.json').read_text())
        arrays=atlas.chunks(candidate_actor,a.source_root/cohort/'inputs')
        lines=['#pragma once','namespace case_data {']
        def array(name,blob):
            lines.append('alignas(32) const unsigned char '+name+'[]={'+','.join(str(b) for b in blob)+'};')
        for name in ('pos','nrm','uv','gx','weights'):array(name,arrays[name])
        runs=report['bindings']['runs']
        for i,row in enumerate(runs):
            base=a.candidate/candidate_actor/'bindings'/f'run-{i:03d}'
            array(f'uv_{i}',(base/'uv.bin').read_bytes());array(f'gx_{i}',(base/'stream.meshlets').read_bytes())
        source_crc,source_fnv=[int(n,16) for n in report['source_key'].split('-')]
        tile_crc,tile_fnv=[int(n,16) for n in report['derived_key'].split('-')]
        lines+=['static unsigned char source_token,tile_token;',
            'inline re4dc_atlas_split::Bundle bundle() {',
            're4dc_atlas_split::Bundle b{};',
            f'b.appearance={appearance};b.role={role};b.source_crc={source_crc}u;b.source_fnv={source_fnv}u;b.epoch=1;',
            'b.source={{pos,sizeof(pos)},{nrm,sizeof(nrm)},{uv,sizeof(uv)},{gx,sizeof(gx)},{weights,sizeof(weights)},'+
            f'{len(arrays["pos"])//8},{len(arrays["nrm"])//8},{len(arrays["weights"])//16},{report["bindings"]["source_triangles"]},119'+'};',
            'b.source_image={&source_token,nullptr,512,512,6,0xffffffffu,0};',
            'b.tile_image={&tile_token,nullptr,128,128,6,0xffffffffu,0};',
            f'b.tile_crc={tile_crc}u;b.tile_fnv={tile_fnv}u;b.run_count={len(runs)};']
        for i,row in enumerate(runs):
            isolated=int(row['texture']=='isolated')
            lines.append(f'b.runs[{i}]='+'{{uv_'+str(i)+',sizeof(uv_'+str(i)+')},{gx_'+str(i)+',sizeof(gx_'+str(i)+')},'+f'{row["triangles"]},{isolated}'+'};')
        lines+=['return b;}']
        if dynamic:
            for name,blob in neck.items():array('neck_'+name,blob)
            spans=','.join('{neck_'+name+',sizeof(neck_'+name+')}' for name in ('pos','nrm','uv','gx','weights'))
            lines+=['inline re4dc_source::ChunkInput neck_input() {return {'+spans+','+f'{len(neck["pos"])//8},{len(neck["nrm"])//8},{len(neck["weights"])//16},37,119'+'};}']
            for i,(_,_,parts) in enumerate(dynamic):
                for name,blob in parts.items():array(f'hand_{i}_{name}',blob)
            lines+=['static constexpr unsigned hand_count='+str(len(dynamic))+';',
                    'inline unsigned hand_role(unsigned n) {const unsigned roles[]={'+','.join(str(role) for role,_,_ in dynamic)+'};return roles[n];}',
                    'inline re4dc_source::ChunkInput hand_input(unsigned n) {switch(n) {']
            for i,(_,triangles,parts) in enumerate(dynamic):
                spans=','.join('{hand_'+str(i)+'_'+name+',sizeof(hand_'+str(i)+'_'+name+')}' for name in ('pos','nrm','uv','gx','weights'))
                lines+=['case '+str(i)+':return {'+spans+','+f'{len(parts["pos"])//8},{len(parts["nrm"])//8},{len(parts["weights"])//16},{triangles},119'+'};']
            lines+=['default:return {};}}']
        lines+=['}']
        header=folder/'atlas-bind-case.h';header.write_text('\n'.join(lines)+'\n')
        for enabled in (0,1):
            exe=folder/f'bind-{enabled}'
            cmd=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',
                '-DRE4DC_ACTOR_PL08=1',f'-DRE4DC_ATLAS_RUNTIME_PROBE={int(bool(a.runtime_data))}',f'-DRE4DC_ATLAS_DYNAMIC_PROBE={int(bool(dynamic))}',f'-DRE4DC_LEON_ATLAS_SPLIT={enabled}',
                '-isystem',str(include),'-I'+str(own),'-I'+str(folder),str(own/'bind_probe.cpp'),'-o',str(exe)]
            if a.runtime_data:cmd[1:1]=['-I'+str(a.runtime_data)]
            build=subprocess.run(cmd,capture_output=True,text=True)
            (folder/f'build-{enabled}.log').write_text(build.stdout+build.stderr)
            if build.returncode:raise RuntimeError(build.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            (folder/f'run-{enabled}.log').write_text(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            results.append(dict(actor=actor,**json.loads(result.stdout)))
    receipt=dict(schema='re4dc-atlas-binding-probe-1',candidate_sha256sums=sha(sums),
        actual_plan_header_sha256=sha(include/'coarse_actor_transaction.h'),actual_preflight_sha256=sha(include/'coarse_actor_preflight.h'),
        adapter_sha256=sha(own/'atlas_bind.h'),fixture_sha256=sha(own/'bind_probe.cpp'),consumer_sha256sums=consumer_seal,runtime_data_sha256=sha(a.runtime_data/'leon_atlas_split_data.h') if a.runtime_data else None,sanitizers=['address','undefined'],results=results,
        limits='Host source-format fixture. Foreign role descriptors are sentinels. No global immutable ID range, current owner/lifetime/material certificate, texture lease or runtime hook is admitted.')
    (a.out/'binding-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
