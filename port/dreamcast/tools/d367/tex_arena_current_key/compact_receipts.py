#!/usr/bin/env python3
"""Retain small, path-independent summaries of successful local controls."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def stack_rows(rows):
    selected = []
    for row in rows:
        function = row["function"]
        if ("Entry*" in function and "load(const Re4dcUiImage" in function) or "tex_final_refusal(" in function:
            selected.append(dict(row, function=re.sub(r"^.*?:\d+:\d+:", "", function)))
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=HERE / "receipts")
    args = parser.parse_args()
    host, target = json.loads(args.host.read_text()), json.loads(args.target.read_text())
    assert host["status"] == target["status"] == "PASS"
    ui = "port/dreamcast/game/platform/native_ui.cpp"
    assert host["source_sha256"][ui] == target["source_sha256"][ui]
    for manifest in (host["source_sha256"], target["source_sha256"]):
        for name, expected in manifest.items():
            assert sha(ROOT / name) == expected, (name, "source changed since controls")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    variants = []
    for row in host["variants"]:
        variants.append({**{key: row[key] for key in ("name", "kind", "fix", "log", "core_pin", "no_top", "cases")},
                         "terminal_refusals": sum(line.startswith("REFUSAL TEX-REFUSE ") for line in row["stdout"].splitlines()),
                         "sanitizer_diagnostics": bool(row["stderr"])})
    host_summary = dict(status="PASS", scope=host["scope"], compiler=host["compiler"],
                        sanitizer="UBSan; -fno-sanitize-recover=all", source_sha256=host["source_sha256"],
                        gate_sha256=host["gate_sha256"], extracted_sha256=host["extracted_sha256"],
                        unit_test_sha256=sha(ROOT / "port/dreamcast/tests/test_tex_arena_current_key.py"),
                        variants=variants, case_executions=host["case_executions"],
                        limitations="Synthetic package/filesystem operations; actual classifier/load()/allocator. No release assets, renderer output, hardware timing, or complete console regression proof.")
    artifacts = {}
    for name, row in target["artifacts"].items():
        obj = row["o"]
        artifacts[name] = dict(preprocessed=row["ii"], object={key: obj[key] for key in (
            "bytes", "sha256", "executable_bytes", "allocated_bytes", "zero_fill_bytes")},
            selected_stack_usage=stack_rows(obj["stack_usage"]))
    current_profile = target["profile_receipts"]["absent"]["profiles"]["native_ui"]
    recipe = current_profile["recipe_inputs"]
    target_summary = dict(status="PASS", scope=target["scope"], baseline=target["baseline"],
                          compiler=target["compiler"], compiler_sha256=target["compiler_sha256"],
                          linker=target["linker"], kos=target["kos"], sdk=target["sdk"],
                          source_sha256=target["source_sha256"],
                          recipe=dict(release=recipe["release"],
                                      missing_asset_overrides=recipe["missing_asset_overrides"],
                                      input_manifest_sha256=canonical_sha(recipe["source_sha256"]),
                                      input_count=len(recipe["source_sha256"])),
                          off_identity_comparisons=target["off_identity_comparisons"], artifacts=artifacts,
                          deltas=target["deltas"], make_states={name: value["state"] for name, value in target["make_states"].items()},
                          rejected_make_configurations=[{key: value for key, value in row.items()
                                                         if key in ("knob", "value", "options", "returncode")}
                                                        for row in target["make_rejections"]],
                          runtime_dependency_manifest_sha256={name: canonical_sha(value)
                                                              for name, value in target["dependency_sha256"].items()},
                          memory_access_scope="The fix retains the bounded core_nkeys scan (at most 16 two-word keys). It adds no allocation, file I/O, table traversal, or VRAM data store. Diagnostic logging separately scans allocator bookkeeping and emits one line per terminal refusal.",
                          performance="Warm/cold cycles, console cache behavior and whole-frame time not measured; no speed claim.",
                          stack_limit="Per-function GCC stack reports; helper and callees are additional. These are not full call-chain peak measurements.",
                          limitations=target["limitations"])
    for name, value in (("host-controls.json", host_summary), ("target-controls.json", target_summary)):
        path = out / name
        path.write_text(json.dumps(value, indent=2) + "\n")
        print(path)


if __name__ == "__main__":
    main()
