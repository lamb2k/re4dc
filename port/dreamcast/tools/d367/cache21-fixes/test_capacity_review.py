#!/usr/bin/env python3
"""Review frozen capacity1f7 without modifying or importing its runtime."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
FIXTURE_DIR = "port/dreamcast/tools/d367/boss21"
FIXTURE_FILES = ("test_motion_lifetime.py", "motion_lifetime_host.cpp", "motion_consumer_audit.py")
FIXTURE_REF = "d396bd9e70f7953866e2055b392dda39e0087644"
CAPACITY_REF = "1f7c34e4fc7a72222fd99c81afe66d08f890aa9e"


def data(ref, path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{ref}:{path}"])


def sha(value):
    return hashlib.sha256(value).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--kos-source", type=Path, default=Path("/root/work/kos-re4dc-d367"))
    parser.add_argument("--motion-source", type=Path)
    parser.add_argument("--expect-context-guard", action="store_true")
    parser.add_argument("--lease-lean", type=int, choices=(0, 1), default=0)
    parser.add_argument("--resume", type=int, choices=(0, 1), default=0)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    fixture = args.out / "h064-fixture" / FIXTURE_DIR
    fixture.mkdir(parents=True)
    fixture_pins = {}
    for name in FIXTURE_FILES:
        content = data(FIXTURE_REF, FIXTURE_DIR + "/" + name)
        (fixture / name).write_bytes(content); fixture_pins[name] = sha(content)
    sys.path.insert(0, str(fixture))
    h064 = module("h064_export", fixture / "test_motion_lifetime.py")
    h064.REPO = REPO
    source, source_pins, _ = h064.export_source(args.out, CAPACITY_REF)
    relative = "port/dreamcast/game/platform/motion_resume_journal.hpp"
    content = data(CAPACITY_REF, relative)
    (source / relative).write_bytes(content); source_pins[relative] = sha(content)
    if args.motion_source:
        relative = "port/dreamcast/game/platform/native_motion.cpp"
        content = args.motion_source.read_bytes()
        (source / relative).write_bytes(content); source_pins[relative] = sha(content)
    capacity = source / FIXTURE_DIR
    capacity.mkdir(parents=True)
    for name in ("test_motion_capacity.py", "motion_capacity_host.cpp", "motion-capacity-source-contract.json"):
        content = data(CAPACITY_REF, FIXTURE_DIR + "/" + name)
        (capacity / name).write_bytes(content); fixture_pins[name] = sha(content)
    contract = json.loads((capacity / "motion-capacity-source-contract.json").read_text())
    for path in sorted({row["path"] for row in contract["rows"]}):
        content = data(CAPACITY_REF, path)
        destination = source / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content); source_pins[path] = sha(content)
    review = module("frozen_capacity", capacity / "test_motion_capacity.py")
    review.source_contract()
    ui = (source / "port/dreamcast/game/ui_bridge.cpp").read_text()
    methods = ["void room_free4(", "void* room_alloc4_high("]
    code = re.search(r"constexpr unsigned kSourceReserve=.*?;", ui)[0] + "\n"
    code += re.search(r"struct alignas\(32\) Room4Cell.*?; };", ui)[0] + "\n"
    code += re.search(r"constexpr unsigned kRoom4Magic=.*?;", ui)[0] + "\n"
    code += re.search(r"struct Room4\s*\{.*?^};", ui, re.S | re.M)[0] + "\nRoom4 room4{};\n"
    code += "\n".join(review.function(ui, marker) for marker in methods) + "\n"
    start = ui.index("#if defined(RE4DC_FAR_SHELL)", ui.index('extern "C" int re4dc_static_heap_free'))
    end = ui.index('extern "C" void re4dc_static_free', start)
    code += ui[start:end]
    memory = (source / "src/game/main_mem.cpp").read_text()
    code += "\n".join(h064.fn(memory, name)[0] for name in ("MemSignalHeap", "MemDestroyHeap", "MemClearAllHeap")) + "\n"
    original_run = subprocess.run
    log_commands = []

    def run(argv, *extra, **kwargs):
        argv = list(map(str, argv))
        original_main = str(capacity / "motion_capacity_host.cpp")
        if original_main in argv:
            out = Path(argv[argv.index("-o") + 1]).parent
            header = out / "kos.h"
            kos = header.read_text().replace("#include <chrono>", "#include <chrono>\n#include <stdexcept>")
            kos = kos.replace("inline thread_local unsigned char host_thread;", "inline thread_local unsigned char host_thread;\ninline thread_local unsigned host_irq_sr,host_masked_yields,host_pass_calls;\ninline thread_local bool host_inside_interrupt;\ninline thread_local bool host_thread_present=true;")
            kos = kos.replace("#define thd_current ((void*)&host_thread)", "#define thd_current (host_thread_present?((void*)&host_thread):nullptr)")
            kos = kos.replace("inline int irq_disable(){unsigned old=host_irq_depth;host_irq.lock();++host_irq_depth;return old?0xf0:0;}",
                              "inline int irq_disable(){host_irq.lock();int old=host_irq_sr;++host_irq_depth;host_irq_sr=(host_irq_sr&0xefffff0f)|0xf0;return old;}")
            kos = kos.replace("inline void irq_restore(int){--host_irq_depth;host_irq.unlock();}",
                              "inline void irq_restore(int old){host_irq_sr=old;--host_irq_depth;host_irq.unlock();}")
            kos = kos.replace("inline int irq_inside_int(){return 0;}", "inline int irq_inside_int(){return host_inside_interrupt;}")
            kos = kos.replace("inline void thd_pass(){std::this_thread::yield();}",
                              'inline void thd_pass(){++host_pass_calls;if(host_irq_sr&0x300000f0){++host_masked_yields;throw std::runtime_error("masked yield observer");}std::this_thread::yield();}')
            assert "return old?0xf0:0;" not in kos
            header.write_text(kos)
            (out / "capacity_actual_review.inc").write_text(code)
            argv[argv.index(original_main)] = str(HERE / "capacity_review_host.cpp")
            argv[1:1] = ["-I" + str(capacity), "-DRE4DC_GAME=1", "-DRE4DC_NATIVE_STATIC=1", "-DRE4DC_NATIVE_PKG_HIGH=1"]
            argv[1:1] = [f"-DCAPACITY_CONTEXT_GUARD_EXPECT={int(args.expect_context_guard)}"]
            argv.insert(-2, "-Wl,--wrap=OSFreeToHeap,--wrap=OSDestroyHeap")
            (out / "review-command.json").write_text(json.dumps(argv, indent=2) + "\n")
        log_commands.append(argv)
        return original_run(argv, *extra, **kwargs)

    subprocess.run = run
    try:
        result = review.run(args.out / "capacity-review", 1, args.lease_lean, args.resume)
    finally:
        subprocess.run = original_run
    kos_paths = ("kernel/arch/dreamcast/include/arch/irq.h", "kernel/thread/thread.c")
    kos_pins = {path: sha((args.kos_source / path).read_bytes()) for path in kos_paths}
    irq_source = (args.kos_source / kos_paths[0]).read_text()
    assert '"stc sr, %0"' in irq_source and "arch_irq_restore((mask & 0xefffff0f) | 0x000000f0);" in irq_source
    receipt = {"scope": "Frozen capacity1f7 actual-source/SDK host review only; raw-SR boundary model and masked-yield exception observer; no runtime repair, target deadlock or gameplay proof",
               "capacity_revision": CAPACITY_REF, "source_sha256": source_pins, "fixture_sha256": fixture_pins,
               "motion_source_override": str(args.motion_source) if args.motion_source else None,
               "expect_context_guard": args.expect_context_guard,
               "review_projection_sha256": sha(code.encode()), "commands": log_commands, "variant": result,
               "local_KOS_source_sha256": kos_pins,
               "test_sha256": {p.name: sha(p.read_bytes()) for p in (Path(__file__), HERE / "capacity_review_host.cpp")}}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
