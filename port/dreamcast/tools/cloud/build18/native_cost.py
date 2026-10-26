#!/usr/bin/env python3
"""Unchanged production native adapter with explicit synthetic room callbacks.

The full Make-derived native_ui translation unit is compiled unchanged. Only
one local symbol is made globally visible in an object copy, allowing a small
separate synthetic caller to retain that exact production function at link.
Actual newlib memset is retained. Real room/game owner lookup, allocation,
payload/packet generation, queue drain and rendering costs are not measured.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
import target_cost as common
build,profile,kernel=common.build,common.profile,common.kernel
DC,ROOT=common.DC,common.ROOT
ADAPTER="__ZN12_GLOBAL__N_1L19fx_r200_tail_selectEjRPhRPj.constprop.0"
GLOBALS=dict(state="__ZN12_GLOBAL__N_1L12fx_r200_tailE",
    model="__ZN12_GLOBAL__N_1L13model_packetsE",
    spill="__ZN12_GLOBAL__N_1L14deferred_spillE",
    spill_top="__ZN12_GLOBAL__N_1L18deferred_spill_topE",
    spill_bytes="__ZN12_GLOBAL__N_1L23deferred_spill_capacityE",
    cell="__ZN11fxroomspill4cellE",generation="__ZN11fxroomspill10generationE")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("output","sh4-cxx","kos-root","sdk-root"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    paths=build.source_paths()+[Path(__file__),HERE/"native_cost_fixture.cpp.in",HERE/"target_cost.py",
        DC/"tools/d367/actor_bytes_lean/kernel_audit.py",DC/"tools/d367/world_replay_lean/target_machine.py",
        DC/"tools/d367/world_replay_lean/sh4_machine.py",DC/"tools/d367/world_replay_lean/memory_trace.py",
        DC/"tools/d367/world_replay_lean/pipeline_cost.py",DC/"tools/d367/world_replay_lean/target_run.py"]
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in paths}
    flags,receipt,sources=profile.derive(out/"profile",cxx,kos,sdk,["FX_R200_ENTRY_CAP=1"],units=("native_ui",))
    builder=profile.Build(out);prefix=str(cxx).removesuffix("g++")
    native=out/"native_ui.o";exported=out/"native_ui-exported.o"
    source=sources["native_ui"]
    builder.run([*flags["native_ui"],"-iquote",source.parent,"-x","c++","-","-c","-fstack-usage","-o",native],
        cwd=source.parent,source=source.read_bytes(),label="native-ui")
    adapter_bytes=build.symbol_bytes(native,ADAPTER)
    builder.run([prefix+"objcopy","--globalize-symbol="+ADAPTER,native,exported],label="expose-local-symbol")
    assert build.symbol_bytes(exported,ADAPTER)==adapter_bytes,"object-copy instruction change"
    fixture,obj,elf=out/"fixture.cpp",out/"fixture.o",out/"fixture.elf"
    fixture.write_text((HERE/"native_cost_fixture.cpp.in").read_text().replace("@DC@",str(DC)).replace("@ADAPTER@",ADAPTER))
    builder.run([*flags["native_ui"],"-c","-fstack-usage",fixture,"-o",obj],label="fixture")
    linker=out/"fixture.ld"
    linker.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
        ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    roots=("fixture_native_select","fixture_native_admit","fixture_native_fill","fixture_native_layout")
    builder.run([cxx,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections","-Wl,-T,"+str(linker),
        "-Wl,-e,_fixture_native_select",*["-Wl,-u,_"+x for x in roots],obj,exported,"-o",elf],label="link")
    (out/"disassembly.txt").write_bytes(builder.run([prefix+"objdump","-d","-C",elf],label="disassembly"))
    program,symbols=kernel.target_machine.scalar.load_elf(elf)
    model=kernel.pipeline_cost.Model(out/"model",elf)
    def machine():
        m=kernel.Machine()
        for address,data,_ in program:m.map(address,data)
        return m
    seed=machine()
    layout=struct.unpack("<12I",seed.bytes_at(symbols["_fixture_native_layout"][0],48))
    size,required_at,storage_at,cursor_at,admitted_at,limit_at,state_bytes=layout[:7]
    state_fields=dict(zip(common.STATE,layout[7:]))
    addresses={key:symbols[value][0] for key,value in GLOBALS.items()}
    params=symbols["_fixture_room_parameters"][0]
    assert state_bytes==20
    base_context=dict(room=0x200,room_live=1,generation=7,room_cell=0x20000,
        room_generation=7,spill=0x20000,spill_top=0,spill_bytes=24576,tail=0x30000)
    bound=dict(data=0x30000,owner=0x20000,generation=7,top=256,poisoned=0)
    cases=[
        dict(name="native-first-tail-select",accepted=1,top=8192),
        dict(name="native-first-tail-admit",entry="fixture_native_admit",accepted=1,top=8064,admitted=1),
        dict(name="native-bound-tail-admit",entry="fixture_native_admit",state=bound,accepted=1,top=128,admitted=1),
        dict(name="native-tail-exhausted",state={**bound,"top":96},accepted=0),
        dict(name="native-outside-r200",context=dict(room=0x201),accepted=0),
        dict(name="native-room-not-live",context=dict(room_live=0),accepted=0),
        dict(name="native-room-allocation-refused-slab-alias",context=dict(room_cell=0,spill=0x30000,spill_bytes=8192),accepted=0),
        dict(name="native-owner-generation-changed",state=bound,context=dict(generation=8,room_generation=8),accepted=0,poisoned=1),
        dict(name="native-fill-128-byte-sprites",entry="fixture_native_fill",accepted=0,top=0,admitted=64,sequence=True,
             scope="Selector stress only: the ordinary sprite producer cap prevents this complete 65-attempt adapter sequence in the game."),
        dict(name="native-fill-192-byte-lasers",entry="fixture_native_fill",required=192,accepted=0,top=128,admitted=42,sequence=True,
             scope="Reachable allocator sequence for uncapped laser-line admission, assuming the primary and room spill are already full."),
    ]
    rows=[]
    for case in cases:
        context={**base_context,**case.get("context",{})}
        state={name:0 for name in common.STATE};state.update(case.get("state",{}))
        required=case.get("required",128)
        raw=bytearray(size)
        for at,value in ((required_at,required),(storage_at,0x60000),(cursor_at,0x9400),(limit_at,128)):
            struct.pack_into("<I",raw,at,value)
        m=machine();m.map(0x9000,raw)
        for name,offset in state_fields.items():
            m.write(addresses["state"]+offset,state[name],1 if name=="poisoned" else 4)
        native_values=dict(model=context["tail"]-24576 if context["tail"] else 0,
            cell=context["room_cell"],generation=context["room_generation"],spill=context["spill"],
            spill_top=context["spill_top"],spill_bytes=context["spill_bytes"])
        for name,value in native_values.items():m.write(addresses[name],value,4)
        for offset,value in enumerate((context["room"],context["room_live"],context["generation"],0,0)):
            m.write(params+offset*4,value,4)
        m.minimum_sp=m.reg[15];m.observe_start()
        m.execute_kernel(symbols["_"+case.get("entry","fixture_native_select")][0],0x9000)
        m.observe_stop()
        def word(at):return int.from_bytes(m.bytes_at(at,4),"little")
        result_state={name:int.from_bytes(m.bytes_at(addresses["state"]+offset,1 if name=="poisoned" else 4),"little") for name,offset in state_fields.items()}
        admitted=word(0x9000+admitted_at)
        assert m.reg[0]==case["accepted"],(case,m.reg[0])
        assert admitted==case.get("admitted",0),(case,admitted)
        for key in ("top","poisoned"):
            if key in case:assert result_state[key]==case[key],(case,result_state)
        if case["accepted"] or admitted:
            assert word(0x9000+storage_at)==context["tail"]
            assert word(0x9000+cursor_at)==addresses["state"]+state_fields["top"]
        else:
            assert word(0x9000+storage_at)==0x60000 and word(0x9000+cursor_at)==0x9400
        calls=admitted+1 if case.get("sequence") else 1
        assert word(params+12)==calls
        assert word(params+16)==(calls if context["room"]==0x200 else 0)
        assert not any(0x20000<=e[3]<0x40000 for e in m.memory_events),"packet arena accessed"
        traffic=kernel.traffic_details(m.memory_events,m.prefetch_events)
        regions={}
        for event in m.memory_events:
            address=event[3]
            region=("stack" if address>=0x4f0000 else "fixture-arguments" if 0x9000<=address<0x9000+size else
                "synthetic-room-callback-state" if params<=address<params+20 else
                "native-admission-state" if addresses["state"]<=address<addresses["state"]+state_bytes else
                "native-global-pointers" if any(address==addresses[key] for key in addresses if key!="state") else "code-literals")
            regions.setdefault(region,[]).append(event)
        traffic["regions"]={name:kernel.summarize(events) for name,events in regions.items()}
        trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
        priced=kernel.price_helpers.price(model,case["name"],trace)
        callback_symbols=("_re4dc_room_id_now","_re4dc_room4_state")
        callback_instructions=sum(any(symbols[name][0]<=pc<symbols[name][0]+symbols[name][1] for name in callback_symbols) for pc in m.instruction_pcs)
        row=dict(case=case["name"],entry=case.get("entry","fixture_native_select"),accepted=case["accepted"],
            required=required,admitted=admitted,state=result_state,instructions=m.steps,
            case_scope=case.get("scope","Single call to the actual production adapter plus synthetic caller/callbacks."),
            synthetic_callbacks=dict(getter_calls=word(params+12),room_state_calls=word(params+16),instructions=callback_instructions),
            peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,traffic=traffic,**priced)
        rows.append(row)
        print("PASS",case["name"],flush=True)
    assert frozen=={str(p.relative_to(ROOT)):profile.sha(p) for p in paths},"production/tool source changed; rerun"
    native_stack=profile.stack_usage(native.with_suffix(".su"))
    frames=[x for x in native_stack if x["function"].endswith(":constprop(unsigned int, unsigned char*&, unsigned int*&)")]
    assert len(frames)==1,frames
    scenario=next(row for row in rows if row["case"]=="native-fill-192-byte-lasers")
    report=dict(status="PASS",scope=__doc__,source_sha256=frozen,profile_receipt=receipt,
        compiler_sha256=profile.sha(cxx),elf_sha256=profile.sha(elf),sections=profile.sections(elf),
        objects={native.name:dict(sha256=profile.sha(native),**profile.sections(native),adapter_stack_frame=frames[0]),
                 obj.name:dict(sha256=profile.sha(obj),**profile.sections(obj),stack_usage=profile.stack_usage(obj.with_suffix(".su")))},
        adapter=dict(symbol=ADAPTER,bytes=len(adapter_bytes),unrelocated_code_sha256=hashlib.sha256(adapter_bytes).hexdigest(),
            symbol_visibility_only_change=True,native_function_abi="r4 required, r5 address of storage, r6 address of cursor; production clone assumes its aligned callers"),
        target_layout=dict(arguments=size,tail=state_bytes),cases=rows,model=model.metadata(),memory_controls=kernel.target_machine.memory_controls(),
        whole_frame_scenario=dict(label="MODELLED admission overhead in a hypothetical 200 MHz frame",
            case="native-fill-192-byte-lasers",clock_hz=200000000,
            warm_ms=scenario["model_cycles"]/200000,cold_i_ms=scenario["cold_icache"]["model_cycles"]/200000,
            assumptions="Primary and room spill already full. Exactly 43 extra-tail attempts through the uncapped laser-line admission path: 42 accepted 192-byte requests plus the first refusal, 8064 bytes used and 128 left; no payload stores or rendering. Cycles/200000 gives milliseconds at 200 MHz. One continuous trace, one cold-I start for the entire sequence.",
            excludes="Actual game lookup cost, primary/spill checks before this adapter, packet building, FIFO/render/PVR, bus stalls and any base frame cost. This is not the total game-frame time or a speedup prediction."),
        limits="Full unchanged native_ui object, with symbol visibility edited only in a copy for isolated linking. Real newlib memset. Synthetic getter/room-state callbacks and small caller are included in traces and identified separately; real lookup subsystem timing is excluded. Payload arenas unmapped. Not a final game link, console timing or rendering speedup.")
    (out/"target-native-cost.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",cases=len(rows),receipt=str(out/"target-native-cost.json"))))


if __name__=="__main__":main()
