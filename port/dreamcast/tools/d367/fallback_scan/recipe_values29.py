#!/usr/bin/env python3
"""Resolve Build29 whole-game knob values with the real public Make command.

Includes all simple ?= knob names from game/Makefile and game/*.mk, not only
the drawing-name subset. A build setting is not evidence of asset admission
or chapter frequency. Public NMR_POOL_LOD=0 is the documented data override.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
GAME = ROOT / "port/dreamcast/game"
spec = importlib.util.spec_from_file_location("fa29_recipe_controls", ROOT / "port/dreamcast/tools/cloud/build29/build_controls.py")
controls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controls
spec.loader.exec_module(controls)
profile = controls.profile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "kos-root", "sdk-root"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    makefiles = [GAME / "Makefile", *sorted(GAME.glob("*.mk"))]
    names = set()
    for path in makefiles:
        names.update(re.findall(r"(?m)^\s*(?:override\s+)?([A-Z][A-Z0-9_]*)\s*\?=", path.read_text()))
    # Deliberately exclude environment/build output roots. Keep all feature
    # prefixes, including GAME_, MOTION_, CLOTH_, GC_, collision and sound.
    names -= {"CC", "CXX", "AS", "AR", "LD", "OBJCOPY", "KOS_BASE", "KOS_CC_BASE", "KOS_PORTS", "BUILD", "ROOT", "TARGET", "TARGET_ELF", "TARGET_BIN"}
    names = sorted(names)
    result = {}
    for name, options in (("public-game", ["NMR_POOL_LOD=0"]),
                          ("public-qa-audit29", controls.QA + ["QA_LINK=1", "QA_LINK_REVIEW28=1", "DRAW_FALLBACK_AUDIT=1", "FALLBACK_AUDIT29=1"]),
                          ("public-qa-composed29", controls.QA + controls.COMPOSED + ["QA_LINK=1", "FALLBACK_AUDIT29=1"])):
        directory = out / name
        directory.mkdir()
        query = directory / "query.mk"
        query.write_text(".PHONY: b29-values\nb29-values:\n\t@:\n" + "\n".join(
            "$(info B29_VALUE " + n + "=$(" + n + "))" for n in names) + "\n")
        command, recipe = profile.make_command(directory, ROOT, args.kos_root.resolve(), args.sdk_root.resolve(), options, "b29-values")
        command[3:3] = ["-f", "Makefile", "-f", str(query)]
        run = subprocess.run(command, cwd=GAME, text=True, capture_output=True)
        output = run.stdout + run.stderr
        (directory / "make.log").write_text(output)
        assert not run.returncode, output[-4000:]
        values = dict(line[len("B29_VALUE "):].split("=", 1) for line in output.splitlines() if line.startswith("B29_VALUE "))
        assert set(values) == set(names)
        result[name] = dict(overrides=options, values=values, recipe_inputs=recipe, command=command)
    receipt = dict(status="PASS", scope=__doc__, profiles=result, queried_knobs=len(names),
                   source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [*makefiles, Path(__file__)]},
                   limitations="The actual public build command, with NMR_POOL_LOD=0 because private generated Ganado data is absent. The tracked CH2 recipe requests NMR_POOL_LOD=1. No runtime package admission or chapter frequency is inferred from Make values.")
    (out / "recipe-values29.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", profiles=list(result), queried_knobs=len(names), receipt=str(out / "recipe-values29.json"))))


if __name__ == "__main__":
    main()
