#!/usr/bin/env python3
"""Build28 Make-derived SH4 compilation, disabled identity and link exclusion.

Complete changed translation units are compared against an independently
archived integration base. The actual Make object selection is preserved:
QA_LINK=0 has the QA menu only, QA_LINK=1 has menu plus transport, and a link
benchmark has benchmark plus transport. DFA/DSA telemetry compositions cover
both menu states; a release-image Make probe proves the link stays excluded.
No full image, console timing, modem session or private-asset claim is made.
"""
import argparse
import difflib
import hashlib
import importlib.util
import io
import itertools
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "568c357656efbec468db06a282c1f79caebaa725"
KNOB = "QA_LINK_REVIEW28"
MACRO = "RE4DC_" + KNOB
spec = importlib.util.spec_from_file_location("b28_shared_gate", HERE.parent / "build26/build_controls.py")
previous = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = previous
spec.loader.exec_module(previous)
shared, profile = previous.shared, previous.profile
UNITS = {name: (name + ".o", name + ".cpp") for name in ("qa_menu", "qa_link", "qa_link_bench")}
profile.UNITS.update(UNITS)
QA = ["DBG_WARP=1", "WARP_AFTER_RESET=1", "QA_MENU=1", "BENCHMARK=0",
      "PMC_ROW=0", "WORLD_METER=1", "NMR_POOL_LOD=0"]
COMPOSITIONS = {
    f"q{link}-f{dfa}-d{dsa}": dict(options=QA + [f"QA_LINK={link}", f"DRAW_FALLBACK_AUDIT={dfa}",
        f"DRAW_SETUP_AUDIT={dsa}", f"DRAW_SETUP_AUDIT_XLU={dsa}"],
        units=("qa_menu", "qa_link") if link else ("qa_menu",), link=bool(link))
    for link, dfa, dsa in itertools.product((0, 1), repeat=3)
}
COMPOSITIONS["bench"] = dict(options=QA + ["QA_MENU=0", "BENCHMARK=1", "QA_LINK=1",
    "DRAW_FALLBACK_AUDIT=0", "DRAW_SETUP_AUDIT=0", "DRAW_SETUP_AUDIT_XLU=0",
    "DISC_READ_METER=1", "PHASE_METER=1", "GAME_TICK_LOG=60", "PACE_VMU_GPU=1",
    "RENDER_OPTION=1", "CRASH_SCREEN=1", "PACE_VMU=1"],
    units=("qa_link", "qa_link_bench"), link=True)
OBJECT_FIELDS = ("PLATFORM_OBJS", "GAME_OBJS", "GAME_LDFLAGS")


def probe(out, tree, kos, sdk, options):
    out.mkdir(parents=True, exist_ok=False)
    fields = (KNOB, "QA_LINK", "QA_MENU", "BENCHMARK", "DRAW_FALLBACK_AUDIT", "DRAW_SETUP_AUDIT",
              "DRAW_SETUP_AUDIT_XLU", *OBJECT_FIELDS)
    query = out / "query.mk"
    query.write_text(".PHONY: b28-state\nb28-state:\n\t@:\n" + "\n".join(
        f"$(info B28_STATE {name}=$({name}))" for name in fields) + "\n")
    command, _ = profile.make_command(out, tree, kos, sdk, options, "b28-state")
    command[3:3] = ["-f", "Makefile", "-f", str(query)]
    result = subprocess.run(command, cwd=tree / "port/dreamcast/game", capture_output=True, text=True)
    output = result.stdout + result.stderr
    (out / "make.log").write_text(output)
    state = dict(line[len("B28_STATE "):].split("=", 1) for line in output.splitlines()
                 if line.startswith("B28_STATE "))
    return dict(command=command, returncode=result.returncode, state=state,
                error=output[-2000:] if result.returncode else None)


