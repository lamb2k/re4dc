#!/usr/bin/env python3
"""Link complete Make-built SH4 motion objects to a synthetic sampler fixture.

No sampler body is extracted or reconstructed. Link-time section collection
retains the public entry, selected hfReg kernels, fallback and Fcc decoders.
The sampler has only a logging return edge. Full MotionMoveCore additionally
uses typed resident-key, model-lookup and unchanged matrix/angle adapters.
Their fixture costs are included and identified, not claimed as original game
math or lookup cost. No game image is built.
"""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = ROOT / "src/game/motion.cpp"
import build_profile


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    compiler = args.sh4_cxx.resolve()
    profiles, profile = build_profile.derive(output / "release-profile", compiler,
        args.kos_root.resolve(), args.sdk_root.resolve(), variants=("reg1",))
    builder = build_profile.Build(output)
    flags = profiles["reg1"]
    fixture = output / "fixture.cpp"
    fixture.write_bytes((HERE / "target_fixture.cpp.in").read_bytes())
    fixture_obj = output / "fixture.o"
    builder.run([*flags, "-fstack-usage", "-c", fixture, "-o", fixture_obj], label="fixture")
    script = output / "fixture.ld"
    script.write_text('''SECTIONS {
 /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
 . = 0x100000;
 .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) }
}
''')
    arms = {}
    source = SOURCE.read_bytes()
    for lean in (0, 1):
        name = "l" + str(lean)
        obj, elf = output / (name + ".o"), output / (name + ".elf")
        builder.run([*flags, f"-DRE4DC_ANIM_SAMPLE_LEAN={lean}", "-x", "c++", "-",
            "-c", "-fstack-usage", "-o", obj], cwd=SOURCE.parent, source=source, label=name)
        builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
            "-Wl,-T," + str(script), "-Wl,-e,_fixture_sample", "-Wl,-u,_fixture_layout", "-Wl,-u,_fixture_pose_layout", "-Wl,-u,_fixture_pose",
            obj, fixture_obj, "-lm", "-o", elf], label=name + "-link")
        (output / (name + ".disassembly.txt")).write_bytes(builder.run(
            [str(compiler).removesuffix("g++") + "objdump", "-dC", elf], label=name + "-objdump"))
        arms[name] = dict(elf=str(elf), sha256=build_profile.sha(elf), object_sha256=build_profile.sha(obj),
            sections=build_profile.sections(obj), stack_usage=build_profile.stack_usage(obj.with_suffix(".su")))
    assert SOURCE.read_bytes() == source, "runtime source changed during build"
    report = dict(status="PASS", scope=__doc__, arms=arms, profile=profile,
        source_sha256={str(path.relative_to(ROOT)): build_profile.sha(path) for path in
            (SOURCE, Path(__file__), HERE / "target_fixture.cpp.in", HERE / "build_profile.py")})
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
