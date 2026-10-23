#!/usr/bin/env python3
"""SDO3 + replay composition: actual extracted geometry, host arithmetic only.

All generated C++, compiler scratch, binaries and detailed traces must stay in
/dev/shm. A small source/evidence report may be copied out after qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def generate(tree):
    """Reuse the existing replay geometry harness; replace only synthetic cases."""
    d=tree/'port/dreamcast';tools=d/'tools/d367'
    controls=load(tools/'world_replay_lean/check_runtime.py','sdo3_boundary')
    original=controls.original;function=original.function
    values=original.extract();raw=original.STATIC.read_text()
    names={'EMITTER':'struct Emitter {','BORROW_GATHER':'bool borrow_gather(){',
           'CORNERS':'const re4dc::room::CompactVertex12* corners(',
           'BORROW':'bool borrow(){','LEAN_FLUSH':'void lean_flush(',
           'STRIPS_LEAN':'const std::uint8_t* strips_lean(','EMIT_PICK':'int emit_pick(',
           'ALPHA_LUT':'const std::uint32_t* ps2_vertex_alpha_lut(){',
           'DD_WORD':'std::uint32_t dd_word(','DD_SOURCE':'const std::uint8_t* dd_source('}
    for name,signature in names.items():values[name]=function(raw,signature)
    for name,signature in (('DD_ACTIVE','bool dd_active('),('DD_UNIQUE','unsigned dd_unique_count(')):
        values[name]=function(raw,signature) if signature in raw else ''
    values['LOAD_SCREEN']=function(raw,'void load_screen(')
    values['REPLAY_RESTART']='#if RE4DC_SCENERY_REPLAY_LEAN\n'+function(raw,'[[gnu::always_inline]] void chunk_restart()')+'\n#endif'
    fill=function(raw,'__attribute__((noinline)) void fill(')
    original_fill=fill
    # The only adapted production instructions: two SH4 FMACs. Dyadic fixture
    # values make these host multiply/add operations exact; no SH4 claim follows.
    for axis,factor,variable in (('ru','au','fu'),('rv','av','fv')):
        old=f'__asm__("fmac fr0,%1,%0" : "+f"({axis}) : "f"({factor}),"w"({variable}));'
        assert fill.count(old)==1,old
        fill=fill.replace(old,f'{axis}={axis}+{factor}*{variable}; // host-only FMAC edge')
    values['DEDUP_FILL']=fill
    geom=(d/'room/pvr_geometry.cpp').read_text()
    for name,signature in (('SHADE_COLOR','std::uint32_t shade_color('),('INTERPOLATE_VERTEX','RenderVertex interpolate_vertex('),('CLIP_PROJECTED_TRIANGLE','std::uint32_t clip_projected_triangle(')):
        values[name]=function(geom,signature)
    active='\n'.join(values[n] for n in names)
    stats=sorted(set(re.findall(r'\bstats\.(\w+)',active)))
    values['STATIC_STATS']='static struct {unsigned '+','.join(n+'=0' for n in stats)+';}stats;'
    values['REPORT_STATS']='queue_events.insert(queue_events.end(),{'+','.join('stats.'+n for n in stats)+'});'
    values['ROOT']=str(tree)
    template=(tools/'world_replay_lean/fixture_boundary.cpp.in').read_text()
    template=template.replace('struct Packet { std::uint32_t word[8]; };','''struct Packet {
    std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;
};
using pvr_vertex_t=Packet;
constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000U,PVR_CMD_VERTEX_EOL=0xf0000000U;
float vp_host_xmtrx[4][4];
static unsigned geometry_low_at;
''')
    template=template.replace('static void sourceWorldTextureAcquired(Key){++acquired;','''static void sourceWorldTextureAcquired(Key){
std::fill(&vp_host_xmtrx[0][0],&vp_host_xmtrx[0][0]+16,-9999.0f);
++acquired;
if(geometry_low_at&&acquired==geometry_low_at)model_pending=kModelPacketBytes/32-300;
''')
    geometry=(tools/'world_replay_lean/fixture_geometry.cpp.in').read_text()
    old_case=function(geometry,'static void queue_case(')
    geometry=geometry.replace(old_case,(HERE/'fixture_composition.cpp.in').read_text())
    geometry=geometry.replace('@BORROW@','@BORROW@\n@DD_WORD@\n@DD_SOURCE@\n@DD_ACTIVE@\n@DD_UNIQUE@')
    geometry=geometry.replace('@EMITTER@;','namespace dedup {\n@DEDUP_FILL@\n}\n@EMITTER@;')
    template='#define RE4DC_SCENERY_DEDUP 3\n'+template.replace('@QUEUE_FIXTURE@',geometry)
    for name,value in values.items():template=template.replace('@'+name+'@',value)
    assert not re.search(r'@[A-Z_]+@',template),'Unfilled extraction seam'
    # Observe selected cache records after the actual chunk_emit body returns.
    seam='const int result=e.chunk_emit(cpk+x.first,x.count);'
    assert template.count(seam)==1
    template=template.replace(seam,seam+'\n            observe_cache(e,cpk+x.first,x.count,result);')
    return template,values,hashlib.sha256(original_fill.encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-tree',type=Path,required=True)
    p.add_argument('--expected-source',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();tree=a.source_tree.resolve();output=a.output.resolve()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    if not output.is_relative_to(Path('/dev/shm')):raise ValueError('Generated outputs must remain in /dev/shm')
    if (tree/'source-pins.json').is_file():
        pins=json.loads((tree/'source-pins.json').read_text())
        assert pins['source']==a.expected_source
        for name,sha in pins['files'].items():assert digest(tree/name)==sha,name
    else:
        assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==a.expected_source
    output.mkdir(parents=True,exist_ok=False)
    for name,text in {
        'dc/pvr.h':'#pragma once\n',
        'kos/fs.h':'#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n',
        'dc/matrix.h':'#pragma once\nusing matrix_t=float[4][4];\nstatic void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}\nstatic void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}\n',
    }.items():
        path=output/'shim'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    source,values,fill_sha=generate(tree);fixture=output/'composition.cpp';fixture.write_text(source)
    env=dict(os.environ,TMPDIR='/dev/shm',PYTHONDONTWRITEBYTECODE='1')
    cases=list(range(100,112));results={};counts=[]
    def build(label,replay,decoded,batch,source_path=fixture):
        binary=output/label
        cmd=['g++','-std=c++20','-O2','-ffp-contract=off','-Wall','-Wextra',
             '-DRE4DC_SCENERY_SELECT_ONLY=1',f'-DRE4DC_SCENERY_SUBMIT_BATCH={batch}',
             f'-DRE4DC_SCENERY_REPLAY_LEAN={replay}',f'-DCOMPOSITION_DECODED={decoded}',
             '-DCHECK_DIAGNOSTICS=0','-DRE4DC_SCENERY_SELECT_LEAN2=0','-I'+str(output/'shim'),
             '-I'+str(tree/'port/dreamcast/game/platform/include'),str(source_path),'-o',str(binary)]
        run=subprocess.run(cmd,cwd=output,capture_output=True,env=env)
        (output/(label+'.compile.log')).write_bytes(run.stdout+run.stderr)
        assert run.returncode==0,(label,run.stderr.decode())
        return binary
    for batch in (0,1):
        for decoded in (0,1):
            fresh=None
            for replay in (0,1):
                label=f'b{batch}-d{decoded}-r{replay}';binary=build(label,replay,decoded,batch);records=[]
                for case in cases:
                    run=subprocess.run([str(binary),str(case)],cwd=output,capture_output=True,env=env)
                    assert run.returncode==0,(label,case,run.stderr.decode())
                    assert len(run.stdout.splitlines())==3,(label,case,'incomplete report')
                    assert re.search(rb'lock=(\d+) unlock=\1',run.stderr),(label,case,'unbalanced locks')
                    records.append(run.stdout)
                data=b''.join(records);(output/(label+'.stdout')).write_bytes(data)
                results[label]=hashlib.sha256(data).hexdigest()
                if not replay:fresh=records
                else:assert records==fresh,(label,'reused context differs from fresh')
                if decoded:assert records==encoded[replay],(label,'encoded geometry differs from decoded-position oracle')
                else:
                    if not replay:encoded={}
                    encoded[replay]=records
                counts.append(dict(submit_batch=batch,decoded_positions=decoded,replay=replay,cases=len(cases),equal=True))
    # Sensitivity control: stale borrowed-cache/constants must be detected.
    mutant=output/'mutant.cpp';assert source.count('cache=nullptr;primed=0;')==1
    mutant.write_text(source.replace('cache=nullptr;primed=0;','/* intentionally broken restart: cache/constants remain */'))
    binary=build('mutation-missing-cache-reset',1,0,0,mutant)
    run=subprocess.run([str(binary),'100'],cwd=output,capture_output=True,env=env)
    baseline=(output/'b0-d0-r0.stdout').read_bytes().splitlines()[:3]
    assert run.returncode or run.stdout.splitlines()!=baseline,'Mutation was not detected'
    (output/'mutation.stdout').write_bytes(run.stdout);(output/'mutation.stderr').write_bytes(run.stderr)
    files=[tree/'port/dreamcast/game/platform/native_static.cpp',tree/'port/dreamcast/game/platform/native_ui.cpp',
           *[tree/'port/dreamcast/room'/n for n in ('instanced_mesh.hpp','mesh_fastpath.hpp','mesh_fastpath_sched.hpp','pvr_geometry.cpp','pvr_geometry.hpp','static_room_prepare.hpp')]]
    report=dict(status='PASS_HOST_COMPOSITION_ONLY',source=a.expected_source,comparisons=96,configurations=8,
                helper_sha256=digest(Path(__file__)),fixture_sha256=digest(HERE/'fixture_composition.cpp.in'),
                source_snapshot_manifest_sha256=digest(tree/'source-pins.json') if (tree/'source-pins.json').is_file() else None,
                compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
                mutation_returncode=run.returncode,mutation_stdout_sha256=hashlib.sha256(run.stdout).hexdigest(),
                knobs={'SCENERY_DEDUP':3,'SCENERY_REPLAY_LEAN':[0,1],'SCENERY_SUBMIT_BATCH':[0,1],'SCENERY_SELECT_ONLY':1,'SCENERY_SELECT_LEAN2':0},
                cases=counts,source_sha256={str(f.relative_to(tree)):digest(f) for f in files},
                extracted_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in values.items()},
                original_dedup_fill_sha256=fill_sha,output_sha256=results,missing_cache_reset_mutation_detected=True,
                target_gate_verdict='NOT_EVALUATED',
                scope='Actual extracted Emitter, MeshDraw corner/borrow/dedup/emit/restart, chunk replay and portable clipper; source admission of synthetic R4IM; controlled SQ/texture/owner edges. Only two SH4 FMAC instructions adapted to host arithmetic. No SH4 optimized clipping/FTRV/FSRRA, real room/frame, performance or target acceptance.')
    (output/'composition-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','source','comparisons','configurations','missing_cache_reset_mutation_detected')}))


if __name__=='__main__':main()
