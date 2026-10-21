#!/usr/bin/env python3
"""Small-object/static-frame audit; no complete stack high-water assertion."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
GAME = REPO / "port/dreamcast/game"
sys.path.insert(0, str(HERE))
import qualify_event_admission_txn_sh4 as qualified


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frames(path):
    rows = []
    for line in path.read_text().splitlines():
        name, size, kind = line.rsplit("\t", 2)
        rows.append(dict(name=name, bytes=int(size), kind=kind))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sealed-event", required=True, type=Path)
    args = parser.parse_args()
    start = qualified.space(128)
    args.out.mkdir(parents=True, exist_ok=False)
    sealed_receipt = json.loads((args.sealed_event.parents[1] / "receipt.json").read_text())
    assert sha(REPO / "src/game/event.cpp") == sealed_receipt["candidate_event_sha256"]
    event_source = args.sealed_event.parent.parent / "candidate-event.cpp"
    assert sha(event_source) == sealed_receipt["candidate_event_sha256"]
    shutil.copy2(args.sealed_event / "src/game/event.o", args.out / "event.o")
    shutil.copy2(args.sealed_event / "src/game/event.su", args.out / "event.su")
    object_rows = [dict(source="src/game/event.cpp", source_sha256=sha(REPO / "src/game/event.cpp"),
                        object_sha256=sha(args.out / "event.o"), frames=frames(args.out / "event.su"),
                        provenance="Read-only copy of qualified cabin1 enabled event.o and .su")]
    prerequisites = ["CABIN_SOURCE=1", "EVD_ADMISSION_TXN=1", "ROUTE_CH21=1", "ROUTE_CH22=1", "ROUTE_OVL=1",
                     "EM10_SHARED=1", "WORLD_STAGE_MODULES=0", "ROUTE_MOVIES=1", "AICA_AUDIO=1", "AICA_STREAMS=1",
                     "NATIVE_STATIC=1", "D349_RENDERER_STACK=1", "PVR_STREAM=1", "DVD_READ_SAFE=1"]
    for name in ("db_log", "game", "scheduler"):
        out = args.out / name; out.mkdir()
        obj = out / f"src/game/{name}.o"
        make = ["make", "--no-print-directory", f"OBJDIR={out}", *prerequisites]
        dry = qualified.run([*make, "-n", obj], out / "make-command.log")
        commands = [shlex.split(line) for line in dry.splitlines() if line.startswith("kos-c++ ")]
        assert len(commands) == 1
        command = commands[0]
        generated = []
        for i, item in enumerate(command):
            if item == "-include" and command[i + 1].startswith(str(out) + "/"):
                generated.append(command[i + 1])
        if generated:
            qualified.run([*make, *sorted(set(generated))], out / "headers.log")
        obj.parent.mkdir(parents=True, exist_ok=True)
        command.append("-fstack-usage")
        (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        qualified.run(command, out / "compile.log")
        object_rows.append(dict(source=f"src/game/{name}.cpp", source_sha256=sha(REPO / f"src/game/{name}.cpp"),
                                object_sha256=sha(obj), frames=frames(obj.with_suffix(".su")), provenance="Actual current Make small object"))
    # Keep relocation/disassembly proof, not only a source-level assumed chain.
    sections = {}
    dump = qualified.run(["sh-elf-objdump", "-dr", "-C", args.out / "event.o"], args.out / "event-disassembly.txt")
    for section in dump.split("Disassembly of section ")[1:]:
        heading = re.search(r"^[0-9a-f]+ <(.*)>:$", section, re.M)
        if not heading:
            continue
        references = re.findall(r"R_SH_[A-Z0-9_]+\s+(.+)", section)
        if any(item in heading[1] for item in ("SetEvd(", "SetEvt(", "SetBin(", "EvtReadExec(", "SetEvs(", "GetEvd(")):
            sections[heading[1]] = references
    receipt = dict(scope="Actual SH4 static source frames/call references, not a full call-chain bound or target high-water measurement.",
                   source_head=subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
                   start_C_free_bytes=start, finish_C_free_bytes=qualified.space(64),
                   start_guard=16 * 1024 ** 3 + 128 * 1024 ** 2, stop_guard=16 * 1024 ** 3 + 64 * 1024 ** 2,
                   make_prerequisites=prerequisites, objects=object_rows, selected_event_references=sections,
                   source_subtotals={"EvtReadExec52_SetEvtData24_SetEvd752_SetBin20_SetDat52": 900,
                                     "SetEvs40_SetEvd752_SetBin20_SetDat52": 864,
                                     "GetEvd292_SetEvd752_SetBin20_SetDat52": 1116},
                   limits=["Unmeasured outer callers, libc/printf/device paths, IRQ/OS frames and dynamic target high-water remain outside these source-frame sums.",
                           "SetEvt(name) is called after SetEvd returns; its36-byte frame does not overlap this752-byte admission frame.",
                           "GetEvd finishes HDReadDebugAlloc before SetEvd; deep file-open temporaries must not be added as simultaneous admission frames."],
                   qualifier_sha256=sha(Path(__file__)))
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    for row in object_rows:
        chosen = [r for r in row["frames"] if any(name in r["name"] for name in
                  ("SetEvd(", "SetEvt(", "SetBin(", "SetDat(", "EvtReadExec(", "SetEvs(", "GetEvd(", "gameRoomInit(", "GetStackSize(", "cLog::err(", "cLog::verr(", "cLog::add("))]
        print(json.dumps(dict(source=row["source"], frames=chosen)))


if __name__ == "__main__":
    main()
