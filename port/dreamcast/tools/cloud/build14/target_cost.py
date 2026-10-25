#!/usr/bin/env python3
"""Actual SH4 observer/control opcodes and access traces, with synthetic PRFC1 inputs.

The production core, inline KOS IRQ helpers and pinned perfctr.c are compiled
unchanged. Synthetic register memory is not a model of event generation. Cache
misses, PMU/MMIO wait states, interrupts and full game timing remain unpriced.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
build=module("pm14_build",HERE/"build_controls.py")
kernel=module("pm14_target",DC/"tools/d367/actor_bytes_lean/kernel_audit.py")
profile=build.profile

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("output","sh4-cxx","kos-root","sdk-root"):p.add_argument("--"+n,type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    paths=[DC/"game/perf_phase_miss.cpp",DC/"game/platform/include/perf_phase_miss.h",DC/"game/platform/include/perf_phase_accounting.hpp",
        HERE/"cost_fixture.cpp.in",Path(__file__),HERE/"build_controls.py",DC/"tools/d367/world_replay_lean/target_machine.py",
        DC/"tools/d367/world_replay_lean/sh4_machine.py",DC/"tools/d367/world_replay_lean/memory_trace.py",
        DC/"tools/d367/world_replay_lean/pipeline_cost.py",DC/"tools/d367/actor_bytes_lean/kernel_audit.py"]
    frozen={str(x.relative_to(ROOT)):profile.sha(x) for x in paths}
    flags,receipt=build.derive(out/"profile",cxx,kos,sdk,build.PROFILES["census"]+["PERF_PHASE_MISS=1","PERF_PHASE_MISS_EVENT=15"],["pmu"])
    builder=profile.Build(out);prefix=str(cxx).removesuffix("g++")
    fixture=out/"fixture.cpp";fixture.write_text((HERE/"cost_fixture.cpp.in").read_text().replace("@DC@",str(DC)))
    obj,elf=out/"fixture.o",out/"fixture.elf"
    builder.run([*flags["pmu"],"-c","-fstack-usage",fixture,"-o",obj],label="fixture")
    kos_source=kos/"kernel/arch/dreamcast/kernel/perfctr.c";kos_obj=out/"perfctr.o"
    kos_flags=[*profile.target_flags(kos),"-std=gnu11","-fstack-usage"]
    builder.run([prefix+"gcc",*kos_flags,"-c",kos_source,"-o",kos_obj],label="kos-perfctr")
    linker=out/"fixture.ld";linker.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
        ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    builder.run([cxx,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections","-Wl,-T,"+str(linker),
        "-Wl,-e,_fixture_transition","-Wl,-u,_fixture_finish","-Wl,-u,_fixture_chase","-Wl,-u,_fixture_layout",obj,kos_obj,"-o",elf],label="link")
    (out/"disassembly.txt").write_bytes(builder.run([prefix+"objdump","-d","-C",elf],label="disassembly"))
    program,symbols=kernel.target_machine.scalar.load_elf(elf)
    model=kernel.pipeline_cost.Model(out/"model",elf)
    rows=[]
    for case in ("sampled-edge","same-bin","unrun","finish-tick","wrap48","resident-control","heavy-control"):
        m=kernel.Machine()
        for at,data,_ in program:m.map(at,data)
        layout=struct.unpack("<18I",m.bytes_at(symbols["_fixture_layout"][0],72))
        arg_size,now_off,nodes_off,snap_size=layout[:4]
        addresses=dict(zip(("window","control","owner","previous_count","previous_us","bin","owned","running","active","paused","lost"),layout[4:15]))
        for name in ("owned","running","active"):m.map(addresses[name],b"\1")
        for name in ("paused","lost"):m.map(addresses[name],b"\0")
        m.map(addresses["owner"],struct.pack("<I",1))
        m.map(addresses["previous_count"],struct.pack("<Q",0))
        m.map(addresses["previous_us"],struct.pack("<Q",0))
        m.map(addresses["bin"],struct.pack("<I",39))
        m.map(addresses["window"],bytes(snap_size))
        # Pinned KOS counter1 addresses only. Nothing maps/uses counter0.
        m.map(0xff000088,struct.pack("<H",0xc00f))
        m.map(0xff10000c,struct.pack("<II",0,100))
        args_blob=bytearray(arg_size)
        struct.pack_into("<I",args_blob,0,1|(1<<3)) # NearOP / Transform
        struct.pack_into("<Q",args_blob,now_off,1000)
        struct.pack_into("<I",args_blob,nodes_off,0x20000)
        m.map(0x9000,args_blob)
        entry="_fixture_transition"
        if case=="same-bin":m.map(addresses["bin"],struct.pack("<I",1))
        if case=="unrun":m.map(addresses["active"],b"\0")
        if case=="finish-tick":entry="_fixture_finish"
        if case=="wrap48":m.map(addresses["previous_count"],struct.pack("<Q",(1<<48)-5))
        if case.endswith("control"):
            lines=64 if case=="resident-control" else 1024
            data=bytearray(lines*32)
            for i in range(lines):struct.pack_into("<I",data,i*32,((i+17)&(lines-1))*8)
            m.map(0x20000,data);entry="_fixture_chase"
        m.minimum_sp=m.reg[15];m.observe_start();m.execute_kernel(symbols[entry][0],0x9000);m.observe_stop()
        mmio=[e for e in m.memory_events if e[3]>=0xe0000000]
        assert all(e[2]=="read" and e[3] in (0xff000088,0xff10000c,0xff100010) for e in mmio),(case,mmio)
        expected_sample=case in ("sampled-edge","finish-tick","wrap48")
        assert len(mmio)==(4 if expected_sample else 0),(case,"MMIO access count",mmio)
        total=struct.unpack("<Q",m.bytes_at(addresses["window"]+layout[15],8))[0]
        samples=struct.unpack("<I",m.bytes_at(addresses["window"]+layout[16],4))[0]
        assert total==(105 if case=="wrap48" else 100 if expected_sample else 0),(case,total)
        assert samples==int(expected_sample)
        if case.endswith("control"):
            reads=[e for e in m.memory_events if 0x20000<=e[3]<0x30000]
            assert len(reads)==8192 and all(e[2]=="read" and e[4]==4 for e in reads)
            assert len({e[3]>>5 for e in reads})==lines and m.reg[0]==0
        traffic=kernel.traffic_details(m.memory_events,m.prefetch_events)
        regions={}
        for event in m.memory_events:
            a=event[3]
            region="PMU-registers" if a>=0xe0000000 else "control-nodes" if 0x20000<=a<0x30000 else "stack" if a>=0x4f0000 else "arguments" if 0x9000<=a<0x9100 else "observer-and-literals"
            regions.setdefault(region,[]).append(event)
        traffic["regions"]={name:kernel.summarize(events) for name,events in regions.items()}
        trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
        priced=kernel.price_helpers.price(model,case,trace)
        rows.append(dict(case=case,instructions=m.steps,peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,
            traffic=traffic,**priced))
        print("PASS",case,flush=True)
    by={r["case"]:r for r in rows}
    scenarios=[]
    for edges,same in ((1000,200),(5000,1000)):
        cycles=edges*by["sampled-edge"]["model_cycles"]+same*by["same-bin"]["model_cycles"]+by["finish-tick"]["model_cycles"]
        scenarios.append(dict(assumed_sampled_edges_per_drawn_frame=edges,assumed_same_bin_calls=same,assumed_ticks_per_drawn_frame=1,
            assumed_cpu_mhz=200,modelled_observer_ms=cycles/200000.0,
            unpriced_mmio_reads=4*(edges+1),scope="Synthetic frequency assumptions; excludes seal/format/control runs, inherited census cost, cache/interrupt/MMIO wait states"))
    assert frozen=={str(x.relative_to(ROOT)):profile.sha(x) for x in paths},"source changed"
    report=dict(status="PASS",scope=__doc__,source_sha256=frozen,profile_receipt=receipt,flags=flags["pmu"],
        kos_driver=dict(source=str(kos_source),sha256=profile.sha(kos_source),flags=kos_flags,object_sha256=profile.sha(kos_obj)),
        build=dict(compiler_sha256=profile.sha(cxx),elf_sha256=profile.sha(elf),object_sha256=profile.sha(obj),
            sections=profile.sections(elf),stack_usage=profile.stack_usage(obj.with_suffix(".su")),
            kos_stack_usage=profile.stack_usage(kos_obj.with_suffix(".su"))),
        cases=rows,memory_controls=kernel.target_machine.memory_controls(),model=model.metadata(),
        overhead_formula="(sampled_edges*Cedge + same_bin_calls*Csame + completed_ticks*Ctick)/(CPU_MHz*1000) ms + unpriced costs",
        modelled_frame_overhead=scenarios,
        limits="Actual core/IRQ/KOS counter instructions with synthetic state/register values. Includes fixture argument marshalling. No PMU-event generation, cache misses, bus or MMIO wait-state timing, complete gameplay frame, or console result is modelled.")
    (out/"target-cost.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",cases=len(rows),receipt=str(out/"target-cost.json"))))

if __name__=="__main__":main()
