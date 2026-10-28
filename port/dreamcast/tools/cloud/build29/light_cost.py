#!/usr/bin/env python3
"""Price actual old exact and new offline-baked light routines on SH-4.

The current actor TU and light evaluator compile unmodified, with Make flags.
The real converter makes a 128-record FE blob from hand-authored ModelData.
Both arms use unit-distance lamps, the model's qualified FSRRA(1) domain.
Warm/cold-I timings assume perfect D-cache; data lines are touched addresses,
not measured console misses. These are lighting pieces, not complete draws.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
controls=module('b29_light_controls',HERE/'build_controls.py');profile=controls.profile
previous=module('b29_light_machine',HERE.parent/'build25/cost_run.py');kernel=previous.kernel
sys.path.insert(0,str(DC/'tools/d367/fallback_scan'))
import convert

LAYOUT=('version','part_bytes','frame_bytes','lights_bytes','source_bytes','source_part_bytes',
        'part','frame','source','lights','positions','normals','cache','blob','blob_bytes','bake_use','argb_offset')
# The ordinary, mutable-bake fallback is retained by the actual wrapper's
# object code but cannot be reached by any admitted tagged fixture. Bind only
# those external dependencies to distinct fail-closed addresses: executing one
# aborts the model, rather than silently substituting a zero-cost success stub.
UNPRICED=('mat_load','re4dc_avk_light_skin','re4dc_avk_light_rigid_n16s6',
          're4dc_avk_light_rigid_n16','re4dc_avk_light_rigid3','re4dc_avk_light_rigid',
          're4dc_avk_light_skin_n16','re4dc_actor_stream_begin','re4dc_actor_stream_end')
POISON={name:0x3fff0000+i*32 for i,name in enumerate(UNPRICED)}

class Machine(previous.Machine):
    def step(self,pc,delay=False):
        if pc in POISON.values():
            raise RuntimeError('unpriced fallback dependency executed: '+
                               next(k for k,v in POISON.items() if v==pc))
        return super().step(pc,delay)

def dataset():
    pos,nrm,col,uv,weights,part,stream=80,1104,1616,2128,2640,2656,2688
    data=bytearray(stream+4096)
    struct.pack_into('<I',data,0,64);struct.pack_into('<III',data,12,col,uv,weights)
    data[24:26]=bytes((1,1));struct.pack_into('<HIII',data,26,1,part,0xa0000000,1)
    data[40]=4;struct.pack_into('<IIHHI',data,48,pos,nrm,128,128,0x20010801)
    data[64:68]=bytes((0,255,0,0));data[weights:weights+8]=bytes((0,0,0,1,255,0,0,0))
    for i in range(128):
        struct.pack_into('<3bB',data,nrm+i*4,0,0,64,0)
        data[col+i*4:col+i*4+4]=bytes((255,255,255,73))
        struct.pack_into('<2h',data,uv+i*4,i,0)
    struct.pack_into('<II',data,part+24,4096,43)
    data[stream]=0x90;struct.pack_into('>H',data,stream+1,129)
    for i in range(129):struct.pack_into('>4H',data,stream+3+8*i,*([i%128]*4))
    data=bytes(data)
    context=dict(schema=convert.SCHEMA,source_sha256=convert.sha(data),source_kind='PS2-converted-ModelData',
        ownership='source-model',provenance='hand-authored 128-record public lighting cost fixture; no game assets',
        pose_space='source-normal-space',parts=[dict(index=0,static_vertex_colors=True,normal_matrices=[convert.IDENTITY],
            render=dict(blend=0,alpha_state=73,material_animation=False),lighting=dict(enabled=True,
            ambient_vertex=False,material_vertex=False,diffuse=2,ambient_rgb=[64]*3,material_rgb=[128]*3,tev_scale=1,
            actor_probe_mode=1,model_id=0x40,leon_marker=False,headroom_half=False,
            ganado_lit_toggle=False,ganado_mode=0,basis_valid=True,probe_valid=True,
            directional_lights=[dict(direction=[0,0,1],color_rgb=[64]*3)]))])
    converted,receipt=convert.convert(data,json.dumps(context).encode(),fold_light_scale=True)
    result=convert.parse_model_bin(converted)
    assert result['parts'][0]['vertices']==128
    return converted[stream:],receipt

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=a.sh4_cxx.resolve(),a.kos_root.resolve(),a.sdk_root.resolve()
    files=[Path(__file__),HERE/'light_cost_fixture.cpp.in',HERE/'build_controls.py',
           DC/'game/platform/native_actor_fast.cpp',DC/'room/source_lighting.cpp',DC/'game/fallback_scan29.mk',
           *sorted((DC/'game/platform/include').glob('fallback_scan29*')),Path(convert.__file__),
           DC/'tools/d367/fallback_scan/formats.py']
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in files}
    options=controls.QA+['FALLBACK_SCAN29=1','FALLBACK_AUDIT29=0','ACTOR_LIGHT_FAST_ONLY=0','ACTOR_LIGHT_CAP=0',
        'DRAW_FALLBACK_AUDIT=0','DRAW_SETUP_AUDIT=0','QA_LINK=0','ACTOR_EXACT_FAST=1','ACTOR_PROBE_LIGHT=1',
        'GANADO_LIT=0','ACTOR_PROBE_LIGHT_LOG=0']
    flags,receipt,_=profile.derive(out/'profile',cxx,kos,sdk,options,units=('native_actor_fast',))
    command=flags['native_actor_fast'];builder=profile.Build(out)
    blob,conversion=dataset();cpp=out/'fixture.cpp'
    cpp.write_text('#include "'+str(DC/'game/platform/native_actor_fast.cpp')+'"\n'+
        (HERE/'light_cost_fixture.cpp.in').read_text().replace('@BLOB@',','.join(str(x) for x in blob)))
    obj,lighting,identity,elf=out/'fixture.o',out/'source_lighting.o',out/'identity.o',out/'fixture.elf'
    builder.run([*command,'-fstack-usage','-c',cpp,'-o',obj],label='fixture')
    builder.run([*command,'-c',DC/'room/source_lighting.cpp','-o',lighting],label='lighting')
    builder.run([*command,'-x','c++','-c',HERE.parent/'build25/cost_identity.cpp.in','-o',identity],label='identity')
    script=out/'fixture.ld';script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    roots=('fixture_prepare','fixture_fold','fixture_pass','fixture_layout')
    builder.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(script),
        '-Wl,-e,_fixture_fold',*['-Wl,-u,_'+r for r in roots],
        *[f'-Wl,--defsym,_{name}=0x{address:x}' for name,address in POISON.items()],
        obj,lighting,identity,'-lm','-o',elf],label='link')
    prefix=str(cxx).removesuffix('g++')
    (out/'disassembly.txt').write_bytes(builder.run([prefix+'objdump','-d','-C',elf],label='disassembly'))
    program,symbols=kernel.target_machine.scalar.load_elf(elf);model=kernel.pipeline_cost.Model(out/'model',elf)
    arithmetic=previous.conversion_controls()
    for address in POISON.values():
        try:Machine().step(address)
        except RuntimeError:pass
        else:raise AssertionError('unpriced dependency did not fail closed')
    def machine():
        m=Machine()
        for address,data,_ in program:m.map(address,data)
        return m
    seed=machine();layout=dict(zip(LAYOUT,struct.unpack('<'+'I'*len(LAYOUT),seed.bytes_at(symbols['_fixture_layout'][0],4*len(LAYOUT)))))
    assert layout['version']==1 and layout['argb_offset']==24
    cases=[]
    for n in (16,128):
        for arm,name in ((0,'exact'),(1,'baked'),(2,'baked-flash')):
            m=machine();m.execute(symbols['_fixture_prepare'][0],arm)
            before=m.bytes_at(layout['blob'],layout['blob_bytes']);phases={}
            for phase,argument in (('fold',0),('pass',n)):
                m.minimum_sp=m.reg[15];m.observe_start();m.execute(symbols['_fixture_'+phase][0],argument);m.observe_stop()
                traffic=kernel.traffic_details(m.memory_events,m.prefetch_events)
                if phase=='fold':assert m.reg[0]==int(bool(arm)),(arm,'dispatch')
                else:
                    words=[previous.read_u32(m,layout['cache']+i*32+24) for i in range(n)]
                    assert all(w>>24==73 for w in words),(arm,'alpha')
                    if arm:
                        assert previous.read_u32(m,layout['bake_use']) in (1,2),(arm,'bake refused')
                        for key,size in (('positions',1024),('normals',512)):
                            assert not [e for e in m.memory_events if layout[key]<=e[3]<layout[key]+size],(arm,key,'per-vertex geometry read')
                    assert m.bytes_at(layout['blob'],layout['blob_bytes'])==before,'offline blob was mutated'
                trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
                phases[phase]=dict(instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,traffic=traffic,
                    **kernel.price_helpers.price(model,f'{name}-{n}-{phase}',trace))
                if phase=='pass':phases[phase]['first_argb']=f'{words[0]:08x}'
            cases.append(dict(arm=name,vertices=n,phases=phases));print('PASS',name,n,flush=True)
    selected={r['arm']:r for r in cases if r['vertices']==128}
    cycles={name:sum(p['model_cycles'] for p in row['phases'].values()) for name,row in selected.items()}
    assert int(selected['baked-flash']['phases']['pass']['first_argb'],16)&0xffffff > int(selected['baked']['phases']['pass']['first_argb'],16)&0xffffff
    assert frozen=={p:profile.sha(ROOT/p) for p in frozen},'source changed during cost gate'
    report=dict(status='PASS',scope=__doc__,source_sha256=frozen,profile_receipt=receipt,options=options,
        arithmetic_controls=arithmetic,unexecuted_fail_closed_dependencies=POISON,
        conversion_receipt=conversion,fixture_sha256=profile.sha(elf),fixture_sections=profile.sections(elf),
        local_frames=profile.stack_usage(obj.with_suffix('.su')),layout=layout,cases=cases,model=model.metadata(),
        scenario=dict(label='MODELLED',cpu_mhz=200,assumed_pieces=120,vertices_per_piece=128,assumed_other_work_ms=30,
            whole_frame_ms={k:30+v*120/200000 for k,v in cycles.items()},
            note='Synthetic sensitivity at 15360 vertices, not the measured barn distribution or a console prediction. Cold-I costs cannot be added as one frame.'),
        limitations='No deformation, clipping, texture fetch, submit, interrupts, KOS waits or D-cache misses. Stubbed model-kind lookup excludes real bridge work; data bake quantizes RGB565 and approximates live direction/attenuation. Alpha is exact.')
    (out/'light-cost.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',cases=len(cases),cycles_per128=cycles)))

if __name__=='__main__':main()
