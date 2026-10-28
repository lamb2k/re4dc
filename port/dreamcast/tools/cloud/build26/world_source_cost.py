#!/usr/bin/env python3
"""Price production world gathers/accessor with an identical source consumer.

Each arm feeds the same synthetic six-u16-word consumer. Production whole and
subset gather bodies are extracted unchanged; Indexed is the production helper.
The window includes gather copying, offset/index lookups and source-word reads,
and the documented common consumer. Real projection, clipping, package lookup,
submission, cache misses and chapter frequencies are excluded.
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
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


controls = module("world26_cost_controls", HERE / "build_controls.py")
profile = controls.profile
kernel = module("world26_cost_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")
extract = module("world26_cost_extract", DC / "tools/d367/world_submit_spike/check_runtime.py")
LAYOUT = ("version", "bytes", "whole", "partial", "indexed", "record", "strips", "strip_bytes", "output",
          "whole_package", "whole_gathered", "whole_stream", "partial_package", "partial_gathered", "partial_stream",
          "partial_state", "whole_bytes", "partial_bytes", "state_bytes", "vertex_count", "record_bytes", "pool", "offsets")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    paths = [Path(__file__), HERE / "world_source_fixture.cpp.in", HERE / "build_controls.py",
             DC / "game/platform/native_static.cpp", DC / "game/platform/include/scenery_clip_gather.hpp",
             DC / "game/platform/include/scenery_clip_indexed26.hpp", DC / "room/instanced_mesh.hpp",
             DC / "tools/d367/world_submit_spike/check_runtime.py", DC / "tools/d367/actor_bytes_lean/kernel_audit.py",
             *[DC / "tools/d367/world_replay_lean" / (name + ".py") for name in
               ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in paths}
    options = controls.QA + ["QA_LINK=0", "DRAW_FALLBACK_AUDIT=0", "DRAW_SETUP_AUDIT=0", "SCENERY_CLIP_INDEXED26=1"]
    flags, receipt, _ = profile.derive(out / "profile", cxx, kos, sdk, options, units=("native_static",))
    world = (DC / "game/platform/native_static.cpp").read_text()
    extracted = {
        "CORNERS": extract.function(world, "const re4dc::room::CompactVertex12* corners(const RE4DC_SCENERY_RECORD& l)"),
        "WHOLE": extract.function(world, "__attribute__((noinline)) const re4dc::room::CompactVertex12* stream_gather(){"),
        "PARTIAL": extract.function(world, "__attribute__((noinline)) const re4dc::room::CompactVertex12* stream_gather(\n"),
    }
    assert extracted["CORNERS"].count("{\n#endif") == 1
    extracted["CORNERS"] = extracted["CORNERS"].replace("{\n#endif", "{", 1)
    body = (HERE / "world_source_fixture.cpp.in").read_text().replace("@DC@", str(DC))
    for key, value in extracted.items():
        body = body.replace("@" + key + "@", value)
    source, obj, elf = out / "fixture.cpp", out / "fixture.o", out / "fixture.elf"
    source.write_text(body)
    builder = profile.Build(out)
    builder.run([*flags["native_static"], "-fstack-usage", "-c", source, "-o", obj], label="fixture")
    script = out / "fixture.ld"
    script.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
                      ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(script),
                 "-Wl,-e,_fixture_whole", "-Wl,-u,_fixture_partial", "-Wl,-u,_fixture_indexed", "-Wl,-u,_fixture_layout",
                 obj, "-o", elf], label="link")
    prefix = str(cxx).removesuffix("g++")
    (out / "disassembly.txt").write_bytes(builder.run([prefix + "objdump", "-d", "-C", elf], label="disassembly"))
    program, symbols = kernel.target_machine.scalar.load_elf(elf)
    model = kernel.pipeline_cost.Model(out / "model", elf)

    def machine():
        value = kernel.Machine()
        for address, data, _ in program:
            value.map(address, data)
        return value

    seed = machine()
    layout = dict(zip(LAYOUT, struct.unpack("<" + "I" * len(LAYOUT),
                       seed.bytes_at(symbols["_fixture_layout"][0], 4 * len(LAYOUT)))))
    assert layout["version"] == 1 and layout["state_bytes"] == 36 and layout["record_bytes"] == 28
    cases = [dict(case=f"v{n}-no-clips", vertices=n, strips=[]) for n in (16, 64, 256)]
    cases += [dict(case=f"v{n}-unique{k}", vertices=n, strips=[list(range(k))])
              for n, k in ((16, 3), (16, 16), (64, 3), (64, 16), (64, 64), (256, 3), (256, 64), (256, 255))]
    cases += [dict(case="v256-repeat3-x32", vertices=256, strips=[[0, 127, 255]] * 32),
              dict(case="v256-alias3", vertices=256, strips=[[0, 127, 255]], alias=True),
              dict(case="v256-duplicate255", vertices=256, strips=[[255] * 255])]
    rows = []
    for case in cases:
        count = case["vertices"]
        pool_at, offset_at, gather_at, strips_at, output_at = 0x20000, 0x28000, 0x30000, 0x34000, 0x38000
        pool = bytes((i * 73 + 19) & 255 for i in range(2048 * 12))
        offsets = [(i * 37 + 13) % 2048 for i in range(count)]
        if case.get("alias"):
            offsets[127] = offsets[255] = offsets[0]
        strips = bytes(value for strip in case["strips"] for value in (len(strip), *strip))
        selected = [i for strip in case["strips"] for i in strip]
        expected = b"".join(struct.pack("<I", sum(struct.unpack_from("<6H", pool, 12 * offsets[i]))) for i in selected)
        for arm in ("whole", "partial", "indexed"):
            raw = bytearray(layout["bytes"])
            for name in ("whole", "partial"):
                origin = layout[name]
                package = origin + layout[name + "_package"]
                for at, value in ((package + layout["pool"], pool_at), (package + layout["offsets"], offset_at),
                                  (origin + layout[name + "_gathered"], gather_at)):
                    struct.pack_into("<I", raw, at, value)
            for at, value in ((layout["indexed"] + layout["pool"], pool_at), (layout["indexed"] + layout["offsets"], offset_at),
                              (layout["strips"], strips_at), (layout["strip_bytes"], len(strips)), (layout["output"], output_at)):
                struct.pack_into("<I", raw, at, value)
            struct.pack_into("<H", raw, layout["record"] + layout["vertex_count"], count)
            m = machine()
            m.map(0x9000, raw); m.map(pool_at, pool); m.map(offset_at, struct.pack("<" + "H" * count, *offsets))
            m.map(gather_at, bytes([0xa5]) * (256 * 12)); m.map(strips_at, strips or b"\0")
            m.map(output_at, bytes([0xcd]) * max(4, len(expected)))
            m.minimum_sp = m.reg[15]
            m.observe_start(); m.execute_kernel(symbols["_fixture_" + arm][0], 0x9000); m.observe_stop()
            assert m.reg[0] == len(selected) and m.bytes_at(output_at, len(expected)) == expected, (case["case"], arm)
            if arm == "indexed":
                assert m.bytes_at(gather_at, 256 * 12) == bytes([0xa5]) * (256 * 12), "candidate touched gather storage"
            traffic = kernel.traffic_details(m.memory_events, m.prefetch_events)
            grouped = {}
            for event in m.memory_events:
                address = event[3]
                region = ("source_pool" if pool_at <= address < pool_at + len(pool) else
                          "offset_table" if offset_at <= address < offset_at + 2 * count else
                          "gather_scratch" if gather_at <= address < gather_at + 3072 else
                          "strip_indices" if strips_at <= address < strips_at + len(strips) else
                          "consumer_output" if output_at <= address < output_at + max(4, len(expected)) else
                          "arguments" if 0x9000 <= address < 0x9000 + len(raw) else "stack" if address >= 0x4f0000 else "code_literals")
                grouped.setdefault(region, []).append(event)
            traffic["regions"] = {name: kernel.summarize(events)["cached"] for name, events in grouped.items()}
            trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
            rows.append(dict(case=case["case"], arm=arm, meshlet_vertices=count, clip_strips=len(case["strips"]),
                             consumed_corners=len(selected), unique_source_corners=len(set(selected)), instructions=m.steps,
                             peak_stack_bytes=m.initial_regs[15] - m.minimum_sp, traffic=traffic,
                             **kernel.price_helpers.price(model, case["case"] + "-" + arm, trace)))
        print("PASS", case["case"], flush=True)
    assert frozen == {str(path.relative_to(ROOT)): profile.sha(path) for path in paths}, "source changed; rerun"
    report = dict(status="PASS", baseline=controls.BASELINE, scope=__doc__, source_sha256=frozen,
                  profile_receipt=receipt, elf_sha256=profile.sha(elf), sections=profile.sections(elf),
                  object=dict(sha256=profile.sha(obj), **profile.sections(obj), stack_usage=profile.stack_usage(obj.with_suffix(".su"))),
                  target_layout=layout, cases=rows, model=model.metadata(), memory_controls=kernel.target_machine.memory_controls(),
                  limitations="Production gather bodies and indexed accessor with resolved package pointers, followed by a common synthetic six-word sum/store consumer. This is a source-acquisition window, not the production decoder, clipper or full draw. Includes wrapper/consumer instructions. Perfect D-cache; unique data lines are not misses. No whole-frame frequency or console benefit is measured.")
    (out / "world-source-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(cases), arms=3, receipt=str(out / "world-source-cost.json"))))


if __name__ == "__main__":
    main()
