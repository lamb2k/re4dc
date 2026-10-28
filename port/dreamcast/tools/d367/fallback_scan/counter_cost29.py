#!/usr/bin/env python3
"""Execute the unchanged FA29 core including KOS IRQ save/restore on synthetic SH4 states.

Warm/cold-I instruction cycles have perfect D-cache. Lines are architectural
32-byte addresses including stack and literals, not physical console misses.
No interrupt scheduling, firmware, private game data or device wait is modeled.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result)
    return result
controls=module('fa29_counter_controls',DC/'tools/cloud/build26/build_controls.py')
profile=controls.profile
profile.UNITS['fallback_audit29']=('fallback_audit29.o','fallback_audit29.cpp')
kernel=module('fa29_counter_kernel',DC/'tools/d367/actor_bytes_lean/kernel_audit.py')
LAYOUT=('version','reason_count','snapshot_bytes','state','state_bytes','sealed','totals','current','tick','room','ticks','draws','overflow','outside_tick','sequence','active','paused','have_room','draw','valid','output')

class Machine(kernel.Machine):
    def step(self,pc,delay=False):
        opcode=self.fetch(pc)
        if opcode&0xff00==0xca00:
            self.reg[0]^=opcode&255;self.instruction_pcs.append(pc);self.steps+=1;return pc+2
        return super().step(pc,delay)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('output','sh4-cxx','kos-root','sdk-root'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=a.sh4_cxx.resolve(),a.kos_root.resolve(),a.sdk_root.resolve()
    inputs=[Path(__file__),HERE/'counter_fixture.cpp.in',DC/'game/fallback_audit29.cpp',DC/'game/platform/include/fallback_audit29.h',DC/'game/platform/include/fallback_audit29.def',DC/'game/fallback_audit29.mk']
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in inputs}
    flags,receipt,sources=profile.derive(out/'profile',cxx,kos,sdk,controls.QA+['DRAW_FALLBACK_AUDIT=1','FALLBACK_AUDIT29=1','QA_LINK=0'],units=('fallback_audit29',))
    command=flags['fallback_audit29'];builder=profile.Build(out)
    cpp,obj,elf=out/'fixture.cpp',out/'fixture.o',out/'fixture.elf'
    cpp.write_text((HERE/'counter_fixture.cpp.in').read_text().replace('@DC@',str(DC)))
    builder.run([*command,'-fstack-usage','-c',cpp,'-o',obj],label='fixture')
    production=out/'production.o';builder.run([*command,'-fstack-usage','-c',sources['fallback_audit29'],'-o',production],label='production')
    script=out/'fixture.ld';script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } . = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
    roots=('fixture_hit','fixture_begin','fixture_end','fixture_snapshot','fixture_layout')
    builder.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(script),'-Wl,-e,_fixture_hit',*['-Wl,-u,_'+r for r in roots],obj,'-o',elf],label='link')
    prefix=str(cxx).removesuffix('g++');(out/'disassembly.txt').write_bytes(builder.run([prefix+'objdump','-d','-C',elf],label='disassembly'))
    program,symbols=kernel.target_machine.scalar.load_elf(elf);model=kernel.pipeline_cost.Model(out/'model',elf)
    def new():
        m=Machine()
        for address,data,_ in program:m.map(address,data)
        return m
    seed=new();layout=dict(zip(LAYOUT,struct.unpack('<'+'I'*len(LAYOUT),seed.bytes_at(symbols['_fixture_layout'][0],4*len(LAYOUT)))))
    n=layout['reason_count'];assert layout['snapshot_bytes']==36+8*n
    cases=[dict(name='hit-active',entry='fixture_hit',arg=1),dict(name='hit-8192',entry='fixture_hit',arg=8192),dict(name='hit-outside',entry='fixture_hit',arg=1,active=0),dict(name='hit-paused',entry='fixture_hit',arg=1,paused=1),dict(name='hit-unarmed',entry='fixture_hit',arg=1,have_room=0),dict(name='hit-saturated',entry='fixture_hit',arg=9,old=0xfffffffd),dict(name='begin-same-room',entry='fixture_begin',arg=18),dict(name='begin-new-room',entry='fixture_begin',arg=18,room=0x100),dict(name='begin-paused',entry='fixture_begin',arg=18,paused=1),dict(name='seal-drawn',entry='fixture_end'),dict(name='seal-skipped',entry='fixture_end',draw=0),dict(name='seal-inactive',entry='fixture_end',active=0),dict(name='snapshot',entry='fixture_snapshot'),dict(name='snapshot-invalid',entry='fixture_snapshot',valid=0)]
    rows=[]
    for case in cases:
        m=new()
        def put(name,value,size=4):m.map(layout[name],int(value).to_bytes(size,'little'))
        def get(name,size=4):return int.from_bytes(m.bytes_at(layout[name],size),'little')
        totals=[100+i for i in range(n)];current=[10+i for i in range(n)]
        totals[0]=case.get('old',totals[0]);current[0]=case.get('old',current[0])
        m.map(layout['totals'],struct.pack('<'+'I'*n,*totals));m.map(layout['current'],struct.pack('<'+'I'*n,*current))
        oldsealed=[7,16,0x103,3,2,0,0,16,1]+[50+i for i in range(n)]+[30+i for i in range(n)]
        sealedbytes=struct.pack('<'+'I'*len(oldsealed),*oldsealed);m.map(layout['sealed'],sealedbytes);m.map(layout['output'],b'\xa5'*layout['snapshot_bytes'])
        for name,value in (('active',case.get('active',1)),('paused',case.get('paused',0)),('have_room',case.get('have_room',1)),('draw',case.get('draw',1)),('valid',case.get('valid',1))):put(name,value,1)
        for name,value in (('tick',17),('room',case.get('room',0x103)),('ticks',3),('draws',2),('overflow',0),('outside_tick',0),('sequence',7)):put(name,value)
        initial_sr=m.sr;m.observe_start();m.execute(symbols['_'+case['entry']][0],case.get('arg',0));m.observe_stop();assert m.sr&~1==initial_sr&~1,(case,'IRQ mask not restored')
        after=list(struct.unpack('<'+'I'*n,m.bytes_at(layout['totals'],4*n)))
        cur=list(struct.unpack('<'+'I'*n,m.bytes_at(layout['current'],4*n)))
        if case['entry']=='fixture_hit':
            expected=totals.copy();expected_cur=current.copy();armed=not case.get('paused',0) and case.get('have_room',1)
            if armed:expected[0]=min(0xffffffff,expected[0]+case['arg'])
            if armed and case.get('active',1):expected_cur[0]=min(0xffffffff,expected_cur[0]+case['arg'])
            assert after==expected and cur==expected_cur,case
            assert get('outside_tick')==int(armed and not case.get('active',1)),case
            assert get('overflow')==int(armed and totals[0]+case['arg']>0xffffffff),case
        elif case['entry']=='fixture_begin':
            if case.get('paused',0):assert cur==current and get('active',1)==0,case
            else:
                assert cur==[0]*n and get('tick')==18 and get('room')==0x103 and get('active',1)==1,case
                assert after==(totals if case.get('room',0x103)==0x103 else [0]*n),case
        elif case['entry']=='fixture_end':
            sealed=list(struct.unpack('<'+'I'*len(oldsealed),m.bytes_at(layout['sealed'],layout['snapshot_bytes'])))
            if case.get('active',1):
                expected=[8,17,case.get('room',0x103),4,2+case.get('draw',1),0,0,17 if case.get('draw',1) else 16,1]+totals+(current if case.get('draw',1) else oldsealed[9+n:])
                assert sealed==expected and get('active',1)==0,case
            else:assert sealed==oldsealed,case
        else:assert m.bytes_at(layout['output'],layout['snapshot_bytes'])==(sealedbytes if case.get('valid',1) else b'\xa5'*layout['snapshot_bytes']),case
        traffic=kernel.traffic_details(m.memory_events,m.prefetch_events);trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
        rows.append(dict(case=case['name'],instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,traffic=traffic,**kernel.price_helpers.price(model,case['name'],trace)))
        print('PASS',case['name'],flush=True)
    by={r['case']:r for r in rows};scenarios=[]
    for hits in (1000,10000):
        frequency={'hit-active':hits,'begin-same-room':1,'seal-drawn':1};cycles=sum(by[k]['model_cycles']*v for k,v in frequency.items())
        scenarios.append(dict(label='MODELLED',assumed_calls=frequency,cpu_mhz=200,assumed_other_work_ms=30,observer_ms=cycles/200000,whole_frame_ms=30+cycles/200000))
    assert frozen=={str(p.relative_to(ROOT)):profile.sha(p) for p in inputs}
    report=dict(status='PASS',scope=__doc__,source_sha256=frozen,profile_receipt=receipt,flags=command,layout=layout,fixture_sha256=profile.sha(elf),fixture_sections=profile.sections(elf),production_object=dict(sha256=profile.sha(production),**profile.sections(production),stack_usage=profile.stack_usage(production.with_suffix('.su'))),cases=rows,scenarios=scenarios,model=model.metadata(),limits='Synthetic scalar core only; native KOS IRQ instructions included but interrupt delivery/preemption not modeled. No formatting, actor reset callback, modem, game data, hardware D-cache misses or device waits. Off runtime delta zero. Cold-I cannot be summed into a frame.')
    (out/'counter-cost29.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='PASS',cases=len(rows),receipt=str(out/'counter-cost29.json'))))
if __name__=='__main__':main()
