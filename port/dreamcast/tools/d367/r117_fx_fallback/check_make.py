#!/usr/bin/env python3
"""Check strict Make knob/dependency parsing and the actual native/PPC guard."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
KNOB = "R117_FX_QUALIFIED_FALLBACK"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True,
                        help="Current fx3-lean0-profile/esp-profile.json from build_controls.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=False)
    profile = json.loads(args.profile.read_text())
    base = profile["seed"]["command"]
    cases = [("valid0", [KNOB + "=0"], True), ("valid1", [KNOB + "=1"], True)]
    cases += [("invalid" + str(i), [KNOB + "=" + value], False)
              for i, value in enumerate(("", "0 1", "1 1", "%", "0%", "2", "-1", "01", "x"))]
    cases += [("needs_trim", [KNOB + "=1", "FX_LEVEL=0", "FX_TRIM=0"], False),
              ("needs_additions", [KNOB + "=1", "PS2_FX_ADDITIONS=0"], False)]
    results = []
    for name, changes, valid in cases:
        command = [*base, *changes]
        result = subprocess.run(command, cwd=ROOT / "port/dreamcast/game", capture_output=True, text=True)
        (out / (name + ".log")).write_text(result.stdout + result.stderr)
        assert (result.returncode == 0) == valid, (name, result.stdout + result.stderr)
        if not valid:assert KNOB in result.stderr, (name, "wrong validation failure")
        results.append(dict(name=name, overrides=changes, returncode=result.returncode))
    spec = importlib.util.spec_from_file_location("r117_guard_extract", HERE.parent / "esp_setup_lean/check_runtime.py")
    extract = importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)
    source = (ROOT / "src/game/esp_sub.cpp").read_text()
    guard = extract.conditional(source, "#if defined(RE4DC_R117_FX_QUALIFIED_FALLBACK)")
    guards = []
    for name, definitions, enabled in (
        ("native", ["RE4DC_GAME=1"], True),
        ("ppc", ["RE4DC_GAME=1", "__PPC__=1"], False),
        ("other", [], False),
    ):
        command = ["g++", "-x", "c++", "-", "-E", "-dM", "-DRE4DC_" + KNOB + "=1",
                   "-DRE4DC_FX_TRIM=1", "-DRE4DC_PS2_FX_ADDITIONS=1", *["-D" + item for item in definitions]]
        result = subprocess.run(command, input=guard, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert ("#define RE4DC_R117_FX_FALLBACK 1" in result.stdout) == enabled
        guards.append(dict(name=name, enabled=enabled, scope="actual guard only; no PPC compiler/run claim"))
    (out / "make-receipt.json").write_text(json.dumps(dict(status="PASS", cases=results, guards=guards), indent=2) + "\n")
    print(json.dumps(dict(status="PASS", make_cases=len(results), native_guards=len(guards))))


if __name__ == "__main__":
    main()
