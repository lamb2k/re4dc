#!/usr/bin/env python3
"""Build compiled SH4 actor fixed-setup fixtures using complete real layouts.

native_actor_fast.cpp is included verbatim. AVK kernel entries are explicit
observed return stubs; their unchanged transformation/lighting/packing costs
are excluded. Ready palette tables avoid FTRV execution in this scalar runner.
Full production objects and identity are checked independently.
"""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_actor_fast.cpp"
import build_profile

KERNELS = tuple("re4dc_avk_" + name for name in (
    "pos_skin_s16", "pos_skin_u16", "pos_rigid_s16", "pos_rigid_u16",
    "pos_rigid6_s16", "pos_rigid6_u16", "light_skin", "light_rigid", "light_rigid3",
    "light_skin_n16", "light_rigid_n16", "light_rigid_n16s6"))
EDGES = ("fixture_part_edge", "fixture_lights_edge")
RETURN_ZERO = ("re4dc_actor_model_id",)
TRAPS = ("mat_load", "mat_store", "re4dc_log", "re4dc_missing")


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.sh4_cxx.resolve()
    profiles, profile = build_profile.derive(output / "release-profile", compiler,
        args.kos_root.resolve(), args.sdk_root.resolve(), direct_values=(1,), cone_values=(0,))
    builder = build_profile.Build(output)
    source = SOURCE.read_bytes()
    source_path = output / "native_actor_fast.cpp"
    source_path.write_bytes(source)
    fixture = output / "target_fixture.cpp"
    fixture.write_text('#include "native_actor_fast.cpp"\n' + (HERE / "target_fixture.cpp.in").read_text())
    inputs = {str(SOURCE.relative_to(ROOT)): build_profile.sha(SOURCE),
              str((HERE / "target_fixture.cpp.in").relative_to(ROOT)): build_profile.sha(HERE / "target_fixture.cpp.in")}
    assembly = []
    for name in KERNELS + EDGES + RETURN_ZERO + TRAPS:
        symbol = "_" + name
        assembly += [f'.section .text.{symbol},"ax"', '.align 1', f'.global {symbol}',
                     f'.type {symbol},@function', symbol + ':']
        assembly += ['trapa #255'] if name in TRAPS else (['mov #0,r0'] if name in RETURN_ZERO else []) + ['rts', 'nop']
        assembly += [f'.size {symbol},.-{symbol}']
    for name, value in (("re4dc_screen_wf", 0x44200000), ("re4dc_screen_hf", 0x43f00000)):
        symbol = "_" + name
        assembly += [f'.section .data.{symbol},"aw"', '.align 2', f'.global {symbol}',
                     f'.type {symbol},@object', symbol + ':', f'.long {value}', f'.size {symbol},4']
    stubs = output / "edges.S"
    stubs.write_text('\n'.join(assembly) + '\n')
    stub_object = output / "edges.o"
    builder.run([str(compiler).removesuffix("g++") + "gcc", "-m4-single", "-ml", "-c", stubs,
                 "-o", stub_object], label="edges")
    script = output / "fixture.ld"
    script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) }
 .bss : { *(.bss*) *(COMMON) }
}
''')
    roots = ("fixture_layout", "fixture_prepare", "fixture_prepare_lights", "fixture_run", "fixture_reset_lights",
             "fixture_constant_lights", "fixture_palette_hit", "fixture_prime")
    common = [word for word in profiles["d1-c0"] if not word.startswith("-DRE4DC_ACTOR_SETUP_LEAN=")]
    arms = {}
    for lean in args.lean_values:
        name = f"l{lean}"
        obj = output / (name + ".o")
        flags = [*common, f"-DRE4DC_ACTOR_SETUP_LEAN={lean}", "-iquote", str(SOURCE.parent)]
        builder.run([*flags, "-fstack-usage", "-c", fixture, "-o", obj], label=name)
        elf = output / (name + ".elf")
        builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
            "-Wl,-T," + str(script), "-Wl,-e,_fixture_run", *("-Wl,-u,_" + root for root in roots),
            obj, stub_object, "-lm", "-o", elf], label=name + "-link")
        prefix = str(compiler).removesuffix("g++")
        (output / (name + ".disassembly.txt")).write_bytes(builder.run(
            [prefix + "objdump", "-d", "-C", elf], label=name + "-disassembly"))
        arms[name] = dict(elf=str(elf), sha256=build_profile.sha(elf),
            object_sha256=build_profile.sha(obj), sections=build_profile.sections(elf),
            stack_usage=build_profile.stack_usage(obj.with_suffix(".su")), flags=flags)
    for path, digest in inputs.items():
        assert build_profile.sha(ROOT / path) == digest, (path, "changed during target build")
    result = dict(status="PASS", scope=__doc__,
        base="28da09802ed9ff6756529bab02978230983453be", profile=profile,
        source_sha256=inputs, observed_kernel_edges=KERNELS, observed_edges=EDGES + RETURN_ZERO,
        forbidden_edges=TRAPS, arms=arms)
    (output / "target-build-controls.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--lean-values", nargs="+", type=int, choices=(0, 1), default=(0, 1))
    result = build(parser.parse_args())
    print(json.dumps(dict(status=result["status"], arms=list(result["arms"]))))


if __name__ == "__main__":
    main()
