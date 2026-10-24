#!/usr/bin/env python3
"""Compile the real world TU and an isolated setup/selection target fixture.

This is a compiler/object gate, not a whole-game link or a Dreamcast run. The
optional fixture includes native_static.cpp; its selected entry points are
linked with the actual group_visible implementation and compiler libraries.
"""
import argparse
import hashlib
import json
import shlex
import struct
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import release_profile

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_static.cpp"
BASELINE = "8c7226467dba68ac8ee16652accc10f683562685"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flags(compiler, kos, sdk):
    # Same complete-TU profile as the retained PR56 world qualification. Use
    # the production -Os profile; function-specific optimization attributes
    # in native_static.cpp remain effective.
    values = ["-std=gnu++20", "-Wall", "-Wextra", "-Os", "-fno-PIC", "-fno-PIE",
              "-fomit-frame-pointer", "-m4-single", "-ml", "-mfsrra", "-mfsca",
              "-ffunction-sections", "-fdata-sections", "-matomic-model=soft-gusa",
              "-ftls-model=local-exec", "-fno-exceptions", "-fno-unwind-tables",
              "-fno-asynchronous-unwind-tables", "-fno-threadsafe-statics",
              "-D__DREAMCAST__", "-D_arch_dreamcast=1", "-D_arch_sub_pristine=1",
              "-DRE4DC_GAME"]
    for path in (kos / "include", kos / "kernel/arch/dreamcast/include", kos / "addons/include"):
        values += ["-isystem", str(path)]
    values += ["-I" + str(DC / "game/platform/include"), "-I" + str(sdk / "include")]
    macros = dict(NATIVE_STATIC=1, NATIVE_MESH=1, D349_RENDERER_STACK=1,
                  PS2_WORLD_DRAW=1, PS2_WORLD_MESH=1, PS2_WORLD_ROOMS=1,
                  MESH_LOD=1, MESH_FASTPATH=1, MESH_DIRECT=1, PS2_WORLD_LEAN=23,
                  PS2_STRIP_GROUPS=1, MESH_PRIME_LAZY=1, MESH_VP_SCHED=1,
                  MESH_STRIP_LEAN=1, HW_LEAN=1, SCENERY_CHUNK=1, SG_SELECT_LEAN=1,
                  SCENERY_UNIT_CONCAT=1, SCENERY_SCREEN_MEMO=1, SCENERY_FAR_LOD=4,
                  PS2_VERTEX_ALPHA=1, PS2_WORLD_NONEMPTY_LOD=1,
                  SCENERY_CONE_SIGN=1, CPU_BACKFACE=0, GAME_SH4ZAM=1, TA_DIRECT=1)
    return [str(compiler), *values, *("-DRE4DC_%s=%s" % item for item in macros.items())]


def sections(path):
    data = path.read_bytes()
    assert data[:6] == b"\x7fELF\x01\x01", path
    offset = struct.unpack_from("<I", data, 32)[0]
    size, count = struct.unpack_from("<HH", data, 46)
    rows = [struct.unpack_from("<10I", data, offset + i * size) for i in range(count)]
    return dict(executable_bytes=sum(row[5] for row in rows if row[2] & 4),
                allocated_bytes=sum(row[5] for row in rows if row[2] & 2),
                zero_fill_bytes=sum(row[5] for row in rows if row[1] == 8 and row[2] & 2))


def stack_usage(path):
    result = []
    if path.exists():
        for line in path.read_text().splitlines():
            function, count, kind = line.rsplit("\t", 2)
            result.append(dict(function=function, bytes=int(count), kind=kind))
    return result


