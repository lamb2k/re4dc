#!/usr/bin/env python3
"""Price ordered metadata/key preparation, not a complete world draw.

The fixture uses the production plan compiler and layout and exact baseline
R4PW16/R4IM36 records. It compares a pass scan/key build with its precompiled
pass span. Allocation/build-once cost, other live predicates, vertex work and
submission are excluded. Perfect D-cache; reported lines are address touches,
not observed cache misses. Cold-I is an isolated helper experiment.
"""
import argparse, importlib.util, json, struct, sys
from pathlib import Path
from types import SimpleNamespace
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
old=module('wp29_cost_machine',HERE.parent/'build29/light_cost.py')
profile,kernel=old.profile,old.kernel
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('output','sh4-cxx','kos-root','sdk-root'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx=a.sh4_cxx.resolve();builder=profile.Build(out)
    options=['NMR_POOL_LOD=0','WORLD_PART_PLAN29=1','WORLD_PORTAL29=0']
    flags,receipt,_=profile.derive(out/'profile',cxx,a.kos_root.resolve(),a.sdk_root.resolve(),options,units=('native_static',))
    header=DC/'game/platform/include/world_part_plan29.hpp';cpp=out/'fixture.cpp'
    cpp.write_text((HERE/'part_plan_cost.cpp.in').read_text().replace('@HEADER@',str(header)))
    obj=out/'fixture.o';elf=out/'fixture.elf'
    builder.run([*flags['native_static'],'-fstack-usage','-c',cpp,'-o',obj],label='compile')
    ld=out/'fixture.ld';ld.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    names=('fixture_prepare','fixture_before','fixture_after','fixture_layout')
    builder.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(ld),'-Wl,-e,_fixture_before',*['-Wl,-u,_'+n for n in names],obj,'-o',elf],label='link')
    program,symbols=kernel.target_machine.scalar.load_elf(elf);model=kernel.pipeline_cost.Model(out/'model',elf)
    def machine():
        m=old.previous.Machine()
        for address,data,_ in program:m.map(address,data)
        return m
    seed=machine();layout=struct.unpack('<III',seed.bytes_at(symbols['_fixture_layout'][0],12));assert layout[0]==1
    rows=[]
    for n in (1,16,64,128):
        expected=None;arms={}
        for arm in ('before','after'):
            m=machine();m.execute(symbols['_fixture_prepare'][0],n);assert m.reg[0]==1
            m.minimum_sp=m.reg[15];m.observe_start();m.execute(symbols['_fixture_'+arm][0],n);m.observe_stop()
            count=m.reg[0];data=m.bytes_at(layout[1],count*28)
            if expected is None:expected=(count,data)
            else:assert expected==(count,data)
            trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
            arms[arm]=dict(selected=count,instructions=m.steps,stack=m.initial_regs[15]-m.minimum_sp,
                traffic=kernel.traffic_details(m.memory_events,m.prefetch_events),**kernel.price_helpers.price(model,f'{n}-{arm}',trace),
                helper_code_bytes=symbols['_fixture_'+arm][1])
        rows.append(dict(source_parts=n,arms=arms))
    report=dict(status='PASS',scope=__doc__,cases=rows,profile_receipt=receipt,model=model.metadata(),
        source_sha256={str(p.relative_to(ROOT)):profile.sha(p) for p in (Path(__file__),HERE/'part_plan_cost.cpp.in',header)},
        fixture_sections=profile.sections(elf),local_frames=profile.stack_usage(obj.with_suffix('.su')),
        scenario=dict(label='MODELLED',cpu_mhz=200,assumed_other_work_ms=30,assumed_meshes_of64_parts=20,
            whole_frame_ms={arm:30+rows[2]['arms'][arm]['model_cycles']*20/200000 for arm in ('before','after')},
            limitation='Synthetic metadata-only sensitivity; no real room/console frame or D-cache saving claimed.'))
    (out/'part-plan-cost.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='PASS',cases=len(rows),scenario=report['scenario'])))
if __name__=='__main__':main()
