#!/usr/bin/env python3
"""Bounded SH-4 cost of the actual Build32 cone admission/near/numeric helpers.

This is the new guard's overhead floor, not a full before/after actor draw.
Make-derived actor flags are used; the production helper is included verbatim.
Cold-I is one isolated initially cold instruction cache and perfect D-cache.
Data-line counts are address footprints, not measured misses.
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
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value
controls=module('cone32_controls',HERE/'build_controls.py');profile=controls.profile
cost=module('cone32_machine',HERE.parent/'build29/light_cost.py');kernel=cost.kernel
LAYOUT=('version','cone_bytes','eye_bytes','guard_bytes','source_bytes')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    helper=DC/'game/platform/include/actor_cone32.hpp'
    files=[Path(__file__),HERE/'cone_cost_fixture.cpp.in',helper]
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in files}
    options=controls.QA+['ACTOR_LIGHT_FAST_ONLY=1','ACTOR_BACKFACE=0','ACTOR_BACKFACE_CONE=1',
        'ACTOR_FORMAT32=1','NATIVE_ACTOR_UV16=1','COARSE_ONE_SUBMIT=1','DRAW_FALLBACK_AUDIT=0','DRAW_SETUP_AUDIT=0','QA_LINK=0']
    flags,receipt,_=profile.derive(out/'profile',cxx,kos,sdk,options,units=('native_actor_fast',))
    builder=profile.Build(out);cpp,obj,elf=out/'fixture.cpp',out/'fixture.o',out/'fixture.elf'
    cpp.write_text((HERE/'cone_cost_fixture.cpp.in').read_text().replace('@HEADER@',str(helper)))
    builder.run([*flags['native_actor_fast'],'-fstack-usage','-c',cpp,'-o',obj],label='fixture')
    script=out/'fixture.ld';script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } '
        '. = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    roots=('fixture_prepare','fixture_guard','fixture_test','fixture_source','fixture_layout')
    builder.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(script),
        '-Wl,-e,_fixture_test',*['-Wl,-u,_'+name for name in roots],obj,'-lm','-o',elf],label='link')
    prefix=str(cxx).removesuffix('g++')
    (out/'disassembly.txt').write_bytes(builder.run([prefix+'objdump','-d','-C',elf],label='disassembly'))
    program,symbols=kernel.target_machine.scalar.load_elf(elf);model=kernel.pipeline_cost.Model(out/'model',elf)
    def machine():
        value=cost.previous.Machine()
        for address,data,_ in program:value.map(address,data)
        return value
    seed=machine();layout=dict(zip(LAYOUT,struct.unpack('<'+'I'*len(LAYOUT),
        seed.bytes_at(symbols['_fixture_layout'][0],4*len(LAYOUT)))))
    cases=[]
    work=[('prepare-qualified',0,'guard',0,1),('prepare-singular',5,'guard',0,0),
          ('test-hidden',0,'test',0,1),('test-facing',1,'test',0,0),('test-near',2,'test',0,2),
          ('test-no-proof',3,'test',0,3),('test-empty',4,'test',0,4),
          ('source-match',0,'source',0,1),('source-changed',0,'source',4,0)]
    for name,config,phase,argument,expected in work:
        m=machine();m.execute(symbols['_fixture_prepare'][0],config)
        m.minimum_sp=m.reg[15];m.observe_start();m.execute(symbols['_fixture_'+phase][0],argument);m.observe_stop()
        assert m.reg[0]==expected,(name,m.reg[0],expected)
        trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
        cases.append(dict(case=name,result=m.reg[0],instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,
            traffic=kernel.traffic_details(m.memory_events,m.prefetch_events),**kernel.price_helpers.price(model,name,trace)))
        print('PASS',name,flush=True)
    assert frozen=={name:profile.sha(ROOT/name) for name in frozen},'helper changed during cost gate'
    by={row['case']:row for row in cases}
    report=dict(status='PASS',scope=__doc__,source_sha256=frozen,options=options,profile_receipt=receipt,layout=layout,cases=cases,
        fixture_sections=profile.sections(elf),fixture_sha256=profile.sha(elf),local_frames=profile.stack_usage(obj.with_suffix('.su')),
        kernel_symbols={name:dict(address=symbols['_'+name][0],bytes=symbols['_'+name][1]) for name in roots},model=model.metadata(),
        scenario=dict(label='MODELLED',cpu_mhz=200,assumed_other_ms=30,assumed_palette_prepares=40,assumed_cone_tests=200,
            whole_frame_ms=30+(40*by['prepare-qualified']['model_cycles']+200*by['test-hidden']['model_cycles'])/200000,
            note='Added helper overhead only. No saved vertices are assumed; this does not estimate complete actor cost or FPS.'),
        limitations='Excludes existing matrix composition/inversion, source bridge lookup, table validation, counters, cone construction, '
            'skinning/lighting/UV/submission savings, D-cache misses and GPU. Near/condition refusals keep ordinary rendering. '
            'This helper has conservative engineering bounds; real hardware raster/pose checks remain required.')
    (out/'cone-cost.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',cases=len(cases),layout=layout)))
if __name__=='__main__':main()
