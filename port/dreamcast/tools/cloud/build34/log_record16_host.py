#!/usr/bin/env python3
"""Actual-source bounded engine records; raw compatibility and OFF controls.

Coherent synthetic scheduling and host code generation only. Byte-work counts
are not target IRQ latency, NMI safety, raw RAM/cache visibility or memory PASS.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASE = "d45eb759dd92685255929625e04fae3d7a46bca7"
spec = importlib.util.spec_from_file_location("extract", DC / "tools/d367/world_submit_spike/check_runtime.py")
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)
MEM = DC / "game/platform/mem.cpp"
FAULT = DC / "game/platform/fault.cpp"
INCLUDE = DC / "game/platform/include"


def run(command, output, label, *, cwd=ROOT, env=None, success=True):
    result = subprocess.run(command, cwd=cwd, capture_output=True, env=env)
    (output / (label + ".log")).write_bytes(result.stdout + result.stderr)
    if success and result.returncode:
        raise RuntimeError(label + ": " + result.stderr.decode(errors="replace"))
    return result


def fixture():
    mem, fault = MEM.read_text(), FAULT.read_text()
    source = (HERE / "log_record16_fixture.cpp.in").read_text()
    for marker, body in {
        "CRASH": extract.function(mem, "static void logCrashAppend16("),
        "RAW": extract.function(mem, "void re4dc_log_raw("),
        "CALLBACK": extract.function(fault, "static int ringWriteBuffer("),
        "RECORD": extract.function(mem, "static void logAppendRecord16("),
        "APPEND": extract.function(mem, "static void logAppend("),
        "LOG": extract.function(mem, "void re4dc_log("),
    }.items():
        source = source.replace("@" + marker + "@", body)
    return source


def make_checks(output):
    kos = output / "kos-make-stub"
    kos.mkdir()
    (kos / "Makefile.rules").write_text("")
    targets = ["obj/platform/mem.o", "obj/platform/fault.o", "obj/platform/crash_screen.o"]
    base = ["make", "--no-print-directory", "-f", "Makefile", "-n", "KOS_BASE=" + str(kos),
            *targets, "LOG_ATOMIC16=1"]
    commands = []
    for value in (None, "0", "1"):
        result = run(base + ([] if value is None else ["LOG_RECORD16=" + value]), output,
                     "make-" + str(value), cwd=DC / "game")
        commands.append([line for line in result.stdout.decode().splitlines() if line.startswith("kos-c++")])
    assert commands[0] == commands[1], "absent and explicit0 Make commands differ"
    assert len(commands[2]) == len(targets), commands[2]
    for index, command in enumerate(commands[2]):
        assert command.count("-DRE4DC_LOG_RECORD16=1") == int(index == 0), command
        assert command.count("-DRE4DC_LOG_ATOMIC16=1") == int(index < 2), command
    rejected = {}
    for i, value in enumerate(("", "0 1", "2", "-1", "%", "0%", "1%", "1 ", "0 ")):
        result = run(base + ["LOG_RECORD16=" + value], output, "make-invalid-" + str(i),
                     cwd=DC / "game", success=False)
        assert result.returncode and b"LOG_RECORD16" in result.stderr, (value, result.stderr)
        rejected[value] = result.returncode
    # GNU Make removes leading assignment whitespace before setting the value.
    # Check that its normalized literal1 has the same effective command scope.
    leading = run(base + ["LOG_RECORD16= 1"], output, "make-normalized-leading", cwd=DC / "game")
    assert [line for line in leading.stdout.decode().splitlines() if line.startswith("kos-c++")] == commands[2]
    result = run(base + ["LOG_ATOMIC16=0", "LOG_RECORD16=1"], output, "make-dependency",
                 cwd=DC / "game", success=False)
    assert result.returncode and b"LOG_RECORD16 requires LOG_ATOMIC16=1" in result.stderr
    return dict(default_zero_command_identity=True, exact_mem_only_define=True,
                invalid_values=rejected, missing_dependency_rejected=True)


def off_checks(output):
    """Full production TUs, with declaration-only KOS host substitutes."""
    stubs = output / "kos-declarations"
    (stubs / "kos").mkdir(parents=True)
    (stubs / "arch").mkdir()
    (stubs / "kos.h").write_text("""#pragma once
#include <stdint.h>
typedef unsigned irq_t;
struct irq_context_t { unsigned long pc, pr, sr, r[16]; };
struct TestThread { int tid; void* stack; unsigned stack_size; };
extern TestThread* thd_current;
extern "C" void arch_exit();
extern "C" void thd_sleep(unsigned);
extern "C" int irq_disable();
extern "C" void irq_restore(int);
extern "C" int irq_inside_int();
extern "C" void irq_set_handler(irq_t, void (*)(irq_t, irq_context_t*, void*), void*);
#define EXC_UNHANDLED_EXC 1
#define EXC_DOUBLE_FAULT 2
""")
    (stubs / "arch/irq.h").write_text('#include <kos.h>\n')
    (stubs / "kos/dbgio.h").write_text("""#pragma once
