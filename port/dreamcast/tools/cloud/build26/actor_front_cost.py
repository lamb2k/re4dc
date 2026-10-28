#!/usr/bin/env python3
"""Price the actual actor clip dispatch with a bounded shared-clipper edge.

The complete production actor TU supplies Part::clip_strip, world_of, project,
the new front-triangle helper and real RAM-packet writes. The shared clipper
exposes its prepared input then returns zero in every arm. Its arithmetic and
output, TA/device work, position/light prepasses and cache misses are excluded.
Mixed strips have one near vertex followed by wholly-front triangles. An all-
front forced-call control and an all-slow control expose savings and overhead.
Geometry has depth +/-1 and identity transforms; no game assets are involved.
Warm/cold-I estimates assume perfect D-cache and a synthetic isolated layout.
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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


controls = module("actor26_cost_controls", HERE / "build_controls.py")
profile = controls.profile
kernel = module("actor26_cost_kernel", DC / "tools/d367/actor_bytes_lean/kernel_audit.py")
old = module("actor26_observed_edge", HERE.parent / "build24/actor_target_run.py")
LAYOUT = (*old.LAYOUT, "outcodes", "output", "written", "vertex_flag", "eol_flag", "near_bit")


class Machine(old.Machine):
    def attach(self, symbols):
        super().attach(symbols)
        at = symbols["_fixture_layout"][0]
        self.layout = dict(zip(LAYOUT, (self.word(at + 4 * i) for i in range(len(LAYOUT)))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    source = DC / "game/platform/native_actor_fast.cpp"
    sources = [Path(__file__), HERE / "actor_front_fixture.cpp.in", HERE / "build_controls.py", source,
               source.parent / "include/actor_clip_front26.hpp", source.parent / "include/actor_clip_reuse.hpp",
               DC / "room/pvr_geometry.hpp", HERE.parent / "build24/actor_target_run.py",
               DC / "tools/d367/actor_bytes_lean/kernel_audit.py",
               *[DC / "tools/d367/world_replay_lean" / (name + ".py") for name in
                 ("target_machine", "sh4_machine", "memory_trace", "pipeline_cost", "target_run")]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}
    flags, receipt, _ = profile.derive(out / "profile", cxx, kos, sdk,
        controls.QA + ["DRAW_FALLBACK_AUDIT=0", "DRAW_SETUP_AUDIT=0", "QA_LINK=0",
                       "ACTOR_CLIP_FRONT26=0", "ACTOR_CLIP_REUSE=0"], units=("native_actor_fast",))
    common = [x for x in flags["native_actor_fast"] if not x.startswith(
        ("-DRE4DC_ACTOR_CLIP_FRONT26=", "-DRE4DC_ACTOR_CLIP_REUSE="))]
    fixture = out / "fixture.cpp"
    fixture.write_text('#include "' + str(source) + '"\n' + (HERE / "actor_front_fixture.cpp.in").read_text())
    stub = out / "clip_edge.cpp"
    stub.write_text('''#include "pvr_geometry.hpp"
extern "C" void fixture_clip_edge(const void*, const float*);
namespace re4dc::render {
std::uint32_t clip_projected_triangle(const RenderVertex* p,pvr_vertex_t*,
    std::uint8_t,const ClipParameters&,ClipStats*,const float* alpha) {
    fixture_clip_edge(p,alpha); return 0;
}
}
''')
    marker = out / "marker.cpp"
    marker.write_text('''#include <cstddef>
extern "C" {
void fixture_clip_edge(const void*, const float*) {}
void* sq_fast_cpy(void* destination, const void*, std::size_t) { return destination; }
float re4dc_screen_wf=640.0f, re4dc_screen_hf=480.0f;
}
''')
    script = out / "fixture.ld"
    script.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
                      ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
    builder = profile.Build(out)
    for name, path in (("clip_edge", stub), ("marker", marker)):
        builder.run([*common, "-I" + str(DC / "room"), "-c", path, "-o", out / (name + ".o")], label=name)
    prefix = str(cxx).removesuffix("g++")
    arms, programs, models = {}, {}, {}
    for reuse in (0, 1):
        for front in (0, 1):
            name = f"front{front}-reuse{reuse}"
            obj, elf = out / (name + ".o"), out / (name + ".elf")
            command = [*common, f"-DRE4DC_ACTOR_CLIP_FRONT26={front}", f"-DRE4DC_ACTOR_CLIP_REUSE={reuse}",
                       "-fstack-usage", "-c", fixture, "-o", obj]
            builder.run(command, label=name)
            builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(script),
                         "-Wl,-e,_fixture_run", "-Wl,-u,_fixture_prepare", "-Wl,-u,_fixture_layout",
                         obj, out / "clip_edge.o", out / "marker.o", "-lm", "-o", elf], label=name + "-link")
            (out / (name + ".disassembly.txt")).write_bytes(builder.run(
                [prefix + "objdump", "-d", "-C", elf], label=name + "-disassembly"))
            arms[name] = dict(elf_sha256=profile.sha(elf), sections=profile.sections(elf),
                             object_sections=profile.sections(obj), stack_usage=profile.stack_usage(obj.with_suffix(".su")),
                             command=[str(value) for value in command])
            programs[name] = kernel.target_machine.scalar.load_elf(elf)
            models[name] = kernel.pipeline_cost.Model(out / ("model-" + name), elf)

    rows = []
    for pattern, label in enumerate(("forced-front-control", "one-near", "all-near-control")):
        for skin in (0, 1):
            kind = 2 * pattern + skin
            for n in ((3, 16) if args.quick else (3, 16, 64)):
                case = ("skin" if skin else "rigid") + "-" + label + f"-n{n}"
                expected_slow = list(range(n - 2)) if pattern == 2 else [0] if pattern == 1 else []
                old_prepared = None
                case_arms = {}
                for name, (program, symbols) in programs.items():
                    m = Machine()
                    for address, data, _ in program:
                        m.map(address, data)
                    m.attach(symbols)
                    m.execute(symbols["_fixture_prepare"][0], kind)
                    cache = [m.bytes_at(m.layout["cache"] + 32 * i, 32) for i in range(n)]
                    expected_output = bytearray()
                    for t in range(n - 2):
                        if t in expected_slow:
                            continue
                        for k, i in enumerate((t + (t & 1), t + ((t & 1) ^ 1), t + 2)):
                            value = bytearray(cache[i])
                            struct.pack_into("<I", value, 0, m.layout["eol_flag"] if k == 2 else m.layout["vertex_flag"])
                            struct.pack_into("<I", value, 28, 0)
                            expected_output += value
                    m.minimum_sp = m.reg[15]
                    m.observe_start(); m.execute(symbols["_fixture_run"][0], n); m.observe_stop()
                    assert m.reg[0] == 1, (case, name, "clip call failed")
                    candidate = name.startswith("front1")
                    if old_prepared is None:
                        old_prepared = list(m.prepared)
                        assert len(old_prepared) == n - 2
                    wanted = [old_prepared[t] for t in expected_slow] if candidate else old_prepared
                    assert m.prepared == wanted, (case, name, "slow-edge preparation changed")
                    written = m.word(m.layout["written"])
                    expected = bytes(expected_output) if candidate else b""
                    assert written * 32 == len(expected), (case, name, written, len(expected))
                    assert m.bytes_at(m.layout["output"], len(expected)) == expected, (case, name, "cached packet differs")
                    traffic = old.traffic(m.memory_events, m.layout, kind=skin)
                    for key, size in (("outcodes", 128), ("output", 384 * 32)):
                        events = [e for e in m.memory_events if m.layout[key] <= e[3] < m.layout[key] + size]
                        traffic["input_regions"][key] = kernel.summarize(events)["cached"]
                    if candidate and pattern == 0:
                        for key in ("positions", "normals", "palette", "records", "colors"):
                            assert traffic["input_regions"][key]["load_instructions"] == 0, (case, name, key)
                    trace = SimpleNamespace(instruction_pcs=list(m.instruction_pcs), steps=m.steps, read=m.read)
                    case_arms[name] = dict(instructions=m.steps, traffic=traffic,
                        peak_stack_bytes=m.initial_regs[15] - m.minimum_sp,
                        prepared_triangles=len(m.prepared), emitted_cached_vertices=written,
                        prepared_sha256=hashlib.sha256(b"".join(m.prepared)).hexdigest(),
                        output_sha256=hashlib.sha256(expected).hexdigest(),
                        part_size=m.layout["part_size"], frame_size=m.layout["frame_size"],
                        **kernel.price_helpers.price(models[name], case, trace))
                rows.append(dict(case=case, vertices=n, slow_triangles=len(expected_slow),
                                 front_triangles=n - 2 - len(expected_slow), arms=case_arms))
                print("PASS", case, flush=True)
    assert frozen == {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}, "source changed; rerun"
    report = dict(status="PASS", baseline=controls.BASELINE, scope=__doc__, source_sha256=frozen,
                  profile_receipt=receipt, arms=arms, cases=rows,
                  model={name: model.metadata() for name, model in models.items()},
                  memory_controls=kernel.target_machine.memory_controls(), opcode_controls=old.opcode_controls(),
                  limitations="Actual actor clip dispatch and candidate cached RAM writes; shared clipper returns zero in every arm, so omitted clipper work is not priced and old output is not charged. Forced-front is a helper control; one-near is an eligible crossing strip. No image or console qualification, no actual chapter frequency, perfect D-cache. Full production object sizes are in target-controls receipts, not these synthetic linked fixtures.")
    (out / "actor-front-cost.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", cases=len(rows), arms=len(arms), receipt=str(out / "actor-front-cost.json"))))


if __name__ == "__main__":
    main()
