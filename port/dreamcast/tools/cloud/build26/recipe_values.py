#!/usr/bin/env python3
"""Record resolved draw-path knob values from the actual public Make recipes."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b26_recipe_controls", HERE / "build_controls.py")
controls = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controls
spec.loader.exec_module(controls)
profile = controls.profile
PATTERNS = ("SCENERY_%", "PS2_WORLD_%", "PS2_STRIP_%", "PS2_PVS%", "PS2_INTERIOR_%", "MESH_%", "ACTOR_%",
            "NATIVE_ACTOR%", "NATIVE_STATIC%", "NATIVE_RENDER%", "MODEL_%", "ESP_%", "UI_%", "TEX_%",
            "FRAME_QUEUE%", "WORLD_%", "QA_%", "DRAW_%", "GIGANTE_%", "CROWD_%", "LEON_LIGHT_%", "GANADO_LIT%",
            "D349_%", "TA_%", "FX_EARLY_%", "CHAR_%", "RIGID_%", "COARSE_%", "STATIC_OBJ_%", "LEON_SKIN_%")
EXPLICIT = ("G1_PRESORT_LAZY", "COPY_LEAN", "BRIDGE_LEAN", "NMR_POOL_LOD", "MEMSET_LEAN", "SG_SELECT_LEAN",
            "CPU_BACKFACE", "HW_LEAN", "EFFECT_SPRITES", "SHADOWS", "MV_SHADOWS", "BARN28_DIAG",
            "UI_HANDLES", "UI_QUAD_LEAN", "UI_PALETTE_SLOTS", "ESP_SETUP_LEAN", "ESP_SPRITE_FAST")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    rows = {}
    for name, options in (("public-game", ["NMR_POOL_LOD=0"]),
                          ("public-qa-audit", controls.QA + ["QA_LINK=1", "DRAW_FALLBACK_AUDIT=1"])):
        directory = out / name
        directory.mkdir()
        query = directory / "query.mk"
        query.write_text(".PHONY: b26-values\nb26-values:\n\t@:\n"
            "B26_NAMES := $(sort $(filter " + " ".join(PATTERNS) + ",$(.VARIABLES)) " + " ".join(EXPLICIT) + ")\n"
            "$(foreach name,$(B26_NAMES),$(info B26_VALUE $(name)=$($(name))))\n")
        command, recipe = profile.make_command(directory, controls.ROOT, args.kos_root.resolve(), args.sdk_root.resolve(), options, "b26-values")
        command[3:3] = ["-f", "Makefile", "-f", str(query)]
        completed = subprocess.run(command, cwd=controls.DC / "game", capture_output=True, text=True)
        output = completed.stdout + completed.stderr
        (directory / "make.log").write_text(output)
        assert completed.returncode == 0, output[-4000:]
        values = dict(line[len("B26_VALUE "):].split("=", 1) for line in output.splitlines() if line.startswith("B26_VALUE "))
        assert values and all(key in values for key in EXPLICIT)
        rows[name] = dict(overrides=options, values=values, recipe_inputs=recipe, command=command)
    report = dict(status="PASS", baseline=controls.BASELINE, scope=__doc__, profiles=rows,
                  script_sha256=profile.sha(Path(__file__)),
                  limitations="Resolved public game/QA Make values with NMR_POOL_LOD=0 because private Ganado data is unavailable. These are build settings, not runtime package admission, counters or recorded chapter frequencies.")
    (out / "recipe-values.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", profiles={key: len(row["values"]) for key, row in rows.items()},
                         receipt=str(out / "recipe-values.json"))))


if __name__ == "__main__":
    main()
