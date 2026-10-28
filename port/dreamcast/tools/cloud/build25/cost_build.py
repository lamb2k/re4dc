#!/usr/bin/env python3
"""Build actual old-exact/new-flat actor light fixtures with public Make flags.

The production actor TU is compiled unchanged in each arm. One adapter creates
synthetic source records and calls its real light fold and pass. Rendering,
transform, submit and device functions are discarded by the fixture link.
The exact arm uses the deployed ACTOR_EXACT_FAST=1 pass. Every input point is
exactly one unit from its lights so the existing interpreter's qualified
FSRRA(1) operation is sufficient; general hardware reciprocal bits are untested.
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
spec = importlib.util.spec_from_file_location("b25_cost_controls", HERE / "build_controls.py")
controls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controls
spec.loader.exec_module(controls)
profile = controls.profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    source = DC / "game/platform/native_actor_fast.cpp"
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in
              (source, HERE / "cost_fixture.cpp.in", HERE / "cost_identity.cpp.in", Path(__file__), HERE / "build_controls.py",
               DC / "room/source_lighting.cpp", DC / "game/Makefile",
               DC / "game/platform/include/actor_light_fast_only.h",
               DC / "game/platform/include/actor_light_fast_only.inc",
               DC / "game/platform/native_actor_chunk.inc")}
    prefix = str(cxx).removesuffix("g++")
    arms = {}
    for value in (0, 1):
        name = "fast" if value else "exact"
        destination = out / name
        destination.mkdir()
        options = controls.QA + [f"ACTOR_LIGHT_FAST_ONLY={value}", "ACTOR_LIGHT_CAP=0", "QA_LINK=0", "DRAW_SETUP_AUDIT=0",
                                 "ACTOR_EXACT_FAST=1", "ACTOR_PROBE_LIGHT=1", "GANADO_LIT=0", "ACTOR_PROBE_LIGHT_LOG=0"]
        flags, receipt, _ = profile.derive(destination / "profile", cxx, kos, sdk, options,
                                          units=("native_actor_fast",))
        command = flags["native_actor_fast"]
        assert ("-DRE4DC_ACTOR_LIGHT_FAST_ONLY=1" in command) == bool(value), "Make lost enabled control"
        builder = profile.Build(destination)
        # Identical path spelling and original include resolution in both arms.
        fixture = destination / "fixture.cpp"
        fixture.write_text('#include "' + str(source) + '"\n' + (HERE / "cost_fixture.cpp.in").read_text())
        obj, elf = destination / "fixture.o", destination / "fixture.elf"
        builder.run([*command, "-fstack-usage", "-c", fixture, "-o", obj], label="fixture")
        lighting = destination / "source_lighting.o"
        builder.run([*command, "-fstack-usage", "-c", DC / "room/source_lighting.cpp", "-o", lighting], label="reference-light")
        identity_source = destination / "identity.cpp"
        identity_source.write_bytes((HERE / "cost_identity.cpp.in").read_bytes())
        identity = destination / "identity.o"
        builder.run([*command, "-fstack-usage", "-c", identity_source, "-o", identity], label="identity")
        script = destination / "fixture.ld"
        script.write_text("SECTIONS { /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }\n"
                          ". = 0x100000; .text : { *(.text*) } .rodata : { *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }\n")
        roots = ("fixture_prepare", "fixture_fold", "fixture_pass", "fixture_layout", "fixture_read_stats", "fixture_stats")
        builder.run([cxx, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections", "-Wl,-T," + str(script),
                     "-Wl,-e,_fixture_fold", *["-Wl,-u,_" + root for root in roots], obj, lighting, identity,
                     "-lm", "-o", elf], label="link")
        (destination / "disassembly.txt").write_bytes(builder.run([prefix + "objdump", "-d", "-C", elf], label="disassembly"))
        arms[name] = dict(elf=str(elf), sha256=profile.sha(elf), sections=profile.sections(elf),
                          stack_usage=profile.stack_usage(obj.with_suffix(".su")), profile=receipt,
                          validation_overrides=options)
        print("PASS built", name, flush=True)
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, "source changed during build"
    report = dict(status="PASS", scope=__doc__, baseline=controls.BASELINE, arms=arms, source_sha256=frozen,
                  limitations="Synthetic fixture linker only; no production linker changes, game assets, full game or device execution. Exact arm uses ACTOR_EXACT_FAST=1 at unit light distance. Both arms use public fallback ACTOR_PROBE_LIGHT=1 with synthetic non-Ganado identity0x40; probe2 requires a private PS2_GANADO_DIR, which is not invented here. Separately compiled identity stub instructions are included, actual model_bridge lookup cost is unpriced. Timing is a bounded address/instruction fixture and not a recorded game frame.")
    (out / "cost-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", receipt=str(out / "cost-build.json"))))


if __name__ == "__main__":
    main()
