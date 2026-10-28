#!/usr/bin/env python3
"""Bounded SH-4 cost of actual FRONT_TEXOBJ cache and uncached init bodies.

The old and repaired helper compile with actual Make-derived trans flags.
External TEXGet/GXInitTexObj/cTexChg::move remain separately compiled calls.
Warm/cold-I models assume perfect D-cache; 32-byte data lines are address
footprints, not cache misses. This prices small helper scenarios, not a game
frame, real descriptor frequency, render look, STRICT or physical console.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
import front_sources as source
HERE,DC,ROOT=source.HERE,source.DC,source.ROOT
BASELINE='36643bf8ab5a78c581274f28eca702ae8aa48330'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value


controls=module('front34_controls',HERE/'build_controls.py');profile=controls.profile
cost=module('front34_machine',HERE.parent/'build29/light_cost.py');kernel=cost.kernel
LAYOUT=('version','key_bytes','record_bytes','key_array_bytes','record_array_bytes',
        'descriptor_header_bytes','descriptor_bytes','model_info_bytes','global_bytes')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--control-ref',default=BASELINE)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    files=[*source.source_files(),Path(__file__),HERE/'front_cost_fixture.cpp.in',HERE/'build_controls.py']
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in files}
    options=controls.QA+['FRONT_TEXOBJ=1','DRAW_FALLBACK_AUDIT=0','DRAW_SETUP_AUDIT=0','QA_LINK=0']
    profile.UNITS.update({name:tuple(value) for name,value in controls.DEFAULT['units'].items()})
    flags,receipt,_=profile.derive(out/'profile',cxx,kos,sdk,options,units=('trans',))
    builder=profile.Build(out);cases=[];artifacts={}
    for arm,ref in (('baseline',args.control_ref),('repaired',None)):
        values=source.source_values(ref)
        types_template=(HERE/'front_fixture_types.hpp.in').read_text()
        providers=dict(values,CACHE='',SOURCE_LOOP='',TEX_GET=values['TEX_GET'],GX_INIT=values['GX_INIT'],SWAP=values['SWAP'])
        provider=out/(arm+'-providers.cpp')
        provider_text=source.render(types_template,providers)
        provider_text=provider_text.replace('FixtureGame* pG=&game;','extern FixtureGame* pG;')
        provider_text=provider_text.replace('static_assert(sizeof(FtKey)==16 && sizeof(FtRec)==16);','')
        provider.write_text(provider_text)
        # Deliberately separate the provider bodies so the compiler cannot
        # inline external source TPL/GX helpers into the measured trans code.
        measured=dict(values,TEX_GET='',SWAP='',GX_INIT='void GXInitTexObj(GXTexObj*,void*,u16,u16,int,int,int,u8);')
        types=source.render(types_template,measured)
        cpp=out/(arm+'.cpp');cpp.write_text(source.render((HERE/'front_cost_fixture.cpp.in').read_text(),{'TYPES':types}))
        obj=out/(arm+'.o');provider_obj=out/(arm+'-providers.o');elf=out/(arm+'.elf')
        builder.run([*flags['trans'],'-fstack-usage','-c',cpp,'-o',obj],label=arm+'-fixture')
        builder.run([*flags['trans'],'-c',provider,'-o',provider_obj],label=arm+'-providers')
        script=out/(arm+'.ld')
        script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } '
            '. = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
        roots=('fixture_prepare','fixture_run','fixture_check','fixture_layout')
        builder.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(script),
            '-Wl,-e,_fixture_run',*['-Wl,-u,_'+name for name in roots],obj,provider_obj,'-o',elf],label=arm+'-link')
        prefix=str(cxx).removesuffix('g++')
        (out/(arm+'-disassembly.txt')).write_bytes(builder.run([prefix+'objdump','-d','-C',elf],label=arm+'-disassembly'))
        program,symbols=kernel.target_machine.scalar.load_elf(elf)
        model=kernel.pipeline_cost.Model(out/(arm+'-model'),elf)
        def machine():
            m=cost.previous.Machine()
            for address,data,_ in program:m.map(address,data)
            return m
        seed=machine()
        layout=dict(zip(LAYOUT,struct.unpack('<'+'I'*len(LAYOUT),seed.bytes_at(symbols['_fixture_layout'][0],4*len(LAYOUT)))))
        work=[]
        for count in (1,8,32,248):
            work.extend([(f'cold-{count}',count,0,0,1),(f'hit-{count}',count,1,0,1),
                         (f'uncached-{count}',count,0,1,1)])
        work.extend([(f'wrap-hit-{count}',count,2,0,1) for count in (8,32)])
        work.extend([(f'dirty-last-{count}',count,3,0,0 if arm=='baseline' else 1) for count in (8,32,248)])
        for name,count,mode,uncached,correct in work:
            m=machine();m.execute(symbols['_fixture_prepare'][0],count|(mode<<8));m.minimum_sp=m.reg[15]
            m.observe_start();m.execute(symbols['_fixture_run'][0],uncached);m.observe_stop()
            assert m.reg[0]==1,(arm,name,m.reg[0])
            trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
            row=dict(arm=arm,case=name,descriptors=count,correct=bool(correct),instructions=m.steps,
                peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,
                traffic=kernel.traffic_details(m.memory_events,m.prefetch_events),
                **kernel.price_helpers.price(model,arm+'-'+name,trace))
            m.execute(symbols['_fixture_check'][0],0)
            assert m.reg[0]==correct,(arm,name,'unexpected semantic result',m.reg[0],correct)
            cases.append(row);print('PASS',arm,name,flush=True)
        artifacts[arm]=dict(layout=layout,fixture_sections=profile.sections(elf),fixture_sha256=profile.sha(elf),
            local_frames=profile.stack_usage(obj.with_suffix('.su')),
            kernel_symbols={name:dict(address=symbols['_'+name][0],bytes=symbols['_'+name][1]) for name in roots},model=model.metadata())
    assert frozen=={name:profile.sha(ROOT/name) for name in frozen},'Source changed during cost gate'
    rows={(row['arm'],row['case']):row for row in cases}
    scenario=[]
    for count in (1,8,32,248):
        old,new,uncached=(rows[(arm,name)] for arm,name in [('baseline',f'hit-{count}'),('repaired',f'hit-{count}'),('repaired',f'uncached-{count}')])
        scenario.append(dict(descriptors=count,assumed_lookups=200,
            baseline_helper_ms=old['model_cycles']*200/200000,
            repaired_helper_ms=new['model_cycles']*200/200000,
            uncached_helper_ms=uncached['model_cycles']*200/200000,
            validation_added_ms=(new['model_cycles']-old['model_cycles'])*200/200000))
    report=dict(status='PASS',scope=__doc__,source_sha256=frozen,control_ref=args.control_ref,
        options=options,profile_receipt=receipt,cases=cases,artifacts=artifacts,
        scenario=dict(label='MODELLED',cpu_mhz=200,rows=scenario,
            note='200 repeated helper calls is an explicit sensitivity assumption, not an observed game workload. '
                 'Dirty baseline rows are known incorrect counterexamples and are not viable performance alternatives. '
                 'Cold-I results are isolated and not additive. No FPS or frame gain is predicted.'),
        limits='No material binding, model transforms, renderer, cache misses, I/O or console timing. '
               'Provider bodies are actual source compiled separately with trans Make flags; only cache/plain-init calls are priced. '
               'No periodic log or texture swaps run in the cost cases; host fixtures cover those semantics.')
    path=out/'front-cost.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',cases=len(cases),receipt=str(path))))


if __name__=='__main__':main()
