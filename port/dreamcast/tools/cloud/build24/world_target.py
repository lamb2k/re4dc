#!/usr/bin/env python3
"""Price exact compiled whole/subset gather bodies on synthetic SH4 states.

Uses the current Make-derived native_static flags and its O2 mesh-method scope.
Counts real executed SH4 opcodes and architectural memory accesses; prices warm
and initially cold I-cache with perfect D-cache. Package lookup uses explicit
already-resolved pointer adapters. Clipping, TA writes/backpressure and full
game frames are excluded. This is not a console time/FPS improvement claim.
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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


build = module("world24_build", HERE / "build_controls.py")
profile = build.profile
kernel = module("world24_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")
extract = module("world24_extract", DC / "tools/d367/world_submit_spike/check_runtime.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=False)
    cxx,kos,sdk = args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    paths = [Path(__file__), HERE / "world_target.cpp.in", HERE / "build_controls.py",
        DC / "game/platform/native_static.cpp", DC / "game/platform/include/scenery_clip_gather.hpp",
        DC / "room/instanced_mesh.hpp", DC / "tools/d367/world_submit_spike/check_runtime.py",
        DC / "tools/d367/actor_bytes_lean/kernel_audit.py",
        *[DC / "tools/d367/world_replay_lean" / p for p in
          ("target_machine.py", "sh4_machine.py", "memory_trace.py", "pipeline_cost.py", "target_run.py")]]
    frozen = {str(p.relative_to(ROOT)): profile.sha(p) for p in paths}
    (out / "source-start.json").write_text(json.dumps(frozen,indent=2)+"\n")
    flags,receipt,_ = profile.derive(out / "profile", cxx,kos,sdk,build.QA,units=("native_static",))
    world = (DC / "game/platform/native_static.cpp").read_text()
    values = {
        "CORNERS": extract.function(world,"const re4dc::room::CompactVertex12* corners(const RE4DC_SCENERY_RECORD& l)"),
        "BASELINE": extract.function(world,"__attribute__((noinline)) const re4dc::room::CompactVertex12* stream_gather(){"),
        "CANDIDATE": extract.function(world,"__attribute__((noinline)) const re4dc::room::CompactVertex12* stream_gather(\n"),
    }
    # The production #endif closes the mutually exclusive template/non-template
    # signatures, not the body. This fixture selects the original Meshlet one.
    assert values["CORNERS"].count("{\n#endif") == 1
    values["CORNERS"] = values["CORNERS"].replace("{\n#endif", "{", 1)
    body = (HERE / "world_target.cpp.in").read_text().replace("@DC@",str(DC))
    for key,value in values.items():body=body.replace("@"+key+"@",value)
    source,obj,elf = out / "fixture.cpp",out / "fixture.o",out / "fixture.elf"
    source.write_text(body)
    builder = profile.Build(out)
    builder.run([*flags["native_static"],"-c","-fstack-usage",source,"-o",obj],label="fixture")
    script=out / "fixture.ld"
    script.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
        ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    builder.run([cxx,"-m4-single","-ml","-nostartfiles","-Wl,--gc-sections","-Wl,-T,"+str(script),
        "-Wl,-e,_fixture_baseline","-Wl,-u,_fixture_candidate","-Wl,-u,_fixture_layout",obj,"-o",elf],label="link")
    prefix=str(cxx).removesuffix("g++")
    (out / "disassembly.txt").write_bytes(builder.run([prefix+"objdump","-d","-C",elf],label="disassembly"))
    program,symbols = kernel.target_machine.scalar.load_elf(elf)
    model = kernel.pipeline_cost.Model(out / "model",elf)
    def machine():
        m=kernel.Machine()
        for address,data,_ in program:m.map(address,data)
        return m
    seed=machine()
    layout=struct.unpack("<20I",seed.bytes_at(symbols["_fixture_layout"][0],80))
    (size,ba,ca,record_at,strips_at,bytes_at,bpkg,bgather,bstreamptr,cpkg,cgather,cstreamptr,cstate,
        baseline_size,candidate_size,state_size,count_at,record_size,pool_at,offsets_at)=layout
    assert state_size==36 and candidate_size-baseline_size==36 and record_size==28
    cases=[]
    for count in (16,64,256):
        cases.append(dict(name=f"v{count}-no-clips",vertices=count,strips=[]))
        coverage={16:(3,7,8,9,16),64:(3,8,16,24,32,36,37,38,64),
                  256:(3,8,16,24,32,64,96,128,151,152,153,192,256)}
        for touched in coverage[count]:
            strips=[list(range(touched))] if touched<256 else [list(range(255)),[253,254,255]]
            cases.append(dict(name=f"v{count}-unique{touched}",vertices=count,strips=strips))
    cases += [dict(name="v256-repeat3-x32",vertices=256,strips=[[0,127,255]]*32),
              dict(name="v256-disjoint3-x64",vertices=256,strips=[list(range(i,i+3)) for i in range(0,192,3)]),
              dict(name="v256-alias3",vertices=256,strips=[[0,127,255]],alias=True),
              dict(name="v256-duplicate255",vertices=256,strips=[[255]*255])]
    rows=[]
    for case in cases:
        count=case["vertices"]
        pool_base,offset_base,local_base,strips_base=0x20000,0x28000,0x30000,0x34000
        pool=bytes((i*73+19)&255 for i in range(2048*12))
        offsets=[(i*37+13)%2048 for i in range(count)]
        if case.get("alias"):offsets[127]=offsets[255]=offsets[0]
        strips=bytes(x for strip in case["strips"] for x in (len(strip),*strip))
        touched={i for strip in case["strips"] for i in strip}
        for arm in ("baseline","candidate"):
            raw=bytearray(size)
            state_at=ba if arm=="baseline" else ca
            pkg_at=bpkg if arm=="baseline" else cpkg
            gather_at=bgather if arm=="baseline" else cgather
            for at,value in ((state_at+pkg_at+pool_at,pool_base),(state_at+pkg_at+offsets_at,offset_base),
                (state_at+gather_at,local_base),(strips_at,strips_base),(bytes_at,len(strips))):
                struct.pack_into("<I",raw,at,value)
            struct.pack_into("<H",raw,record_at+count_at,count)
            m=machine();m.map(0x9000,raw);m.map(pool_base,pool)
            m.map(offset_base,struct.pack("<"+"H"*count,*offsets));m.map(local_base,b"\xa5"*(256*12))
            m.map(strips_base,strips or b"\0")
            m.minimum_sp=m.reg[15];m.observe_start()
            m.execute_kernel(symbols["_fixture_"+arm][0],0x9000);m.observe_stop()
            assert m.reg[0]==bool(strips),(case,arm,m.reg[0])
            expected=touched if arm=="candidate" else set(range(count)) if strips else set()
            for i in range(256):
                want=pool[12*offsets[i]:12*offsets[i]+12] if i in expected else b"\xa5"*12
                assert m.bytes_at(local_base+12*i,12)==want,(case["name"],arm,i)
            traffic=kernel.traffic_details(m.memory_events,m.prefetch_events)
            grouped={}
            for event in m.memory_events:
                address=event[3]
                region=("source_pool" if pool_base<=address<pool_base+len(pool) else
                    "offset_table" if offset_base<=address<offset_base+2*count else
                    "gather_scratch" if local_base<=address<local_base+3072 else
                    "strip_indices" if strips_base<=address<strips_base+len(strips) else
                    "mask_state" if 0x9000+ca+cstate<=address<0x9000+ca+cstate+state_size else
                    "arguments" if 0x9000<=address<0x9000+size else
                    "stack" if address>=0x4f0000 else "code_literals")
                grouped.setdefault(region,[]).append(event)
            traffic["regions"]={name:kernel.summarize(events)["cached"] for name,events in grouped.items()}
            trace=SimpleNamespace(instruction_pcs=list(m.instruction_pcs),steps=m.steps,read=m.read)
            priced=kernel.price_helpers.price(model,case["name"]+"-"+arm,trace)
            rows.append(dict(case=case["name"],arm=arm,vertices=count,clip_strips=len(case["strips"]),
                strip_corners=sum(map(len,case["strips"])),unique_referenced=len(touched),
                copied_vertices=len(expected),instructions=m.steps,traffic=traffic,
                peak_stack_bytes=m.initial_regs[15]-m.minimum_sp,**priced))
        print("PASS",case["name"],flush=True)
    current={str(p.relative_to(ROOT)):profile.sha(p) for p in paths}
    assert frozen==current,[key for key in frozen if frozen[key]!=current[key]]
    report=dict(status="PASS",scope=__doc__,source_sha256=frozen,profile_receipt=receipt,
        compiler_sha256=profile.sha(cxx),elf_sha256=profile.sha(elf),sections=profile.sections(elf),
        object=dict(sha256=profile.sha(obj),**profile.sections(obj),stack_usage=profile.stack_usage(obj.with_suffix(".su"))),
        target_layout=dict(arguments=size,baseline=baseline_size,candidate=candidate_size,mask=state_size),
        cases=rows,model=model.metadata(),memory_controls=kernel.target_machine.memory_controls(),
        limitations="Exact gather bodies and fill helper plus explicit pointer adapters/wrappers. Shared clipping, pool/header resolution, transform, actual cache misses, TA stalls, allocation, game-state and whole-frame frequency are not priced. High coverage/duplicate strips can regress; no console acceptance is claimed.")
    (out / "world-target.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",cases=len(cases),receipt=str(out / "world-target.json"))))


if __name__=="__main__":main()