class Build:
    def __init__(self, output):
        self.output = output
        self.commands = []

    def run(self, args, *, cwd=ROOT, source=None, label="build"):
        args = [str(value) for value in args]
        self.commands.append(dict(argv=args, cwd=str(cwd), stdin=source is not None))
        result = subprocess.run(args, cwd=cwd, input=source, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        with (self.output / (label + ".log")).open("ab") as target:
            target.write(("$ " + shlex.join(args) + "\n").encode())
            target.write(result.stdout)
        (self.output / "build-commands.json").write_text(json.dumps(self.commands, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError("command failed; see " + str(self.output / (label + ".log")))
        return result.stdout


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    builder = Build(output)
    compiler = args.sh4_cxx.resolve()
    if args.minimal_profile:
        common = flags(compiler, args.kos_root.resolve(), args.sdk_root.resolve())
        profile = dict(scope="Reduced selection compiler profile, not the release world configuration")
    else:
        common, profile = release_profile.derive(output / "release-profile", compiler,
                                                args.kos_root.resolve(), args.sdk_root.resolve())
    common += ["-D" + macro for macro in args.define]
    production = {}
    current = SOURCE.read_bytes()
    (output / "native_static.cpp").write_bytes(current)
    source_hashes = {str(SOURCE.relative_to(ROOT)): hashlib.sha256(current).hexdigest()}
    for include in sorted((SOURCE.parent / "include").glob("scenery_*.inc")):
        source_hashes[str(include.relative_to(ROOT))] = sha(include)
    if not args.skip_production:
        old = subprocess.check_output(["git", "show", args.baseline + ":" + str(SOURCE.relative_to(ROOT))], cwd=ROOT)
        (output / "baseline-native_static.cpp").write_bytes(old)
        for name, source, knob in (("baseline", old, None), ("absent", current, None),
                                   ("zero", current, 0), ("on", current, 1)):
            extra = [] if knob is None else ["-DRE4DC_SCENERY_SELECT_ONLY=" + str(knob)]
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                path = output / (name + "." + suffix)
                builder.run([*common, *extra, "-x", "c++", "-", *phase, "-o", path],
                            cwd=SOURCE.parent, source=source, label=name)
                production[name + "." + suffix] = dict(bytes=path.stat().st_size, sha256=sha(path))
                if suffix == "o":
                    production[name + ".o"].update(sections(path))
                    production[name + ".o"]["stack_usage"] = stack_usage(path.with_suffix(".su"))
        for suffix in ("ii", "o"):
            baseline = (output / ("baseline." + suffix)).read_bytes()
            for name in ("absent", "zero"):
                assert (output / (name + "." + suffix)).read_bytes() == baseline, (name, suffix, "OFF identity")
    fixture_result = None
    if args.fixture:
        fixture = args.fixture.resolve()
        fixture_copy = output / "selection_fixture.cpp"
        fixture_copy.write_bytes(fixture.read_bytes())
        source_hashes[str(fixture)] = sha(fixture)
        obj = output / "selection_fixture.o"
        builder.run([*common, "-DRE4DC_SCENERY_SELECT_ONLY=1", "-fstack-usage", "-MMD", "-MF",
                     output / "fixture.d", "-c", fixture, "-o", obj], label="fixture")
        dependencies = (output / "fixture.d").read_text().replace("\\\n", " ").split(":", 1)[1]
        for word in shlex.split(dependencies):
            dependency = Path(word)
            if not dependency.is_absolute():
                dependency = ROOT / dependency
            if dependency.is_file() and dependency.is_relative_to(ROOT):
                source_hashes[str(dependency.relative_to(ROOT))] = sha(dependency)
        geometry = output / "pvr_geometry.o"
        builder.run([*common, "-O3", "-fno-predictive-commoning", "-c", DC / "room/pvr_geometry.cpp", "-o", geometry], label="geometry")
        # The fixture explicitly adopts synthetic package data and initializes
        # its inputs. Uncalled game global constructors/destructors would retain
        # unrelated filesystem/renderer code; they are not executed by this
        # bare entry point. Discard only those registration sections.
        linker = output / "fixture.ld"
        linker.write_text("""SECTIONS {
  /DISCARD/ : { *(.ctors*) *(.dtors*) *(.init_array*) *(.fini_array*) }
  . = 0x100000;
  .text : { *(.text*) }
  .rodata : { *(.rodata*) }
  .data : { *(.data*) }
  .bss : { *(.bss*) *(COMMON) }
}
""")
        elf = output / "selection.elf"
        roots = list(dict.fromkeys([args.entry, *args.keep_symbol]))
        builder.run([compiler, "-m4-single", "-ml", "-nostartfiles", "-Wl,--gc-sections",
                     "-Wl,-T," + str(linker), "-Wl,-e," + args.entry,
                     *("-Wl,-u," + root for root in roots), obj, geometry, "-lm", "-o", elf], label="link")
        fixture_result = dict(elf=str(elf), sha256=sha(elf), **sections(elf),
                              stack_usage=stack_usage(obj.with_suffix(".su")), roots=roots)
        tool_prefix = str(compiler).removesuffix("g++")
        (output / "selection.disassembly.txt").write_bytes(builder.run([tool_prefix + "objdump", "-d", "-C", elf], label="objdump"))
        (output / "selection.symbols.txt").write_bytes(builder.run([tool_prefix + "nm", "-n", "-C", elf], label="nm"))
    report = dict(status="PASS", baseline=args.baseline,
                  scope="Complete production TU compilation/OFF identity and optional isolated SH4 fixture link; no game execution or timing",
                  compiler=builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0],
                  flags=common[1:], profile=profile, source_sha256=source_hashes,
                  production=production, fixture=fixture_result)
    for name, expected in source_hashes.items():
        assert sha(ROOT / name) == expected, (name, "source changed during build")
    (output / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--define", action="append", default=[])
    parser.add_argument("--skip-production", action="store_true")
    parser.add_argument("--minimal-profile", action="store_true")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--entry", default="_fixture_select_full")
    parser.add_argument("--keep-symbol", action="append", default=["_fixture_select_light", "_fixture_adopt", "_fixture_configure", "_fixture_reset", "_fixture_snapshot", "_fixture_layout"])
    report = build(parser.parse_args())
    print(json.dumps({"status": report["status"], "fixture": report["fixture"] and report["fixture"]["elf"]}))


if __name__ == "__main__":
    main()
