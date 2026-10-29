#!/usr/bin/env python3
"""Bounded actual SH-4 FA29 collector and drawn-window instruction cost.

KOS IRQ save/restore instructions execute unchanged with architectural SR
state; no IRQ stubs or new assembly are used. Every production executable
section must equal the address-metadata fixture section before timing.
Warm/cold-I cycles use the existing perfect-D-cache scheduling model. Data
lines are 32-byte touched addresses, not measured misses or console latency.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1];GAME=DC/'game'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value


controls=module('window35_controls',HERE/'build_controls.py');profile=controls.profile
previous=module('window35_machine',HERE.parent/'build25/cost_run.py');kernel=previous.kernel
LAYOUT=('version','reason_count','snapshot_bytes','state','state_bytes','sealed','totals','current',
        'tick','room','ticks','draws','overflow','outside_tick','sequence','active','paused','have_room',
        'draw','valid','output','dfa_reasons','dfa','dfa_overflow','window_overflow','fn_hit','fn_begin',
        'fn_end','fn_snapshot','fn_reset','fn_pause','fn_resume')
WINDOW=('version','bytes','row_bytes','N','reasons','window','rows','row_ordinal','row_tick','row_flags',
        'sums','logic','draws','skipped','incomplete','room','tick','last_tick','outside_room','epoch',
        'next','used','overflow_rows','reset_cause','active','paused','have_room','counter_overflow',
        'fn_begin','fn_end','fn_reset','fn_pause','fn_resume')


class Machine(previous.Machine):
    def step(self,pc,delay=False):
        if hasattr(self,'irq_states'):
            self.irq_states[self.steps]=bool(self.sr&0xf0)
        return super().step(pc,delay)


def executable_sections(path):
    data=path.read_bytes();assert data[:6]==b'\x7fELF\x01\x01'
    offset=struct.unpack_from('<I',data,32)[0];stride,count,names_index=struct.unpack_from('<HHH',data,46)
    headers=[struct.unpack_from('<10I',data,offset+i*stride) for i in range(count)]
    names_header=headers[names_index];names=data[names_header[4]:names_header[4]+names_header[5]]
    result={}
    for header in headers:
        name=names[header[0]:].split(b'\0',1)[0].decode()
        if header[2]&4 and header[5]:result[name]=data[header[4]:header[4]+header[5]]
    return result


def section_identity(production,fixture):
    old,new=executable_sections(production),executable_sections(fixture)
    assert old and all(name in new and data==new[name] for name,data in old.items()),[
        name for name,data in old.items() if new.get(name)!=data]
    return dict(status='PASS',sections=len(old),bytes=sum(map(len,old.values())),
        section_sha256={name:hashlib.sha256(data).hexdigest() for name,data in old.items()})


def put(m,address,value,size=4):m.map(address,int(value).to_bytes(size,'little'))
def get(m,address,size=4):return int.from_bytes(m.bytes_at(address,size),'little')
def words(m,address,count,size=4):return [get(m,address+i*size,size) for i in range(count)]
def vector(m,address,values,size=4):m.map(address,b''.join(int(x).to_bytes(size,'little') for x in values))


def prepare(m,layout,window,case):
    n=layout['reason_count'];dfn=layout['dfa_reasons']
    totals=[100+i for i in range(n)];current=[10+i for i in range(n)];dfa=[20+i for i in range(dfn)]
    totals[0]=case.get('old',totals[0]);current[0]=case.get('old',current[0])
    vector(m,layout['totals'],totals);vector(m,layout['current'],current);vector(m,layout['dfa'],dfa)
    oldsealed=[7,16,0x103,3,2,0,0,16,1]+[50+i for i in range(n)]+[30+i for i in range(n)]
    vector(m,layout['sealed'],oldsealed);m.map(layout['output'],b'\xa5'*layout['snapshot_bytes'])
    for name in ('active','have_room','draw','valid'):put(m,layout[name],case.get(name,1),1)
    put(m,layout['paused'],case.get('paused',0),1)
    for name,value in (('tick',17),('room',case.get('room',0x103)),('ticks',3),('draws',2),
        ('overflow',0),('outside_tick',0),('sequence',7),('dfa_overflow',0)):
        put(m,layout[name],value)
    if layout['window_overflow']:put(m,layout['window_overflow'],0)
    if window:
        w=window;N=w['N'];reasons=w['reasons'];full=case.get('full',False)
        m.map(w['window'],bytes(w['bytes']))
        for name,value in (('room',case.get('room',0x103)),('tick',17),('last_tick',16),('epoch',1)):
            put(m,w[name],value)
        for name,value in (('active',case.get('active',1)),('have_room',1),('paused',case.get('paused',0))):
            put(m,w[name],value,1)
        if full:
            values=[i+1 for i in range(reasons)]
            for row in range(N):
                at=w['rows']+row*w['row_bytes'];vector(m,at,values)
                put(m,at+w['row_ordinal'],row+1,8);put(m,at+w['row_tick'],row+1)
                put(m,at+w['row_flags'],int(case.get('expire',False) and row==N-1))
            vector(m,w['sums'],[N*x for x in values],8)
            put(m,w['logic'],N,8);put(m,w['draws'],N,8);put(m,w['used'],N);put(m,w['next'],N-1)
            put(m,w['overflow_rows'],int(case.get('expire',False)))
    return totals,current,dfa,oldsealed


def timed(m,entry,argument,model,name,window_ranges):
    m.minimum_sp=m.reg[15];m.irq_states={};initial_sr=m.sr
    m.observe_start();m.execute(entry,argument);m.observe_stop()
    assert m.sr&~1==initial_sr&~1,(name,'IRQ mask not restored')
    assert set(m.irq_states)==set(range(m.steps)),(name,'missing retired SR state')
    pcs=list(m.instruction_pcs)
    for i,pc in enumerate(pcs):
        if any(start<=pc<end for start,end in window_ranges):assert not m.irq_states[i],(name,'window ran with IRQs masked')
    trace=SimpleNamespace(instruction_pcs=pcs,steps=m.steps,read=m.read)
    protected=[i for i in range(m.steps) if m.irq_states[i]]
    row=dict(instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,
        traffic=kernel.traffic_details(m.memory_events,m.prefetch_events),
        **kernel.price_helpers.price(model,name,trace))
    row['irq_masked']=dict(instructions=len(protected),
        traffic=kernel.traffic_details([e for e in m.memory_events if e[0] in set(protected)],
                                      [e for e in m.prefetch_events if e[0] in set(protected)]))
    if protected:
        # All measured collector entries have one contiguous protected region.
        assert protected==list(range(protected[0],protected[-1]+1)),name
        sub=SimpleNamespace(instruction_pcs=[pcs[i] for i in protected],steps=len(protected),read=m.read)
        row['irq_masked'].update(kernel.price_helpers.price(model,name+'-masked',sub))
        row['irq_masked']['scope']='Isolated instruction segment after the mask is installed through its restore instruction; model scheduling starts at this segment. It is not hardware interrupt latency.'
    del m.irq_states
    return row


def collector_cases(window):
    rows=[dict(name='hit-active',entry='hit',arg=1),dict(name='hit-batched8192',entry='hit',arg=8192),
        dict(name='hit-outside',entry='hit',arg=1,active=0),dict(name='hit-paused',entry='hit',arg=1,paused=1),
        dict(name='hit-unarmed',entry='hit',arg=1,have_room=0),dict(name='hit-saturated',entry='hit',arg=9,old=0xfffffffd),
        dict(name='hit-zero',entry='hit',arg=0),dict(name='hit-invalid',entry='hit',arg=1,invalid=True),
        dict(name='begin-same-room',entry='begin',arg=18),dict(name='begin-new-room',entry='begin',arg=18,room=0x100),
        dict(name='begin-paused',entry='begin',arg=18,paused=1),dict(name='seal-drawn',entry='end'),
        dict(name='seal-skipped',entry='end',draw=0),dict(name='seal-inactive',entry='end',active=0),
        dict(name='snapshot',entry='snapshot'),dict(name='snapshot-invalid',entry='snapshot',valid=0),
        dict(name='reset',entry='reset',full=True)]
    if window:rows.append(dict(name='seal-full-drawn',entry='end',full=True,expire=True))
    return rows


def run_collector(m,l,w,case,model,arm,ranges):
    totals,current,dfa,oldsealed=prepare(m,l,w,case);kind=case['entry'];arg=case.get('arg',0)
    if kind=='hit':m.reg[5]=arg;arg=l['reason_count'] if case.get('invalid') else 0
    elif kind=='begin':m.reg[5]=0x103
    elif kind=='snapshot':arg=l['output']
    row=timed(m,l['fn_'+kind],arg,model,arm+'-'+case['name'],ranges)
    after=words(m,l['totals'],len(totals));cur=words(m,l['current'],len(current))
    if kind=='hit':
        expected=totals.copy();expected_cur=current.copy()
        armed=not case.get('paused',0) and case.get('have_room',1) and not case.get('invalid') and bool(case['arg'])
        if armed:expected[0]=min(0xffffffff,expected[0]+case['arg'])
        if armed and case.get('active',1):expected_cur[0]=min(0xffffffff,expected_cur[0]+case['arg'])
        assert after==expected and cur==expected_cur,case
        assert get(m,l['outside_tick'])==int(armed and not case.get('active',1)),case
        assert get(m,l['overflow'])==int(armed and totals[0]+case['arg']>0xffffffff),case
        if w:assert get(m,l['window_overflow'])==int(armed and case.get('active',1) and current[0]+case['arg']>0xffffffff)
    elif kind=='begin':
        if case.get('paused',0):assert cur==current and get(m,l['active'],1)==0,case
        else:
            assert cur==[0]*len(cur) and get(m,l['tick'])==18 and get(m,l['room'])==0x103 and get(m,l['active'],1)==1,case
            assert after==(totals if case.get('room',0x103)==0x103 else [0]*len(totals)),case
    elif kind=='end':
        sealed=words(m,l['sealed'],len(oldsealed))
        if case.get('active',1):
            expected=[8,17,case.get('room',0x103),4,2+case.get('draw',1),0,0,17 if case.get('draw',1) else 16,1]+totals+(current if case.get('draw',1) else oldsealed[9+len(totals):])
            assert sealed==expected and get(m,l['active'],1)==0,case
            if w:
                expected_sum=dfa+current if case.get('draw',1) else [0]*w['reasons']
                if case.get('full'):expected_sum=[value+(w['N']-1)*(i+1) for i,value in enumerate(expected_sum)]
                assert words(m,w['sums'],w['reasons'],8)==expected_sum,case
                assert get(m,w['overflow_rows'])==0,case
        else:assert sealed==oldsealed,case
    elif kind=='snapshot':
        expected=b''.join(x.to_bytes(4,'little') for x in oldsealed) if case.get('valid',1) else b'\xa5'*l['snapshot_bytes']
        assert m.bytes_at(l['output'],l['snapshot_bytes'])==expected,case
    elif kind=='reset':
        assert m.bytes_at(l['state'],l['state_bytes'])==bytes(l['state_bytes']),case
        if w:assert get(m,w['used'])==0 and words(m,w['sums'],w['reasons'],8)==[0]*w['reasons'],case
    return dict(arm=arm,case=case['name'],entry='fa29::'+kind,**row)


def run_window(m,l,w,case,model,arm,ranges):
    totals,current,dfa,_=prepare(m,l,w,case);kind=case['entry'];arg=case.get('arg',0)
    old_sums=words(m,w['sums'],w['reasons'],8);old_used=get(m,w['used']);old_incomplete=get(m,w['incomplete'],8)
    if kind=='end':
        arg=case.get('draw',1);m.reg[5]=l['dfa'];m.reg[6]=case.get('flags',0);m.reg[7]=l['current']
        put(m,m.reg[15],0);put(m,m.reg[15]+4,7)
    elif kind=='begin':arg=18;m.reg[5]=0x104 if case.get('new_room') else 0x103
    row=timed(m,w['fn_'+kind],arg,model,arm+'-window-'+case['name'],ranges)
    assert row['irq_masked']['instructions']==0,case
    if kind=='end':
        expected=old_sums.copy()
        if case.get('draw',1):
            for i,value in enumerate(dfa+current):expected[i]+=value-(i+1 if case.get('full') else 0)
        assert words(m,w['sums'],w['reasons'],8)==expected,case
        assert get(m,w['used'])==min(w['N'],old_used+case.get('draw',1)),case
        assert get(m,w['active'],1)==0 and get(m,w['outside_room'])==7,case
        assert get(m,w['overflow_rows'])==int(bool(case.get('flags'))),case
    elif kind in ('reset','resume') or kind=='begin' and case.get('new_room'):
        assert get(m,w['used'])==0 and words(m,w['sums'],w['reasons'],8)==[0]*w['reasons'],case
    elif kind=='pause':
        assert words(m,w['sums'],w['reasons'],8)==old_sums and get(m,w['paused'],1)==1,case
        assert get(m,w['incomplete'],8)==old_incomplete+1,case
    else:assert get(m,w['tick'])==18 and get(m,w['incomplete'],8)==old_incomplete+1,case
    return dict(arm=arm,case='window-'+case['name'],entry='fw35::'+kind,**row)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    names=['fallback_audit29.h','fallback_audit29.def','fallback_audit35.h','fallback_audit35.def',
           'fallback_window35.h','fallback_window35_core.hpp','draw_fallback_audit.h']
    files=[Path(__file__),HERE/'window_counter_cost_fixture.cpp.in',HERE/'window_core_cost_fixture.cpp.in',HERE/'build_controls.py',
        GAME/'fallback_audit29.cpp',GAME/'fallback_window35.cpp',GAME/'Makefile',GAME/'fallback_audit35.mk',GAME/'fallback_audit29.mk',
        *[GAME/'platform/include'/name for name in names],*sorted((GAME/'platform/include').glob('draw_fallback_*.def'))]
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in files};builder=profile.Build(out);rows=[];artifacts={}
    profile.UNITS.update({name:tuple(value) for name,value in controls.DEFAULT['units'].items()})
    for arm,gaps,N in (('old33',0,0),('gaps91',1,0),('window1',0,1),('combined32',1,32),('combined64',1,64)):
        directory=out/arm;directory.mkdir();options=controls.AUDIT+['QA_LINK=0','FALLBACK_AUDIT35='+str(gaps),'FALLBACK_WINDOW35='+str(N)]
        units=('fallback_audit29','fallback_window35') if N else ('fallback_audit29',)
        flags,receipt,sources=profile.derive(directory/'profile',cxx,kos,sdk,options,units=units)
        objects=[];identity={};production={}
        for unit,template in [('fallback_audit29','window_counter_cost_fixture.cpp.in')]+([('fallback_window35','window_core_cost_fixture.cpp.in')] if N else []):
            cpp=directory/(unit+'-fixture.cpp');cpp.write_text((HERE/template).read_text().replace('@DC@',str(DC)))
            obj=directory/(unit+'-fixture.o');prod=directory/(unit+'.o');objects.append(obj)
            builder.run([*flags[unit],'-fstack-usage','-c',cpp,'-o',obj],label=arm+'-'+unit+'-fixture')
            builder.run([*flags[unit],'-fstack-usage','-c',sources[unit],'-o',prod],label=arm+'-'+unit+'-production')
            identity[unit]=section_identity(prod,obj)
            production[unit]=dict(sha256=profile.sha(prod),sections=profile.sections(prod),local_frames=profile.stack_usage(prod.with_suffix('.su')))
        elf=directory/'fixture.elf';script=directory/'fixture.ld'
        script.write_text('SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) } '
            '. = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n')
        roots=['fixture_layout']+(['fixture_window_layout'] if N else [])
        builder.run([cxx,'-m4-single','-ml','-nostartfiles','-Wl,--gc-sections','-Wl,-T,'+str(script),'-Wl,-e,_fixture_layout',
            *['-Wl,-u,_'+name for name in roots],*objects,'-o',elf],label=arm+'-link')
        prefix=str(cxx).removesuffix('g++')
        (directory/'disassembly.txt').write_bytes(builder.run([prefix+'objdump','-d','-C',elf],label=arm+'-disassembly'))
        program,symbols=kernel.target_machine.scalar.load_elf(elf);model=kernel.pipeline_cost.Model(directory/'model',elf)
        def machine():
            m=Machine()
            for address,data,_ in program:m.map(address,data)
            return m
        seed=machine();layout=dict(zip(LAYOUT,words(seed,symbols['_fixture_layout'][0],len(LAYOUT))))
        window=dict(zip(WINDOW,words(seed,symbols['_fixture_window_layout'][0],len(WINDOW)))) if N else None
        assert layout['snapshot_bytes']==36+8*layout['reason_count']
        if window:assert window['N']==N and window['reasons']==layout['reason_count']+layout['dfa_reasons']
        ranges=[(at,at+size) for name,(at,size,info) in symbols.items() if '4fw35' in name and size and info&15==2]
        for case in collector_cases(window):
            rows.append(run_collector(machine(),layout,window,case,model,arm,ranges));print('PASS',arm,case['name'],flush=True)
        if window:
            cases=[dict(name='first-draw',entry='end'),dict(name='replace-draw',entry='end',full=True),
                dict(name='saturation-expiry',entry='end',full=True,expire=True),dict(name='saturated-input',entry='end',flags=1),
                dict(name='skip-full',entry='end',full=True,draw=0),dict(name='begin-same-room',entry='begin'),
                dict(name='begin-new-room',entry='begin',new_room=True,full=True),dict(name='pause-incomplete',entry='pause',full=True),
                dict(name='resume',entry='resume',full=True),dict(name='reset',entry='reset',full=True)]
            for case in cases:
                rows.append(run_window(machine(),layout,window,case,model,arm,ranges));print('PASS',arm,'window-'+case['name'],flush=True)
        artifacts[arm]=dict(gaps=gaps,N=N,options=options,profile_receipt=receipt,layout=layout,window_layout=window,
            fixture_sha256=profile.sha(elf),fixture_sections=profile.sections(elf),production_objects=production,
            production_fixture_text_identity=identity,model=model.metadata())
    assert frozen=={name:profile.sha(ROOT/name) for name in frozen},'Source changed during cost gate'
    lookup={(row['arm'],row['case']):row for row in rows};scenarios=[]
    for hits in (1000,10000):
        for arm in artifacts:
            calls={'hit-active':hits,'begin-same-room':1,'seal-full-drawn' if artifacts[arm]['N'] else 'seal-drawn':1}
            cycles=sum(lookup[(arm,case)]['model_cycles']*n for case,n in calls.items())
            old=sum(lookup[('old33','seal-drawn' if case=='seal-full-drawn' else case)]['model_cycles']*n for case,n in calls.items())
            scenarios.append(dict(label='MODELLED',arm=arm,assumed_calls=calls,cpu_mhz=200,assumed_other_work_ms=30,
                collector_and_window_ms=cycles/200000,whole_frame_ms=30+cycles/200000,delta_vs_old33_ms=(cycles-old)/200000))
    external={str(path):profile.sha(path) for path in (kos/'include/kos/irq.h',kos/'kernel/arch/dreamcast/include/arch/irq.h')}
    report=dict(status='PASS',scope=__doc__,source_sha256=frozen,external_irq_sha256=external,artifacts=artifacts,cases=rows,scenarios=scenarios,
        limits='Entry-to-return callee instructions, including actual KOS inline IRQ mask/restore and linked toolchain memcpy/memset. '
        'Caller argument setup/call instruction, optional weak actor-reset callback, formatting, QA transport, thread scheduling, interrupt delivery, D-cache misses and real gap event frequencies are excluded. '
        'All window instructions observed with IRQ mask clear. Protected-region timings start from an isolated model pipeline and are not measured interrupt latency. '
        'Local per-slot/probe counter accumulation at gap hooks is not in the common hit cost. Scenarios assume 1000 or10000 events and30ms other work; no frame-speedup prediction. '
        'Cold-I costs are isolated and cannot be summed into a frame. No private data, full image or console result.')
    path=out/'window-cost.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',cases=len(rows),arms=len(artifacts),receipt=str(path))))


if __name__=='__main__':main()
