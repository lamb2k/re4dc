#!/usr/bin/env python3
"""Production Build18 admission helper on compiled SH4 synthetic states.

Cycles price actual dynamic instructions with perfect caches and an initially
cold instruction cache. Architectural bytes/32-byte lines are not cache misses.
Room lookups, packet generation, payload writes, FIFO drain, texture work and
PVR/owner rendering are unpriced. Admitting more sprites can add rendering
work; this is neither a game-frame saving nor a console timing claim.
"""
import argparse
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


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    sys.modules[name]=result
    spec.loader.exec_module(result)
    return result


build=module("fx18_build",HERE/"build_controls.py")
profile=build.profile
kernel=module("fx18_kernel",DC/"tools/d367/actor_bytes_lean/kernel_audit.py")
STATE=("data","owner","generation","top","poisoned")
CONTEXT=("room","room_live","generation","room_cell","room_generation","room_bytes",
         "spill","spill_top","spill_bytes","tail","tail_bytes")
RESULTS=("Accepted","OtherRoom","RoomClosed","NoRoomSpill","StaleGeneration","WrongSpill",
         "NoTail","InvalidStorage","Overlap","BadRequest","SpillAvailable","Exhausted","OwnerChanged")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("output","sh4-cxx","kos-root","sdk-root"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    paths=build.source_paths()+[Path(__file__),HERE/"cost_fixture.cpp.in",
        DC/"tools/d367/actor_bytes_lean/kernel_audit.py",DC/"tools/d367/world_replay_lean/target_machine.py",
        DC/"tools/d367/world_replay_lean/sh4_machine.py",DC/"tools/d367/world_replay_lean/memory_trace.py",
        DC/"tools/d367/world_replay_lean/pipeline_cost.py",DC/"tools/d367/world_replay_lean/target_run.py"]
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in paths}
    flags,receipt,_=profile.derive(out/"profile",cxx,kos,sdk,["FX_R200_ENTRY_CAP=1"],units=("native_ui",))
    builder=profile.Build(out)
    source,obj,elf=out/"fixture.cpp",out/"fixture.o",out/"fixture.elf"
    source.write_text((HERE/"cost_fixture.cpp.in").read_text().replace("@DC@",str(DC)))
    builder.run([*flags["native_ui"],"-c","-fstack-usage",source,"-o",obj],label="fixture")
    linker=out/"fixture.ld"
    linker.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
        ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    roots=("fixture_select","fixture_admit","fixture_fill","fixture_reset","fixture_layout")
    builder.run([cxx,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections","-Wl,-T,"+str(linker),
        "-Wl,-e,_fixture_select",*["-Wl,-u,_"+x for x in roots],obj,"-o",elf],label="link")
    prefix=str(cxx).removesuffix("g++")
    (out/"disassembly.txt").write_bytes(builder.run([prefix+"objdump","-d","-C",elf],label="disassembly"))
    program,symbols=kernel.target_machine.scalar.load_elf(elf)
    model=kernel.pipeline_cost.Model(out/"model",elf)
    def machine():
        m=kernel.Machine()
        for address,data,_ in program:m.map(address,data)
        return m
    seed=machine()
    layout=struct.unpack("<39I",seed.bytes_at(symbols["_fixture_layout"][0],156))
    size,state_at,context_at,required_at,storage_at,cursor_at,admitted_at,limit_at,state_bytes,context_bytes=layout[:10]
    state_fields=dict(zip(STATE,layout[10:15]));context_fields=dict(zip(CONTEXT,layout[15:26]))
    result_values=dict(zip(RESULTS,layout[26:]))
    assert state_bytes==20 and context_bytes==44
    base_context=dict(room=0x200,room_live=1,generation=7,room_cell=0x20000,
        room_generation=7,room_bytes=24576,spill=0x20000,spill_top=0,spill_bytes=24576,
        tail=0x30000,tail_bytes=8192)
    bound=dict(data=0x30000,owner=0x20000,generation=7,top=256,poisoned=0)
    cases=[
        dict(name="first-tail-select",expected="Accepted"),
        dict(name="first-tail-admit",entry="fixture_admit",expected="Accepted",top=8064,admitted=1),
        dict(name="bound-tail-admit",entry="fixture_admit",state=bound,expected="Accepted",top=128,admitted=1),
        dict(name="exact-tail-end",entry="fixture_admit",state={**bound,"top":128},expected="Accepted",top=0,admitted=1),
        dict(name="tail-exhausted",state={**bound,"top":96},expected="Exhausted"),
        dict(name="outside-r200",context=dict(room=0x201),expected="OtherRoom"),
        dict(name="room-not-live",context=dict(room_live=0),expected="RoomClosed"),
        dict(name="room-allocation-refused-slab-alias",context=dict(room_cell=0,spill=0x30000,spill_bytes=8192),expected="NoRoomSpill"),
        dict(name="stale-room-generation",context=dict(room_generation=6),expected="StaleGeneration"),
        dict(name="wrong-active-spill",context=dict(spill=0x28000),expected="WrongSpill"),
        dict(name="no-model-tail",context=dict(tail=0,tail_bytes=0),expected="NoTail"),
        dict(name="room-tail-overlap",context=dict(tail=0x24000),expected="Overlap"),
        dict(name="invalid-tail-wrap",context=dict(tail=0xfffff000),expected="InvalidStorage"),
        dict(name="unaligned-request",required=127,expected="BadRequest"),
        dict(name="primary-spill-still-fits",context=dict(spill_top=128),expected="SpillAvailable"),
        dict(name="owner-generation-changed",state=bound,context=dict(generation=8,room_generation=8),expected="OwnerChanged",poisoned=1),
        dict(name="already-poisoned",state={**bound,"poisoned":1},expected="OwnerChanged",poisoned=1),
        dict(name="reset-after-drain",entry="fixture_reset",state={**bound,"poisoned":1},expected="Accepted",reset=True),
        dict(name="fill-128-byte-sprites",entry="fixture_fill",required=128,expected="Exhausted",top=0,admitted=64),
        dict(name="fill-192-byte-lines",entry="fixture_fill",required=192,expected="Exhausted",top=128,admitted=42),
        dict(name="fill-320-byte-octagons",entry="fixture_fill",required=320,expected="Exhausted",top=192,admitted=25),
        dict(name="fill-whole-6-sprite-batches",entry="fixture_fill",required=768,expected="Exhausted",top=512,admitted=10),
    ]
    rows=[]
    for case in cases:
        raw=bytearray(size)
        context={**base_context,**case.get("context",{})}
        for name,offset in context_fields.items():
            at=context_at+offset;value=context[name]
            if name=="room_live":raw[at]=value
            else:struct.pack_into("<I",raw,at,value)
        state={name:0 for name in STATE};state.update(case.get("state",{}))
        for name,offset in state_fields.items():
            at=state_at+offset;value=state[name]
            if name=="poisoned":raw[at]=value
            else:struct.pack_into("<I",raw,at,value)
        required=case.get("required",128)
        for at,value in ((required_at,required),(storage_at,0x60000),(cursor_at,0x9400),(limit_at,128)):
            struct.pack_into("<I",raw,at,value)
        m=machine();m.map(0x9000,raw)
        m.minimum_sp=m.reg[15];m.observe_start()
        m.execute_kernel(symbols["_"+case.get("entry","fixture_select")][0],0x9000)
        m.observe_stop()
        def word(at):return int.from_bytes(m.bytes_at(0x9000+at,4),"little")
        result_state={name:int.from_bytes(m.bytes_at(0x9000+state_at+offset,1 if name=="poisoned" else 4),"little") for name,offset in state_fields.items()}
        assert m.reg[0]==result_values[case["expected"]],(case["name"],m.reg[0])
        if case.get("reset"):
            assert not any(result_state.values()),result_state
        else:
            if "top" in case:assert result_state["top"]==case["top"],(case,result_state)
            if "poisoned" in case:assert result_state["poisoned"]==case["poisoned"]
            assert word(admitted_at)==case.get("admitted",0)
            if case["expected"]=="Accepted" or case.get("admitted"):
                assert word(storage_at)==context["tail"]
                assert word(cursor_at)==0x9000+state_at+state_fields["top"]
            else:
                assert word(storage_at)==0x60000 and word(cursor_at)==0x9400
        # The selector and cursor update cannot read/write packet arenas.
        assert not any(0x20000<=e[3]<0x40000 for e in m.memory_events)
        traffic=kernel.traffic_details(m.memory_events,m.prefetch_events)
        regions={}
        for event in m.memory_events:
            address=event[3]
            region=("stack" if address>=0x4f0000 else "state" if 0x9000+state_at<=address<0x9000+state_at+state_bytes else
                    "context" if 0x9000+context_at<=address<0x9000+context_at+context_bytes else
                    "fixture-arguments" if 0x9000<=address<0x9000+size else "code-literals")
            regions.setdefault(region,[]).append(event)
        traffic["regions"]={name:kernel.summarize(events) for name,events in regions.items()}
        trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
        priced=kernel.price_helpers.price(model,case["name"],trace)
        rows.append(dict(case=case["name"],entry=case.get("entry","fixture_select"),result=case["expected"],
            required=required,admitted=word(admitted_at),state=result_state,instructions=m.steps,
            peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,traffic=traffic,**priced))
        print("PASS",case["name"],flush=True)
    assert frozen=={str(p.relative_to(ROOT)):profile.sha(p) for p in paths},"production/tool source changed; rerun"
    report=dict(status="PASS",scope=__doc__,source_sha256=frozen,profile_receipt=receipt,
        compiler_sha256=profile.sha(cxx),elf_sha256=profile.sha(elf),sections=profile.sections(elf),
        objects={obj.name:dict(sha256=profile.sha(obj),**profile.sections(obj),stack_usage=profile.stack_usage(obj.with_suffix(".su")))},
        target_layout=dict(arguments=size,tail=state_bytes,context=context_bytes),
        cases=rows,model=model.metadata(),memory_controls=kernel.target_machine.memory_controls(),
        limits="Production Tail::select/reset and small fixture wrapper only. Accepted admission decrements the same cursor once. Packet buffers are unmapped and untouched. Source room lookup, native adapter, packet construction/FIFO/PVR work and actual frame/cache timing remain unpriced; no rendering speedup is claimed.")
    (out/"target-cost.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",cases=len(rows),receipt=str(out/"target-cost.json"))))


if __name__=="__main__":main()
