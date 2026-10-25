#!/usr/bin/env python3
"""SH4 census error bookkeeping: actual opcodes and traffic, synthetic inputs.

Make-derived production flags compile the unchanged core. Deterministic HOST
clock/thread/log adapters replace hardware services. Warm/cold-I model cycles
assume a perfect D-cache, exclude IRQ/timer/bus waits, formatting/serial output,
renderer error-detail tag overhead and complete game frames. Not console timing.
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

build=module("wc24e_cost_build",HERE.parent/"build14/build_controls.py")
kernel=module("wc24e_cost_kernel",DC/"tools/d367/actor_bytes_lean/kernel_audit.py")
profile=build.profile
KEYS="arg_size frame_size snap_size current window sealed owner state paused have_sealed begin last tick errors active complete attempt finished phase_us counters snap_errors snap_sequence snap_identity snap_first_tick snap_last_tick errors_live errors_sealed errors_live_size errors_sealed_size live_bins sealed_bins typed_key untyped_key".split()
CASES=("phase-no-error","finish-no-error","fault-first","fault-repeat-first","fault-repeat-last",
       "fault-spill","fault-untyped","fault-inactive","clear-window","clear-snapshot","seal-empty","seal-full")

class Machine(kernel.Machine):
    forbidden=()
    def step(self,pc,delay=False):
        assert pc not in self.forbidden,"unpriced formatter was reached"
        opcode=self.fetch(pc)
        if opcode&0xff00==0xca00: # XOR #imm,R0: zero-extended byte; T unchanged.
            self.reg[0]^=opcode&255
            self.instruction_pcs.append(pc);self.steps+=1
            return pc+2
        return super().step(pc,delay)

def xor_controls():
    cases=0
    for initial in (0,0xffffffff,0x12345678):
        for immediate in (0,1,255):
            for t in (0,1):
                m=Machine();m.map(0x100000,struct.pack("<H",0xca00|immediate))
                m.reg[0]=initial;m.t=t;before=m.reg.copy()
                m.observe_start();next_pc=m.step(0x100000);m.observe_stop()
                assert m.reg[0]==initial^immediate and m.reg[1:]==before[1:] and m.t==t
                assert next_pc==0x100002 and m.steps==1 and m.instruction_pcs==[0x100000]
                assert not m.memory_events;cases+=1
    return dict(status="PASS",cases=cases,scope="XOR immediate preserves upper bits, other registers and T; fetch is not data traffic")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("output","sh4-cxx","kos-root","sdk-root"):p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    paths=[DC/"game/world_census24.cpp",DC/"game/platform/include/world_census24.h",
        DC/"game/platform/include/world_census24_errors.inc",DC/"game/world_census24_errors.mk",
        HERE/"census_errors_cost.cpp.in",Path(__file__),HERE.parent/"build14/build_controls.py",
        DC/"tools/d367/world_replay_lean/target_machine.py",DC/"tools/d367/world_replay_lean/sh4_machine.py",
        DC/"tools/d367/world_replay_lean/memory_trace.py",DC/"tools/d367/world_replay_lean/pipeline_cost.py",
        DC/"tools/d367/world_replay_lean/target_run.py",DC/"tools/d367/actor_bytes_lean/kernel_audit.py"]
    frozen={str(x.relative_to(ROOT)):profile.sha(x) for x in paths}
    rows=[];artifacts={};receipts={};prefix=str(cxx).removesuffix("g++")
    for arm,enabled in (("off",0),("on",1)):
        folder=out/arm;folder.mkdir()
        flags,receipt=build.derive(folder/"profile",cxx,kos,sdk,
            build.PROFILES["census"]+["PERF_PHASE_MISS=0",f"WORLD_CENSUS24_ERRORS={enabled}"],["census"])
        receipts[arm]=receipt
        builder=profile.Build(folder)
        fixture=folder/"fixture.cpp";fixture.write_text((HERE/"census_errors_cost.cpp.in").read_text().replace("@DC@",str(DC)))
        obj,elf=folder/"fixture.o",folder/"fixture.elf"
        builder.run([*flags["census"],"-c","-fstack-usage",fixture,"-o",obj],label="fixture")
        script=folder/"fixture.ld"
        script.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
            ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
        entries=("phase","fault","untyped","finish","clear","seal","layout")
        builder.run([cxx,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections","-Wl,-T,"+str(script),
            "-Wl,-e,_fixture_phase","-Wl,--wrap=snprintf",*["-Wl,-u,_fixture_"+s for s in entries],obj,"-o",elf],label="link")
        (folder/"disassembly.txt").write_bytes(builder.run([prefix+"objdump","-d","-C",elf],label="disassembly"))
        program,symbols=kernel.target_machine.scalar.load_elf(elf)
        model=kernel.pipeline_cost.Model(folder/"model",elf)
        for case in CASES:
            m=Machine();m.forbidden=(symbols["___wrap_snprintf"][0],)
            for at,data,_ in program:m.map(at,data)
            layout=dict(zip(KEYS,struct.unpack("<"+"I"*len(KEYS),m.bytes_at(symbols["_fixture_layout"][0],4*len(KEYS)))))
            def put(address,value,size=4):m.map(address,int(value).to_bytes(size,"little"))
            def get(address,size=4):return int.from_bytes(m.bytes_at(address,size),"little")
            frame=layout["current"]
            m.map(frame,bytes(layout["frame_size"]));m.map(layout["window"],bytes(layout["snap_size"]))
            m.map(layout["sealed"],bytes(layout["snap_size"]))
            put(layout["owner"],1);put(layout["state"],0);put(layout["paused"],0,1)
            put(frame+layout["begin"],900,8);put(frame+layout["last"],1000,8);put(frame+layout["tick"],42)
            for flag in ("active","complete","attempt","finished"):put(frame+layout[flag],1,1)
            m.map(0x9000,struct.pack("<QIII",1100,0x12345678,0xabcdef01,int(case=="clear-snapshot"))+bytes(layout["arg_size"]-20))
            entry="phase" if case.startswith("phase") else "finish" if case.startswith("finish") else "clear" if case.startswith("clear") else "seal" if case.startswith("seal") else "untyped" if case=="fault-untyped" else "fault"
            if case=="fault-inactive":put(frame+layout["active"],0,1)
            if enabled:
                live=layout["errors_live"]
                m.map(live,bytes(layout["errors_live_size"]))
                m.map(layout["errors_sealed"],bytes(layout["errors_sealed_size"]))
                used=1 if case=="fault-repeat-first" else 32 if case in ("fault-repeat-last","fault-spill","seal-full","clear-window","clear-snapshot") else 0
                put(live,used)
                for i in range(used):
                    # 32 legal, distinct path/phase contexts; context zero is
                    # reserved for the wanted OUT key so all other bins miss.
                    context=(i%6+1)|((i//6)<<3)
                    key=layout["typed_key"] if case=="fault-repeat-first" or (case=="fault-repeat-last" and i==31) else layout["typed_key"]|(context<<16)
                    m.map(live+layout["live_bins"]+20*i,struct.pack("<5I",key,10,7,8,9))
                if case.startswith("clear"):
                    put(live+4,17);put(live+8,1)
                    m.map(layout["errors_sealed"],bytes([0xa5])*layout["errors_sealed_size"])
                live_before=m.bytes_at(live,layout["errors_live_size"])
                snapshot_before=m.bytes_at(layout["errors_sealed"],layout["errors_sealed_size"])
                put(layout["sealed"]+layout["snap_errors"],used*10)
                put(layout["sealed"]+layout["snap_sequence"],3)
                put(layout["sealed"]+layout["snap_identity"],0x101)
                put(layout["sealed"]+layout["snap_first_tick"],1)
                put(layout["sealed"]+layout["snap_last_tick"],300)
            m.minimum_sp=m.reg[15];m.observe_start();m.execute_kernel(symbols["_fixture_"+entry][0],0x9000);m.observe_stop()
            if case.startswith("fault"):
                expected=int(case!="fault-inactive")
                assert get(frame+layout["errors"])==expected,(arm,case,"aggregate")
                if enabled:
                    used=get(live);spill=get(live+4)
                    total=spill+sum(get(live+layout["live_bins"]+20*i+4) for i in range(used))
                    before=10 if case=="fault-repeat-first" else 320 if case in ("fault-repeat-last","fault-spill") else 0
                    assert total==before+expected,(case,total)
                    bins_offset=layout["live_bins"]
                    if case in ("fault-first","fault-untyped"):
                        key=layout["untyped_key"] if case=="fault-untyped" else layout["typed_key"]
                        a,b=(0,0) if case=="fault-untyped" else (0x12345678,0xabcdef01)
                        assert used==1 and spill==0 and m.bytes_at(live+bins_offset,20)==struct.pack("<5I",key,1,42,a,b)
                    elif case in ("fault-repeat-first","fault-repeat-last"):
                        changed=bytearray(live_before);index=0 if case=="fault-repeat-first" else 31
                        struct.pack_into("<I",changed,bins_offset+20*index+4,11)
                        assert m.bytes_at(live,len(changed))==changed,"repeat changed wrong bin or first evidence"
                    elif case=="fault-spill":
                        changed=bytearray(live_before);struct.pack_into("<I",changed,4,1)
                        assert used==32 and spill==1 and m.bytes_at(live,len(changed))==changed
                    else:assert m.bytes_at(live,len(live_before))==live_before
            elif case=="phase-no-error":
                assert get(frame+layout["errors"])==0 and get(frame+layout["counters"])==6
            elif case=="finish-no-error":assert get(layout["window"]+layout["snap_errors"])==0
            elif case.startswith("clear") and enabled:
                assert get(live)==get(live+4)==get(live+8)==0
                expected=bytes(layout["errors_sealed_size"]) if case=="clear-snapshot" else snapshot_before
                assert m.bytes_at(layout["errors_sealed"],len(expected))==expected,"clear snapshot contract"
            elif case.startswith("seal") and enabled:
                sealed=layout["errors_sealed"]
                used=32 if case=="seal-full" else 0
                expected=bytearray(layout["errors_sealed_size"])
                struct.pack_into("<8I",expected,0,3,0x101,1,300,used*10,used,0,0)
                expected[layout["sealed_bins"]:layout["sealed_bins"]+used*20]=live_before[layout["live_bins"]:layout["live_bins"]+used*20]
                assert m.bytes_at(sealed,len(expected))==expected,"seal metadata or bin copy"
                assert get(live)==get(live+4)==get(live+8)==0
            traffic=kernel.traffic_details(m.memory_events,m.prefetch_events)
            grouped={}
            for event in m.memory_events:
                a=event[3]
                region="stack" if a>=0x4f0000 else "arguments" if 0x9000<=a<0x9100 else "census-and-literals"
                if enabled and (layout["errors_live"]<=a<layout["errors_live"]+layout["errors_live_size"] or layout["errors_sealed"]<=a<layout["errors_sealed"]+layout["errors_sealed_size"]):region="error-bookkeeping"
                grouped.setdefault(region,[]).append(event)
            traffic["regions"]={name:kernel.summarize(events) for name,events in grouped.items()}
            if enabled and case in ("phase-no-error","finish-no-error"):
                assert "error-bookkeeping" not in grouped,"fault-free core touched diagnostic bins"
            trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
            priced=kernel.price_helpers.price(model,case,trace)
            rows.append(dict(arm=arm,case=case,instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,traffic=traffic,**priced))
            print("PASS",arm,case,flush=True)
        artifacts[arm]=dict(flags=flags["census"],object_sha256=profile.sha(obj),elf_sha256=profile.sha(elf),
            sections=profile.sections(elf),stack_usage=profile.stack_usage(obj.with_suffix(".su")),model=model.metadata(),layout=layout)
    by={(r["arm"],r["case"]):r for r in rows}
    delta={case:by["on",case]["model_cycles"]-by["off",case]["model_cycles"] for case in CASES}
    scenarios=[]
    for fault_calls in (0,4):
        cycles=1000*delta["phase-no-error"]+delta["finish-no-error"]+fault_calls*delta["fault-repeat-last"]+delta["seal-full" if fault_calls else "seal-empty"]/300
        scenarios.append(dict(assumed_phase_count_leave_sequences=1000,assumed_completed_drawn_ticks=1,assumed_skipped_ticks=0,
            assumed_repeated_faults=fault_calls,assumed_draws_per_seal=300,assumed_cpu_mhz=200,
            MODELLED_incremental_core_ms=cycles/200000.0,
            scope="Weighted isolated probe deltas at synthetic frequencies, warm-I perfect-D; one drawn tick and no skips. Fault arm assumes matching bin is last of 32. Add unpriced renderer tags, formatting/serial, hardware timer/IRQ and memory wait states."))
    assert frozen=={str(x.relative_to(ROOT)):profile.sha(x) for x in paths},"source changed"
    report=dict(status="PASS",scope=__doc__,source_sha256=frozen,compiler_sha256=profile.sha(cxx),
        profile_receipts=receipts,artifacts=artifacts,cases=rows,warm_cycle_delta=delta,
        memory_controls=kernel.target_machine.memory_controls(),xor_immediate_controls=xor_controls(),MODELLED_frame_overhead=scenarios,
        limitations="No console result, D-cache miss rate, full-frame estimate or render speedup is claimed. Cold-I results are isolated ELF layouts, not additive per-hook frame costs. PM14 composition is checked by the separate target controls.")
    (out/"target-costs.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",cases=len(rows),receipt=str(out/"target-costs.json"),warm_cycle_delta=delta)))

if __name__=="__main__":main()
