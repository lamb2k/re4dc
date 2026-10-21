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
    source = args.out / "read.cpp"
    baseline_read = subprocess.check_output(["git", "-C", str(REPO), "show", args.baseline_ref + ":src/game/read.cpp"])
    candidate_read = (REPO / "src/game/read.cpp").read_bytes()
    baseline_make = args.out / "baseline.Makefile"
    baseline_make.write_bytes(subprocess.check_output(["git", "-C", str(REPO), "show", args.baseline_ref + ":port/dreamcast/game/Makefile"]))
    rows = []
    for heap in (0, 1):
        hashes = {}
        for variant, enabled, data in (("baseline", 0, baseline_read), ("disabled", 0, candidate_read), ("enabled", 1, candidate_read)):
            out = args.out / f"heap{heap}" / variant
            out.mkdir(parents=True)
            make = ["make", "--no-print-directory", "-f", str(baseline_make if variant == "baseline" else GAME / "Makefile"),
                    f"OBJDIR={out}", f"WEAPON_HEAP4={heap}"]
            if variant != "baseline":
                make.append(f"EM_ADMISSION_DISP_FIX={enabled}")
            run([*make, str(out / "cabin-source.h"), str(out / "demo-presentation-knobs.txt")], out / "headers.log")
            dry = run([*make, "-n", str(out / "src/game/read.o")], out / "make-command.log")
            commands = [shlex.split(line) for line in dry.splitlines() if line.startswith("kos-c++ ")]
            assert len(commands) == 1
            command = commands[0]
            command[command.index("../../../src/game/read.cpp")] = str(source)
            expected_define = "-DRE4DC_EM_ADMISSION_DISP_FIX=1"
            assert (expected_define in command) == bool(enabled)
            source.write_bytes(data)
            (out / "src/game").mkdir(parents=True)
            (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
            run(command, out / "compile.log")
            obj = out / "src/game/read.o"
            stripped = out / "read-stripped.o"
            run(["sh-elf-objcopy", "--strip-debug", obj, stripped], out / "strip.log")
            size = run(["sh-elf-size", stripped], out / "size.txt")
            hashes[variant] = sha(stripped)
            rows.append({"heap4": heap, "variant": variant, "read_cpp_sha256": hashlib.sha256(data).hexdigest(),
                         "stripped_read_o_sha256": hashes[variant], "size": size})
        assert hashes["baseline"] == hashes["disabled"]
    invalid = []
    for value in ("2", "-1", "yes"):
        result = subprocess.run(["make", "--no-print-directory", "-n", f"EM_ADMISSION_DISP_FIX={value}"],
                                cwd=GAME, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (args.out / f"invalid-{value}.log").write_text(result.stdout)
        assert result.returncode != 0 and "EM_ADMISSION_DISP_FIX must be 0 or 1" in result.stdout
        invalid.append(value)
    receipt = {"scope": "Actual SH-4 read.o only; no linked-program, guest or hardware acceptance",
               "baseline_revision": args.baseline_ref, "candidate_read_sha256": hashlib.sha256(candidate_read).hexdigest(),
               "start_C_free_bytes": start_free, "finish_C_free_bytes": space(64),
               "start_guard": 16 * GIB + 128 * MIB, "stop_guard": 16 * GIB + 64 * MIB,
               "invalid_knobs_rejected": invalid, "objects": rows}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
