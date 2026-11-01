#!/usr/bin/env python3
"""Compact Build28 target receipts without changing numeric evidence."""
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
spec = importlib.util.spec_from_file_location("b28_compact_shared", HERE.parent / "build24/compact_receipt.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def remove_commands(value):
    if isinstance(value, list):
        return [remove_commands(item) for item in value]
    if isinstance(value, dict):
        return {key: remove_commands(item) for key, item in value.items() if key != "command"}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    raw = json.loads(source.read_text())
    assert raw["status"] in ("PASS", "CONTROLLED_SYNTAX_PASS")
    if "artifacts" in raw:
        prepared = copy.deepcopy(raw)
        for receipt in prepared["profiles"].values():
            for row in receipt["profiles"].values():
                assert row["flags"][0].startswith("-")
                row["flags"].insert(0, raw["compiler_path"])
        result = shared.compact_controls(prepared, source)
        result["explicit_zero_defines"] = ["-DRE4DC_QA_LINK_REVIEW28=0"]
        for name, units in raw["artifacts"].items():
            for unit, row in units.items():
                # These three small TUs are the entire reviewed console scope.
                result["artifacts"][name][unit]["o"]["relevant_stack_frames"] = row["o"]["stack_usage"]
        for name, row in raw["make_states"].items():
            state = result["make_state_checks"][name]
            value = state["controls"].pop("GAME_OBJS")
            replacements = [(str(source.parent / (name + "-make")), "$PROFILE"),
                            (str(source.parent / "baseline-tree"), "$TREE"), (str(ROOT), "$TREE")]
            state["normalized_game_objects_sha256"] = shared.packed(shared.normalize(value, replacements))
        result["make_state_identity"] = "The gate compares complete PLATFORM_OBJS/GAME_OBJS/GAME_LDFLAGS after source/profile path normalization. Raw preprocessor and object bytes are unchanged. QA_LINK=0 excludes both link TUs even when review28=1."
    else:
        result = remove_commands(copy.deepcopy(raw))
    result["raw_receipt_sha256"] = sha(source)
    result["compactor_sha256"] = sha(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status=result["status"], output=str(args.output), bytes=args.output.stat().st_size)))


if __name__ == "__main__":
    main()
