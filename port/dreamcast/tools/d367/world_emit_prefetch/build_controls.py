#!/usr/bin/env python3
"""Whole-TU OFF identity and five existing switches x PREF_WALK composition.

The exact baseline Make tree is archived independently. Actual Make flags and
generated headers must match absent/zero, with ON adding only the static-world
define. Complete preprocessed text and raw objects compare byte for byte.
Debug records/line markers are omitted consistently, not executable options.
Identical compiler inputs reuse a recorded artifact; no comparison is omitted.
"""
import argparse
from contextlib import contextmanager
import hashlib
import io
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "20df6734578cacc7033bb32a660d4b466a7cfbe9"
KNOBS = ("SCENERY_SELECT_ONLY", "SCENERY_SUBMIT_BATCH", "SCENERY_REPLAY_LEAN",
         "SCENERY_UV_SNAPSHOT", "SCENERY_SELECT_LEAN2", "PREF_WALK")
NEW_KNOB = "SCENERY_EMIT_PREFETCH"
NEW_DEFINE = "RE4DC_SCENERY_EMIT_PREFETCH"
import build_profile as profile_tools


@contextmanager
def source_tree(tree):
    modules = (profile_tools, profile_tools.helpers, profile_tools.helpers.release_profile)
    saved = [(m, m.ROOT, m.DC) for m in modules]
    try:
        for m in modules:
            m.ROOT, m.DC = tree, tree / "port/dreamcast"
        yield
    finally:
        for m, root, dc in saved:
            m.ROOT, m.DC = root, dc


def normalized(flags, profile, tree):
    return [x.replace(str(profile), "<PROFILE>").replace(str(tree), "<SOURCE>") for x in flags]


