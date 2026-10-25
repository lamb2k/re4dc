#!/usr/bin/env python3
"""Build 10: independent Make-derived OFF identity and enabled SH4 objects.

Uses the public R21 + Test22 + current rr recipe, its real generated headers,
the existing private-asset fallbacks, and the QA menu prerequisites. No stub
target headers, game data, executable, emulator, or console result is involved.
The optional unpinned compiler mode is preliminary evidence only.
"""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "011d8dee628e0105fba987df26b649a795d67d24"
spec = importlib.util.spec_from_file_location(
    "wc24_make_profile", DC / "tools/d367/ui_draw_lean/build_profile.py")
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)

UNITS = {
    "main": ("src/game/main.o", "../../../src/game/main.cpp"),
    "pace": ("pace.o", "pace.cpp"),
    "pace_present": ("pace_present.o", "pace_present.cpp"),
    "qa_menu": ("qa_menu.o", "qa_menu.cpp"),
    "native_static": ("platform/native_static.o", "platform/native_static.cpp"),
    "native_ps2_world": ("platform/native_ps2_world.o", "platform/native_ps2_world.cpp"),
    "native_ui": ("platform/native_ui.o", "platform/native_ui.cpp"),
    "gpu_lifecycle": ("native-reuse/gpu_lifecycle.o", "../room/gpu_lifecycle.cpp"),
}
p.SPECIFICATIONS = {**UNITS, "census": ("world_census24.o", "world_census24.cpp")}
QA = ["DBG_WARP=1", "WARP_AFTER_RESET=1", "QA_MENU=1", "BENCHMARK=0"]
STACK = ["SCENERY_SELECT_ONLY=1", "SCENERY_REPLAY_LEAN=1", "SCENERY_SUBMIT_BATCH=1"]
PROFILES = {
    "production": [*QA, *STACK],
    "standalone_observer": [*QA, *STACK, "PACE_VMU_GPU=0", "PHASE_METER=0",
        "PMC_ROW=0", "DISC_READ_METER=0", "TAIL_METER=0"],
}


def normalized(values, output, tree):
    return [v.replace(str(output), "<PROFILE>").replace(str(tree), "<SOURCE>") for v in values]


def header_hashes(row, output):
    return {str(Path(path).relative_to(output)): digest
            for path, digest in row["generated_headers"].items()}


def derive(output, compiler, kos, sdk, profiles, knob=None, core=False):
    p.PROFILES = {name: [*PROFILES[name], *([] if knob is None else [f"WORLD_CENSUS24={knob}"])]
                  for name in profiles}
    return p.derive(output, compiler, kos, sdk, variants=profiles,
                    units=[*UNITS, *(["census"] if core else [])])


def make_probe(output, tree, kos, sdk, changes):
    """Read the final Make variables without running generation or compilation."""
    output.mkdir(parents=True)
    with p.source_tree(tree):
        assignments, _ = p.recipe_inputs(output)
        extra = output / "query.mk"
        extra.write_text(".PHONY: wc24-state\nwc24-state:\n\t@:\n" + "\n".join(
            f"$(info WC24_STATE {name}=$({name}))" for name in
            ("WORLD_CENSUS24", "WORLD_CENSUS24_WINDOW", "PLATFORM_OBJS", "GAME_LDFLAGS")) + "\n")
        command = ["make", "--no-print-directory", "-n", "-f", "Makefile", "-f", str(extra),
            "wc24-state", *assignments, *changes,
            "KOS_CFLAGS=" + shlex.join(p.target_flags(kos)), "KOS_BASE=" + str(kos),
            "KOS_LDFLAGS=-T" + str(kos / "utils/ldscripts/shlelf.xc"),
            "SH4ZAM_DIR=" + str(sdk), "--assume-old=" + str(output / "obj/modules.mk")]
        result = subprocess.run(command, cwd=tree / "port/dreamcast/game", text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output / "make.log").write_text(result.stdout)
    state = {}
    for line in result.stdout.splitlines():
        if line.startswith("WC24_STATE "):
            key, value = line[len("WC24_STATE "):].split("=", 1)
            state[key] = value
    return dict(command=command, returncode=result.returncode, state=state,
                log=str(output / "make.log"))


