#!/usr/bin/env python3
"""Compile actual actor clip reconstruction with an observed clipper edge.

The complete production actor TU, including world_of/project/Part::clip_strip,
is compiled from the current Make-derived public profile. The unchanged shared
clipper is an external stub that exposes its prepared input then returns zero;
its arithmetic and TA/device work are excluded. This isolates repeated corner
preparation and strip-parity reuse; it is not a whole renderer cost.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location("b24_actor_profile", HERE.parent / "build18/build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx = args.sh4_cxx.resolve()
    kos, sdk = args.kos_root.resolve(), args.sdk_root.resolve()
    profile.UNITS["actor"] = ("platform/native_actor_fast.o", "platform/native_actor_fast.cpp")
    flags, receipt, sources = profile.derive(out / "profile", cxx, kos, sdk,
        ["DRAW_SETUP_AUDIT=0", "ACTOR_CLIP_REUSE=0", "NMR_POOL_LOD=0"], units=("actor",))
    source = sources["actor"]
    runtime = source.read_bytes()
    (out / "native_actor_fast.cpp").write_bytes(runtime)
    fixture = out / "fixture.cpp"
    fixture.write_text('#include "native_actor_fast.cpp"\n' + (HERE / "actor_target.cpp.in").read_text())
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
    edges = out / "edges.S"
    edges.write_text('''.section .text.fixture_clip_edge,"ax"
.align 1
.global _fixture_clip_edge
.type _fixture_clip_edge,@function
_fixture_clip_edge:
 rts
 nop
.size _fixture_clip_edge,.-_fixture_clip_edge
.section .text.sq_fast_cpy,"ax"
.align 1
.global _sq_fast_cpy
.type _sq_fast_cpy,@function
_sq_fast_cpy:
 rts
 nop
.size _sq_fast_cpy,.-_sq_fast_cpy
.section .data.re4dc_screen_wf,"aw"
.align 2
.global _re4dc_screen_wf
_re4dc_screen_wf: .long 0x44200000
.global _re4dc_screen_hf
_re4dc_screen_hf: .long 0x43f00000
''')
    script = out / "fixture.ld"
    script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) }
}
''')
    builder = profile.Build(out)
    prefix = str(cxx).removesuffix("g++")
    builder.run([prefix + "gcc", "-m4-single", "-ml", "-c", edges, "-o", out / "edges.o"], label="edges")
    common = [x for x in flags["actor"] if not x.startswith("-DRE4DC_ACTOR_CLIP_REUSE=")]
    builder.run([*common, "-I" + str(DC / "room"), "-c", stub, "-o", out / "clip_edge.o"], label="clip-edge")
    arms = {}
    for value in (0, 1):
        name = f"reuse{value}"
        obj, elf = out / (name + ".o"), out / (name + ".elf")
        command = [*common, f"-DRE4DC_ACTOR_CLIP_REUSE={value}", "-iquote", str(source.parent),
                   "-fstack-usage", "-c", fixture, "-o", obj]
        builder.run(command, label=name)
        builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
            "-Wl,-T," + str(script), "-Wl,-e,_fixture_run", "-Wl,-u,_fixture_prepare", "-Wl,-u,_fixture_layout",
            obj, out / "clip_edge.o", out / "edges.o", "-lm", "-o", elf], label=name + "-link")
        (out / (name + ".disassembly.txt")).write_bytes(builder.run(
            [prefix + "objdump", "-d", "-C", elf], label=name + "-disassembly"))
        arms[name] = dict(elf=str(elf), sha256=profile.sha(elf),
            sections=profile.sections(elf), stack_usage=profile.stack_usage(obj.with_suffix(".su")),
            command=[str(value) for value in command])
    assert source.read_bytes() == runtime
    result = dict(status="PASS", scope=__doc__, profile=receipt, arms=arms,
        source_sha256={str(p.relative_to(ROOT)): profile.sha(p) for p in
            (source, source.parent / "include/actor_clip_reuse.hpp", Path(__file__), HERE / "actor_target.cpp.in")})
    (out / "actor-target-build.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", arms=list(arms), receipt=str(out / "actor-target-build.json"))))


if __name__ == "__main__":
    main()
