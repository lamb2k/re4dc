#!/usr/bin/env python3
"""Compile the real dying-actor FIFO path excluded by missing-private-data flags.

Uses complete Make-derived public native_ui flags, adding exactly the recorded
RE4DC_ACTOR_GANADO_DEATH_FADE=1 compile define. This is a source-branch target
check, not a supported game recipe, private-asset build, link or runtime test.
Pinned-base/current absent/zero preprocessed and object identity are checked;
the diagnostic-enabled full translation unit is also compiled.
"""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b24_fade_build", HERE / "build_controls.py")
build = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = build
spec.loader.exec_module(build)
ROOT, profile = build.ROOT, build.profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    baseline = out / "baseline-tree"
    baseline.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", build.BASELINE], cwd=ROOT))) as archive:
        archive.extractall(baseline, filter="data")
    paths = [Path(__file__), HERE / "build_controls.py", ROOT / "port/dreamcast/game/platform/native_ui.cpp",
             ROOT / "port/dreamcast/game/platform/include/native_ui_actor_fade.inc",
             ROOT / "port/dreamcast/game/platform/include/actor_death_fade.h",
             ROOT / "port/dreamcast/game/platform/include/draw_setup_audit.h"]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in paths}
    builder = profile.Build(out)
    rows = {}
    for name in ("baseline", "absent", "zero", "audit"):
        tree = baseline if name == "baseline" else ROOT
        options = build.QA + (["DRAW_SETUP_AUDIT=1"] if name == "audit" else
                              [knob + "=0" for knob in build.KNOBS] if name == "zero" else [])
        flags, receipt, sources = profile.derive(out / name, cxx, kos, sdk, options, tree=tree, units=("native_ui",))
        source = sources["native_ui"]
        original = flags["native_ui"]
        common = [flag for flag in original if not flag.startswith("-DRE4DC_ACTOR_GANADO_DEATH_FADE=")]
        common += ["-DRE4DC_ACTOR_GANADO_DEATH_FADE=1"]
        if name == "zero":
            common += ["-DRE4DC_" + knob + "=0" for knob in build.KNOBS]
        common += ["-iquote", str(source.parent)]
        artifacts = {}
        for suffix, phase in (("ii", ["-E", "-P"]),
                              ("o", ["-c", "-fstack-usage", "-MMD", "-MF", out / (name + ".d")])):
            destination = out / (name + "." + suffix)
            builder.run([*common, "-x", "c++", "-", *phase, "-o", destination], cwd=source.parent,
                        source=source.read_bytes(), label=name + "-" + suffix)
            artifacts[suffix] = dict(bytes=destination.stat().st_size, sha256=profile.sha(destination))
            if suffix == "o":
                stack = profile.stack_usage(destination.with_suffix(".su"))
                artifacts[suffix].update(profile.sections(destination), stack_usage_sha256=profile.sha(destination.with_suffix(".su")),
                                        max_function_frame_bytes=max((row["bytes"] for row in stack), default=0),
                                        compiler_reported_function_count=len(stack),
                                        fade_stack_frames=[row for row in stack if "actor_fade" in row["function"]])
            if name in ("absent", "zero"):
                assert destination.read_bytes() == (out / ("baseline." + suffix)).read_bytes(), (name, suffix, "identity")
        deps = build.dependencies(out / (name + ".d"), tree, source.parent)
        assert "port/dreamcast/game/platform/include/native_ui_actor_fade.inc" in deps
        if tree == ROOT:
            for path, digest in deps.items():
                assert frozen.get(path, digest) == digest, (path, "changed during fade gate")
                frozen[path] = digest
        text = (out / (name + ".ii")).read_text()
        assert "bool actor_fade_drain_head()" in text
        if name == "audit":
            part = text.split("bool actor_fade_drain_head()", 1)[1].split("extern \"C\" int re4dc_model_actor_fade_reserve", 1)[0]
            assert "const re4dc::dsa24::Scope dsa_model(re4dc::dsa24::ModelList);" in part
        row = receipt["profiles"]["native_ui"]
        rows[name] = dict(artifacts=artifacts, make_flags=original, compile_flags=common,
                          overrides=options, generated_headers=row["generated_headers"], recipe_inputs=row["recipe_inputs"],
                          dependency_sha256=deps)
        print("PASS actor-fade", name, flush=True)
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, "source changed; rerun"
    report = dict(status="PASS", scope=__doc__, baseline=build.BASELINE, source_sha256=frozen,
                  explicit_compile_override="-DRE4DC_ACTOR_GANADO_DEATH_FADE=1 (all arms)",
                  compiler_sha256=profile.sha(cxx), configurations=rows,
                  off_identity_comparisons=4, audit_hook_present=True,
                  limits="Actual complete SH4 native_ui translation unit, including the real actor-fade ticket/drain include. Public Make recipe plus explicitly forced compile define only; no fabricated data, private model assets, final game link, console execution or actor-fade output/parity claim.")
    (out / "fade-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", receipt=str(out / "fade-controls.json"))))


if __name__ == "__main__":
    main()
