#!/usr/bin/env python3
"""Build SH4 Part-construction + color-phase probes from production fragments.

Part, Frame, Lights, Records and flat_colors are the complete real definitions.
Part alpha/retained-color setup and both color/post-half loops are copied from
the source verbatim. Three unchanged directional/exact lighting calls become
explicit observed return edges. Position, selection, emit and optional Leon
debug-toggle phases are excluded. Complete production objects are independent.
The external Part observer deliberately keeps the entire constructor live and
can retain stores that production callers eliminate. These are isolated phase
prices with synthetic register allocation/alias boundaries, not call-site cost.
"""
import argparse
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_actor_fast.cpp"
import build_profile


def fragments(text):
    starts = [match.start() for match in re.finditer(re.escape("    e.colors = (p.alpha_state & 256) ? p.colors : nullptr;"), text)]
    assert len(starts) == 2, "actor part setup sites changed"
    result = {}
    for name, start in zip(("submit", "chunk"), starts):
        end = text.index("    const auto* table" if name == "submit" else "    const unsigned rs", start)
        setup = text[start:end]
        begin = text.index("        if (lights.constant) {", end)
        finish = text.index("#if RE4DC_LEON_LIGHT_TOGGLE", begin)
        phase = text[begin:finish]
        post_begin = text.index("#if RE4DC_LEON_LIGHT_HEADROOM\n        // LEON_LIGHT_HEADROOM", finish)
        post_end = text.index("        if (bake == kBakeNone)", post_begin)
        post = text[post_begin:post_end]
        for call in ("pass_lights", "chunk_lights", "pass_lights_exact"):
            before = call + "(e, lights, r, nv);"
            assert phase.count(before) == 1, (name, call, "lighting edge changed")
            phase = phase.replace(before, "fixture_light_edge(&e, &lights, &r, nv);")
        result[name] = dict(setup=setup, phase=phase, post=post)
    return result


def function(name, fragment):
    return '''extern "C" __attribute__((noinline)) unsigned fixture_run_''' + name + '''(unsigned meshlets) {
    const auto& p = fixture_part;
    auto& f = fixture_frame;
    auto& lights = fixture_lights;
    Part e{p, f, {p.projection, p.viewport},
        {0.125f, 1000.0f, 640.0f, 480.0f, project, nullptr}};
    e.clip.context = &e.projection;
    e.cache.v = fixture_vertices;
    e.cache.oc = fixture_outcodes;
    e.packet.vertices = fixture_vertices;
    e.packet.capacity = kMaxVertices;
    fixture_part_edge(&e);
''' + fragment["setup"] + '''
    const BakeUse bake = kBakeNone;
    unsigned bake_scale[3]{};
    for (unsigned mi = 0; mi < meshlets; ++mi) {
        const unsigned nv = fixture_counts[mi];
        const Records r{fixture_records, 4, 0, true};
''' + fragment["phase"] + fragment["post"] + '''
        fixture_color_edge(&e, nv);
    }
    return e.alpha;
}
'''


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.sh4_cxx.resolve()
    profiles, profile = build_profile.derive(output / "release-profile", compiler,
        args.kos_root.resolve(), args.sdk_root.resolve(), direct_values=(1,), cone_values=(0,))
    builder = build_profile.Build(output)
    source = SOURCE.read_bytes()
    (output / "native_actor_fast.cpp").write_bytes(source)
    extracts = fragments(source.decode())
    functions = "\n".join(function(name, fragment) for name, fragment in extracts.items())
    fixture = output / "target_fixture.cpp"
    fixture.write_text('#include "native_actor_fast.cpp"\n' +
        (HERE / "target_fixture.cpp.in").read_text().replace("@FUNCTIONS@", functions))
    (output / "extracted-fragments.json").write_text(json.dumps(extracts, indent=2) + "\n")
    assembly = []
    for name in ("fixture_part_edge", "fixture_color_edge", "fixture_light_edge"):
        symbol = "_" + name
        assembly += [f'.section .text.{symbol},"ax"', '.align 1', f'.global {symbol}',
            f'.type {symbol},@function', symbol + ':', 'rts', 'nop', f'.size {symbol},.-{symbol}']
    for name, value in (("re4dc_screen_wf", 0x44200000), ("re4dc_screen_hf", 0x43f00000)):
        symbol = "_" + name
        assembly += [f'.section .data.{symbol},"aw"', '.align 2', f'.global {symbol}',
            f'.type {symbol},@object', symbol + ':', f'.long {value}', f'.size {symbol},4']
    edges = output / "edges.S"
    edges.write_text("\n".join(assembly) + "\n")
    edge_object = output / "edges.o"
    prefix = str(compiler).removesuffix("g++")
    builder.run([prefix + "gcc", "-m4-single", "-ml", "-c", edges, "-o", edge_object], label="edges")
    script = output / "fixture.ld"
    script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) }
}
''')
    roots = ("fixture_layout", "fixture_prepare", "fixture_run_submit", "fixture_run_chunk")
    arms = {}
    for setup in (0, 1):
        common = profiles[f"s{setup}-d1-c0"]
        for lean in (0, 1):
            name = f"s{setup}-l{lean}"
            obj, elf = output / (name + ".o"), output / (name + ".elf")
            flags = [*common, f"-DRE4DC_ACTOR_BYTES_LEAN={lean}", "-iquote", str(SOURCE.parent)]
            builder.run([*flags, "-fstack-usage", "-c", fixture, "-o", obj], label=name)
            builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
                "-Wl,-T," + str(script), "-Wl,-e,_fixture_run_submit", *("-Wl,-u,_" + root for root in roots),
                obj, edge_object, "-lm", "-o", elf], label=name + "-link")
            (output / (name + ".disassembly.txt")).write_bytes(builder.run(
                [prefix + "objdump", "-d", "-C", elf], label=name + "-disassembly"))
            arms[name] = dict(elf=str(elf), sha256=build_profile.sha(elf), object_sha256=build_profile.sha(obj),
                sections=build_profile.sections(elf), stack_usage=build_profile.stack_usage(obj.with_suffix(".su")), flags=flags)
    assert SOURCE.read_bytes() == source, "runtime source changed during target build"
    report = dict(status="PASS", scope=__doc__, profile=profile, arms=arms,
        source_sha256={str(path.relative_to(ROOT)): build_profile.sha(path)
            for path in (SOURCE, Path(__file__), HERE / "target_fixture.cpp.in")},
        fixture_sha256=build_profile.sha(fixture), extracted_fragments_sha256=build_profile.sha(output / "extracted-fragments.json"),
        observed_edges=["fixture_part_edge", "fixture_color_edge", "fixture_light_edge"])
    (output / "target-build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    result = build(parser.parse_args())
    print(json.dumps(dict(status=result["status"], arms=list(result["arms"]))))


if __name__ == "__main__":
    main()