def git_revision(path):
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return result.stdout.strip() if not result.returncode else None


def run(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    compiler, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = p.Build(out)
    version = builder.run([compiler, "--version"], label="compiler").decode().splitlines()[0]
    macros = builder.run([compiler, "-dM", "-E", "-x", "c++", "/dev/null"], label="compiler-macros").decode()
    prefix_line = next(line for line in macros.splitlines() if line.startswith("#define __USER_LABEL_PREFIX__"))
    symbol_prefix = prefix_line.removeprefix("#define __USER_LABEL_PREFIX__").strip()
    pinned = bool(re.search(r"\b15\.2\.0\b", version))
    if not pinned and not args.allow_unpinned:
        raise RuntimeError("GCC 15.2.0 is required; --allow-unpinned labels a preliminary check only")
    profiles = args.profile or list(PROFILES)
    tree = out / "baseline-tree"; tree.mkdir()
    archive = subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(tree, filter="data")

    watched = [(DC / "game" / source).resolve() for _, source in p.SPECIFICATIONS.values()]
    watched += [DC / "game/platform/include/world_census24.h", DC / "game/Makefile",
        DC / "game/platform/far_shell.inc", *sorted((DC / "game").glob("*.mk")),
        *sorted((DC / "game/platform/include").glob("scenery_*.inc")),
        *sorted((DC / "game/platform/include").glob("native_source_world*.inc")),
        *sorted((DC / "game/platform/include").glob("source_world*.inc")), Path(__file__).resolve()]
    source_hashes = {str(path.relative_to(ROOT)): p.sha(path) for path in watched}

    with p.source_tree(tree):
        old_flags, old_receipt = derive(out / "baseline-profile", compiler, kos, sdk, profiles)
    current = {arm: derive(out / (arm + "-profile"), compiler, kos, sdk, profiles, knob, core=arm == "on")
               for arm, knob in (("absent", None), ("zero", 0), ("on", 1))}
    make_checks, objects, integer_core = {}, {}, {}
    off_comparisons = 0
    for profile in profiles:
        make_checks[profile], objects[profile] = {}, {}
        for unit in UNITS:
            reference = normalized(old_flags[profile][unit], out / "baseline-profile", tree)
            old_headers = header_hashes(old_receipt["profiles"][profile][unit], out / "baseline-profile")
            for arm, (flags, receipt) in current.items():
                actual = normalized(flags[profile][unit], out / (arm + "-profile"), ROOT)
                if arm == "on":
                    assert actual.count("-DRE4DC_WORLD_CENSUS24=1") == 1, (profile, unit, "missing define")
                    actual.remove("-DRE4DC_WORLD_CENSUS24=1")
                assert actual == reference, (profile, unit, arm, "Make flags differ")
                assert header_hashes(receipt["profiles"][profile][unit], out / (arm + "-profile")) == old_headers, (
                    profile, unit, arm, "generated headers differ")
            make_checks[profile][unit] = dict(off_flags_identical=True, headers_identical=True,
                                               on_adds_only_census_define=True)
            rows = {}
            for arm in ("baseline", "absent", "zero", "on"):
                source = ((tree if arm == "baseline" else ROOT) / "port/dreamcast/game" / UNITS[unit][1]).resolve()
                flags = old_flags[profile][unit] if arm == "baseline" else current[arm][0][profile][unit]
                extra = ["-DRE4DC_WORLD_CENSUS24=0"] if arm == "zero" else []
                label = f"{profile}-{unit}-{arm}"
                for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
                    target = out / (label + "." + suffix)
                    builder.run([*flags, *extra, "-x", "c++", "-", *phase, "-o", target],
                                cwd=source.parent, source=source.read_bytes(), label=label + "-" + suffix)
                    row = dict(bytes=target.stat().st_size, sha256=p.sha(target))
                    if suffix == "o":
                        row.update(p.sections(target), stack_usage=p.stack_usage(target.with_suffix(".su")))
                    rows[arm + "." + suffix] = row
                    if arm in ("absent", "zero"):
                        assert target.read_bytes() == (out / f"{profile}-{unit}-baseline.{suffix}").read_bytes(), (
                            profile, unit, arm, suffix, "OFF byte identity")
                        off_comparisons += 1
            objects[profile][unit] = rows
            print("PASS", profile, unit, flush=True)

        core_source = DC / "game/world_census24.cpp"
        core = out / f"{profile}-census-on.o"
        core_flags = current["on"][0][profile]["census"]
        for required in ("-DRE4DC_WORLD_CENSUS24=1", "-DRE4DC_WORLD_CENSUS24_WINDOW=300",
                         "-DRE4DC_WC24_PACE_OBSERVER=" + ("1" if profile == "production" else "0")):
            assert core_flags.count(required) == 1, (profile, "core Make flag", required)
        assert "-DRE4DC_FAR_SHELL=1" in current["on"][0][profile]["native_static"], "far shell not exercised"
        builder.run([*core_flags, "-x", "c++", "-", "-c", "-fstack-usage", "-o", core],
                    cwd=core_source.parent, source=core_source.read_bytes(), label=profile + "-census-on")
        objects[profile]["census"] = dict(bytes=core.stat().st_size, sha256=p.sha(core),
            **p.sections(core), stack_usage=p.stack_usage(core.with_suffix(".su")))
        assembly = out / f"{profile}-census-on.s"
        builder.run([*core_flags, "-x", "c++", "-", "-S", "-o", assembly],
                    cwd=core_source.parent, source=core_source.read_bytes(), label=profile + "-census-assembly")
        # Check compiler instructions, not literal pools misdecoded as opcodes.
        # All core functions are integer-only, stronger than just hot entries.
        floating = [line.strip() for line in assembly.read_text().splitlines()
                    if re.match(r"\s+(?:f[a-z0-9./]*(?:\s|$)|(?:lds|sts)(?:\.l)?\s+.*(?:fpscr|fpul))", line)]
        assert not floating, (profile, "census core contains FPU instructions", floating)
        integer_core[profile] = dict(assembly_sha256=p.sha(assembly), floating_instructions=0,
            scope="All compiler-emitted core instructions; external KOS/libc callees are not part of this proof")

    make_states = {}
    for profile in profiles:
        states = {}
        for arm in ("baseline", "absent", "zero", "on"):
            changes = [*PROFILES[profile], *(["WORLD_CENSUS24=0"] if arm == "zero" else
                         ["WORLD_CENSUS24=1"] if arm == "on" else [])]
            result = make_probe(out / f"make-{profile}-{arm}", tree if arm == "baseline" else ROOT,
                                kos, sdk, changes)
            assert result["returncode"] == 0, result
            state = result["state"]
            count = sum(word.endswith("/world_census24.o") for word in state["PLATFORM_OBJS"].split())
            assert count == (1 if arm == "on" else 0), (profile, arm, "census object membership")
            if arm in ("absent", "zero"): assert state["WORLD_CENSUS24"] == "0"
            if arm == "on":
                for symbol in ("pvr_sync_stats", "pvr_wait_ready", "pvr_wait_render_done"):
                    assert state["GAME_LDFLAGS"].split().count("-Wl,--wrap=" + symbol) == 1, (profile, symbol)
            states[arm] = result
        for arm in ("absent", "zero"):
            for key in ("PLATFORM_OBJS", "GAME_LDFLAGS"):
                a = normalized([states[arm]["state"][key]], out / f"make-{profile}-{arm}", ROOT)
                b = normalized([states["baseline"]["state"][key]], out / f"make-{profile}-baseline", tree)
                assert a == b, (profile, arm, key, "OFF Make identity")
        make_states[profile] = states

    rejections = {}
    for change in ("WORLD_CENSUS24=2", "QA_MENU=0", "PS2_WORLD_MESH=0", "PVR_STREAM=0",
                   "MESH_DIRECT=0", "TA_DIRECT=0", "MESH_VP_SCHED=2", "MESH_STRIP_LEAN=2",
                   "MESH_CLIP_ACCEPT=2", "PS2_INTERIOR_CULL=2", "SG_SELECT_LEAN=2", "SCENERY_DEDUP_CHECK=1"):
        label = change.replace("=", "-")
        result = make_probe(out / ("reject-" + label), ROOT, kos, sdk,
                            [*PROFILES["production"], "WORLD_CENSUS24=1", change])
        assert result["returncode"] != 0, (change, "invalid build accepted")
        rejections[change] = result
    for value in (299, 601):
        flags = [x for x in current["on"][0][profiles[0]]["census"]
                 if not x.startswith("-DRE4DC_WORLD_CENSUS24_WINDOW=")]
        command = [*flags, f"-DRE4DC_WORLD_CENSUS24_WINDOW={value}", "-E", "-o", "/dev/null", str(core_source)]
        result = subprocess.run(command, cwd=core_source.parent, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / f"reject-window-{value}.log").write_text(result.stdout)
        assert result.returncode != 0 and "between 300 and 600" in result.stdout
        rejections[f"WORLD_CENSUS24_WINDOW={value}"] = dict(returncode=result.returncode, command=command)

    nm = Path(str(compiler).removesuffix("g++") + "nm")
    ld = Path(str(compiler).removesuffix("g++") + "ld")
    objdump = Path(str(compiler).removesuffix("g++") + "objdump")
    wrapper_checks = {}
    for profile in profiles:
        inputs = [out / f"{profile}-{unit}-on.o" for unit in UNITS] + [out / f"{profile}-census-on.o"]
        linked = out / (profile + "-combined.o")
        builder.run([ld, "-m", "shlelf", "-r", "--wrap=pvr_sync_stats", "--wrap=pvr_wait_ready", "--wrap=pvr_wait_render_done",
                     *inputs, "-o", linked], label=profile + "-partial-link")
        symbols = builder.run([nm, "--defined-only", linked], label=profile + "-symbols").decode()
        (out / (profile + "-census-disassembly.txt")).write_bytes(builder.run(
            [objdump, "-drC", out / f"{profile}-census-on.o"], label=profile + "-census-disassembly"))
        for symbol in ("__wrap_pvr_sync_stats", "__wrap_pvr_wait_ready", "__wrap_pvr_wait_render_done"):
            assert sum(line.split()[-1] == symbol_prefix + symbol for line in symbols.splitlines() if line.split()) == 1, (profile, symbol)
        wrapper_checks[profile] = dict(partial_link=True, one_definition_per_wrapper=True,
                                       sha256=p.sha(linked), bytes=linked.stat().st_size)

    for name, digest in source_hashes.items(): assert p.sha(ROOT / name) == digest, (name, "changed during check")
    result = dict(status="PASS" if pinned else "PRELIMINARY_PASS", scope=__doc__, baseline=args.baseline,
        compiler=version, compiler_sha256=p.sha(compiler), pinned_compiler=pinned, symbol_prefix=symbol_prefix,
        kos_revision=git_revision(kos), sdk_revision=git_revision(sdk),
        source_sha256=source_hashes, objects=objects, off_identity_comparisons=off_comparisons,
        make_checks=make_checks, make_states=make_states, rejections=rejections,
        wrapper_checks=wrapper_checks, integer_core=integer_core, baseline_profile=old_receipt,
        profiles={arm: receipt for arm, (_, receipt) in current.items()},
        limits=["Independent translation units and relocatable integration only; no game executable linked",
                "PVR declaration overlay applied; KOS library patches and runtime behavior not validated here",
                "No private assets, emulator timing, physical-console timings, or gameplay claim"])
    (out / "build-controls.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--profile", choices=list(PROFILES), action="append")
    parser.add_argument("--allow-unpinned", action="store_true")
    result = run(parser.parse_args())
    print(json.dumps(dict(status=result["status"], off_identity_comparisons=result["off_identity_comparisons"],
                          compiler=result["compiler"])))


if __name__ == "__main__": main()
