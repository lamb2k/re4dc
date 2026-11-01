#!/usr/bin/env python3
"""Execute unchanged production transport/bench TUs against explicit host boundaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sanitizer", action="store_true")
    ap.add_argument("--receipt", type=Path)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[4]
    sources = [
        "port/dreamcast/game/qa_link.cpp",
        "port/dreamcast/game/qa_link_bench.cpp",
        "port/dreamcast/tools/cloud/build28/transport_fixture_prefix.hpp",
        "port/dreamcast/tools/cloud/build28/transport_fixture.cpp.in",
        "port/dreamcast/tools/cloud/build28/bench_fixture.cpp.in",
        "port/dreamcast/tools/cloud/build28/transport_host.py",
    ]
    results = {}
    with tempfile.TemporaryDirectory(prefix="re4dc-build28-") as name:
        temp = Path(name)
        include = temp / "include"
        for header in ["kos.h", "kos/thread.h", "kos/worker_thread.h", "kos/net.h", "kos/fs_socket.h", "kos/irq.h",
                       "dc/modem/modem.h", "ppp/ppp.h", "arch/timer.h"]:
            path = include / header
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#pragma once\n")
        for case in ["transport", "bench"]:
            cpp = temp / f"{case}.cpp"
            cpp.write_text((here / f"{case}_fixture.cpp.in").read_text().replace("@ROOT@", str(root)))
            exe = temp / case
            command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-Wno-address",
                       "-DRE4DC_QA_LINK_REVIEW28=1", "-DRE4DC_QA_LINK=1", "-no-pie",
                       "-include", str(here / "transport_fixture_prefix.hpp"), "-I", str(include),
                       str(cpp), "-o", str(exe)]
            if args.sanitizer:
                command[1:1] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
            subprocess.run(command, check=True)
            env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, env=env)
            print(result.stdout, end="")
            results[case] = result.stdout.strip()
    receipt = {
        "status": "PASS", "sanitizer": "address,undefined" if args.sanitizer else None,
        "scope": "Complete production transport and benchmark TUs; synthetic KOS, socket, timer and thread services. No real network, scheduler, target ABI, PVR, or hardware acceptance.",
        "source_adaptations": "None. Only external header/service boundary is synthetic.",
        "results": results,
        "source_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sources},
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