def selected_units(state):
    objects = shlex.split(state["PLATFORM_OBJS"])
    return {name: sum(Path(item).name == name + ".o" for item in objects) for name in UNITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root", "toolchain-receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--only", choices=("off", "on"))
    parser.add_argument("--composition", choices=tuple(COMPOSITIONS), help="Preliminary single profile; omit for full matrix")
    parser.add_argument("--syntax-control", action="store_true",
        help="TEST ONLY: repair exactly three malformed baseline QA directives in compiler stdin on both sides; never raw identity")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    prefix = str(cxx).removesuffix("g++")
    builder = profile.Build(out)
    toolchain = previous.verify_toolchain(builder, cxx, kos, sdk, args.toolchain_receipt.resolve())
    baseline = subprocess.check_output(["git", "rev-parse", args.baseline], cwd=ROOT, text=True).strip()
    tree = out / "baseline-tree"
    tree.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", baseline], cwd=ROOT))) as archive:
        archive.extractall(tree, filter="data")
    checked_units = COMPOSITIONS[args.composition]["units"] if args.composition else tuple(UNITS)
    sources = [(DC / "game" / UNITS[unit][1]).resolve() for unit in checked_units]
    sources += [Path(__file__), HERE.parent / "build26/build_controls.py", HERE.parent / "build24/build_controls.py",
                HERE.parent / "build18/build_profile.py", DC / "game/Makefile", DC / "build-public.sh",
                DC / "tools/d367/rr/recipe.conf", DC / "tools/d367/build-r21.sh",
                DC / "tools/d367/kos_cache_audit/prepare.py", DC / "patches/kos-804b319-cache-p2.patch",
                *sorted((DC / "game").glob("*.mk"))]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}
    artifacts, receipts, flag_rows, states, closure, links, wiring = {}, {}, {}, {}, {}, {}, {}
    disabled, enabled, inert = [], [], []
    cache_preparations = {}
    syntax_overlays, baseline_raw_failure = {}, {}

    def compile_unit(name, unit, flags, source_files, source_tree, zero=False):
        source = source_files[unit]
        guards = [Path(flag) for flag in flags[unit] if flag.endswith("/koscache-p2/require_p2.h")]
        if guards:
            assert len(guards) == 1
            key = "baseline" if source_tree == tree else "current"
            if key not in cache_preparations:
                prepared = out / ("kos-cache-" + key)
                builder.run([sys.executable, source_tree / "port/dreamcast/tools/d367/kos_cache_audit/prepare.py",
                    "--kos-root", kos, "--output", prepared,
                    "--patch", source_tree / "port/dreamcast/patches/kos-804b319-cache-p2.patch"], label="prepare-cache-" + key)
                cache_preparations[key] = json.loads((prepared / "prepare.json").read_text())
            destination = guards[0].parent
            if not destination.exists():
                shutil.copytree(out / ("kos-cache-" + key), destination)
            for generated in (guards[0], destination / "tree/kernel/arch/dreamcast/include/arch/cache.h"):
                receipts[name]["profiles"][unit]["generated_headers"][str(generated)] = profile.sha(generated)
        common = [*flags[unit], *(["-D" + MACRO + "=0"] if zero else []), "-iquote", str(source.parent)]
        body = source.read_bytes()
        if args.syntax_control and unit == "qa_menu":
            # The integration merge contains a literal backslash+n inside three
            # #if expressions. This controlled mode never edits either tree and
            # cannot be presented as the requested raw disabled identity proof.
            broken = bytes((92, 110)) + b"    (defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT)"
            repaired = bytes((92, 10)) + broken[2:]
            assert body.count(broken) == 3, "syntax overlay requires exactly the three known malformed directives"
            if source_tree == tree and not baseline_raw_failure:
                command = [*common, "-x", "c++", "-", "-E", "-P", "-o", out / "baseline-raw-rejected.ii"]
                raw = subprocess.run(command, cwd=source.parent, input=body, capture_output=True)
                errors = raw.stderr.decode()
                assert raw.returncode and errors.count("not valid in preprocessor expressions") == 3, errors
                (out / "baseline-raw-failure.log").write_text(errors)
                baseline_raw_failure.update(returncode=raw.returncode, command=[str(x) for x in command],
                    errors=errors, source_sha256=hashlib.sha256(body).hexdigest())
            transformed = body.replace(broken, repaired)
            patch = "".join(difflib.unified_diff(body.decode().splitlines(keepends=True),
                transformed.decode().splitlines(keepends=True), fromfile="original/qa_menu.cpp",
                tofile="TEST-ONLY-compiler-stdin/qa_menu.cpp"))
            patch_path = out / (name + "-qa-menu-syntax-control.patch")
            patch_path.write_text(patch)
            syntax_overlays[name] = dict(replacements=3, original_sha256=hashlib.sha256(body).hexdigest(),
                compiler_input_sha256=hashlib.sha256(transformed).hexdigest(),
                patch=patch, patch_sha256=profile.sha(patch_path), production_edited=False)
            body = transformed
        row = {}
        for suffix, phase in (("ii", ["-E", "-P"]),
                              ("o", ["-c", "-fstack-usage", "-MMD", "-MF", out / f"{name}-{unit}.d"])):
            target = out / f"{name}-{unit}.{suffix}"
            builder.run([*common, "-x", "c++", "-", *phase, "-o", target], cwd=source.parent,
                        source=body, label=f"{name}-{unit}-{suffix}")
            row[suffix] = dict(bytes=target.stat().st_size, sha256=profile.sha(target))
            if suffix == "o":
                row[suffix].update(profile.sections(target), stack_usage=profile.stack_usage(target.with_suffix(".su")))
                depfile = out / f"{name}-{unit}.d"
                # stdin plus exclusively -isystem includes legitimately emits
                # an empty -MMD file (the transport/benchmark baseline case).
                deps = shared.dependencies(depfile, source_tree, source.parent) if depfile.read_text().strip() else {}
                closure.setdefault(name, {})[unit] = deps
                if source_tree == ROOT:
                    for path, digest in deps.items():
                        assert frozen.get(path, digest) == digest, (path, "source changed during gate")
                        frozen[path] = digest
        artifacts.setdefault(name, {})[unit] = row

    def compare_states(name, reference, current_tree, ref_tree):
        for field in OBJECT_FIELDS:
            assert shared.normalized(states[name]["state"][field], out / (name + "-make"), current_tree) == shared.normalized(
                states[reference]["state"][field], out / (reference + "-make"), ref_tree), (name, field)

    for kind, spec in COMPOSITIONS.items():
        if args.composition and kind != args.composition:
            continue
        options, units = spec["options"], spec["units"]
        arms = []
        if args.only != "on":
            arms.extend(("baseline", "absent", "zero"))
        elif not spec["link"]:
            arms.append("baseline")  # Prove new-knob-on remains inert with QA_LINK=0.
        if args.only != "off":
            arms.append("on")
        for arm in arms:
            name = kind + "-" + arm
            source_tree = tree if arm == "baseline" else ROOT
            extra = [KNOB + "=" + ("1" if arm == "on" else "0")] if arm in ("zero", "on") else []
            flags, receipts[name], source_files = profile.derive(out / name, cxx, kos, sdk, options + extra,
                                                                tree=source_tree, units=units)
            flag_rows[name] = flags
            inactive = arm != "on" or not spec["link"]
            for unit in units:
                if arm != "baseline" and inactive:
                    reference = kind + "-baseline"
                    left = [shared.normalized(x, out / reference, tree) for x in flag_rows[reference][unit]]
                    right = [shared.normalized(x, out / name, ROOT) for x in flags[unit]]
                    assert left == right, (name, unit, "Make flags changed while feature inactive")
                if arm == "on":
                    assert ("-D" + MACRO + "=1" in flags[unit]) == spec["link"], (name, unit, "wrong feature propagation")
                compile_unit(name, unit, flags, source_files, source_tree, arm == "zero")
                if arm != "baseline" and inactive:
                    for suffix in ("ii", "o"):
                        assert (out / f"{name}-{unit}.{suffix}").read_bytes() == (
                            out / f"{kind}-baseline-{unit}.{suffix}").read_bytes(), (name, unit, suffix)
                        (inert if arm == "on" else disabled).append(dict(profile=kind, control=arm, unit=unit,
                                                                         artifact=suffix, identical=True))
            states[name] = probe(out / (name + "-make"), source_tree, kos, sdk, options + extra)
            assert states[name]["returncode"] == 0, states[name]
            selection = selected_units(states[name]["state"])
            assert selection == {unit: int(unit in units) for unit in UNITS}, (name, selection, units)
            wiring[name] = dict(selected_units=selection, actual_make_selection=True)
            if arm != "baseline":
                assert states[name]["state"][KNOB] == ("1" if arm == "on" else "0")
                if inactive:
                    compare_states(name, kind + "-baseline", ROOT, tree)
            if arm == "on":
                combined = out / (name + "-combined.o")
                builder.run([prefix + "ld", "-m", "shlelf", "-r", *[out / f"{name}-{unit}.o" for unit in units],
                             "-o", combined], label=name + "-partial-link")
                undefined = builder.run([prefix + "nm", "-u", "-C", combined], label=name + "-undefined").decode()
                unresolved = [line for line in undefined.splitlines() if "review28" in line or "qalink28" in line
                              or (not spec["link"] and "re4dc_qalink" in line)]
                assert not unresolved, (name, unresolved)
                links[name] = dict(sha256=profile.sha(combined), new_review_references_resolved=True,
                    scope="Relocatable link of actual selected changed TUs; inherited game/KOS/diagnostic imports remain explicit")
                enabled.append(dict(profile=kind, link=spec["link"], compiled_units=list(units),
                                    link_off_inert=not spec["link"]))
            print("PASS", name, flush=True)
    release = ["NMR_POOL_LOD=0", "QA_MENU=0", "BENCHMARK=0", "QA_LINK=0", "DRAW_FALLBACK_AUDIT=0",
               "DRAW_SETUP_AUDIT=0", "DRAW_SETUP_AUDIT_XLU=0"]
    for arm in ("baseline", "absent", "zero", "on"):
        name = "release-" + arm
        source_tree = tree if arm == "baseline" else ROOT
        extra = [KNOB + "=" + ("1" if arm == "on" else "0")] if arm in ("zero", "on") else []
        states[name] = probe(out / (name + "-make"), source_tree, kos, sdk, release + extra)
        assert states[name]["returncode"] == 0, states[name]
        selection = selected_units(states[name]["state"])
        assert not any(selection.values()), (name, selection)
        if arm != "baseline":
            compare_states(name, "release-baseline", ROOT, tree)
        wiring[name] = dict(selected_units=selection, actual_make_selection=True)
    rejected = []
    for value in ("", "2", "0 1"):
        state = probe(out / ("reject-" + str(len(rejected))), ROOT, kos, sdk, QA + ["QA_LINK=1", KNOB + "=" + value])
        assert state["returncode"] != 0, (value, "invalid knob accepted")
        rejected.append(dict(value=value, **state))
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, "source changed during gate; rerun"
    status = "CONTROLLED_SYNTAX_PASS" if args.syntax_control else "PASS"
    report = dict(status=status, baseline=baseline, scope=__doc__, gate_half=args.only or "both", knob=KNOB,
                  source_sha256=frozen, **toolchain, cache_header_preparation=cache_preparations,
                  off_identity_comparisons=len(disabled), disabled_identity=disabled, enabled_compiles=enabled,
                  link_off_on_identity=inert, artifacts=artifacts, profiles=receipts, dependency_sha256=closure,
                  make_states=states, partial_links=links, wiring=wiring, make_rejections=rejected,
                  syntax_control=dict(enabled=args.syntax_control, overlays=syntax_overlays,
                      baseline_raw_failure=baseline_raw_failure,
                      identity_scope="qa_menu comparisons use the explicit three-directive repair on both sides; raw qa_menu identity is BLOCKED by the invalid integration base. Transport/bench inputs remain unmodified." if args.syntax_control else "All compiler source inputs are unmodified production bytes."),
                  validation_only_overrides=dict(NMR_POOL_LOD=0,
                      reason="Public recipe lacks private Ganado assets; mirrored baseline/candidate override"),
                  limitations="Complete selected-TU byte identity without debug records; no final game image, private assets, modem session, hardware or gameplay acceptance.")
    destination = out / ("target-controls-syntax.json" if args.syntax_control else "target-controls.json")
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status=status, off_comparisons=len(disabled), enabled=len(enabled),
                          inert_comparisons=len(inert), receipt=str(destination))))


if __name__ == "__main__":
    main()