def headers(profile, root):
    return {str(Path(p).relative_to(root)): digest for p, digest in profile["generated_headers"].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sh4-cxx", type=Path, required=True)
    parser.add_argument("--kos-root", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--profile-only", action="store_true")
    parser.add_argument("--quick", action="store_true", help="smoke: release's three switches on, UV/selection/PREF both values")
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    flags, profile = profile_tools.derive(out / "release-profile", compiler, kos, sdk)
    if args.profile_only:
        (out / "profile.json").write_text(json.dumps(dict(flags=flags, profile=profile), indent=2) + "\n")
        print(json.dumps(dict(status="PASS", profile=str(out / "profile.json")))); return
    tree = out / "baseline-tree"; tree.mkdir()
    archive = subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(tree, filter="data")
    with source_tree(tree):
        _, old_profile = profile_tools.derive(out / "baseline-profile", compiler, kos, sdk)
    baseline_platform = out / "baseline-platform"; (baseline_platform / "include").mkdir(parents=True)
    # Changed quote includes resolve to the independently archived versions.
    # Other platform/room inputs are immutable and identified in the manifest.
    for p in (tree / "port/dreamcast/game/platform/include").glob("scenery_*"):
        if p.is_file():
            shutil.copyfile(p, baseline_platform / "include" / p.name)
    sources = {}
    for tu, _, _ in profile_tools.SPECIFICATIONS:
        path = DC / "game/platform" / (tu + ".cpp")
        sources[tu] = (path, (tree / path.relative_to(ROOT)).read_bytes(), path.read_bytes())
    watched = [p[0] for p in sources.values()] + [DC / "game/scenery19.mk",
        DC / "game/cache20.mk", DC / "tools/d367/rr/recipe.conf",
        *sorted((DC / "game/platform/include").glob("scenery_*")),
        *[DC / "room" / name for name in ("mesh_fastpath.hpp", "mesh_fastpath_sched.hpp",
            "mesh_strip_lean.hpp", "instanced_mesh.hpp", "static_room_prepare.hpp")],
        HERE / "build_profile.py", HERE / "build_controls.py"]
    hashes = {str(p.relative_to(ROOT)): profile_tools.sha(p) for p in watched if p.is_file()}
    builder = profile_tools.Build(out); cache = {}; cache_receipts = []

    def compile_one(label, common, content, cwd, suffix):
        target = out / (label + "." + suffix)
        phase = ["-E", "-P"] if suffix == "ii" else ["-c", "-fstack-usage"]
        key = hashlib.sha256(json.dumps([common, str(cwd), phase], separators=(",", ":")).encode() + content).hexdigest()
        if key in cache:
            prior = cache[key]; shutil.copyfile(prior, target)
            if suffix == "o":
                shutil.copyfile(prior.with_suffix(".su"), target.with_suffix(".su"))
            cache_receipts.append(dict(target=target.name, reused_from=prior.name, input_sha256=key))
        else:
            builder.run([*common, "-x", "c++", "-", *phase, "-o", target], cwd=cwd, source=content, label=label)
            cache[key] = target
        result = dict(bytes=target.stat().st_size, sha256=profile_tools.sha(target), compiler_input_sha256=key)
        if suffix == "o":
            result.update(profile_tools.sections(target))
            result["stack_usage"] = profile_tools.stack_usage(target.with_suffix(".su"))
        return result

    configurations = list(itertools.product((0, 1), repeat=6))
    if args.quick:
        configurations = [bits for bits in configurations if bits[:3] == (1, 1, 1)]
    production, make_checks = {}, {}
    for bits in configurations:
        name = "s%d-b%d-r%d-u%d-l%d-p%d" % bits
        options = ["%s=%d" % (k, v) for k, v in zip(KNOBS, bits)]
        with source_tree(tree):
            base_flags, base_rec = profile_tools.expand_existing(out / "baseline-profile", compiler, sdk,
                old_profile, options, prefix=name)
        arm_flags, arm_receipts = {}, {}
        for arm, extra in (("absent", []), ("zero", [NEW_KNOB + "=0"]), ("on", [NEW_KNOB + "=1"])):
            arm_flags[arm], arm_receipts[arm] = profile_tools.expand_existing(out / "release-profile", compiler,
                sdk, profile, options + extra, prefix=name + "-" + arm)
        production[name], make_checks[name] = {}, {}
        for tu, (path, old, current) in sources.items():
            baseline = normalized(base_flags[tu], out / "baseline-profile", tree)
            for arm in ("absent", "zero", "on"):
                actual = normalized(arm_flags[arm][tu], out / "release-profile", ROOT)
                if arm == "on" and tu == "native_static":
                    define = "-D" + NEW_DEFINE + "=1"
                    assert actual.count(define) == 1, (name, tu, "missing ON define")
                    actual = [x for x in actual if x != define]
                assert actual == baseline, (name, tu, arm, "Make flag identity")
                assert headers(arm_receipts[arm][tu], out / "release-profile") == headers(
                    base_rec[tu], out / "baseline-profile"), (name, tu, arm, "generated headers")
            make_checks[name][tu] = dict(flags_identical_off=True, generated_headers_identical=True,
                on_adds_only_static_define=True,
                absent_flags_sha256=hashlib.sha256(json.dumps(baseline).encode()).hexdigest())
            records = {}
            for arm in ("baseline", "absent", "zero", "on"):
                content = old if arm == "baseline" else current
                common = arm_flags["absent" if arm == "baseline" else arm][tu] + ["-iquote", str(path.parent)]
                if arm == "zero" and tu == "native_static":
                    common.append("-D" + NEW_DEFINE + "=0")
                cwd = baseline_platform if arm == "baseline" else path.parent
                label = name + "-" + tu + "-" + arm
                for suffix in ("ii", "o"):
                    records[arm + "." + suffix] = compile_one(label, common, content, cwd, suffix)
                    if arm in ("absent", "zero") or (arm == "on" and tu != "native_static"):
                        before = out / (name + "-" + tu + "-baseline." + suffix)
                        assert (out / (label + "." + suffix)).read_bytes() == before.read_bytes(), (label, suffix, "OFF/unaffected identity")
            production[name][tu] = records
        print("PASS", name, flush=True)
    for path, digest in hashes.items():
        assert profile_tools.sha(ROOT / path) == digest, (path, "source changed during build")
    count, tus = len(configurations), len(sources)
    report = dict(status="PASS", baseline=args.baseline, knob=NEW_KNOB, scope=__doc__, quick=args.quick,
        configurations=count, translation_units=tus, off_identity_comparisons=count * tus * 2 * 2,
        enabled_unaffected_tu_identities=count * (tus - 1) * 2, unique_compiler_invocations=len(cache),
        compiler=builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0],
        source_sha256=hashes, profile=profile, make_identity=make_checks, production=production,
        artifact_reuse=cache_receipts, frame_population=dict(r101_parts=87, r100_parts=50,
            meshlets_per_part="not observed; no implicit extrapolation"))
    (out / "build-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "configurations", "translation_units",
        "off_identity_comparisons", "enabled_unaffected_tu_identities", "unique_compiler_invocations")}))


if __name__ == "__main__":
    main()
