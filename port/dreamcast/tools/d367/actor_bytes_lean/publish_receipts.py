#!/usr/bin/env python3
"""Publish compact, path-independent Build7 measurement and identity receipts.

The raw scratch receipts retain compile commands and disassemblies. Published
receipts retain their hashes, source/tool hashes, profile source identity, full
comparison counts and the quantitative rows used by the report. No result is
recomputed from a prose claim; every numeric row comes from a completed gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    result = json.loads(path.read_text())
    assert result["status"] == "PASS", path
    return result


def tools(names):
    return {str((HERE / name).relative_to(ROOT)): sha(HERE / name) for name in names}


def verify_sources(record):
    for name, digest in record.get("source_sha256", {}).items():
        path = ROOT / name
        assert path.exists() and sha(path) == digest, (name, "measured source changed")


def object_row(row):
    fields = ("sha256", "bytes", "executable_bytes", "allocated_bytes", "zero_fill_bytes")
    result = {name: row[name] for name in fields if name in row}
    if "stack_usage" in row:
        result["stack_bytes"] = {re.sub(r"^.*?:\d+:\d+:", "", item["function"]): item["bytes"]
                                 for item in row["stack_usage"]}
    return result


def traffic(row):
    fields = ("load_instructions", "store_instructions", "load_bytes", "store_bytes",
              "unique_read_lines", "unique_write_lines", "unique_data_lines")
    result = {name: row["cached"][name] for name in fields}
    result.update({name: row[name] for name in ("demand_line_visits", "repeated_demand_line_visits") if name in row})
    for name in ("vertex_cache", "argb"):
        if name in row:
            result[name] = {field: row[name][field] for field in fields}
    if "regions" in row:
        result["regions"] = {name: {field: part[field] for field in fields} for name, part in row["regions"].items()}
    if "prefetch" in row:
        result["prefetch"] = {name: value for name, value in row["prefetch"].items() if name != "scope"}
    return result


def recipe(profile):
    source = profile["recipe_inputs"]
    return {name: source[name] for name in ("recipe", "recipe_sha256", "current_ch2", "public_ch2",
        "removed_asset_path_assignments", "missing_asset_overrides", "source_sha256")}


def model(record):
    if not record: return None
    return {name: record[name] for name in ("scope", "source_sha256", "flags",
        "exact_dynamic_instruction_and_delay_slot_counts", "no_hardware_time_or_frame_speedup_claim")}


def publish(args):
    build, supplement, kernel, target_build, target = [read(path) for path in
        (args.build, args.supplement, args.kernel, args.target_build, args.target)]
    for record in (build, kernel, target_build, target): verify_sources(record)
    assert supplement["source_sha256"] == build["source_sha256"]["port/dreamcast/game/platform/native_actor_fast.cpp"]
    assert target["target_build_sha256"] == sha(args.target_build)
    source = build["source_sha256"]
    build_receipt = dict(status="PASS", baseline=build["baseline"], knob=build["knob"], scope=build["scope"],
        raw_receipt_sha256=sha(args.build), compiler=build["compiler"],
        off_identity_comparisons=build["off_identity_comparisons"], make_identity=build["make_identity"],
        source_sha256=source, tool_sha256=tools(("build_profile.py", "build_controls.py")),
        recipe=recipe(build["profiles"]["absent"]),
        production={name: {arm: object_row(row) for arm, row in arms.items()} for name, arms in build["production"].items()})
    supplemental_receipt = dict(status="PASS", baseline=supplement["baseline"], scope=supplement["scope"],
        raw_receipt_sha256=sha(args.supplement), source_sha256=supplement["source_sha256"],
        tool_sha256=tools(("build_profile.py", "build_controls.py", "supplemental_controls.py")),
        off_identity_comparisons=supplement["off_identity_comparisons"],
        movca_on_identity_comparisons=supplement["movca_on_identity_comparisons"],
        cases={name: {**{field: case[field] for field in ("direct", "overrides", "zero_identity", "on_off_identity")},
            "production": {arm: object_row(row) for arm, row in case["production"].items() if not arm.endswith("_profile")}}
            for name, case in supplement["cases"].items()})
    kernel_receipt = dict(status="PASS", scope=kernel["scope"], raw_receipt_sha256=sha(args.kernel),
        source_sha256=kernel["source_sha256"], tool_sha256=tools(("build_profile.py", "kernel_audit.py")),
        make_assembly_flags=kernel["build"]["applied_flags"],
        source_object_sha256={name: kernel["build"][name] for name in ("profile_sha256", "source_sha256", "object_sha256", "elf_sha256")},
        memory_controls=kernel["memory_controls"], kernel_controls=kernel["kernel_controls"], model=model(kernel["model"]),
        cases=[{**{name: case[name] for name in ("name", "vertices", "palette_run_length", "normal_stride", "scattered", "record_stride")},
            "combined_traffic": traffic(case["combined_traffic"]),
            "kernels": {name: dict(instructions=row["instructions"], warm_cycles=row["model_cycles"],
                cold_i_cycles=row["cold_icache"]["model_cycles"], peak_stack_bytes=row["peak_stack_bytes"],
                traffic=traffic(row["traffic"])) for name, row in case["kernels"].items()}}
            for case in kernel["cases"]])
    target_receipt = dict(status="PASS", scope=target["scope"], build_scope=target_build["scope"],
        raw_receipt_sha256=sha(args.target), raw_target_build_sha256=sha(args.target_build),
        source_sha256={**target_build["source_sha256"], **target["source_sha256"]},
        tool_sha256=tools(("build_profile.py", "target_build.py", "target_fixture.cpp.in", "target_run.py")),
        fixture_sha256=target_build["fixture_sha256"],
        extracted_fragments_sha256=target_build["extracted_fragments_sha256"],
        recipe=recipe(target_build["profile"]),
        memory_controls=target["memory_controls"], opcode_controls=target["opcode_controls"],
        models={name: model(row) for name, row in target["model"].items()},
        compiled_arms={name: {field: row[field] for field in ("sha256", "object_sha256", "sections")}
                       for name, row in target_build["arms"].items()},
        cases=[{**{name: case[name] for name in ("name", "entry", "kind", "meshlets", "shape", "counts")},
            "arms": {name: dict(instructions=row["instructions"], warm_cycles=row["model_cycles"],
                cold_i_cycles=row["cold_icache"]["model_cycles"], part_size=row["part_size"],
                peak_stack_bytes=row["peak_stack_bytes"], traffic=traffic(row["traffic"]),
                argb_sha256=row["argb_sha256"], observed_light_calls=row["observed_light_calls"],
                interval_line_touches=row["interval_line_touches"], interval_definition=row["interval_definition"],
                intervals=[traffic(interval) for interval in row["intervals"]]) for name, row in case["arms"].items()}}
            for case in target["cases"]])
    for name, receipt in (("build_receipt.json", build_receipt), ("supplemental_receipt.json", supplemental_receipt),
                          ("kernel_receipt.json", kernel_receipt), ("target_receipt.json", target_receipt)):
        path = args.output / name
        assert not path.exists(), (path, "refuse receipt overwrite")
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        print(name, path.stat().st_size, sha(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("build", "supplement", "kernel", "target-build", "target"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--output", type=Path, default=HERE)
    publish(parser.parse_args())


if __name__ == "__main__":
    main()
