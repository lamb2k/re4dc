#!/usr/bin/env python3
"""Build26 public Make-derived target compilation and disabled byte identity.

The pinned integration tree is archived independently. Every changed existing
translation unit is compared as complete preprocessed source and target object
with all controls absent, each control explicitly zero, and all explicitly zero,
with QA_LINK off/on. Debug records and line markers are omitted consistently.
Enabled audit/fix compositions compile the real translation units. No private
asset, full linked game, emulator, console or image-equivalence claim is made.
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
BASELINE = "9a66e3fce8899f69378f12b5f9517f297f1fa314"
KOS_PIN = "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
SDK_PIN = "33fa4850cacb30dd0ad35485ef035526ec4ce782"
KNOBS = ("DRAW_FALLBACK_AUDIT", "ACTOR_CLIP_FRONT26", "SCENERY_CLIP_INDEXED26")
spec = importlib.util.spec_from_file_location("b26_shared_controls", HERE.parent / "build24/build_controls.py")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)
profile = shared.profile
UNITS = {
    "main": ("src/game/main.o", "../../../src/game/main.cpp"),
    "esp_sub": ("src/game/esp_sub.o", "../../../src/game/esp_sub.cpp"),
    "model_bridge": ("model_bridge.o", "model_bridge.cpp"),
    "native_actor_fast": ("platform/native_actor_fast.o", "platform/native_actor_fast.cpp"),
    "native_model": ("platform/native_model.o", "platform/native_model.cpp"),
    "native_static": ("platform/native_static.o", "platform/native_static.cpp"),
    "native_ui": ("platform/native_ui.o", "platform/native_ui.cpp"),
    "native_ps2_world": ("platform/native_ps2_world.o", "platform/native_ps2_world.cpp"),
    "chunk_submit": ("platform/chunk_submit.o", "platform/chunk_submit.cpp"),
    "qa_menu": ("qa_menu.o", "qa_menu.cpp"),
    "draw_fallback_audit": ("draw_fallback_audit.o", "draw_fallback_audit.cpp"),
}
NEW_UNITS = ("draw_fallback_audit",)
BASE_UNITS = tuple(name for name in UNITS if name not in NEW_UNITS)
profile.UNITS.update(UNITS)
QA = ["DBG_WARP=1", "WARP_AFTER_RESET=1", "QA_MENU=1", "BENCHMARK=0",
      "PMC_ROW=0", "WORLD_METER=1", "NMR_POOL_LOD=0"]
OFF_PROFILES = {"qa": QA + ["QA_LINK=0"], "link": QA + ["QA_LINK=1"]}
ON_PROFILES = {
    "audit": QA + [KNOBS[0] + "=1", "QA_LINK=0"],
    "audit-link": QA + [KNOBS[0] + "=1", "QA_LINK=1"],
    "actor-fix": QA + [KNOBS[1] + "=1", "QA_LINK=0"],
    "world-fix": QA + [KNOBS[2] + "=1", "QA_LINK=0"],
    "fixes": QA + [name + "=1" for name in KNOBS[1:]] + ["QA_LINK=1"],
    "audit-fixes": QA + [name + "=1" for name in KNOBS] + ["QA_LINK=1"],
    "audit-fixes-reuse": QA + [name + "=1" for name in KNOBS] + ["QA_LINK=1",
        "ACTOR_SETUP_LEAN=1", "ACTOR_CLIP_REUSE=1", "ACTOR_BYTES_LEAN=1", "SCENERY_CLIP_GATHER=1",
        "ESP_SETUP_LEAN=1", "DRAW_SETUP_AUDIT=1", "DRAW_SETUP_AUDIT_XLU=1"],
}
CONTROL_UNITS = {KNOBS[0]: tuple(UNITS), KNOBS[1]: ("native_actor_fast",), KNOBS[2]: ("native_static",)}
OBJECT_FIELDS = ("PLATFORM_OBJS", "GAME_OBJS", "GAME_LDFLAGS")


def probe(out, tree, kos, sdk, options):
    out.mkdir(parents=True, exist_ok=False)
    fields = (*KNOBS, "QA_LINK", "QA_MENU", *OBJECT_FIELDS)
    query = out / "query.mk"
    query.write_text(".PHONY: b26-state\nb26-state:\n\t@:\n" + "\n".join(
        f"$(info B26_STATE {name}=$({name}))" for name in fields) + "\n")
    command, _ = profile.make_command(out, tree, kos, sdk, options, "b26-state")
    command[3:3] = ["-f", "Makefile", "-f", str(query)]
    result = subprocess.run(command, cwd=tree / "port/dreamcast/game", capture_output=True, text=True)
    output = result.stdout + result.stderr
    (out / "make.log").write_text(output)
    state = dict(line[len("B26_STATE "):].split("=", 1) for line in output.splitlines()
                 if line.startswith("B26_STATE "))
    return dict(command=command, returncode=result.returncode, state=state,
                error=output[-2000:] if result.returncode else None)


def verify_toolchain(builder, cxx, kos, sdk, receipt_path):
    prefix = str(cxx).removesuffix("g++")
    compiler = builder.run([cxx, "--version"], label="compiler").decode().splitlines()[0]
    verbose = subprocess.run([str(cxx), "-v"], capture_output=True, text=True).stderr
    assert "15.2.0" in compiler and "Thread model: kos" in verbose, verbose
    linker = builder.run([prefix + "ld", "--version"], label="linker").decode().splitlines()[0]
    assert "2.45.1" in linker, linker
    actual = json.loads(receipt_path.read_text())
    known = json.loads((HERE.parent / "build24/receipts/toolchain.json").read_text())
    assert actual["image"] == known["image"], "different compiler image"
    restored = cxx.parents[5]
    for relative, digest in known["original_executable_sha256"].items():
        original = restored / (relative + ".real")
        if not original.exists():
            original = restored / relative
        assert original.is_file() and profile.sha(original) == digest, (relative, "pinned executable mismatch")
        assert actual["original_executable_sha256"].get(relative) == digest, (relative, "receipt mismatch")
    for folder, pin in ((kos, KOS_PIN), (sdk, SDK_PIN)):
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip() == pin
    return dict(compiler=compiler, compiler_path=str(cxx), compiler_sha256=profile.sha(cxx), linker=linker, kos=KOS_PIN, sdk=SDK_PIN,
                pinned_executable_sha256=known["original_executable_sha256"],
                toolchain_receipt=dict(path=str(receipt_path), sha256=profile.sha(receipt_path)))


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
    toolchain = verify_toolchain(builder, cxx, kos, sdk, args.toolchain_receipt.resolve())
    tree = out / "baseline-tree"
    tree.mkdir()
    baseline_sha = subprocess.check_output(["git", "rev-parse", args.baseline], cwd=ROOT, text=True).strip()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", baseline_sha], cwd=ROOT))) as archive:
        archive.extractall(tree, filter="data")
    sources_to_hash = [(DC / "game" / source).resolve() for _, source in UNITS.values()]
    sources_to_hash += [Path(__file__), DC / "game/Makefile", DC / "build-public.sh",
                       DC / "tools/d367/rr/recipe.conf", DC / "tools/d367/build-r21.sh",
                       *sorted((DC / "game").glob("*.mk"))]
    frozen = {str(source.relative_to(ROOT)): profile.sha(source) for source in sources_to_hash}
    artifacts, receipts, flag_rows, states, closure, links, disabled, enabled = {}, {}, {}, {}, {}, {}, [], []
    explicit_zero = {}

    def compile_unit(name, unit, flags, sources, source_tree, zeros=()):
        source = sources[unit]
        common = [*flags[unit], *["-DRE4DC_" + knob + "=0" for knob in zeros], "-iquote", str(source.parent)]
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
                closure.setdefault(name, {})[unit] = shared.dependencies(out / f"{name}-{unit}.d", source_tree, source.parent)
                if source_tree == ROOT:
                    for path, digest in closure[name][unit].items():
                        assert frozen.get(path, digest) == digest, (path, "source changed during gate")
                        frozen[path] = digest
        artifacts.setdefault(name, {})[unit] = row

    if args.only != "on":
        off_arms = [("baseline", ()), ("absent", ())]
        off_arms += [("zero-" + knob.lower(), (knob,)) for knob in KNOBS]
        off_arms += [("zero", KNOBS)]
        for kind, options in OFF_PROFILES.items():
            for arm, zeros in off_arms:
                name = kind + "-" + arm
                source_tree = tree if arm == "baseline" else ROOT
                extra = [knob + "=0" for knob in zeros]
                flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk, options + extra,
                                                                tree=source_tree, units=BASE_UNITS)
                flag_rows[name] = flags
                explicit_zero[name] = ["-DRE4DC_" + knob + "=0" for knob in zeros]
                for unit in BASE_UNITS:
                    if arm != "baseline":
                        left = [shared.normalized(x, out / (kind + "-baseline"), tree)
                                for x in flag_rows[kind + "-baseline"][unit]]
                        right = [shared.normalized(x, out / name, ROOT) for x in flags[unit]]
                        assert left == right, (name, unit, "Make flags differ with controls disabled")
                    compile_unit(name, unit, flags, sources, source_tree, zeros)
                    if arm != "baseline":
                        for suffix in ("ii", "o"):
                            assert (out / f"{name}-{unit}.{suffix}").read_bytes() == (
                                out / f"{kind}-baseline-{unit}.{suffix}").read_bytes(), (name, unit, suffix)
                            disabled.append(dict(profile=kind, control=arm, unit=unit, artifact=suffix, identical=True))
                    print("PASS", name, unit, flush=True)
                states[name] = probe(out / (name + "-make"), source_tree, kos, sdk, options + extra)
                assert states[name]["returncode"] == 0, states[name]
                if arm != "baseline":
                    assert all(states[name]["state"][knob] == "0" for knob in KNOBS), states[name]
                    for field in OBJECT_FIELDS:
                        assert shared.normalized(states[name]["state"][field], out / (name + "-make"), ROOT) == shared.normalized(
                            states[kind + "-baseline"]["state"][field], out / (kind + "-baseline-make"), tree), (name, field)

    if args.only != "off":
        for kind, options in ON_PROFILES.items():
            name = "on-" + kind
            units = BASE_UNITS + (NEW_UNITS if KNOBS[0] + "=1" in options else ())
            flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk, options, units=units)
            for unit in units:
                for knob, targets in CONTROL_UNITS.items():
                    if knob + "=1" in options and unit in targets:
                        assert "-DRE4DC_" + knob + "=1" in flags[unit], (name, unit, knob, "Make lost enabled control")
                compile_unit(name, unit, flags, sources, ROOT)
            combined = out / (name + "-combined.o")
            builder.run([prefix + "ld", "-m", "shlelf", "-r", *[out / f"{name}-{unit}.o" for unit in units],
                         "-o", combined], label=name + "-partial-link")
            undefined = builder.run([prefix + "nm", "-u", "-C", combined], label=name + "-undefined").decode()
            unresolved = [line for line in undefined.splitlines() if "dfa26" in line or "draw_fallback" in line]
            assert not unresolved, (name, unresolved)
            links[name] = dict(sha256=profile.sha(combined), new_audit_hooks_resolved=True,
                               scope="Relocatable link; ordinary game/KOS/QA_LINK symbols remain unresolved")
            states[name] = probe(out / (name + "-make"), ROOT, kos, sdk, options)
            assert states[name]["returncode"] == 0, states[name]
            for knob in KNOBS:
                assert states[name]["state"][knob] == str(int(knob + "=1" in options)), (name, knob, states[name])
            enabled.append(dict(profile=kind, new_audit_hooks_resolved=True, compiled_units=list(units)))
            print("PASS enabled", kind, flush=True)
    rejected = []
    for knob in KNOBS:
        for value in ("", "2", "0 1"):
            state = probe(out / f"reject-{len(rejected)}", ROOT, kos, sdk, QA + [knob + "=" + value])
            assert state["returncode"] != 0, (knob, value, "invalid value accepted")
            rejected.append(dict(knob=knob, value=value, **state))
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, "sources changed during gate; rerun"
    report = dict(status="PASS", scope=__doc__, baseline=baseline_sha, gate_half=args.only or "both", knobs=KNOBS,
                  source_sha256=frozen, **toolchain,
                  validation_only_overrides=dict(NMR_POOL_LOD=0,
                      reason="Selected CH2 NMR_POOL_LOD=1 needs private GANADO_LOD assets; public fallback disables GANADO_LOD. Mirrored base/current override; no release edit."),
                  off_identity_comparisons=len(disabled), disabled_identity=disabled, enabled_compiles=enabled,
                  explicit_zero_by_profile=explicit_zero, artifacts=artifacts, profiles=receipts, dependency_sha256=closure,
                  make_states=states, partial_links=links, make_rejections=rejected,
                  limitations="Full target translation-unit identity without debug records; no full-image, private asset, visual/gameplay, hardware, D-cache-miss or frame-time acceptance.")
    (out / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_comparisons=len(disabled), enabled=enabled,
                          receipt=str(out / "target-controls.json"))))


if __name__ == "__main__":
    main()
