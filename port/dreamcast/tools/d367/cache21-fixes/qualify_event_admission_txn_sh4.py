#!/usr/bin/env python3
"""Small-object proof using actual Make commands; source snapshots share a path."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
GAME = REPO / "port/dreamcast/game"
GIB = 1024 ** 3
MIB = 1024 ** 2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def space(extra):
    available = shutil.disk_usage("/mnt/c").free
    if available < 16 * GIB + extra * MIB:
        raise RuntimeError(f"Small-object C: guard refused: {available} bytes free")
    return available


def run(argv, log):
    space(64)
    result = subprocess.run(list(map(str, argv)), cwd=GAME, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    log.write_text(result.stdout)
    if len(result.stdout.encode()) > 4 * MIB:
        raise RuntimeError("Small-object log exceeded 4 MiB bound")
    space(64)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); see {log}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline-ref", default="54cef5d1560c41d074beee05ffa1ecd38f2ee642")
    args = parser.parse_args()
    start_free = space(128)
    args.out.mkdir(parents=True, exist_ok=False)
    source = args.out / "event.cpp"
    baseline_event = subprocess.check_output(["git", "-C", str(REPO), "show", args.baseline_ref + ":src/game/event.cpp"])
    candidate_event = (REPO / "src/game/event.cpp").read_bytes()
    (args.out / "baseline-event.cpp").write_bytes(baseline_event)
    (args.out / "candidate-event.cpp").write_bytes(candidate_event)
    baseline_make = args.out / "baseline.Makefile"
    baseline_make.write_bytes(subprocess.check_output(["git", "-C", str(REPO), "show", args.baseline_ref + ":port/dreamcast/game/Makefile"]))
    rows = []
    for cabin in (0, 1):
        hashes = {}
        for variant, enabled, data in (("baseline", 0, baseline_event), ("disabled", 0, candidate_event), ("enabled", 1, candidate_event)):
            out = args.out / f"cabin{cabin}" / variant
            out.mkdir(parents=True)
            make = ["make", "--no-print-directory", "-f", str(baseline_make if variant == "baseline" else GAME / "Makefile"),
                    f"OBJDIR={out}", f"CABIN_SOURCE={cabin}", "ROUTE_CH21=1", "ROUTE_CH22=1", "ROUTE_OVL=1",
                    "EM10_SHARED=1", "WORLD_STAGE_MODULES=0", "ROUTE_MOVIES=1", "AICA_AUDIO=1", "AICA_STREAMS=1",
                    "NATIVE_STATIC=1", "D349_RENDERER_STACK=1", "PVR_STREAM=1"]
            if variant != "baseline":
                make.append(f"EVD_ADMISSION_TXN={enabled}")
            run([*make, str(out / "cabin-source.h"), str(out / "demo-presentation-knobs.txt")], out / "headers.log")
            dry = run([*make, "-n", str(out / "src/game/event.o")], out / "make-command.log")
            commands = [shlex.split(line) for line in dry.splitlines() if line.startswith("kos-c++ ")]
            assert len(commands) == 1
            command = commands[0]
            command.append("-fstack-usage")
            command[command.index("../../../src/game/event.cpp")] = str(source)
            expected_define = "-DRE4DC_EVD_ADMISSION_TXN=1"
            assert (expected_define in command) == bool(enabled)
            source.write_bytes(data)
            (out / "src/game").mkdir(parents=True)
            (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
            run(command, out / "compile.log")
            obj = out / "src/game/event.o"
            stripped = out / "event-stripped.o"
            run(["sh-elf-objcopy", "--strip-debug", obj, stripped], out / "strip.log")
            size = run(["sh-elf-size", stripped], out / "size.txt")
            stack = (out / "src/game/event.su").read_text()
            selected_stack = [line for line in stack.splitlines() if "EventMgr::SetEvd(" in line]
            assert len(selected_stack) == 1
            hashes[variant] = sha(stripped)
            rows.append({"cabin_source": cabin, "variant": variant, "event_cpp_sha256": hashlib.sha256(data).hexdigest(),
                         "stripped_event_o_sha256": hashes[variant], "size": size,
                         "setevd_stack_usage": selected_stack[0]})
        assert hashes["baseline"] == hashes["disabled"]
    invalid = []
    for value in ("2", "-1", "yes"):
        result = subprocess.run(["make", "--no-print-directory", "-n", f"EVD_ADMISSION_TXN={value}"],
                                cwd=GAME, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (args.out / f"invalid-{value}.log").write_text(result.stdout)
        assert result.returncode != 0 and "EVD_ADMISSION_TXN must be 0 or 1" in result.stdout
        invalid.append(value)
    receipt = {"scope": "Actual SH-4 event.o only; no linked-program, guest or hardware acceptance",
               "baseline_revision": args.baseline_ref, "candidate_event_sha256": hashlib.sha256(candidate_event).hexdigest(),
               "qualifier_sha256": sha(Path(__file__)), "baseline_make_sha256": sha(baseline_make),
               "start_C_free_bytes": start_free, "finish_C_free_bytes": space(64),
               "start_guard": 16 * GIB + 128 * MIB, "stop_guard": 16 * GIB + 64 * MIB,
               "invalid_knobs_rejected": invalid, "objects": rows}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
