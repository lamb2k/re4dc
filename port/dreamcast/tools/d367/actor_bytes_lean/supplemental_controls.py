#!/usr/bin/env python3
"""Compile supported MOVCA, CHAR_CHUNK and UV16 actor compatibility profiles.

MOVCA deliberately disables retained ARGB: complete ON/OFF TUs and objects must
be identical. CHAR_CHUNK 1/2 use the public grouped-direct recipe. UV16 uses the
existing direct-off compatibility profile because COARSE_ONE_SUBMIT explicitly
requires UV16=0. Every profile also proves zero-vs-integration identity.
"""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_actor_fast.cpp"
import build_profile
import build_controls

CASES = (("movca", 1, ("ACTOR_MOVCA=1",)), ("chunk1", 1, ("CHAR_CHUNK=1",)),
         ("chunk2", 1, ("CHAR_CHUNK=2",)), ("uv16", 0, ("NATIVE_ACTOR_UV16=1",)))


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    tree = output / "baseline-tree"
    build_controls.archive_tree(tree, args.baseline)
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    source_hash = build_profile.sha(SOURCE)
    builder = build_profile.Build(output)
    results = {}
    for name, direct, overrides in CASES:
        rows = {}
        for arm in ("baseline", "zero", "on"):
            destination = output / (name + "-" + arm + "-profile")
            kwargs = dict(setup_values=(1,), direct_values=(direct,), cone_values=(0,),
                lean=1 if arm == "on" else None if arm == "baseline" else 0, overrides=overrides)
            if arm == "baseline":
                with build_profile.source_tree(tree):
                    profiles, profile = build_profile.derive(destination, compiler, kos, sdk, **kwargs)
            else:
                profiles, profile = build_profile.derive(destination, compiler, kos, sdk, **kwargs)
            flags = profiles[f"s1-d{direct}-c0"]
            source = tree / SOURCE.relative_to(ROOT) if arm == "baseline" else SOURCE
            for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                target = output / (name + "-" + arm + "." + suffix)
                extra = ["-DRE4DC_ACTOR_BYTES_LEAN=0"] if arm == "zero" else []
                builder.run([*flags, *extra, "-x", "c++", "-", *phase, "-o", target], cwd=source.parent,
                    source=source.read_bytes(), label=name + "-" + arm + "-" + suffix)
                row = dict(sha256=build_profile.sha(target), bytes=target.stat().st_size)
                if suffix == "o":
                    row.update(build_profile.sections(target))
                    row["stack_usage"] = build_profile.stack_usage(target.with_suffix(".su"))
                rows[arm + "." + suffix] = row
                if arm == "zero" or name == "movca" and arm == "on":
                    assert target.read_bytes() == (output / (name + "-baseline." + suffix)).read_bytes(), (
                        name, arm, suffix, "required object/TU identity")
            rows[arm + "_profile"] = profile
        results[name] = dict(direct=direct, overrides=overrides, production=rows,
            zero_identity=True, on_off_identity=name == "movca")
        print("PASS", name, flush=True)
    assert build_profile.sha(SOURCE) == source_hash, "runtime source changed during supplemental build"
    report = dict(status="PASS", baseline=args.baseline, scope=__doc__, source_sha256=source_hash, cases=results,
        off_identity_comparisons=8, movca_on_identity_comparisons=2)
    (output / "supplemental-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--baseline", default=build_controls.BASELINE)
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], profiles=list(result["cases"])) ))


if __name__ == "__main__":
    main()
