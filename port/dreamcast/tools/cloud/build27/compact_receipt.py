#!/usr/bin/env python3
"""Compact Build27 qualification receipts while retaining exact numeric results."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
spec = importlib.util.spec_from_file_location("wep27_compact", HERE.parent / "build24/compact_receipt.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commands_removed(value):
    if isinstance(value, list):
        return [commands_removed(item) for item in value]
    if isinstance(value, dict):
        return {key: commands_removed(item) for key, item in value.items() if key != "command"}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS"
    if "artifacts" in raw:
        prepared = copy.deepcopy(raw)
        for receipt in prepared["profiles"].values():
            for row in receipt["profiles"].values():
                assert row["flags"][0].startswith("-")
                row["flags"].insert(0, raw["compiler_path"])
        result = shared.compact_controls(prepared, source)
        result["explicit_zero_defines"] = ["-DRE4DC_WEP_MODULES_27=0"]
        for name, units in raw["artifacts"].items():
            for unit, row in units.items():
                result["artifacts"][name][unit]["o"]["relevant_stack_frames"] = [frame for frame in row["o"]["stack_usage"]
                    if any(token in frame["function"] for token in ("weapon27", "weaponLoad", "ReadWepData", "debugWeapon",
                        "cItemMgr::arm", "loadRelData", "revert", "linkRelData", "re4dc_module_bind", "Weapon"))]
        for name, row in raw["make_states"].items():
            state = result["make_state_checks"][name]
            value = state["controls"].pop("GAME_OBJS")
            replacements = [(str(source.parent / (name + "-make")), "$PROFILE"),
                            (str(source.parent / "baseline-tree"), "$TREE"), (str(ROOT), "$TREE")]
            state["normalized_game_objects_sha256"] = shared.packed(shared.normalize(value, replacements))
        result["make_state_identity"] = "Complete MODULES/MODULE_ARGS/PLATFORM_OBJS/GAME_OBJS/GAME_LDFLAGS compared after source/profile path normalization; raw preprocessed and object bytes are unmodified."
    else:
        result = commands_removed(copy.deepcopy(raw))
        if "modules" in result and "profiles" in result:
            recipes, flag_sets, rows = {}, {}, {}
            for name, row in result["profiles"].items():
                recipe = row.pop("recipe_inputs")
                flags = row.pop("flags")
                row.pop("compile_command", None)
                rows[name] = dict(row, recipe=shared.intern(recipes, recipe, "recipe-"),
                                 flags=shared.intern(flag_sets, flags, "flags-"))
            result.update(profiles=rows, recipe_inputs=recipes, flag_sets=flag_sets)
    result["raw_receipt_sha256"] = sha(source)
    result["compactor_sha256"] = sha(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status="PASS", output=str(args.output), bytes=args.output.stat().st_size)))


if __name__ == "__main__":
    main()
