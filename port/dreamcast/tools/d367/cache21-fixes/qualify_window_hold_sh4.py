#!/usr/bin/env python3
"""Qualify the whole native_ui.cpp SH-4 object without linking/staging a game."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

from qualify_readem_display_flags_sh4 import GAME, REPO, run, sha, space

KNOBS = {
    "UI_VRAM": 1, "TEX_RESIDENT": 1, "VRAM_PAGES": 1, "MOVIE_WINDOW": 1,
    "SUBSCREEN": 1, "SS_PACK": 1, "SS_HOLD_RESTORE": 1,
    "UI_FRAG_WINDOW": 1, "UI_FRAG_LATCH": 1, "PVR_STREAM": 1, "PS2_WORLD_DRAW": 1,
    "COARSE": 1, "PACE_CATCHUP": 2, "PACE_TRANS_SKIP": 4063,
    "TREE_IMPOSTOR": 1,
    "NATIVE_MESH": 1, "MESH_LOD": 1,
    "D349_RENDERER_STACK": 1, "TA_DIRECT": 1,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline-ref", default="a3727579d2f3a8c49cc6877e330f8a783780ce99")
    args = parser.parse_args()
    start_free = space(128)
    args.out.mkdir(parents=True, exist_ok=False)
    ui = "port/dreamcast/game/platform/native_ui.cpp"
    source = args.out / "native_ui.cpp"
    baseline_source = subprocess.check_output(["git", "-C", str(REPO), "show", f"{args.baseline_ref}:{ui}"])
    candidate_source = (REPO / ui).read_bytes()
    baseline_make = args.out / "baseline.Makefile"
    baseline_make.write_bytes(subprocess.check_output(["git", "-C", str(REPO), "show", f"{args.baseline_ref}:port/dreamcast/game/Makefile"]))
    rows = []
    for variant, enabled, data in (("baseline", 0, baseline_source), ("disabled", 0, candidate_source), ("enabled", 1, candidate_source)):
        out = args.out / variant
        out.mkdir()
        make = ["make", "--no-print-directory", "-f", str(baseline_make if variant == "baseline" else GAME / "Makefile"),
                f"OBJDIR={out}", *(f"{key}={value}" for key, value in KNOBS.items())]
        if variant != "baseline":
            make.append(f"SS_WINDOW_HOLD_RESTORE={enabled}")
        target = out / "platform/native_ui.o"
        dry = run([*make, "-n", target], out / "make-command.log")
        commands = [shlex.split(line) for line in dry.splitlines() if line.startswith("kos-c++ ")]
        assert len(commands) == 1
        command = commands[0]
        # Generate only the forced headers this one object needs, through their
        # actual Make targets. No other compilation or link target is requested.
        for i, value in enumerate(command):
            if value == "-include":
                header = Path(command[i + 1])
                if header.is_absolute() and header.is_relative_to(out) and not header.exists():
                    run([*make, header], out / (header.name + ".log"))
        command[command.index("platform/native_ui.cpp")] = str(source)
        command[1:1] = ["-iquote", str(GAME / "platform")]
        assert ("-DRE4DC_SS_WINDOW_HOLD_RESTORE=1" in command) == bool(enabled)
        source.write_bytes(data)
        target.parent.mkdir(parents=True)
        (out / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        run(command, out / "compile.log")
        stripped = out / "native_ui-stripped.o"
        run(["sh-elf-objcopy", "--strip-debug", target, stripped], out / "strip.log")
        rows.append({"variant": variant, "source_sha256": sha(source), "stripped_native_ui_o_sha256": sha(stripped),
                     "size": run(["sh-elf-size", stripped], out / "size.txt")})
    assert rows[0]["stripped_native_ui_o_sha256"] == rows[1]["stripped_native_ui_o_sha256"]
    invalid = []
    tests = [({"SS_WINDOW_HOLD_RESTORE": value}, "must be 0 or 1") for value in ("2", "-1", "yes")]
    tests += [({"SS_WINDOW_HOLD_RESTORE": "1", key: "0"}, "needs SS_HOLD_RESTORE=1 MOVIE_WINDOW=1 TEX_RESIDENT=1")
              for key in ("SS_HOLD_RESTORE", "MOVIE_WINDOW", "TEX_RESIDENT")]
    for i, (changed, expected) in enumerate(tests):
        knobs = {**KNOBS, **changed}
        # Avoid an earlier fragment-policy guard masking the specific missing
        # MOVIE_WINDOW/TEX_RESIDENT prerequisite that this repair validates.
        knobs["UI_FRAG_WINDOW"] = 0
        if knobs.get("TEX_RESIDENT") == "0":
            knobs["SS_PACK"] = knobs["SS_HOLD_RESTORE"] = knobs["MOVIE_WINDOW"] = 0
        result = subprocess.run(["make", "--no-print-directory", "-n", *(f"{key}={value}" for key, value in knobs.items())],
                                cwd=GAME, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        (args.out / f"invalid-{i}.log").write_text(result.stdout)
        assert result.returncode and expected in result.stdout, (knobs, result.stdout)
        invalid.append(changed)
    receipt = {"scope": "Actual whole SH-4 native_ui.o; matching-source default/off identity; no linked-program/guest/hardware gate",
               "baseline_revision": args.baseline_ref, "knobs": KNOBS, "start_C_free_bytes": start_free,
               "finish_C_free_bytes": space(64), "objects": rows, "invalid_values_or_prerequisites_rejected": invalid}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
