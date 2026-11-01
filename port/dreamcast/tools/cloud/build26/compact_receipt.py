#!/usr/bin/env python3
"""Compact Build26 target receipts without changing costs or identity hashes."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
spec = importlib.util.spec_from_file_location("b26_compact_shared", HERE.parent / "build24/compact_receipt.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_controls(raw, source):
    # Build18 stores flags without the executable; the shared compactor expects
    # a complete invocation prefix. Supply the actual verified compiler, never
    # mistake its first -O2 flag for a compiler path.
    prepared = copy.deepcopy(raw)
    for receipt in prepared["profiles"].values():
        for row in receipt["profiles"].values():
            assert row["flags"][0].startswith("-"), "unexpected compiler in stored flag vector"
            row["flags"].insert(0, raw["compiler_path"])
    result = shared.compact_controls(prepared, source)
    result["explicit_zero_defines"] = ["-DRE4DC_" + knob + "=0" for knob in raw["knobs"]]
    grouped = {}
    for row in raw["disabled_identity"]:
        name = row["profile"] + "-" + row["control"]
        grouped[(name, row["unit"])] = row["profile"] + "-baseline"
    result["identity_matrix"] = []
    for (name, unit), baseline in grouped.items():
        left = raw["artifacts"][baseline][unit]
        right = raw["artifacts"][name][unit]
        check = dict(profile=name, unit=unit,
                     preprocessed_identical=left["ii"]["sha256"] == right["ii"]["sha256"],
                     whole_object_identical=left["o"]["sha256"] == right["o"]["sha256"])
        assert check["preprocessed_identical"] and check["whole_object_identical"], check
        result["identity_matrix"].append(check)
    for name, row in result["profiles"].items():
        definitions = raw["explicit_zero_by_profile"].get(name, [])
        row["explicit_zero_defines"] = bool(definitions)
        row["extra_defines"] = definitions
    for name, units in raw["artifacts"].items():
        for unit, row in units.items():
            result["artifacts"][name][unit]["o"]["relevant_stack_frames"] = [
                frame for frame in row["o"]["stack_usage"] if any(token in frame["function"] for token in
                    ("dfa26", "actor_clip26", "clip_strip", "clip_stream_strip", "front_triangle", "diag_rows",
                     "re4dc_actor_submit", "ModelRoot::Draw", "EspDraw"))]
    for name, row in raw["make_states"].items():
        value = row["state"]["GAME_OBJS"]
        replacements = [(str(source.parent / (name + "-make")), "$PROFILE"),
                        (str(source.parent / "baseline-tree"), "$TREE"), (str(ROOT), "$TREE")]
        result["make_state_checks"][name]["controls"].pop("GAME_OBJS", None)
        result["make_state_checks"][name]["normalized_game_objects_sha256"] = shared.packed(shared.normalize(value, replacements))
    result["make_state_identity"] = "The gate compared full PLATFORM_OBJS/GAME_OBJS/GAME_LDFLAGS strings after source/profile path normalization. Object/preprocessed bytes were not normalized or stripped."
    return result


def remove_commands(value):
    if isinstance(value, list):
        return [remove_commands(item) for item in value]
    if isinstance(value, dict):
        return {key: remove_commands(item) for key, item in value.items() if key != "command"}
    return value


def compact_cost(raw):
    result = remove_commands(copy.deepcopy(raw))
    # Keep every numeric traffic field. Repeated model command paths are the
    # only discarded information; source scripts reproduce those commands.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS"
    result = compact_controls(raw, source) if "artifacts" in raw else compact_cost(raw)
    result["raw_receipt_sha256"] = sha(source)
    result["compactor_sha256"] = sha(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status="PASS", input_bytes=source.stat().st_size,
                          output_bytes=args.output.stat().st_size, output=str(args.output))))


if __name__ == "__main__":
    main()
