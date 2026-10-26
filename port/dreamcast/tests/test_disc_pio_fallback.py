#!/usr/bin/env python3
"""Build17 production-controller/native-adapter gate, using synthetic devices.

The native run imports unchanged production functions, maps fake SH4 register
and RAM addresses, and supplies BIOS/semaphore/clock functions. A second run
checks the portable controller and validator with ASan/UBSan. This verifies
software control flow, not real DMA, cache coherence, firmware or PIO rates.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
PLATFORM = ROOT / "port/dreamcast/game/platform"
TEST = ROOT / "port/dreamcast/tests/disc_pio_fallback_test.cpp"
SOURCES = [
    "port/dreamcast/game/platform/disc_pio_fallback.h",
    "port/dreamcast/game/platform/disc_stream_table_check.h",
    "port/dreamcast/game/platform/disc_pio_native.inc",
    "port/dreamcast/game/platform/dvd_read_safe.cpp",
    "src/game/snd.cpp",
    "port/dreamcast/game/Makefile",
    "port/dreamcast/patches/kos-804b319-iso-pio-retry.patch",
    "port/dreamcast/tests/disc_pio_fallback_test.cpp",
    "port/dreamcast/tests/test_disc_pio_fallback.py",
]


def function(source: str, signature: str) -> str:
    """Extract one actual C/C++ function; fixture signatures have no braces in strings."""
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def imported_source(tmp: Path) -> dict[str, str]:
    native = (PLATFORM / "dvd_read_safe.cpp").read_text()
    # Use the v2 marker family (the file also contains an older v1 marker).
    marker_start = native.index("// The marker: the destination's last 32 bytes")
    marker_source = native[marker_start:]
    helpers = "\n\n".join(function(marker_source, signature) for signature in (
        "volatile uint32_t* mark_at(", "uint32_t mark_word(", "bool aligned32(",
        "bool cached(", "void mark(", "bool marker_gone(",
    ))
    wrappers = "\n\n".join(function(native, signature) for signature in (
        'extern "C" int __wrap_cdrom_read_sectors_ex(',
        'extern "C" int __wrap_cdrom_stream_start(',
        'extern "C" int __wrap_cdrom_stream_request(',
        'extern "C" int __wrap_cdrom_stream_stop(',
        'extern "C" void re4dc_disc_pio_validation_begin(',
        'extern "C" void re4dc_disc_pio_validation_reject(',
        'extern "C" void re4dc_disc_pio_validation_end(',
    ))
    snd = (ROOT / "src/game/snd.cpp").read_text()
    snd = snd[snd.index("void SndInit()") :]
    sound = snd[snd.index("#line 120 SND_FILE") : snd.index("#line 166 SND_FILE")]
    # Import the actual added helper from its unified patch, without the fake's
    # owning/caching assertions being substituted for the production body.
    patch = (ROOT / "port/dreamcast/patches/kos-804b319-iso-pio-retry.patch").read_text()
    additions = "\n".join(line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
    iso = function(additions, "void re4dc_iso_retry_invalidate(")
    blocks = {
        "disc_pio_test_helpers.inc": helpers,
        "disc_pio_test_wrappers.inc": wrappers,
        "disc_pio_test_snd.inc": sound,
        "disc_pio_test_iso.inc": iso,
    }
    for name, source in blocks.items():
        (tmp / name).write_text(source + "\n")
    return {name: hashlib.sha256((source + "\n").encode()).hexdigest() for name, source in blocks.items()}


def run_step(label: str, command: list[str], steps: list[dict], env=None) -> subprocess.CompletedProcess:
    start = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, env=env, timeout=120)
    steps.append({
        "label": label,
        "argv": command,
        "returncode": result.returncode,
        "host_wall_seconds": round(time.monotonic() - start, 6),
        "stdout": result.stdout,
        "stderr": result.stderr,
    })
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit {result.returncode}")
    return result


def case_results(output: str) -> dict:
    cases = []
    for line in output.splitlines():
        if line.startswith("CASE\t"):
            fields = line.split("\t", 4)
            cases.append({"group": fields[1], "name": fields[2], "status": fields[3],
                          **({"error": fields[4]} if len(fields) > 4 else {})})
    summary = re.search(r"^TOTAL\tpassed=(\d+)\tfailed=(\d+)\tassertions=(\d+)$", output, re.MULTILINE)
    if not summary or len(cases) != int(summary[1]) + int(summary[2]):
        raise RuntimeError("Test did not produce a complete, consistent case receipt")
    return {
        "passed": int(summary[1]), "failed": int(summary[2]), "assertions": int(summary[3]),
        "groups": dict(Counter(case["group"] for case in cases)), "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the actual commands, hashes, case results and limits as JSON")
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"), help="host C++ compiler command (default CXX or g++)")
    args = parser.parse_args()
    compiler = shlex.split(args.compiler)
    if not compiler or not shutil.which(compiler[0]):
        parser.error(f"host compiler is unavailable: {args.compiler}")
    report = {
        "schema": "re4dc-build17-host-gate-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "result": "FAIL",
        "scope": "Synthetic production-controller, actual native adapter/wrappers/Snd first-read region and added KOS cache helper",
        "steps": [],
        "limitations": [
            "No game data, console, emulator, real drive, or DreamShell firmware is used.",
            "The native adapter runs with fake BIOS, semaphore, timer and MMIO; shared mapped aliases do not model SH4 cache coherence.",
            "The first Snd file-read region and added KOS helper are executed; the complete game and complete KOS filesystem are not host-emulated.",
            "Sanitizers cover the portable controller/validator; fixed SH4-address native mappings run separately without ASan shadow memory.",
            "LeakSanitizer is disabled because the sandbox does not permit its /proc task inspection; AddressSanitizer and UndefinedBehaviorSanitizer remain enabled.",
            "Host wall times and fake device deadlines are not Dreamcast cycles, disc throughput, or a measured PIO read-rate cost.",
            "Target build, exact option-off object identity and real-loader tests require the separate build/owner gates.",
        ],
    }
    try:
        report["source_sha256"] = hashes()
        version = run_step("host compiler version", compiler + ["--version"], report["steps"])
        report["compiler"] = version.stdout.splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="re4dc-disc-pio-") as directory:
            tmp = Path(directory)
            report["imported_source_sha256"] = imported_source(tmp)
            common = compiler + ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-I" + str(PLATFORM), "-I" + str(tmp), str(TEST)]
            native = tmp / "native"
            run_step("compile production adapter with fake device", common + ["-O2", "-o", str(native)], report["steps"])
            result = run_step("run controller, native adapter and integration", [str(native)], report["steps"])
            report["native_run"] = case_results(result.stdout)
            sanitized = tmp / "sanitized"
            run_step("compile portable ASan/UBSan gate", common + ["-DRE4DC_TEST_PORTABLE_ONLY", "-O1", "-g", "-fsanitize=address,undefined",
                     "-fno-omit-frame-pointer", "-no-pie", "-o", str(sanitized)], report["steps"])
            env = dict(os.environ)
            env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
            env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
            result = run_step("run portable ASan/UBSan gate", [str(sanitized)], report["steps"], env)
            report["sanitized_run"] = case_results(result.stdout)
        after = hashes()
        if after != report["source_sha256"]:
            report["source_sha256_after"] = after
            raise RuntimeError("Production/test sources changed during gate; rerun on the frozen source")
        report["result"] = "PASS"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
        print("Build17 gate FAILED:", error)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("Receipt:", args.report)
    if report["result"] == "PASS":
        print(f"Build17 PASS: {report['native_run']['passed']} cases; {report['sanitized_run']['passed']} portable cases repeated under ASan/UBSan.")
        print("No hardware cycle or PIO throughput measurement is claimed.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
