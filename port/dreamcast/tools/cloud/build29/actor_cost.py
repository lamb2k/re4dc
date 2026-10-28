#!/usr/bin/env python3
"""Price real compiled actor attribution with bounded synthetic pointer keys.

Full actor, bridge and FA29 core TUs compile unchanged under Make flags. Existing
and overflow rows exercise 1/32-key searches. Fresh rows use the real bridge's
unknown-owner return; valid model-info/part-table traversal remains unpriced.
Warm/cold-I cycles assume perfect D-cache; data lines are touched addresses.
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
controls=module('b29_actor_controls',HERE/'build_controls.py');profile=controls.profile
cost=module('b29_actor_machine',HERE/'light_cost.py');kernel=cost.kernel
LAYOUT=('version','state_bytes','row_bytes','used','spill','rows','setups','vertices','changes')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=a.sh4_cxx.resolve(),a.kos_root.resolve(),a.sdk_root.resolve()
    inputs=[Path(__file__),HERE/'actor_cost_fixture.cpp.in',HERE/'light_cost.py',HERE/'build_controls.py',
        DC/'game/platform/native_actor_fast.cpp',DC/'game/model_bridge.cpp',DC/'game/fallback_audit29.cpp',
        *sorted((DC/'game/platform/include').glob('fallback_actor_audit29*')),
        DC/'game/platform/include/fallback_audit29.h',DC/'game/platform/include/fallback_audit29.def']
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in inputs}
    options=controls.QA+['FALLBACK_AUDIT29=1','FALLBACK_SCAN29=0','DRAW_FALLBACK_AUDIT=1','QA_LINK=0']
    units=('native_actor_fast','model_bridge','fallback_audit29')
    flags,receipt,sources=profile.derive(out/'profile',cxx,kos,sdk,options,units=units)
    builder=profile.Build(out);cpp=out/'fixture.cpp';elf=out/'fixture.elf'
    cpp.write_text('#include "'+str(sources['native_actor_fast'])+'"\n'+(HERE/'actor_cost_fixture.cpp.in').read_text())
    objects=[]
    for unit in units:
        obj=out/(unit+'.o');objects.append(obj)
        builder.run([*flags[unit],'-fstack-usage','-c',cpp if unit=='native_actor_fast' else sources[unit],'-o',obj],label=unit)
    script=out/'fixture.ld';script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    roots=('fixture_prepare','fixture_note','fixture_vertices','fixture_layout')
    builder.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(script),
        '-Wl,-e,_fixture_note',*['-Wl,-u,_'+r for r in roots],*objects,'-o',elf],label='link')
    program,symbols=kernel.target_machine.scalar.load_elf(elf);model=kernel.pipeline_cost.Model(out/'model',elf)
    def machine():
        m=cost.previous.Machine()
        for address,data,_ in program:m.map(address,data)
        return m
    seed=machine();layout=dict(zip(LAYOUT,struct.unpack('<'+'I'*len(LAYOUT),seed.bytes_at(symbols['_fixture_layout'][0],4*len(LAYOUT)))))
    assert layout['version']==1 and layout['row_bytes']==72
    cases=[('new-unknown-owner',0),('first-of-one',1),('first-of32',32),('last-of32',32+(31<<6)),
           ('overflow-of32',32+(32<<6)),('paused',1+(1<<12)),('successful-probe',1+(1<<14)),
           ('changed-context',1+(1<<15))]
    rows=[]
    for name,config in cases:
        m=machine();m.execute(symbols['_fixture_prepare'][0],config)
        target=(config>>6)&63;before_used=cost.previous.read_u32(m,layout['used'])
        def value(field,index=target):return cost.previous.read_u32(m,layout['rows']+index*layout['row_bytes']+layout[field])
        oldsetup=value('setups') if target<32 else 0;oldvertices=value('vertices') if target<32 else 0
        phases={}
        for phase,arg in (('note',0),('vertices',128)):
            m.minimum_sp=m.reg[15];m.observe_start();m.execute(symbols['_fixture_'+phase][0],arg);m.observe_stop()
            trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
            phases[phase]=dict(instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,
                traffic=kernel.traffic_details(m.memory_events,m.prefetch_events),**kernel.price_helpers.price(model,name+'-'+phase,trace))
        if name=='overflow-of32':assert cost.previous.read_u32(m,layout['spill'])==1
        elif name=='paused':assert value('setups')==oldsetup and value('vertices')==oldvertices
        elif name=='successful-probe':assert value('setups')==oldsetup and value('vertices')==oldvertices+128
        else:assert value('setups')==oldsetup+1 and value('vertices')==oldvertices+128
        assert cost.previous.read_u32(m,layout['used'])==max(1,before_used)
        if name=='changed-context':assert value('changes')==1
        rows.append(dict(case=name,phases=phases));print('PASS',name,flush=True)
    assert frozen=={p:profile.sha(ROOT/p) for p in frozen},'source changed during gate'
    report=dict(status='PASS',scope=__doc__,source_sha256=frozen,profile_receipt=receipt,layout=layout,cases=rows,
        fixture_sha256=profile.sha(elf),fixture_sections=profile.sections(elf),
        local_frames={u:profile.stack_usage((out/(u+'.o')).with_suffix('.su')) for u in units},model=model.metadata(),
        limitations='Diagnostic hooks only, not formatted QA transport. No D-cache misses, interrupts, allocator, private models or whole draw. Unknown-owner callback is a lower bound for the first encounter; later rows do not call it. Successful-probe vertices case deliberately invokes the independent accounting helper, which production does not do for a fast probe.')
    (out/'actor-cost.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='PASS',cases=len(rows))))
if __name__=='__main__':main()
