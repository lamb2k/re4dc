#!/usr/bin/env python3
"""Execute real compiled world direct boundaries and uncontended KOS locks.

These are synthetic instruction traces, not a game frame or console result.
The modeled CPU cost includes actual SQ/mutex/empty-wait-queue/MMU code, with
perfect data cache and no bus, DMA, SQ backpressure, IRQ or scheduling events.
Only the direct boundary is measured: static-world replay/emission is excluded.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"world_setup_spike"))
import run_target as setup
target=setup.target
pipeline_cost=setup.pipeline_cost


class Machine(setup.Machine):
    def __init__(self):
        super().__init__()
        self.sr=0x40000000
        # Privileged register state for non-MMU KOS; these are state reads and
        # writes, not claims to simulate the external bus or interrupt system.
        self.map(0xff000010,bytes(4))
        self.map(0xff000038,bytes(8))

    def step(self,pc,delay=False):
        opcode=self.read(pc,2)
        register=(opcode>>8)&15
        if opcode&0xf0ff==0x0002:  # STC SR,Rn
            self.instruction_pcs.append(pc)
            self.reg[register]=(self.sr&~1)|self.t
            self.steps+=1
            return pc+2
        if opcode&0xf0ff==0x400e:  # LDC Rm,SR (privileged; no bank switch)
            value=self.reg[register]&0x700083f3
            assert (value^self.sr)&(1<<29)==0,"SR register bank switches unsupported"
            self.instruction_pcs.append(pc)
            self.sr=value;self.t=value&1
            self.steps+=1
            return pc+2
        if opcode&0xff00==0xcb00:  # OR #imm,R0; zero-extended immediate, T unchanged
            self.instruction_pcs.append(pc)
            self.reg[0]|=opcode&255
            self.steps+=1
            return pc+2
        return super().step(pc,delay)


def sr_controls():
    checked=0
    for register in range(15):
        for initial in (0x40000000,0x400000f0,0x500083f3):
            machine=Machine();machine.sr=initial;machine.t=initial&1
            machine.map(0x100000,struct.pack("<2H",0x0002|(register<<8),0x400e|(register<<8)))
            assert machine.step(0x100000)==0x100002
            assert machine.reg[register]==initial
            value=(initial&0xefffff0f)|0xf0
            machine.reg[register]=value
            assert machine.step(0x100002)==0x100004
            assert machine.sr==value&0x700083f3 and machine.t==value&1
            assert machine.steps==len(machine.instruction_pcs)==2
            checked+=1
    for a in (0,1,0x40000000,0xffffffff):
        for immediate in (0,1,0x7f,0x80,0xf0,0xff):
            machine=Machine();machine.reg[0]=a;machine.t=1
            machine.map(0x100000,struct.pack("<H",0xcb00|immediate))
            assert machine.step(0x100000)==0x100002
            assert machine.reg[0]==a|immediate and machine.t==1
    return dict(status="PASS",controls=checked,immediate_or_controls=24,
                scope="STC SR/Rn and LDC Rm/SR state/mask only, no interrupts or bank switch",
                manual="https://www.renesas.com/en/document/mas/sh-4-software-manual")


def load(path):
    program,symbols=target.load_elf(path)
    machine=Machine()
    for address,data,_ in program:machine.map(address,data)
    at=symbols["_fixture_layout"][0]
    layout=[machine.read(at+i*4,4) for i in range(8)]
    assert layout[0]==1 and layout[1]==80,layout
    return machine,symbols,layout


def execute(path,kind,parts,vertices=25,normal_end=False,repeats=1):
    machine,symbols,layout=load(path)
    pcs=[];results=[];headers=[];counts=[]
    for _ in range(repeats):
        machine.execute(symbols["_fixture_kos_reset"][0])
        machine.reg[5]=parts;machine.reg[6]=vertices
        machine.execute(symbols["_fixture_configure"][0],kind)
        if normal_end:machine.execute(symbols["_fixture_prepare_normal_end"][0])
        machine.output.clear()
        machine.write_bytes=0;machine.tracking=True;machine.minimum_sp=machine.reg[15]
        machine.execute(symbols["_fixture_normal_end" if normal_end else "_fixture_submit"][0])
        machine.tracking=False
        pcs+=machine.instruction_pcs
        counts.append(machine.steps)
        headers.append(bytes(machine.output))
        assert machine.sr&0xfffffffe==0x40000000,"IRQ mask was not restored"
        machine.execute(symbols["_fixture_snapshot"][0])
        results.append(machine.bytes_at(layout[2],layout[1]))
    assert all(value==results[0] for value in results)
    assert all(value==headers[0] for value in headers)
    report=dict(instructions=len(pcs),per_call_instructions=counts,
                final_observed_store_bytes=machine.write_bytes,
                peak_stack_bytes=machine.initial_regs[15]-machine.minimum_sp,
                output_sha256=hashlib.sha256(headers[0]).hexdigest(),output_bytes=len(headers[0]),
                result_sha256=hashlib.sha256(results[0]).hexdigest(),
                counters=list(struct.unpack("<18I",results[0][:72])),
                scales=list(struct.unpack("<2f",results[0][72:])))
    report["lock_calls"]=pcs.count(symbols["_sq_lock"][0])
    report["unlock_calls"]=pcs.count(symbols["_sq_unlock"][0])
    counters=report["counters"]
    expected=parts if kind in (0,3) else (parts+1)//2 if kind==2 else 0
    if normal_end:
        assert counters[2:5]==[1,1,vertices]
        assert not headers[0] and report["lock_calls"]==0 and report["unlock_calls"]==repeats
    else:
        assert counters[:5]==[expected,parts-expected,expected,expected,expected*vertices]
        assert counters[5:8]==[expected*(vertices+1)*32]*3
        assert len(headers[0])==expected*32
        assert counters[12]==(parts-expected if kind in (1,2) else 0)
        assert report["lock_calls"]==report["unlock_calls"]
    assert counters[13]==0 and counters[16]==0,"scene opened or direct ownership leaked"
    trace=SimpleNamespace(instruction_pcs=pcs,steps=len(pcs),read=machine.read)
    report["symbol_instructions"]=pipeline_cost.symbol_costs(trace,symbols)
    return report,results[0],headers[0],trace


def run(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    builds=json.loads(args.build.read_text())
    paths={name:Path(row["elf"]) for name,row in builds["arms"].items()}
    models={}
    for name,path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==builds["arms"][name]["sha256"]
        if not args.no_model:models[name]=pipeline_cost.Model(output/("model-"+name),path,args.host_cc)
    cases=[]
    for kind,label in ((0,"same-material"),(3,"changing-material"),(1,"all-miss-refusal"),
                       (2,"alternating-hit-refusal"),(4,"frame-not-ready")):
        for parts in (1,2,8,48):cases.append((label+"-"+str(parts),kind,parts,False))
    cases.append(("ordinary-direct-end",0,1,True))
    rows=[]
    for label,kind,parts,normal_end in cases:
        pair={};raw={}
        for name,path in paths.items():
            row,result,headers,trace=execute(path,kind,parts,normal_end=normal_end,repeats=args.repeats)
            if name in models:row.update(setup.cached_price(models[name],label,trace,not args.icache))
            pair[name]=row;raw[name]=(result,headers)
        assert raw["baseline"]==raw["batch"],(label,"state/header difference")
        rows.append(dict(name=label,parts=parts,kind=kind,calls=args.repeats,**pair))
        (output/"progress.json").write_text(json.dumps(rows,indent=2)+"\n")
        print("PASS",label,pair["baseline"]["instructions"],pair["batch"]["instructions"],flush=True)
    report=dict(status="PASS",scope=__doc__,checks=len(rows),cases=rows,
                source_sha256={str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                               str(Path(setup.__file__)):hashlib.sha256(Path(setup.__file__).read_bytes()).hexdigest()},
                target_build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),
                sr_controls=sr_controls(),address_controls=setup.address_controls(),
                model={name:model.metadata() for name,model in models.items()},
                no_real_scene_or_frame_time_claim=True)
    (output/"target-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--no-model",action="store_true")
    parser.add_argument("--icache",action="store_true")
    parser.add_argument("--repeats",type=int,default=1)
    parser.add_argument("--host-cc",default="gcc")
    args=parser.parse_args();assert 1<=args.repeats<=64
    result=run(args);print(json.dumps({"status":result["status"],"checks":result["checks"]}))


if __name__=="__main__":main()
