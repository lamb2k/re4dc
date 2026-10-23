#!/usr/bin/env python3
"""Run public synthetic cone-front qualification and retain reproducible receipts.

No game data, emulator, frame-rate or hardware claim. Every output directory
must be new. A supplied KOS checkout enables full target translation-unit checks.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DEPENDENCIES = {
    "backface_sh4_kernel/build_oracle.py": "0a4b8dae698686ba31006d9c735db79618d3b59326f39dab6bba4f8db5756d71",
    "backface_sh4_kernel/object_test.py": "2d657e7ca60f0a758aed403522e7a06f7ac13ce3b49cc920ae73e35c2b72926c",
    "backface_sh4_kernel/oracle.cpp": "b8aaa9622b8eee9a85be965929921ef23bd5f2f952acb1046c9a873bdc299a34",
    "backface_sh4_kernel/include/dc/pvr.h": "113b49f72fd868381b4ba6910d87da21d4f46b2440949e73c260c34a0dc625c0",
    "backface_sh4_actors/check_actor_dispatch.py": "7444f0587dac1303f4b798bcc1ea1578779f76d851ba6578af99e44ec7bb0d21",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", default=os.getenv("SH4_CXX", "/opt/toolchains/dc/sh-elf/bin/sh-elf-g++"))
    parser.add_argument("--kos-root", type=Path)
    # The unconditional queue-flush cull fix intentionally changes OFF code.
    # Feature identity is checked after that separate correctness commit.
    parser.add_argument("--baseline", default="dd8981e8de6dadb94997795867c85e8ede9a876f")
    parser.add_argument("--compare-helper-o1", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    stages = []
    recovered = {}
    for name, expected in DEPENDENCIES.items():
        path = HERE.parent / name
        recovered[name] = sha(path)
        assert recovered[name] == expected, (name, recovered[name], expected)

    def stage(name, arguments, receipt):
        command = [sys.executable, str(HERE / arguments[0]), *map(str, arguments[1:])]
        print("BEGIN", name, flush=True)
        log = output / (name + ".log")
        with log.open("w") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            print(log.read_text(), file=sys.stderr)
            raise RuntimeError("%s failed; see %s" % (name, log))
        path = output / receipt
        data = json.loads(path.read_text())
        stages.append(dict(stage=name, command=command, receipt=receipt,
                           receipt_sha256=sha(path), status="PASS"))
        print("PASS", name, flush=True)
        return data

    sdk = output / "sdk"
    command = [sys.executable, str(HERE.parent / "backface_sh4zam_fused/materialize.py"),
               "--output", str(sdk), "--receipt", str(output / "sdk-receipt.json")]
    subprocess.run(command, cwd=ROOT, check=True)
    stages.append(dict(stage="sdk", command=command, receipt="sdk-receipt.json",
                       receipt_sha256=sha(output / "sdk-receipt.json"), status="PASS"))
    make = stage("make", ["make_test.py", "--output", output / "make", "--baseline", args.baseline],
                 "make/make-controls.json")
    helper = stage("helper", ["helper_test.py", "--output", output / "helper"],
                   "helper/helper-controls.json")
    rounding = stage("rounding", ["rounding_test.py", "--output", output / "rounding-controls.json"],
                     "rounding-controls.json")
    world = stage("world-producer", ["world_test.py", "--output", output / "world-producer", "--baseline", args.baseline],
                  "world-producer/world-producer-controls.json")
    actor_args = ["actor_test.py", "--out", output / "actor", "--sdk", sdk, "--baseline", args.baseline]
    if args.kos_root:
        actor_args += ["--sh4-cxx", args.sh4_cxx, "--kos-root", args.kos_root.resolve()]
    actor = stage("actor", actor_args, "actor/actor-controls.json")
    world_args = ["world_runtime_test.py", "--output", output / "world-runtime", "--baseline", args.baseline]
    if args.kos_root:
        world_args += ["--sh4-cxx", args.sh4_cxx, "--kos-root", args.kos_root.resolve(), "--sdk-root", sdk]
    runtime = stage("world-runtime", world_args, "world-runtime/world-runtime-controls.json")
    target = stage("target", ["target_test.py", "--output", output / "target", "--sh4-cxx", args.sh4_cxx,
                              "--optimization=-O1", "--helper-optimization=-O2"], "target/target-controls.json")
    world_target = None
    if args.kos_root:
        world_target = stage("world-target", ["world_target_test.py", "--output", output / "world-target",
                             "--sh4-cxx", args.sh4_cxx, "--kos-root", args.kos_root.resolve(),
                             "--sdk-root", sdk], "world-target/world-target-controls.json")
    if args.compare_helper_o1:
        stage("target-helper-o1", ["target_test.py", "--output", output / "target-helper-o1", "--sh4-cxx", args.sh4_cxx,
                                    "--optimization=-O1", "--helper-optimization=-O1"], "target-helper-o1/target-controls.json")
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline, stages=stages,
                  test_dependencies_source="2249d3cfa203a7bc679739379cb6d5668edb7ecc", dependencies=recovered,
                  summary=dict(helper=helper["counts"], target_comparisons=target["comparisons"],
                               full_world_target_requested=bool(args.kos_root),
                               world_target_packet_comparisons=len(world_target["cases"]) if world_target else None),
                  test_source_sha256={p.name: sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.suffix in (".py", ".cpp", ".in")},
                  limits="Public synthetic source/host/target-opcode evidence only. hwsim uses perfect caches and no memory/PVR/DMA events. No scene, emulator, hardware, wall-time, millisecond or FPS acceptance.")
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS qualification:", output / "qualification.json")


if __name__ == "__main__":
    main()
