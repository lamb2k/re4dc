#!/usr/bin/env python3
"""Reuse the pinned H064 extraction and release SDK fixture for A08-SLOTS.

The fixture is exported byte-for-byte from Git into a new output directory.
Its compile command uses our additional main; runtime method bodies are unchanged.
Only A08-SLOTS executes here; the other H064 lifetime cases are out of scope.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
FIXTURE_REF = "d396bd9e70f7953866e2055b392dda39e0087644"
FIXTURE_DIR = "port/dreamcast/tools/d367/boss21"
FIXTURE_FILES = (
    "test_motion_lifetime.py", "motion_lifetime_host.cpp", "motion_consumer_audit.py"
)


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline-ref", default="54cef5d1560c41d074beee05ffa1ecd38f2ee642")
    parser.add_argument("--fixture-ref", default=FIXTURE_REF)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    fixture = args.out / "h064-fixture" / FIXTURE_DIR
    fixture.mkdir(parents=True)
    fixture_pins = {}
    for name in FIXTURE_FILES:
        data = git("show", f"{args.fixture_ref}:{FIXTURE_DIR}/{name}")
        (fixture / name).write_bytes(data)
        fixture_pins[name] = sha(data)
    sys.path.insert(0, str(fixture))
    spec = importlib.util.spec_from_file_location("h064_fixture", fixture / FIXTURE_FILES[0])
    h064 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h064)
    h064.REPO = REPO
    baseline = git("rev-parse", args.baseline_ref).decode().strip()
    selected = git("rev-parse", "HEAD").decode().strip()
    source, pins, reset_order = h064.export_source(args.out, baseline)
    prior_read = (source / "src/game/read.cpp").read_bytes()
    candidate_read = (REPO / "src/game/read.cpp").read_bytes()
    original_command = h064.command
    rows = []
    for name, enabled, read_source in (
        ("baseline", 0, prior_read), ("disabled", 0, candidate_read),
        ("enabled", 1, candidate_read)
    ):
        (source / "src/game/read.cpp").write_bytes(read_source)

        def command(argv, path, timeout=45):
            argv = list(map(str, argv))
            original_main = str(fixture / "motion_lifetime_host.cpp")
            if original_main in argv:
                argv[argv.index(original_main)] = str(HERE / "readem_display_flags_host.cpp")
                argv[1:1] = [f"-DRE4DC_EM_ADMISSION_DISP_FIX={enabled}",
                             f"-DREAD_EM_FLAGS_EXPECT_RESTORE={enabled}", f"-I{fixture}"]
            elif len(argv) == 2 and argv[0] == str(args.out / name / "test") and argv[1] != "slot-failure":
                return f"NOT RUN: {argv[1]} is outside A08-SLOTS.\n"
            return original_command(argv, path, timeout)

        h064.command = command
        result = h064.build_motion(args.out / name, source, 1)
        result["cases"] = [case for case in result["cases"] if case["case"] == "slot-failure"]
        result.update(variant=name, em_admission_disp_fix=enabled,
                      read_cpp_sha256=sha(read_source))
        rows.append(result)
    receipt = {
        "scope": "actual-source release SDK host, ASan and UBSan; external transport/link stubs; no guest or gameplay claim",
        "baseline_revision": baseline, "candidate_head": selected,
        "candidate_read_sha256": sha(candidate_read), "baseline_source_sha256": pins,
        "fixture_revision": args.fixture_ref, "fixture_sha256": fixture_pins,
        "test_sha256": {p.name: sha(p.read_bytes()) for p in (
            Path(__file__), HERE / "readem_display_flags_host.cpp")},
        "reset_order_characterization": reset_order, "variants": rows,
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
