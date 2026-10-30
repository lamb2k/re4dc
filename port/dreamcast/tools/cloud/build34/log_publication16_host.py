#!/usr/bin/env python3
"""EF16 actual-source publication/refusal and coherent copied fault evidence.

Host schedules/objects only. No IRQ timing, raw-RAM/cache, NMI, SDK or hardware
acceptance. Old corruption controls and reader/memory judge are not altered.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASE = "115c6105369f777e5cf883f5b6d69aeab264f1ad"
MEM = DC / "game/platform/mem.cpp"
FAULT = DC / "game/platform/fault.cpp"
INCLUDE = DC / "game/platform/include"
spec = importlib.util.spec_from_file_location("record", HERE / "log_record16_host.py")
record = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record)


def run(command, output, label, **kwargs):
    return record.run(command, output, label, **kwargs)


def fixture(kos):
    mem, fault = MEM.read_text(), FAULT.read_text()
    device = (kos / "kernel/debug/dbgio.c").read_text()
    source = (HERE / "log_publication16_fixture.cpp.in").read_text()
    blocks = {"CRASH": record.extract.function(mem, "static void logCrashAppend16("),
              "PUBLISHER": (INCLUDE / "source_log_publication16.inc").read_text(),
              "RAW": record.extract.function(mem, "void re4dc_log_raw("),
              "LOG": record.extract.function(mem, "void re4dc_log("),
              "CALLBACK": record.extract.function(fault, "static int ringWriteBuffer("),
              "DEVICEWRITE": record.extract.function(device, "int dbgio_write_buffer("),
              "DEVICEXLAT": record.extract.function(device, "int dbgio_write_buffer_xlat("),
              "DEVICESTR": record.extract.function(device, "int dbgio_write_str("),
              "DEVICEPRINTF": record.extract.function(device, "int dbgio_printf("),
              "FAULT": record.extract.function(fault, "static void logFaultRecord16("),
              "HALT": record.extract.function(fault, "static void logHaltRecord16(")}
    for name, signature in (("FAULTENTRY", "static void onFault("), ("HALTENTRY", 'void re4dc_halt(')):
        handler = record.extract.function(fault, signature)
        handler, parks = re.subn(r"for\s*\(;;\)\s*\{\s*\}", "throw Park{};", handler)
        assert parks == 1
        if name == "FAULTENTRY":
            for address, value, expected in (("0xff000024", "test_expevt", 2), ("0xff00000c", "test_tea", 2)):
                handler, count = re.subn(r"\*\(volatile unsigned long\*\)\s*" + address, value, handler)
                assert count == expected
        else:
            handler = handler.replace("{", "{ ++halt_calls;", 1)
        blocks[name] = handler
    for name, body in blocks.items():
        source = source.replace("@" + name + "@", body)
    assert "@PUBLISHER@" not in source
    return source


def make_checks(output):
    kos = output / "make-stub"
    kos.mkdir(); (kos / "Makefile.rules").write_text("")
    targets = ["obj/platform/mem.o", "obj/platform/fault.o", "obj/platform/crash_screen.o", "obj/platform/native_actor_fast.o"]
    base = ["make", "--no-print-directory", "-f", "Makefile", "-n", "KOS_BASE=" + str(kos),
            *targets, "LOG_ATOMIC16=1"]
    commands = []
    for value in (None, "0", "1"):
        result = run(base + ([] if value is None else ["LOG_PUBLICATION16=" + value]), output,
                     "make-" + str(value), cwd=DC / "game")
        commands.append([line for line in result.stdout.decode().splitlines() if line.startswith("kos-c++")])
    assert commands[0] == commands[1]
    assert len(commands[2]) == len(targets), commands[2]
    for index, command in enumerate(commands[2]):
        assert command.count("-DRE4DC_LOG_PUBLICATION16=1") == int(index < 2), command
    rejected = {}
    for i, value in enumerate(("", "0 1", "2", "-1", "%", "0%", "1%", "1 ", "0 ")):
        result = run(base + ["LOG_PUBLICATION16=" + value], output, "make-invalid-" + str(i),
                     cwd=DC / "game", success=False)
        assert result.returncode and b"LOG_PUBLICATION16" in result.stderr
        rejected[value] = result.returncode
    # A recursively expanded value, including trailing whitespace, must be exact.
    for i, value in enumerate(("1 ", "0 ", "1 0", "")):
        result = run(base + ["EF16_VALUE=" + value, "LOG_PUBLICATION16=$(EF16_VALUE)"], output,
                     "make-expanded-invalid-" + str(i), cwd=DC / "game", success=False)
        assert result.returncode and b"LOG_PUBLICATION16" in result.stderr
    for name, value in (("LOG_ATOMIC16", "0"), ("OT_WALK_CHECK", "1")):
        result = run(base + ["LOG_PUBLICATION16=1", name + "=" + value], output,
                     "make-dependency-" + name, cwd=DC / "game", success=False)
        assert result.returncode and ("requires " + name).encode() in result.stderr
    leading = run(base + ["LOG_PUBLICATION16= 1"], output, "make-leading", cwd=DC / "game")
    assert [line for line in leading.stdout.decode().splitlines() if line.startswith("kos-c++")] == commands[2]
    for value, expected in (("0", commands[1]), ("1", commands[2])):
        expanded = run(base + ["EF16_VALUE=" + value, "LOG_PUBLICATION16=$(EF16_VALUE)"], output,
                       "make-expanded-" + value, cwd=DC / "game")
        assert [line for line in expanded.stdout.decode().splitlines() if line.startswith("kos-c++")] == expected
    return dict(default_explicit_zero_identical=True, mem_fault_only=True, invalid=rejected,
                expanded_values=True, dependencies=True)


def off_checks(output):
    # Reuse the established declaration-only KOS substitutes. Its RECORD16
    # checks remain intact; the separate matrix below compares PUBLICATION16.
    record.BASE = BASE
    record.off_checks(output)
    constants = {"SOUND_REGION_BYTES": "0x80000", "CORE_RESIDENT_BYTES": "0x234000",
                 "OPTION_RESIDENT_BYTES": "0x40000", "PLAYER_RESIDENT_BYTES": "0x118000",
                 "WEAPON_RESIDENT_BYTES": "0x70000", "ARENA_KOS_BYTES": "0"}
    flags = ["-std=c++20", "-O2", "-g0", "-ffunction-sections", "-fdata-sections", "-D__sh__=1",
             "-I" + str(output / "kos-declarations"), "-I" + str(INCLUDE), "-I" + str(MEM.parent)]
    flags += ["-DRE4DC_" + name + "=" + value for name, value in constants.items()]
    rows = []
    profiles = [(0, 0, 0, 0, 0), (1, 0, 0, 0, 0), (1, 1, 1, 3, 0),
                (1, 0, 0, 0, 1), (1, 1, 1, 3, 1)]
    for atomic, old, header, crash, record16 in profiles:
        profile = f"publication-off-atomic{atomic}-old{old}-header{header}-crash{crash}-record{record16}"
        defines = [f"-DRE4DC_LOG_ATOMIC16={atomic}", f"-DRE4DC_LOG_ATOMIC={old}",
                   f"-DRE4DC_LOG_RING_HDR={header}", f"-DRE4DC_LOG_CRASH_TEST={crash}",
                   f"-DRE4DC_LOG_RECORD16={record16}"]
        for original in (MEM, FAULT):
            baseline = output / "baseline" / original.name
            pp, objects = [], []
            for arm, path, extra in (("baseline", baseline, []), ("absent", original, []),
                                     ("zero", original, ["-DRE4DC_LOG_PUBLICATION16=0"])):
                label = profile + "-" + original.stem + "-" + arm
                pp.append(run(["g++", *flags, *defines, *extra, "-E", "-P", str(path)], output, label + "-pp").stdout)
                obj = output / (label + ".o")
                run(["g++", *flags, *defines, *extra, "-c", str(path), "-o", str(obj)], output, label + "-object")
                objects.append(obj.read_bytes())
            assert pp[0] == pp[1] == pp[2] and objects[0] == objects[1] == objects[2], label
            rows.append(dict(profile=profile, source=original.name, preprocessed_bytes=len(pp[0]),
                             host_object_bytes=len(objects[0]), host_object_sha256=hashlib.sha256(objects[0]).hexdigest()))
        if atomic:
            for original in (MEM, FAULT):
                name = profile + "-enabled-" + original.stem
                run(["g++", *flags, *defines, "-DRE4DC_LOG_PUBLICATION16=1", "-c", str(original),
                     "-o", str(output / (name + ".o"))], output, name)
    # Complete enabled fault TU, preserving optional crash-screen/VMU hooks.
    common = ["-std=c++20", "-O2", "-g0", "-fpermissive", "-D__sh__=1",
              "-I" + str(output / "kos-declarations"), "-I" + str(INCLUDE),
              "-DRE4DC_LOG_PUBLICATION16=1", "-DRE4DC_LOG_ATOMIC16=1"]
    for hooks in (0, 1):
        hook_flags = [f"-DRE4DC_CRASH_SCREEN={hooks}", f"-DRE4DC_CRASH_FAULT_DETAIL={hooks}",
                      f"-DRE4DC_VMU_DEBUG_SLOT={hooks}"]
        run(["g++", *common, *hook_flags, "-c", str(FAULT), "-o", str(output / f"enabled-fault-hooks{hooks}.o")],
            output, f"enabled-fault-hooks{hooks}")
    bad = run(["g++", *common, "-DRE4DC_OT_WALK_CHECK=1", "-E", "-P", str(FAULT)], output,
              "source-ot-exclusion", success=False)
    assert bad.returncode and b"LOG_PUBLICATION16 requires OT_WALK_CHECK=0" in bad.stderr
    for original in (MEM, FAULT):
        bad = run(["g++", *flags, "-DRE4DC_LOG_PUBLICATION16=1", "-DRE4DC_LOG_ATOMIC16=0", "-E", "-P", str(original)],
                  output, "source-atomic-dependency-" + original.stem, success=False)
        assert bad.returncode and b"LOG_PUBLICATION16 requires LOG_ATOMIC16" in bad.stderr
    return rows


def latch_fixture(output):
    source = (INCLUDE / "log_publication16.hpp").read_text()
    # Instrument a local copy only. The assignment is expanded into equivalent
    # forward object-representation stores to force interruption at every copy
    # byte, plus claim and ready publication edges. Production is unmodified.
    replacements = {
        "if (!slot.claimed.test_and_set(std::memory_order_acquire)) {":
            "latch_edge(); if (!slot.claimed.test_and_set(std::memory_order_acquire)) { latch_edge();",
        "slot.evidence = source;":
            "for (unsigned i = 0; i < sizeof(Evidence); ++i) { reinterpret_cast<unsigned char*>(&slot.evidence)[i] = reinterpret_cast<const unsigned char*>(&source)[i]; latch_edge(); } latch_edge();",
        "slot.ready.store(true, std::memory_order_release);":
            "slot.ready.store(true, std::memory_order_release); latch_edge();",
    }
    for old, new in replacements.items():
        assert source.count(old) == 1
        source = source.replace(old, new)
    (output / "instrumented_log_publication16.hpp").write_text(source)
    return (HERE / "log_publication16_latch.cpp.in").read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--kos", required=True, type=Path, help="selected installed KOS source, read only")
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    cpp = output / "fixture.cpp"; cpp.write_text(fixture(args.kos))
    latch = output / "latch.cpp"; latch.write_text(latch_fixture(output))
    common = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + str(INCLUDE)]
    if args.sanitize:
        common[1:2] = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-no-pie"]
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0", UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    rows = []
    compositions = [(size, record16, 0, header) for size in (8192, 65536) for record16 in (0, 1) for header in (0, 1)]
    compositions += [(65536, record16, 3, 1) for record16 in (0, 1)]
    for size, record16, crash, header in compositions:
        name = f"ring{size}-record{record16}-crash{crash}-header{header}"
        binary = output / name
        command = ["g++", *common, "-Wno-unused-function", f"-DTEST_RING_SIZE={size}",
                   f"-DRE4DC_LOG_CRASH_TEST={crash}", f"-DRE4DC_LOG_RING_HDR={header}", "-DRE4DC_LOG_PUBLICATION16=1",
                   "-DRE4DC_CRASH_SCREEN=1", "-DRE4DC_CRASH_FAULT_DETAIL=1", "-DRE4DC_VMU_DEBUG_SLOT=1",
                   "-DRE4DC_LOG_ATOMIC16=1", f"-DRE4DC_LOG_RECORD16={record16}", str(cpp), "-o", str(binary)]
        run(command, output, name + "-compile")
        rows.append(json.loads(run([str(binary)], output, name + "-run", env=env).stdout))
    run(["g++", *common, str(latch), "-o", str(output / "latch")], output, "latch-compile")
    latch_result = json.loads(run([str(output / "latch")], output, "latch-run", env=env).stdout)
    receipt = dict(status="PASS_SCOPED_PUBLICATION_OR_EXPLICIT_REFUSAL", baseline=BASE,
                   sanitized=args.sanitize, rows=rows, latch=latch_result,
                   excluded_external_printf_false_success_witness=True,
                   external_device_source={str(args.kos / "kernel/debug/dbgio.c"):
                                           hashlib.sha256((args.kos / "kernel/debug/dbgio.c").read_bytes()).hexdigest()},
                   make=make_checks(output), off=off_checks(output),
                   source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in (MEM, FAULT, INCLUDE / "log_publication16.hpp",
                                               INCLUDE / "source_log_publication16.inc", DC / "game/game30.mk", Path(__file__),
                                               HERE / "log_publication16_fixture.cpp.in", HERE / "log_publication16_latch.cpp.in",
                                               HERE / "log_publication16_authority.py", HERE / "log_publication16.md")},
                   limits=["host schedules only; selected KOS soft-gUSA rollback is a target dependency",
                           "255-byte store bound is not IRQ timing or a bound on caller-disabled duration",
                           "external KOS dbgio_printf formats before callback and ignores device refusal",
                           "retained crash-screen snprintf/show run after captured evidence; external formatter completion is unqualified",
                           "legacy void log entry points expose refusal only in fixed sticky state",
                           "two immutable copied terminal slots; unfinished/lost explicitly represented",
                           "ring reader/cache/memory judge and old corrupt controls unchanged",
                           "no target programme, SDK, runtime, NMI or hardware acceptance"])
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in ("status", "sanitized", "rows", "latch", "make")}
                     | {"off_profiles": len(receipt["off"]), "receipt": str(output / "receipt.json")}))


if __name__ == "__main__":
    main()
