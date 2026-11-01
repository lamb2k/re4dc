#!/usr/bin/env python3
"""Build24 complete Make-derived SH4 compilation and disabled byte identity.

The selected public recipe is read by the existing Build18 restricted reader;
no recipe shell code is executed and no game data is used. Every changed
translation unit is compared to the pinned integration tree with all three
new controls absent and explicitly zero. Enabled diagnostic/fix compositions
are compiled and relocatably linked. This is not a linked game or console run.
"""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "a9fa0b8850f762acbf3ce49e86d7c24394df894b"
KOS_PIN = "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
SDK_PIN = "33fa4850cacb30dd0ad35485ef035526ec4ce782"
KNOBS = ("DRAW_SETUP_AUDIT", "ACTOR_CLIP_REUSE", "SCENERY_CLIP_GATHER")
spec = importlib.util.spec_from_file_location("b24_make_profile", HERE.parent / "build18/build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)

UNITS = {
    "main": ("src/game/main.o", "../../../src/game/main.cpp"),
    "trans": ("src/game/trans.o", "../../../src/game/trans.cpp"),
    "native_ui": ("platform/native_ui.o", "platform/native_ui.cpp"),
    "native_static": ("platform/native_static.o", "platform/native_static.cpp"),
    "native_actor_fast": ("platform/native_actor_fast.o", "platform/native_actor_fast.cpp"),
    "native_model": ("platform/native_model.o", "platform/native_model.cpp"),
    "native_ps2_world": ("platform/native_ps2_world.o", "platform/native_ps2_world.cpp"),
    "qa_menu": ("qa_menu.o", "qa_menu.cpp"),
    "perf_phase_miss": ("perf_phase_miss.o", "perf_phase_miss.cpp"),
    "world_census24": ("world_census24.o", "world_census24.cpp"),
    "draw_setup_audit": ("draw_setup_audit.o", "draw_setup_audit.cpp"),
}
profile.UNITS.update(UNITS)
# Public assets disable GANADO_LOD; the selected CH2 recipe also requires its
# private NMR_POOL_LOD source. This validation-only override is mirrored across
# the pinned base and all current arms. No release recipe is changed.
QA = ["DBG_WARP=1", "WARP_AFTER_RESET=1", "QA_MENU=1", "BENCHMARK=0", "PMC_ROW=0", "WORLD_METER=1", "NMR_POOL_LOD=0"]
BASE_UNITS = tuple(name for name in UNITS if name not in ("perf_phase_miss", "world_census24", "draw_setup_audit"))
OFF_PROFILES = {
    "qa": (QA, BASE_UNITS),
    "pmu": (QA + ["WORLD_CENSUS24=1", "PERF_PHASE_MISS=1"],
            BASE_UNITS + ("perf_phase_miss", "world_census24")),
}
ON_PROFILES = {
    "audit": QA + ["DRAW_SETUP_AUDIT=1"],
    "actor-fix": QA + ["ACTOR_CLIP_REUSE=1"],
    "world-fix": QA + ["SCENERY_CLIP_GATHER=1"],
    "audit-fixes": QA + [name + "=1" for name in KNOBS],
    "audit-pmu15": QA + ["DRAW_SETUP_AUDIT=1", "WORLD_CENSUS24=1", "PERF_PHASE_MISS=1", "PERF_PHASE_MISS_EVENT=15"],
    "audit-pmu37-fixes": QA + [name + "=1" for name in KNOBS] +
                          ["WORLD_CENSUS24=1", "PERF_PHASE_MISS=1", "PERF_PHASE_MISS_EVENT=37"],
}


def normalized(value, output, tree):
    return value.replace(str(output), "<PROFILE>").replace(str(tree), "<SOURCE>")


def dependencies(path, tree, cwd):
    result = {}
    body = path.read_text().replace("\\\n", " ").split(":", 1)[1]
    for word in shlex.split(body):
        source = Path(word)
        if not source.is_absolute():
            source = cwd / source
        source = source.resolve()
        if source.is_file() and source.is_relative_to(tree):
            result[str(source.relative_to(tree))] = profile.sha(source)
    return result


def probe(out, tree, kos, sdk, options):
    out.mkdir(parents=True, exist_ok=False)
    fields = (*KNOBS, "PERF_PHASE_MISS", "WORLD_CENSUS24", "WORLD_METER", "PLATFORM_OBJS", "GAME_LDFLAGS")
    query = out / "query.mk"
    query.write_text(".PHONY: b24-state\nb24-state:\n\t@:\n" + "\n".join(
        f"$(info B24_STATE {name}=$({name}))" for name in fields) + "\n")
    command, _ = profile.make_command(out, tree, kos, sdk, options, "b24-state")
    command[3:3] = ["-f", "Makefile", "-f", str(query)]
    result = subprocess.run(command, cwd=tree / "port/dreamcast/game", capture_output=True, text=True)
    text = result.stdout + result.stderr
    (out / "make.log").write_text(text)
    state = dict(line[len("B24_STATE "):].split("=", 1) for line in text.splitlines()
                 if line.startswith("B24_STATE "))
    return dict(command=command, returncode=result.returncode, state=state,
                error=text[-2000:] if result.returncode else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root", "toolchain-receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--only", choices=("off", "on"), help="Run one independently reported gate half")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(out)
    prefix = str(cxx).removesuffix("g++")
    compiler = builder.run([cxx, "--version"], label="compiler").decode().splitlines()[0]
    verbose = subprocess.run([str(cxx), "-v"], capture_output=True, text=True).stderr
    assert "15.2.0" in compiler and "Thread model: kos" in verbose
    linker = builder.run([prefix + "ld", "--version"], label="linker").decode().splitlines()[0]
    assert "2.45.1" in linker
    newlib = cxx.parent.parent / "sh-elf/include/_newlib_version.h"
    assert '#define _NEWLIB_VERSION "4.6.0"' in newlib.read_text()
    for folder, pin in ((kos, KOS_PIN), (sdk, SDK_PIN)):
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip() == pin
    tree = out / "baseline-tree"
    tree.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT))) as archive:
        archive.extractall(tree, filter="data")
    source_hashes = {}
    for source in [DC / "game" / source for _, source in UNITS.values()]:
        source = source.resolve()
        if source.exists():
            source_hashes[str(source.relative_to(ROOT))] = profile.sha(source)
    source_hashes[str(Path(__file__).relative_to(ROOT))] = profile.sha(Path(__file__))
    for source in [DC / "game/Makefile", DC / "build-public.sh", DC / "tools/d367/rr/recipe.conf",
                   DC / "tools/d367/build-r21.sh", *sorted((DC / "game").glob("*.mk"))]:
        source_hashes[str(source.relative_to(ROOT))] = profile.sha(source)
    artifacts, receipts, flag_rows, states, closure, links = {}, {}, {}, {}, {}, {}

    def compile_unit(name, unit, flags, sources, source_tree, zero=False):
        source = sources[unit]
        common = [*flags[unit], *(["-DRE4DC_" + knob + "=0" for knob in KNOBS] if zero else []),
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
                closure.setdefault(name, {})[unit] = dependencies(out / f"{name}-{unit}.d", source_tree, source.parent)
                if source_tree == ROOT:
                    for path, digest in closure[name][unit].items():
                        assert source_hashes.get(path, digest) == digest, (path, "dependency changed during gate; rerun")
                        source_hashes[path] = digest
        artifacts.setdefault(name, {})[unit] = row

    comparisons = 0
    if args.only != "on":
        for kind, (options, units) in OFF_PROFILES.items():
            for arm, extra in (("baseline", []), ("absent", []), ("zero", [name + "=0" for name in KNOBS])):
                name = kind + "-" + arm
                source_tree = tree if arm == "baseline" else ROOT
                flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk, options + extra,
                                                                tree=source_tree, units=units)
                flag_rows[name] = flags
                for unit in units:
                    if arm != "baseline":
                        left = [normalized(x, out / (kind + "-baseline"), tree) for x in flag_rows[kind + "-baseline"][unit]]
                        right = [normalized(x, out / name, ROOT) for x in flags[unit]]
                        assert left == right, (name, unit, "Make flags differ with controls disabled")
                    compile_unit(name, unit, flags, sources, source_tree, arm == "zero")
                    if arm != "baseline":
                        for suffix in ("ii", "o"):
                            assert (out / f"{name}-{unit}.{suffix}").read_bytes() == (out / f"{kind}-baseline-{unit}.{suffix}").read_bytes(), (name, unit, suffix, "disabled identity")
                            comparisons += 1
                    print("PASS", name, unit, flush=True)
                state = probe(out / (name + "-make"), source_tree, kos, sdk, options + extra)
                assert state["returncode"] == 0, state
                states[name] = state
                if arm != "baseline":
                    assert all(state["state"][knob] == "0" for knob in KNOBS), state
                    for field in ("PLATFORM_OBJS", "GAME_LDFLAGS"):
                        assert normalized(state["state"][field], out / (name + "-make"), ROOT) == normalized(
                            states[kind + "-baseline"]["state"][field], out / (kind + "-baseline-make"), tree), (name, field)
    if args.only != "off":
        for name, options in ON_PROFILES.items():
            units = BASE_UNITS
            if "DRAW_SETUP_AUDIT=1" in options:
                units += ("draw_setup_audit",)
            if "PERF_PHASE_MISS=1" in options:
                units += ("perf_phase_miss", "world_census24")
            flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk, options, units=units)
            for unit in units:
                compile_unit(name, unit, flags, sources, ROOT)
            combined = out / (name + "-combined.o")
            builder.run([prefix + "ld", "-m", "shlelf", "-r", *[out / f"{name}-{unit}.o" for unit in units], "-o", combined], label=name + "-partial-link")
            undefined = builder.run([prefix + "nm", "-u", "-C", combined], label=name + "-undefined").decode()
            unresolved_new = [line for line in undefined.splitlines()
                              if "draw_setup" in line or "dsa24::" in line or "re4dc_dsa24_" in line]
            assert not unresolved_new, unresolved_new
            links[name] = dict(sha256=profile.sha(combined), new_audit_hooks_resolved=True,
                               scope="Relocatable link; ordinary game/KOS symbols remain unresolved")
            states[name] = probe(out / (name + "-make"), ROOT, kos, sdk, options)
            assert states[name]["returncode"] == 0
            print("PASS enabled", name, flush=True)
    rejected = []
    for knob in KNOBS:
        for value in ("", "2", "0 1"):
            state = probe(out / f"reject-{len(rejected)}", ROOT, kos, sdk, QA + [knob + "=" + value])
            assert state["returncode"] != 0, (knob, value, "invalid value accepted")
            rejected.append(dict(knob=knob, value=value, **state))
    for option in ("QA_MENU=0", "WORLD_METER=0"):
        state = probe(out / f"reject-{len(rejected)}", ROOT, kos, sdk, QA + ["DRAW_SETUP_AUDIT=1", option])
        assert state["returncode"] != 0, (option, "missing diagnostic prerequisite accepted")
        rejected.append(dict(prerequisite=option, **state))
    assert source_hashes == {path: profile.sha(ROOT / path) for path in source_hashes}, "sources changed during gate; rerun"
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline, gate_half=args.only or "both",
                  source_sha256=source_hashes, compiler=compiler, compiler_sha256=profile.sha(cxx),
                  linker=linker, newlib_header_sha256=profile.sha(newlib), kos=KOS_PIN, sdk=SDK_PIN,
                  toolchain_receipt=dict(path=str(args.toolchain_receipt), sha256=profile.sha(args.toolchain_receipt)),
                  validation_only_overrides=dict(NMR_POOL_LOD=0,
                      reason="Selected CH2 NMR_POOL_LOD=1 needs private GANADO_LOD data; public fallback disables GANADO_LOD. Identical base/current override; release recipe untouched."),
                  off_identity_comparisons=comparisons, artifacts=artifacts, profiles=receipts,
                  dependency_sha256=closure, make_states=states, partial_links=links, make_rejections=rejected,
                  limitations="Complete target translation units and disabled whole-object identity without debug records. No final linked game/full-image identity, emulator scene, console, private data, or real cache-miss measurement.")
    (out / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_comparisons=comparisons, enabled=list(links), receipt=str(out / "target-controls.json"))))


if __name__ == "__main__":
    main()
