#!/usr/bin/env python3
"""Compact Build25 receipts, retaining identity and numeric cost evidence.

The Build24 compactor interns identical target flags, recipe inputs and
dependency hashes. This adapter retains lighting-specific stack frames and
the Build25 control. Cost numbers/traffic are unchanged; repeated command
paths are reconstructible from the committed scripts and omitted here.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b25_compact_shared", HERE.parent / "build24/compact_receipt.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_controls(raw, source):
    result = shared.compact_controls(raw, source)
    result["explicit_zero_defines"] = ["-DRE4DC_ACTOR_LIGHT_FAST_ONLY=0"]
    for name, units in raw["artifacts"].items():
        for unit, row in units.items():
            result["artifacts"][name][unit]["o"]["relevant_stack_frames"] = [
                frame for frame in row["o"]["stack_usage"] if any(token in frame["function"] for token in
                    ("light25", "fast_only", "pass_lights", "part_lights", "probe_of", "build_lights",
                     "light_part", "diag_rows", "light_vertex", "one_chunk", "re4dc_actor_submit"))]
    return result


def remove_commands(value):
    if isinstance(value, list):
        return [remove_commands(item) for item in value]
    if isinstance(value, dict):
        return {key: remove_commands(item) for key, item in value.items() if key != "command"}
    return value


def compact_cost(raw):
    result = remove_commands(copy.deepcopy(raw))
    for row in result["cases"]:
        for phase in row["phases"].values():
            traffic = phase["traffic"]
            for kind in ("uncached", "store_queue"):
                assert all(value == 0 for value in traffic[kind].values())
            phase["traffic"] = dict(traffic["cached"], demand_line_visits=traffic["demand_line_visits"],
                                    repeated_demand_line_visits=traffic["repeated_demand_line_visits"],
                                    regions=traffic["regions"])
    result["traffic_scope"] = "Cached architectural demand traffic only. No uncached or store-queue accesses were observed. Unique lines and repeated line visits are not cache misses. Opcode fetches are excluded; literals and stack are included."
    result["model_commands"] = dict(warm="hwsim --elf <view.elf> --out <case> --perfect-ic --perfect-dc --no-dma --sq-cost 0 <case.bin>",
                                    cold_i="hwsim --elf <view.elf> --out <case> --perfect-dc --no-dma --sq-cost 0 <case.bin>")
    return result


def compact_build(raw, source):
    result = {key: value for key, value in raw.items() if key != "arms"}
    result["arms"] = {}
    for arm, row in raw["arms"].items():
        result["arms"][arm] = {key: value for key, value in row.items() if key not in ("profile", "stack_usage")}
        compiled = row["profile"]["profiles"]["native_actor_fast"]
        result["arms"][arm]["profile"] = dict(flags=compiled["flags"], generated_headers=compiled["generated_headers"],
                                                overrides=compiled["overrides"], recipe_inputs=compiled["recipe_inputs"])
        stack = row["stack_usage"]
        result["arms"][arm]["stack"] = dict(
            compiler_reported_function_count=len(stack), max_function_frame_bytes=max(x["bytes"] for x in stack),
            raw_stack_usage_sha256=sha(source.parent / arm / "fixture.su"),
            relevant_frames=[frame for frame in stack if any(token in frame["function"] for token in
                ("light25", "fast_only", "pass_lights", "part_lights", "probe_of", "build_lights", "fixture_"))])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS"
    result = compact_controls(raw, source) if "artifacts" in raw else compact_cost(raw) if "cases" in raw else compact_build(raw, source)
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
