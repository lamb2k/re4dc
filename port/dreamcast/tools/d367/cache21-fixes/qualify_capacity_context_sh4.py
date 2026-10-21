#!/usr/bin/env python3
"""Reuse sealed capacity SH-4 commands; never link, stage or alter old proof."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
GAME = REPO / "port/dreamcast/game"
BASE = "1f7c34e4fc7a72222fd99c81afe66d08f890aa9e"
GIB = 1024 ** 3
MIB = 1024 ** 2


def sha(content):
    return hashlib.sha256(content).hexdigest()


def git(path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASE}:{path}"])


def space(extra):
    free = shutil.disk_usage("/mnt/c").free
    if free < 16 * GIB + extra * MIB:
        raise RuntimeError(f"C: small-object guard refused: {free} bytes")
    return free


def run(argv, log):
    space(64)
    result = subprocess.run(list(map(str, argv)), cwd=GAME, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    log.write_text(result.stdout)
    space(64)
    if len(result.stdout.encode()) > 2 * MIB or result.returncode:
        raise RuntimeError(f"Small-object command failed or exceeded log bound: {log}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    start_free = space(128)
    args.out.mkdir(parents=True, exist_ok=False)
    proof_bytes = git("port/dreamcast/tools/d367/boss21/motion-capacity-object-receipt.json")
    proof = json.loads(proof_bytes)
    commands = proof["objects"]["platform/native_motion.o"]
    source = args.out / "native_motion.cpp"
    original = git("port/dreamcast/game/platform/native_motion.cpp")
    current = (GAME / "platform/native_motion.cpp").read_bytes()
    headers = args.out / "headers"
    headers.mkdir()
    header_pins = {}
    rows = []
    for enabled in (0, 1):
        for variant, data in (("baseline", original), ("guard", current)):
            out = args.out / f"capacity{enabled}-{variant}"
            out.mkdir()
            command = list(commands["on" if enabled else "off"]["command"])
            command[command.index("platform/native_motion.cpp")] = str(source)
            command[command.index("-o") + 1] = str(out / "native_motion.o")
            command[1:1] = ["-iquote", str(GAME / "platform")]
            for i, option in enumerate(command):
                if option == "-include":
                    prior = Path(command[i + 1])
                    if prior.is_absolute():
                        content = prior.read_bytes()
                        snapshot = headers / prior.name
                        if snapshot.exists():
                            assert snapshot.read_bytes() == content
                        else:
                            snapshot.write_bytes(content)
                        command[i + 1] = str(snapshot)
                        header_pins[str(prior)] = sha(content)
            assert ("-DRE4DC_MOTION_CAPACITY=1" in command) == bool(enabled)
            source.write_bytes(data)
            (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
            run(command, out / "compile.log")
            stripped = out / "native_motion-stripped.o"
            run(["sh-elf-objcopy", "--strip-debug", out / "native_motion.o", stripped], out / "strip.log")
            rows.append({"capacity": enabled, "variant": variant, "source_sha256": sha(data),
                         "stripped_object_sha256": sha(stripped.read_bytes()),
                         "size": run(["sh-elf-size", stripped], out / "size.txt")})
    assert rows[0]["stripped_object_sha256"] == rows[1]["stripped_object_sha256"]
    receipt = {"scope": "Actual native_motion SH-4 object only; copied sealed flags/headers, no full program or gameplay qualification",
               "baseline_revision": BASE, "sealed_command_receipt_sha256": sha(proof_bytes), "forced_header_sha256": header_pins,
               "start_C_free_bytes": start_free, "finish_C_free_bytes": space(64), "objects": rows,
               "default_off_identity": "PASS versus exact1f7 MOTION_CAPACITY=0 with otherwise identical flags/headers"}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
