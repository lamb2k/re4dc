#!/usr/bin/env python3
"""Whole SH4 event.o OFF identity and ON checks for exact failed-start rollback."""
import argparse
import hashlib
import json
from pathlib import Path
import re
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
    parser.add_argument("--baseline-ref")
    parser.add_argument("--debug-cleanup-pair",action="store_true")
    parser.add_argument("--exec-failure-pair",action="store_true")
    args = parser.parse_args()
    assert not(args.debug_cleanup_pair and args.exec_failure_pair)
    args.baseline_ref=args.baseline_ref or ("dfc0cf972" if args.exec_failure_pair else "1d1576c35" if args.debug_cleanup_pair else "32172f542")
    knob="EVD_EXEC_FAILURE_CLEANUP" if args.exec_failure_pair else "EVD_DEBUG_READ_CLEANUP" if args.debug_cleanup_pair else "EVD_START_ROLLBACK"
    symbol="RE4DC_"+knob
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
      for txn in (0, 1):
        hashes = {}
        variants = [("baseline", 0, baseline_event), ("disabled", 0, candidate_event)]
        if txn:
            variants.append(("enabled", 1, candidate_event))
        for variant, enabled, data in variants:
            out = args.out / f"cabin{cabin}-txn{txn}" / variant
            out.mkdir(parents=True)
            make = ["make", "--no-print-directory", "-f", str(baseline_make if variant == "baseline" else GAME / "Makefile"),
                    f"OBJDIR={out}", f"CABIN_SOURCE={cabin}", "ROUTE_CH21=1", "ROUTE_CH22=1", "ROUTE_OVL=1",
                    "EM10_SHARED=1", "WORLD_STAGE_MODULES=0", "ROUTE_MOVIES=1", "AICA_AUDIO=1", "AICA_STREAMS=1",
                    "NATIVE_STATIC=1", "D349_RENDERER_STACK=1", "PVR_STREAM=1", f"EVD_ADMISSION_TXN={txn}",f"EVD_START_CLEANUP={txn}"]
            if variant != "baseline":
                make.append(f"{knob}={enabled}")
            if args.debug_cleanup_pair or args.exec_failure_pair:
                make.append(f"EVD_START_ROLLBACK={txn}")
            run([*make, str(out / "cabin-source.h"), str(out / "demo-presentation-knobs.txt")], out / "headers.log")
            dry = run([*make, "-n", str(out / "src/game/event.o")], out / "make-command.log")
            commands = [shlex.split(line) for line in dry.splitlines() if line.startswith("kos-c++ ")]
            assert len(commands) == 1
            command = commands[0]
            command.append("-fstack-usage")
            command[command.index("../../../src/game/event.cpp")] = str(source)
            assert ("-DRE4DC_EVD_ADMISSION_TXN=1" in command) == bool(txn)
            assert ("-DRE4DC_EVD_START_CLEANUP=1" in command) == bool(txn)
            assert ("-D"+symbol+"=1" in command) == bool(enabled)
            if variant == "disabled":
                # Omitted switch and explicit zero resolve the same compiler
                # invocation, including target-specific flags and forced headers.
                implicit = [part for part in make if part != knob+"=0"]
                implicit_dry = run([*implicit, "-n", str(out / "src/game/event.o")], out / "default-command.log")
                assert implicit_dry == dry
            source.write_bytes(data)
            (out / "src/game").mkdir(parents=True)
            (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
            run(command, out / "compile.log")
            obj = out / "src/game/event.o"
            stripped = out / "event-stripped.o"
            run(["sh-elf-objcopy", "--strip-debug", obj, stripped], out / "strip.log")
            size = run(["sh-elf-size", stripped], out / "size.txt")
            stack = (out / "src/game/event.su").read_text()
            stack_names=("EventMgr::SetEvd(", "EventMgr::SetEvt(", "Event::init(")+(('EventMgr::EvtReadExec(',)if args.exec_failure_pair else())
            selected_stack = [line for line in stack.splitlines() if any(name in line for name in stack_names)]
            assert len(selected_stack) == (5 if args.exec_failure_pair else 4)
            hashes[variant] = sha(stripped)
            rows.append({"cabin_source": cabin, "evd_admission_txn": txn, "start_cleanup": txn,knob:enabled, "variant": variant, "event_cpp_sha256": hashlib.sha256(data).hexdigest(),
                         "stripped_event_o_sha256": hashes[variant], "size": size,
                         "selected_stack_usage": selected_stack})
        assert hashes["baseline"] == hashes["disabled"]
    invalid = []
    for value in ("2", "-1", "yes"):
        result = subprocess.run(["make", "--no-print-directory", "-n", f"{knob}={value}"],
                                cwd=GAME, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (args.out / f"invalid-{value}.log").write_text(result.stdout)
        assert result.returncode != 0 and knob+" must be 0 or 1" in result.stdout
        invalid.append(value)
    prerequisites = []
    for txn in (("0",) if args.debug_cleanup_pair or args.exec_failure_pair else ("0", "1")):
        argv = ["make", "--no-print-directory", "-n", knob+"=1","EVD_START_CLEANUP=0","EVD_ADMISSION_TXN="+txn]
        result = subprocess.run(argv, cwd=GAME, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (args.out / f"missing-transaction-{txn}.log").write_text(result.stdout)
        assert result.returncode != 0 and knob+" requires EVD_" in result.stdout
        prerequisites.append(txn)
    # Original PPC policy is guarded out: preprocess just the two actual edited
    # methods, with the source prerequisite block, through the selected tool.
    text = candidate_event.decode()
    contract = re.search(r'#if defined\('+re.escape(symbol)+r'\).*?^#endif\n#endif', text, re.M | re.S)[0]
    selected = []
    for signature in (("int EventMgr::EvtReadExec(char* nm, int em, u32 flags)",) if args.exec_failure_pair else ("int EventMgr::GetBin(void** out, const char* nm, int flagGet)","int EventMgr::GetEvd(void** out, char* nm, int flagGet)") if args.debug_cleanup_pair else ("int EventMgr::SetEvt(void* data, u32* key)",)):
        start = text.index(signature)
        end = start + re.search(r'^}', text[start:], re.M).end()
        selected.append(text[start:end])
    policy = args.out / "selected-policy.cpp"
    policy.write_text(contract + "\n" + "\n".join(selected) + "\n")
    ppc = []
    for enabled in (0, 1):
        result = run(["kos-c++", "-E", "-P", "-x", "c++", "-D__PPC__=1", "-DRE4DC_CABIN_SOURCE=0",
                      "-DRE4DC_EVD_ADMISSION_TXN=0", f"-D{symbol}={enabled}", policy], args.out / f"ppc-preprocessed-{enabled}.txt")
        ppc.append(result)
    assert ppc[0] == ppc[1]
    raw_contract = args.out / "compile-contract.inc"
    raw_contract.write_text(contract + "\n")
    direct_refusals = []
    for txn in ((None,"0") if args.debug_cleanup_pair or args.exec_failure_pair else (None, "0","1")):
        argv = ["kos-c++", "-E", "-P", "-x", "c++", "-D"+symbol+"=1", str(raw_contract)]
        if txn is not None: argv.append("-DRE4DC_EVD_ADMISSION_TXN=" + txn)
        result = subprocess.run(argv, cwd=GAME, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (args.out / f"direct-prerequisite-{txn}.log").write_text(result.stdout)
        assert result.returncode != 0 and knob+" requires "+("EVD_START_ROLLBACK" if args.exec_failure_pair else "EVD_ADMISSION_TXN") in result.stdout
        direct_refusals.append(txn)
    receipt = {"scope": "Actual SH-4 event.o only; no linked-program, guest or hardware acceptance",
               "baseline_revision": args.baseline_ref, "candidate_event_sha256": hashlib.sha256(candidate_event).hexdigest(),
               "qualifier_sha256": sha(Path(__file__)), "baseline_make_sha256": sha(baseline_make),
               "start_C_free_bytes": start_free, "finish_C_free_bytes": space(64),
               "start_guard": 16 * GIB + 128 * MIB, "stop_guard": 16 * GIB + 64 * MIB,
               "invalid_knobs_rejected": invalid, "missing_make_prerequisites_rejected": prerequisites,
               "direct_source_prerequisites_rejected": direct_refusals,
               "ppc_selected_preprocessed_sha256": hashlib.sha256(ppc[0].encode()).hexdigest(),
               "ppc_limit": "Selected-source preprocessing only, not a PPC object/full-game identity claim.", "objects": rows}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
