#!/usr/bin/env python3
"""Summarize matched relocatable SH4 groups and relevant compiler stack frames.

This consumes successful full-TU receipts, verifies input object/source hashes,
and creates matching baseline relocatable groups. Sizes include the entire
compiled diagnostic/renderer group before final executable garbage collection;
they are not final image sizes or whole-program peak-stack measurements.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b24_summary_build", HERE / "build_controls.py")
build = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = build
spec.loader.exec_module(build)
profile = build.profile
WANTED = ("clip_strip", "reuse_strip", "Gather", "MeshDraw::chunk_emit", "dsa24", "actor_fade_drain")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS" and raw["gate_half"] == "both"
    assert raw["source_sha256"] == {name: profile.sha(build.ROOT / name) for name in raw["source_sha256"]}
    cxx = args.sh4_cxx.resolve()
    assert profile.sha(cxx) == raw["compiler_sha256"]
    prefix = str(cxx).removesuffix("g++")
    builder = profile.Build(out)
    groups = {}
    for name in ("qa-baseline", "pmu-baseline", *raw["partial_links"]):
        units = raw["artifacts"][name]
        for unit, row in units.items():
            assert profile.sha(source.parent / (name + "-" + unit + ".o")) == row["o"]["sha256"]
        if name.endswith("-baseline"):
            obj = out / (name + "-combined.o")
            builder.run([prefix + "ld", "-m", "shlelf", "-r", *[source.parent / (name + "-" + unit + ".o") for unit in units],
                         "-o", obj], label=name)
        else:
            obj = source.parent / (name + "-combined.o")
            assert profile.sha(obj) == raw["partial_links"][name]["sha256"]
        stack = {}
        for unit, row in units.items():
            frames = row["o"]["stack_usage"]
            stack[unit] = dict(max_function_frame_bytes=max((frame["bytes"] for frame in frames), default=0),
                               relevant_frames=[frame for frame in frames if any(word in frame["function"] for word in WANTED)])
        groups[name] = dict(object_sha256=profile.sha(obj), **profile.sections(obj), stack=stack)
        if not name.endswith("-baseline"):
            base = "pmu-baseline" if "pmu" in name else "qa-baseline"
            groups[name]["compared_to"] = base
            groups[name]["delta_bytes"] = {field: groups[name][field] - groups[base][field]
                                           for field in ("executable_bytes", "allocated_bytes", "zero_fill_bytes")}
    report = dict(status="PASS", scope=__doc__, groups=groups, baseline=raw["baseline"],
                  raw_target_receipt_sha256=profile.sha(source),
                  source_sha256={str(Path(__file__).relative_to(build.ROOT)): profile.sha(Path(__file__)),
                                 **raw["source_sha256"]},
                  off_identity_comparisons=raw["off_identity_comparisons"],
                  rejected_make_configurations=len(raw["make_rejections"]),
                  enabled_compositions=list(raw["partial_links"]),
                  limitations="No full game link/image or hardware frame. Static function frames cannot be added without call-graph analysis; dynamic synthetic peaks are in the separate cost receipts. The PMU37 group compares against event15 baseline, so its total also includes the event-selector difference.")
    (out / "object-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", groups=len(groups), receipt=str(out / "object-summary.json"))))


if __name__ == "__main__":
    main()