#include <stdint.h>
struct dbgio_handler_t {
 const char* name; int (*detected)(); int (*init)(); int (*shutdown)();
 int (*set_irq)(int); int (*flush)();
 int (*write)(const uint8_t*,int,int); int (*read)(uint8_t*,int); void* private_data[1];
};
extern "C" void dbgio_add_handler(dbgio_handler_t*);
extern "C" int dbgio_dev_select(const char*);
""")
    constants = {
        "SOUND_REGION_BYTES": "0x80000", "CORE_RESIDENT_BYTES": "0x234000",
        "OPTION_RESIDENT_BYTES": "0x40000", "PLAYER_RESIDENT_BYTES": "0x118000",
        "WEAPON_RESIDENT_BYTES": "0x70000", "ARENA_KOS_BYTES": "0",
    }
    base_flags = ["-std=c++20", "-O2", "-g0", "-ffunction-sections", "-fdata-sections",
                  "-D__sh__=1", "-I" + str(stubs), "-I" + str(INCLUDE)]
    base_flags += ["-DRE4DC_" + key + "=" + value for key, value in constants.items()]
    rows = []
    for atomic, old, header, crash in ((0, 0, 0, 0), (1, 0, 0, 0), (1, 1, 1, 3)):
        profile = f"atomic{atomic}-old{old}-header{header}-crash{crash}"
        flags = base_flags + [f"-DRE4DC_LOG_ATOMIC16={atomic}", f"-DRE4DC_LOG_ATOMIC={old}",
                             f"-DRE4DC_LOG_RING_HDR={header}", f"-DRE4DC_LOG_CRASH_TEST={crash}"]
        for original in (MEM, FAULT):
            baseline = output / "baseline" / original.name
            baseline.parent.mkdir(exist_ok=True)
            baseline.write_bytes(subprocess.check_output(["git", "show", BASE + ":" + str(original.relative_to(ROOT))], cwd=ROOT))
            pp, objects = [], []
            for arm, path, extra in (("baseline", baseline, []), ("absent", original, []),
                                     ("zero", original, ["-DRE4DC_LOG_RECORD16=0"])):
                label = profile + "-" + original.stem + "-" + arm
                pp.append(run(["g++", *flags, *extra, "-E", "-P", str(path)], output, label + "-preprocess").stdout)
                obj = output / (label + ".o")
                run(["g++", *flags, *extra, "-c", str(path), "-o", str(obj)], output, label + "-object")
                objects.append(obj.read_bytes())
            assert pp[0] == pp[1] == pp[2], profile + ": " + original.name + " OFF preprocessing"
            assert objects[0] == objects[1] == objects[2], profile + ": " + original.name + " OFF host objects"
            rows.append(dict(profile=profile, source=original.name, preprocessed_bytes=len(pp[0]),
                             host_object_bytes=len(objects[0]), host_object_sha256=hashlib.sha256(objects[0]).hexdigest()))
    bad = run(["g++", *base_flags, "-DRE4DC_LOG_RECORD16=1", "-DRE4DC_LOG_ATOMIC16=0",
               "-E", "-P", str(MEM)], output, "source-dependency", success=False)
    assert bad.returncode and b"LOG_RECORD16 requires LOG_ATOMIC16" in bad.stderr
    # Compile the complete enabled TU too; this remains a host object, not SH-4.
    for crash in (0, 3):
        run(["g++", *base_flags, "-DRE4DC_LOG_RECORD16=1", "-DRE4DC_LOG_ATOMIC16=1",
             "-DRE4DC_LOG_ATOMIC=0", f"-DRE4DC_LOG_CRASH_TEST={crash}", "-c", str(MEM),
             "-o", str(output / f"enabled-mem-crash{crash}.o")], output, f"enabled-mem-crash{crash}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cpp = output / "fixture.cpp"
    cpp.write_text(fixture())
    rows = []
    compositions = [(size, 0, record, 0) for size in (8192, 16384, 32768, 65536) for record in (0, 1)]
    compositions += [(65536, 1, record, 0) for record in (0, 1)]
    compositions += [(65536, 0, record, 3) for record in (0, 1)]
    for size, old, record, crash in compositions:
        label = f"ring{size}-old{old}-record{record}-crash{crash}"
        binary = output / label
        flags = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-I" + str(INCLUDE),
                 f"-DTEST_RING_SIZE={size}", f"-DRE4DC_LOG_ATOMIC={old}", "-DRE4DC_LOG_ATOMIC16=1",
                 f"-DRE4DC_LOG_RECORD16={record}", f"-DRE4DC_LOG_CRASH_TEST={crash}"]
        if args.sanitize:
            flags[1:2] = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-no-pie"]
        command = ["g++", *flags, str(cpp), "-o", str(binary)]
        run(command, output, label + "-compile")
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0", UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
        row = json.loads(run([str(binary)], output, label + "-run", env=env).stdout)
        row["command"] = command
        rows.append(row)
    receipt = dict(status="PASS_SCOPED_BOUNDED_ENGINE_RECORD_AND_RAW_COMPATIBILITY", sanitized=args.sanitize,
                   baseline=BASE, rows=rows, make=make_checks(output), off=off_checks(output),
                   source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in (MEM, FAULT, INCLUDE / "log_record16.hpp", DC / "game/game30.mk",
                                               Path(__file__), HERE / "log_record16_fixture.cpp.in")},
                   limits=["255 bounds engine-record byte stores, not target time or caller-disabled duration",
                           "arbitrary raw/device appends retain whole-call masking and live alias semantics",
                           "forced returning synchronous/NMI counterexamples remain failures",
                           "coherent host polls only; unchanged observer/cache/target latency gates remain",
                           "host objects are not full target programme/overlay identity or runtime acceptance"])
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key not in ("source_sha256", "rows")}
                     | {"compositions": len(rows), "results": [{k: v for k, v in row.items() if k != "command"} for row in rows]}))


if __name__ == "__main__":
    main()
