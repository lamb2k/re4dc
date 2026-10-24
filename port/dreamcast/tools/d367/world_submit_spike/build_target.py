#!/usr/bin/env python3
"""Compile complete world-submit TUs and check default/OFF program identity.

This gate uses the Make-expanded public Test22 options for each translation
unit. It does not link or run a game image. Optional target fixtures keep their
hardware edges explicit and do not substitute host timings for SH4 execution.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import build_profile
from build_profile import Build, sections, sha, stack_usage

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "86c1b91a72a8d6d419cf9c5fa0c335ff3f552a9d"
KNOB = "RE4DC_SCENERY_SUBMIT_BATCH"


def build(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    builder = Build(output)
    compiler = args.sh4_cxx.resolve()
    flags, profile = build_profile.derive(output / "release-profile", compiler,
                                         args.kos_root.resolve(), args.sdk_root.resolve())
    sources = {}
    production = {}
    for tu in ("native_static", "native_ui"):
        source_path = DC / ("game/platform/" + tu + ".cpp")
        path = str(source_path.relative_to(ROOT))
        current = source_path.read_bytes()
        old = subprocess.check_output(["git", "show", args.baseline + ":" + path], cwd=ROOT)
        sources[path] = hashlib.sha256(current).hexdigest()
        (output / (tu + ".cpp")).write_bytes(current)
        (output / ("baseline-" + tu + ".cpp")).write_bytes(old)
        common = [*flags[tu], *("-D" + item for item in args.define)]
        records = {}
        variants = [("baseline", old, None), ("absent", current, None), ("zero", current, 0)]
        if not args.off_only:
            variants.append(("on", current, 1))
        for name, source, knob in variants:
            extra = [] if knob is None else ["-D" + KNOB + "=" + str(knob)]
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                destination = output / (tu + "-" + name + "." + suffix)
                builder.run([*common, *extra, "-x", "c++", "-", *phase, "-o", destination],
                            cwd=source_path.parent, source=source, label=tu + "-" + name)
                row = dict(bytes=destination.stat().st_size, sha256=sha(destination))
                if suffix == "o":
                    row.update(sections(destination))
                    row["stack_usage"] = stack_usage(destination.with_suffix(".su"))
                records[name + "." + suffix] = row
        for suffix in ("ii", "o"):
            baseline = (output / (tu + "-baseline." + suffix)).read_bytes()
            for name in ("absent", "zero"):
                assert (output / (tu + "-" + name + "." + suffix)).read_bytes() == baseline, (tu, name, suffix, "OFF identity")
        production[tu] = records
    for name, expected in sources.items():
        assert sha(ROOT / name) == expected, (name, "source changed during build")
    report = dict(status="PASS", baseline=args.baseline, knob=KNOB,
                  scope="Two complete production TU compilation and OFF identity; no linked game, frame or hardware timing",
                  compiler=builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0],
                  source_sha256=sources, profile=profile, production=production)
    (output / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--define", action="append", default=[])
    parser.add_argument("--off-only", action="store_true")
    report = build(parser.parse_args())
    print(json.dumps({"status": report["status"], "scope": report["scope"]}))


if __name__ == "__main__":
    main()
