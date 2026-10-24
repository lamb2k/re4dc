#!/usr/bin/env python3
"""Execute complete compiled SH4 Hermite calls and observe demand traffic.

The linked production sampler, layout readers, search, history, interpolation
and cold fallback execute unchanged. Only logging is an observed empty edge.
Scalar binary32 operations use the established opcode interpreter, RN with
DN=1; synthetic values avoid exceptional/denormal boundaries. This is stronger
than source phase extraction but still not general hardware FP conformance.
Qualified clamp cases enter the private clamped entry only in the ON arm; all
other cases enter the public entry. Per-pose admission is priced separately by
pose_run.py. Cycle prices use perfect D-cache/no DMA/zero SQ cost. Demand lines are addresses
touched, not inferred misses or a captured game-frame population.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
REPLAY = HERE.parent / "world_replay_lean"
sys.path.insert(0, str(REPLAY))
import target_machine
import pipeline_cost
from memory_trace import summarize
_spec = importlib.util.spec_from_file_location("anim_target_price", REPLAY / "target_run.py")
price_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(price_helpers)


class Machine(target_machine.Machine):
    def attach(self, symbols):
        self.symbols = symbols
        self.errors = []
        self.log_addresses = {v[0] for n,v in symbols.items() if 'cLog3err' in n}
    def word(self,address,size=4):
        return int.from_bytes(self.bytes_at(address,size),'little')
    def step(self,pc,delay=False):
        if pc in self.log_addresses:
            # this,a,b,fmt occupy r4..r7; the three integer varargs are on stack.
            text=bytearray(); at=self.reg[7]
            while self.word(at,1):
                text.append(self.word(at,1));at+=1
                assert len(text)<512
            self.errors.append([text.decode(),*[self.word(self.reg[15]+4*i) for i in range(3)]])
        return super().step(pc,delay)


def load(path):
    segments,symbols=target_machine.scalar.load_elf(path)
    machine=Machine()
    for address,data,_ in segments: machine.map(address,data)
    machine.attach(symbols)
    layout=[machine.word(symbols['_fixture_layout'][0]+4*i) for i in range(13)]
    assert layout[:4]==[1,20,12,8192] and layout[8:]==[0,4,8,12,16],layout
    return machine,symbols,layout


def payload(kind,frames):
    result=bytearray()
    for axis,keys in enumerate(frames):
        result.extend(struct.pack('<H',len(keys)))
        result.extend(struct.pack('<'+'H'*len(keys),*keys))
        for i in range(len(keys)):
            if kind==0: result.extend(struct.pack('<3f',(i*3-axis*7-11)/8,(i-axis+2)/16,(axis-i-3)/32))
            elif kind==5: result.extend(struct.pack('<3h',i*113-axis*19-2001,i*7-axis*3+1,axis*11-i*5-2))
            elif kind==6: result.extend(struct.pack('<h2b',i*113-axis*19-2001,(i-axis+2)%63-31,(axis-i-3)%63-31))
            else: raise AssertionError(kind)
    return bytes(result)


def cases(quick):
    for kind in (0,5,6):
        for n in ((8,) if quick else (2,8,32,128)):
            keys=[i*4 for i in range(n)]; mid=n//2; maximum=float(n*4)
            defs=[('exact_zero',0.,[0]*3,0),('exact_middle',float(keys[mid]),[mid]*3,0),
                ('exact_last',float(keys[-1]),[n-1]*3,0),('clamp',maximum+1,[n-1]*3,0),
                ('clamp_ignore_history',maximum+1,[n+1]*3,8),
                ('clamp_invalid_history',maximum+1,[n-1,n+1,n-1],0),
                ('interior',float(keys[mid-1])+1.5,[mid-1]*3,0),
                ('rewind',1.5,[n-1]*3,1),('ignore_history',float(keys[mid])+1.5,[n-1]*3,8),
                ('loop',maximum+1.5,[n-1]*3,4),('invalid_history',1.5,[0,n+1,0],0)]
            for label,frame,hist,flags in defs:
                yield dict(name=f't{kind}-n{n}-{label}',kind=kind,frames=[keys]*3,frame=frame,
                    max_frame=maximum,history=hist,flags=flags,alignment=0)
        yield dict(name=f't{kind}-mixed',kind=kind,frames=[[0,4,8],[0,8,16],[0,4,16]],
            frame=4.,max_frame=20.,history=[0,0,0],flags=0,alignment=2)
        yield dict(name=f't{kind}-late_runout',kind=kind,frames=[[0,8,16],[0,4,8],[0,8,16]],
            frame=9.,max_frame=100.,history=[0,0,0],flags=0,alignment=0)


def traffic(events,prefetch):
    result=summarize(events,prefetch)
    visits=sum(len({a>>5 for a in range(e[3],e[3]+e[4])}) for e in events)
    result['demand_line_visits']=visits
    result['repeated_demand_line_visits']=visits-result['cached']['unique_data_lines']
    return result


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    build=json.loads(args.build.read_text())
    models={} if args.no_model else {n:pipeline_cost.Model(output/('model-'+n),Path(v['elf']),args.host_cc) for n,v in build['arms'].items()}
    rows=[]
    for case in cases(args.quick):
        arms={};semantic=[]
        for name,arm in build['arms'].items():
            machine,symbols,layout=load(Path(arm['elf']))
            raw=payload(case['kind'],case['frames'])
            key=layout[4]+case['alignment'];assert len(raw)+case['alignment']<=layout[3]
            machine.map(key,raw)
            machine.map(layout[5],struct.pack('<ffIB3xI',case['frame'],case['max_frame'],case['flags'],case['kind'],key))
            machine.map(layout[6],struct.pack('<3f',17.25,-33.5,49.75))
            machine.map(layout[7],struct.pack('<3H',*case['history']))
            machine.minimum_sp=machine.reg[15]
            entry=symbols['_HermiteInterpolation'][0]
            clamped=case['frame']>=case['max_frame'] and case['flags']&6!=4
            if name=='l1' and clamped:
                entries=[v[0] for n,v in symbols.items() if 'HermiteInterpolationClamped' in n]
                assert len(entries)==1, entries
                entry=entries[0]
            machine.reg[5],machine.reg[6]=layout[6],layout[7]
            machine.observe_start();machine.execute(entry,layout[5]);machine.observe_stop()
            out=list(struct.unpack('<3I',machine.bytes_at(layout[6],12)))
            hist=list(struct.unpack('<3H',machine.bytes_at(layout[7],6)))
            observed=[machine.reg[0],out,hist,machine.errors];semantic.append(observed)
            row=dict(entry_kind='qualified_clamped' if name=='l1' and clamped else 'public',instructions=machine.steps,traffic=traffic(machine.memory_events,machine.prefetch_events),
                peak_stack_bytes=machine.initial_regs[15]-machine.minimum_sp,result=observed,
                output_sha256=hashlib.sha256(json.dumps(observed,separators=(',',':')).encode()).hexdigest())
            if name in models:
                trace=SimpleNamespace(instruction_pcs=list(machine.instruction_pcs),steps=machine.steps,read=machine.read)
                row.update(price_helpers.price(models[name],case['name'],trace))
            arms[name]=row
        assert all(x==semantic[0] for x in semantic),(case,semantic)
        rows.append(dict(**case,arms=arms))
        print('PASS',case['name'],flush=True)
    report=dict(status='PASS',scope=__doc__,cases=rows,
        target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
        memory_controls=target_machine.memory_controls(),models={n:m.metadata() for n,m in models.items()},
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),REPLAY/'target_machine.py',REPLAY/'sh4_machine.py',REPLAY/'memory_trace.py',REPLAY/'pipeline_cost.py')})
    (output/'target-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--host-cc',default='gcc');parser.add_argument('--quick',action='store_true');parser.add_argument('--no-model',action='store_true')
    result=run(parser.parse_args());print(json.dumps(dict(status=result['status'],cases=len(result['cases']))))


if __name__=='__main__':main()
