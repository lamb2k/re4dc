#!/usr/bin/env python3
"""Price complete compiled MotionMoveCore dispatch and sampler traffic.

The real caller executes all frame/flag setup, joint and camera dispatch,
function-pointer selection, histories and samplers over mapped production
layouts. Resident-key acquire, model lookup, matrix helpers, VecRadLimit and
logging are typed fixture adapters; their fixed adapter instructions remain in
both totals, but original math/I/O/lookup implementation costs are not claimed.
Motion sequence advance, IK, hokan and world matrices outside this function are
not included. Matrix work inside this function is disabled by its existing flag.
The matrix/angle adapters therefore are not a general pose-arithmetic oracle.
The only additional opcode is FTRC for finite camera-frame values (-1,256);
other inputs are rejected rather than claiming general conversion behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(HERE))
import target_run as common

FIELDS='version model_bytes work_bytes camera_bytes model parts work motion camera table kinds numbers model_nparts model_motion model_pos model_ang model_scale work_pmot work_keys work_kinds work_numbers work_count work_attr work_flags work_seq_frame work_max work_frame work_old work_saved work_camera work_flip camera_type camera_parts camera_out camera_hist camera_frame part_hist part_flags'.split()


class PoseMachine(common.Machine):
    def attach(self,symbols):
        super().attach(symbols)
        self.calls=[]
        self.edges={v[0]:n for n,v in symbols.items() if any(x in n for x in ('getPartsPtr','re4dc_motion_acquire','re4dc_motion_release','VecRadLimit','RotMatrix','TransMatrix','ScaleMatrix'))}
    def step(self,pc,delay=False):
        if pc in self.edges:
            name=self.edges[pc]
            self.calls.append([name,self.reg[5] if 'getPartsPtr' in name else None])
        opcode=self.fetch(pc)
        if opcode&0xf0ff==0xf03d: # FTRC FRn,FPUL: bounded camera-frame conversion.
            value=self.fp_value((opcode>>8)&15)
            assert -1<value<256, ('unqualified FTRC input',value)
            self.fpul=int(value)
            self.instruction_pcs.append(pc);self.steps+=1
            return pc+2
        return super().step(pc,delay)


def conversion_controls():
    # These source inputs are exact binary32 values. FTRC truncates toward zero;
    # it neither reads/writes memory nor changes T/FPSCR or the source register.
    for value,expected in ((-.5,0),(0.,0),(.5,0),(9.5,9),(33.,33),(254.75,254),(255.,255)):
        m=PoseMachine();m.attach({});m.map(0x100000,struct.pack('<H',0xf13d))
        m.sf(1,struct.unpack('<I',struct.pack('<f',value))[0]);m.t=1
        before=m.f(1),m.fpscr,m.t
        m.observe_start();assert m.step(0x100000)==0x100002;m.observe_stop()
        assert m.fpul==expected and (m.f(1),m.fpscr,m.t)==before
        assert m.steps==1 and m.instruction_pcs==[0x100000] and not m.memory_events
    return 'FTRC camera-frame subset: seven exact finite inputs in (-1,256), no memory or state side effects'


def load(path):
    segments,symbols=common.target_machine.scalar.load_elf(path)
    m=PoseMachine()
    for address,data,_ in segments:m.map(address,data)
    m.attach(symbols)
    layout=[m.word(symbols['_fixture_pose_layout'][0]+4*i) for i in range(len(FIELDS))]
    d=dict(zip(FIELDS,layout));assert d['version']==1 and d['work_bytes']==220 and d['camera_bytes']==152,d
    sampler=[m.word(symbols['_fixture_layout'][0]+4*i) for i in range(13)]
    return m,symbols,d,sampler


def setword(m,at,value,size=4):m.map(at,int(value).to_bytes(size,'little'))
def setfloat(m,at,value):m.map(at,struct.pack('<f',value))


def configure(m,d,sampler,case):
    n=case['joints'];kind=case['kind'];mode=case['mode'];camera=mode=='camera'
    w=d['work'];root=d['model'];parts=d['parts'];maximum=32.;frame=33. if case['clamped'] else 9.5
    attr=0x8000 | (4 if mode=='loop' else 0)
    setword(m,root+d['model_nparts'],n,1)
    for field,value in [('work_pmot',d['motion']),('work_keys',d['table']),('work_kinds',d['kinds']),('work_numbers',d['numbers'])]:
        setword(m,w+d[field],value)
    setword(m,w+d['work_count'],n,1);setword(m,w+d['work_attr'],attr,2)
    setword(m,w+d['work_flags'],0x44000000)
    setfloat(m,w+d['work_seq_frame'],frame);setfloat(m,w+d['work_max'],maximum)
    setfloat(m,w+d['work_saved'],-7.25);setfloat(m,w+d['work_old'],-19.5)
    if camera:
        assert n>=9
        setword(m,w+d['work_camera'],d['camera'])
        setword(m,d['camera']+d['camera_type'],1,1)
        m.map(d['camera']+d['camera_parts'],bytes(range(5)))
    payload_offset=0
    for i in range(n):
        this_kind=(0,5,6)[i%3] if mode=='mixed' else kind
        keys=[0,4,8,12,16,20,24,28]
        payload=common.payload(this_kind,[keys]*3)
        key=sampler[4]+payload_offset
        assert payload_offset+len(payload)<=sampler[3]
        m.map(key,payload);payload_offset+=(len(payload)+3)&~3
        setword(m,d['table']+4*i,key)
        channel=(2,4,8,0x30)[i%4]
        ch=6 if camera and i<5 else 0
        setword(m,d['kinds']+2*i,(this_kind<<12)|(ch<<8)|channel,2)
        setword(m,d['numbers']+i,i,1)
        part=parts+i*d['model_bytes']
        flags=0x04000000 if mode=='ignore_history' or (mode=='mixed' and i%3==0) else 0
        if mode=='skip' and i%3==0:flags|=0x20000000
        setword(m,part+0x174+d['part_flags'],flags)
        for slot in range(6):
            m.map(part+0x174+d['part_hist']+slot*6,struct.pack('<3H',*([7 if case['clamped'] else 2]*3)))
    if camera:
        for i in range(5):m.map(d['camera']+d['camera_hist']+6*i,struct.pack('<3H',*([7 if case['clamped'] else 2]*3)))
    return payload_offset


def snapshot(m,d,case):
    parts=[]
    for i in range(case['joints']):
        p=d['parts']+i*d['model_bytes']
        parts.append(dict(pos=m.bytes_at(p+d['model_pos'],12).hex(),ang=m.bytes_at(p+d['model_ang'],12).hex(),
            scale=m.bytes_at(p+d['model_scale'],12).hex(),history=m.bytes_at(p+0x174+d['part_hist'],36).hex(),
            flags=m.word(p+0x174+d['part_flags'])))
    work={name:m.word(d['work']+d[name],2 if name=='work_attr' else 4) for name in ('work_attr','work_flags','work_frame','work_old','work_saved')}
    camera=dict(out=m.bytes_at(d['camera']+d['camera_out'],60).hex(),hist=m.bytes_at(d['camera']+d['camera_hist'],30).hex(),frame=m.word(d['camera']+d['camera_frame'],1))
    return dict(parts=parts,work=work,camera=camera,calls=m.calls,errors=m.errors)


def cases(quick):
    for kind in (5,) if quick else (0,5,6):
        for n in (1,4,16):
            for clamped in (False,True):
                yield dict(name=f't{kind}-n{n}-'+('clamped' if clamped else 'interior'),kind=kind,joints=n,clamped=clamped,mode='normal')
    for mode in ('camera','mixed','ignore_history','skip','loop'):
        for clamped in (False,True):
            yield dict(name=f't5-n12-{mode}-'+('endpoint' if clamped else 'interior'),kind=5,joints=12,clamped=clamped,mode=mode)


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    build=json.loads(args.build.read_text());models={} if args.no_model else {n:common.pipeline_cost.Model(output/('model-'+n),Path(v['elf']),args.host_cc) for n,v in build['arms'].items()}
    rows=[]
    for case in cases(args.quick):
        arms={};semantics=[]
        for name,arm in build['arms'].items():
            m,symbols,d,sampler=load(Path(arm['elf']));source_bytes=configure(m,d,sampler,case)
            m.minimum_sp=m.reg[15]
            m.observe_start();m.execute(symbols['_fixture_pose'][0]);m.observe_stop()
            observed=snapshot(m,d,case);semantics.append(observed)
            row=dict(instructions=m.steps,traffic=common.traffic(m.memory_events,m.prefetch_events),
                peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,source_key_bytes=source_bytes,
                pose_sha256=hashlib.sha256(json.dumps(observed,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                adapter_calls=m.calls,errors=m.errors)
            if name in models:
                trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
                row.update(common.price_helpers.price(models[name],case['name'],trace))
            arms[name]=row
        assert all(s==semantics[0] for s in semantics),(case,semantics)
        rows.append(dict(**case,arms=arms));print('PASS',case['name'],flush=True)
        (output/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
    report=dict(status='PASS',scope=__doc__,cases=rows,target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        models={n:m.metadata() for n,m in models.items()},conversion_controls=conversion_controls(),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),HERE/'target_run.py')})
    (output/'pose-controls.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--host-cc',default='gcc');parser.add_argument('--quick',action='store_true');parser.add_argument('--no-model',action='store_true')
    result=run(parser.parse_args());print(json.dumps(dict(status=result['status'],cases=len(result['cases']))))


if __name__=='__main__':main()
