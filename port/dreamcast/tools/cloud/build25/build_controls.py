#!/usr/bin/env python3
"""Compile Build25 with the public Make recipe and prove disabled byte identity.

The baseline is archived independently from Git. Complete production actor and
QA translation units are compared with the new control absent and explicitly
zero, in both QA_LINK compositions. Debug records and source line markers are
omitted consistently. Enabled variants compile the real translation units;
the target object must contain no reference to either old vertex-light pass.
This gate does not build a complete game or supply private character assets.
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
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "7acd7d8fd6a828d4e596fdb57516a0655b4dc032"
KOS_PIN = "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
SDK_PIN = "33fa4850cacb30dd0ad35485ef035526ec4ce782"
KNOB = "ACTOR_LIGHT_FAST_ONLY"
MACRO = "RE4DC_" + KNOB
spec = importlib.util.spec_from_file_location("b25_shared_controls", HERE.parent / "build24/build_controls.py")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)
profile = shared.profile
UNITS = {
    "native_actor_fast": ("platform/native_actor_fast.o", "platform/native_actor_fast.cpp"),
    "native_model": ("platform/native_model.o", "platform/native_model.cpp"),
    "native_static": ("platform/native_static.o", "platform/native_static.cpp"),
    "qa_menu": ("qa_menu.o", "qa_menu.cpp"),
}
profile.UNITS.update(UNITS)
QA = ["DBG_WARP=1", "WARP_AFTER_RESET=1", "QA_MENU=1", "BENCHMARK=0",
      "PMC_ROW=0", "WORLD_METER=1", "NMR_POOL_LOD=0"]
OFF_PROFILES = {"qa": QA + ["QA_LINK=0"], "link": QA + ["QA_LINK=1"]}
ON_PROFILES = {
    "recipe": QA + [KNOB + "=1", "QA_LINK=0"],
    "link": QA + [KNOB + "=1", "QA_LINK=1"],
    "probe-off": QA + [KNOB + "=1", "QA_LINK=0", "ACTOR_PROBE_LIGHT=0",
                       "GANADO_LIT=0", "LEON_LIGHT_FILL=0", "GANADO_LIT_FILL=0"],
    "legacy-light-controls": QA + [KNOB + "=1", "QA_LINK=0", "ACTOR_EXACT_FAST=0",
                                   "GIGANTE_LIGHTS=0", "CROWD_FLAT=0", "ACTOR_BYTES_LEAN=0"],
    "lean-clip": QA + [KNOB + "=1", "QA_LINK=1", "ACTOR_SETUP_LEAN=1",
                       "ACTOR_BYTES_LEAN=1", "ACTOR_CLIP_REUSE=1"],
    "light-cap": QA + [KNOB + "=1", "QA_LINK=1", "ACTOR_LIGHT_CAP=1", "BARN28_DIAG=1",
                       "DRAW_SETUP_AUDIT=1", "GIGANTE_LIGHTS=0"],
}


def probe(out, tree, kos, sdk, options):
    out.mkdir(parents=True, exist_ok=False)
    fields = (KNOB, "ACTOR_LIGHT_CAP", "BARN28_DIAG", "QA_LINK", "PLATFORM_OBJS", "GAME_LDFLAGS")
    query = out / "query.mk"
    query.write_text(".PHONY: b25-state\nb25-state:\n\t@:\n" + "\n".join(
        f"$(info B25_STATE {name}=$({name}))" for name in fields) + "\n")
    command, _ = profile.make_command(out, tree, kos, sdk, options, "b25-state")
    command[3:3] = ["-f", "Makefile", "-f", str(query)]
    result = subprocess.run(command, cwd=tree / "port/dreamcast/game", capture_output=True, text=True)
    output = result.stdout + result.stderr
    (out / "make.log").write_text(output)
    state = dict(line[len("B25_STATE "):].split("=", 1) for line in output.splitlines()
                 if line.startswith("B25_STATE "))
    return dict(command=command, returncode=result.returncode, state=state,
                error=output[-2000:] if result.returncode else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root", "toolchain-receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--only", choices=("off", "on"))
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(out)
    prefix = str(cxx).removesuffix("g++")
    compiler = builder.run([cxx, "--version"], label="compiler").decode().splitlines()[0]
    verbose = subprocess.run([str(cxx), "-v"], capture_output=True, text=True).stderr
    assert "15.2.0" in compiler and "Thread model: kos" in verbose, verbose
    linker = builder.run([prefix + "ld", "--version"], label="linker").decode().splitlines()[0]
    assert "2.45.1" in linker, linker
    toolchain = json.loads(args.toolchain_receipt.read_text())
    known = json.loads((HERE.parent / "build24/receipts/toolchain.json").read_text())
    assert toolchain["image"] == known["image"], "different compiler image"
    restored = cxx.parents[5]
    executable_checks = {}
    for relative, digest in known["original_executable_sha256"].items():
        original = restored / (relative + ".real")
        if not original.exists():
            original = restored / relative
        assert original.is_file(), (relative, "missing pinned executable")
        assert profile.sha(original) == digest, (relative, "pinned executable mismatch")
        assert toolchain["original_executable_sha256"].get(relative) == digest, (relative, "receipt mismatch")
        executable_checks[relative] = digest
    for folder, pin in ((kos, KOS_PIN), (sdk, SDK_PIN)):
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip() == pin
    tree = out / "baseline-tree"
    tree.mkdir()
    baseline_sha = subprocess.check_output(["git", "rev-parse", args.baseline], cwd=ROOT, text=True).strip()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", baseline_sha], cwd=ROOT))) as archive:
        archive.extractall(tree, filter="data")
    source_hashes = {}
    for source in [DC / "game" / source for _, source in UNITS.values()]:
        source = source.resolve()
        source_hashes[str(source.relative_to(ROOT))] = profile.sha(source)
    for source in [Path(__file__), DC / "game/Makefile", DC / "build-public.sh",
                   DC / "tools/d367/rr/recipe.conf", DC / "tools/d367/build-r21.sh",
                   *sorted((DC / "game").glob("*.mk"))]:
        source_hashes[str(source.relative_to(ROOT))] = profile.sha(source)
    artifacts, receipts, flag_rows, states, closure, links, disabled, enabled = {}, {}, {}, {}, {}, {}, [], []

    def compile_unit(name, unit, flags, sources, source_tree, zero=False):
        source = sources[unit]
        common = [*flags[unit], *(["-D" + MACRO + "=0"] if zero else []),
                  "-iquote", str(source.parent)]
        row = {}
        for suffix, phase in (("ii", ["-E", "-P"]),
                              ("o", ["-c", "-fstack-usage", "-MMD", "-MF", out / f"{name}-{unit}.d"])):
            destination = out / f"{name}-{unit}.{suffix}"
            builder.run([*common, "-x", "c++", "-", *phase, "-o", destination], cwd=source.parent,
                        source=source.read_bytes(), label=f"{name}-{unit}-{suffix}")
            row[suffix] = dict(bytes=destination.stat().st_size, sha256=profile.sha(destination))
            if suffix == "o":
                row[suffix].update(profile.sections(destination),
                                   stack_usage=profile.stack_usage(destination.with_suffix(".su")))
                closure.setdefault(name, {})[unit] = shared.dependencies(
                    out / f"{name}-{unit}.d", source_tree, source.parent)
                if source_tree == ROOT:
                    for path, digest in closure[name][unit].items():
                        assert source_hashes.get(path, digest) == digest, (path, "changed during gate")
                        source_hashes[path] = digest
        artifacts.setdefault(name, {})[unit] = row

    if args.only != "on":
        for kind, options in OFF_PROFILES.items():
            for arm, extra in (("baseline", []), ("absent", []), ("zero", [KNOB + "=0"])):
                name = kind + "-" + arm
                source_tree = tree if arm == "baseline" else ROOT
                flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk, options + extra,
                                                                tree=source_tree, units=tuple(UNITS))
                flag_rows[name] = flags
                for unit in UNITS:
                    if arm != "baseline":
                        left = [shared.normalized(x, out / (kind + "-baseline"), tree)
                                for x in flag_rows[kind + "-baseline"][unit]]
                        right = [shared.normalized(x, out / name, ROOT) for x in flags[unit]]
                        assert left == right, (name, unit, "Make flags differ with control disabled")
                    compile_unit(name, unit, flags, sources, source_tree, arm == "zero")
                    if arm != "baseline":
                        for suffix in ("ii", "o"):
                            assert (out / f"{name}-{unit}.{suffix}").read_bytes() == (
                                out / f"{kind}-baseline-{unit}.{suffix}").read_bytes(), (name, unit, suffix)
                            disabled.append(dict(profile=kind, control=arm, unit=unit, artifact=suffix, identical=True))
                    print("PASS", name, unit, flush=True)
                states[name] = probe(out / (name + "-make"), source_tree, kos, sdk, options + extra)
                assert states[name]["returncode"] == 0, states[name]
                if arm != "baseline":
                    assert states[name]["state"][KNOB] == "0", states[name]
                    for field in ("PLATFORM_OBJS", "GAME_LDFLAGS"):
                        assert shared.normalized(states[name]["state"][field], out / (name + "-make"), ROOT) == shared.normalized(
                            states[kind + "-baseline"]["state"][field], out / (kind + "-baseline-make"), tree), (name, field)
    if args.only != "off":
        for kind, options in ON_PROFILES.items():
            name = "on-" + kind
            flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk, options, units=tuple(UNITS))
            for unit in UNITS:
                assert "-D" + MACRO + "=1" in flags[unit], (name, unit, "Make lost enabled control")
                compile_unit(name, unit, flags, sources, ROOT)
            forbidden = ("pass_lights_exact", "pass_lights(", "flat_fallback(", "build_lights(", "lights_asm", "re4dc_avk_light",
                         "evaluate_prepared_source_lighting", "evaluate_prepared_actor_lighting",
                         "evaluate_source_lighting")
            for unit in ("native_actor_fast", "native_model", "native_static"):
                obj = out / f"{name}-{unit}.o"
                symbols = builder.run([prefix + "nm", "-C", obj], label=name + "-" + unit + "-symbols").decode()
                old_vertex_passes = [line for line in symbols.splitlines() if any(token in line for token in forbidden)]
                assert not old_vertex_passes, (name, unit, "vertex light evaluators remain in enabled object", old_vertex_passes)
            combined = out / (name + "-combined.o")
            builder.run([prefix + "ld", "-m", "shlelf", "-r", *[out / f"{name}-{unit}.o" for unit in UNITS],
                         "-o", combined], label=name + "-partial-link")
            undefined = builder.run([prefix + "nm", "-u", "-C", combined], label=name + "-undefined").decode()
            unresolved_new = [line for line in undefined.splitlines()
                              if "light_fast_only" in line or "actor_light25" in line]
            assert not unresolved_new, (name, unresolved_new)
            links[name] = dict(sha256=profile.sha(combined), new_light_hooks_resolved=True,
                               scope="Relocatable link; ordinary game/KOS/QA_LINK symbols remain unresolved")
            states[name] = probe(out / (name + "-make"), ROOT, kos, sdk, options)
            assert states[name]["returncode"] == 0 and states[name]["state"][KNOB] == "1", states[name]
            if kind == "light-cap":
                assert states[name]["state"]["ACTOR_LIGHT_CAP"] == "1", states[name]
                assert states[name]["state"]["BARN28_DIAG"] == "1", states[name]
                assert "-DRE4DC_ACTOR_LIGHT_CAP=1" in flags["native_actor_fast"], "Make lost light-cap composition"
                assert "-DRE4DC_BARN28_DIAG=1" in flags["native_actor_fast"], "Make lost barn diagnostics"
            enabled.append(dict(profile=kind, vertex_evaluator_symbols_absent=True))
            print("PASS enabled", kind, flush=True)
    rejected = []
    for value in ("", "2", "0 1"):
        state = probe(out / f"reject-{len(rejected)}", ROOT, kos, sdk, QA + [KNOB + "=" + value])
        assert state["returncode"] != 0, (value, "invalid value accepted")
        rejected.append(dict(value=value, **state))
    assert source_hashes == {path: profile.sha(ROOT / path) for path in source_hashes}, "sources changed during gate; rerun"
    report = dict(status="PASS", scope=__doc__, baseline=baseline_sha, gate_half=args.only or "both",
                  source_sha256=source_hashes, compiler=compiler, compiler_sha256=profile.sha(cxx), linker=linker,
                  kos=KOS_PIN, sdk=SDK_PIN,
                  pinned_executable_sha256=executable_checks,
                  toolchain_receipt=dict(path=str(args.toolchain_receipt), sha256=profile.sha(args.toolchain_receipt)),
                  validation_only_overrides=dict(NMR_POOL_LOD=0,
                      reason="Selected CH2 NMR_POOL_LOD=1 needs private GANADO_LOD assets; public fallback disables GANADO_LOD. Mirrored base/current override; no release edit."),
                  off_identity_comparisons=len(disabled), disabled_identity=disabled, enabled_compiles=enabled,
                  artifacts=artifacts, profiles=receipts, dependency_sha256=closure, make_states=states,
                  partial_links=links, make_rejections=rejected,
                  limitations="Full target translation-unit identity without debug records; no full-image, private asset, visual/gameplay, hardware, D-cache-miss or frame-time acceptance.")
    (out / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_comparisons=len(disabled), enabled=enabled,
                          receipt=str(out / "target-controls.json"))))


if __name__ == "__main__":
    main()
