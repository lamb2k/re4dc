#!/usr/bin/env python3
"""Build13 real Make profiles, complete OFF .ii/object identity and ON gates.

No fake target headers: pinned KOS declarations plus the repository's existing
PVR declaration overlay, actual generated project headers, real SH4 compiler.
These are complete translation units, not a game link or a console benchmark.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "9b248c5b40a49e4c954ea834fdf665fdbbc314f0"
KOS_PIN = "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
SDK_PIN = "33fa4850cacb30dd0ad35485ef035526ec4ce782"
spec = importlib.util.spec_from_file_location("layout_build_profile", DC/"tools/d367/ui_draw_lean/build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)
UNITS = {"native_static": ("platform/native_static.o", "platform/native_static.cpp"),
         "native_ui": ("platform/native_ui.o", "platform/native_ui.cpp")}
ALL_UNITS = {**UNITS, "census": ("world_census24.o", "world_census24.cpp")}
MATCHED = ["PS2_INTERIOR_CULL=0", "WORLD_RECT21=0", "FOLIAGE_MIP24=0"]
QA = ["DBG_WARP=1", "WARP_AFTER_RESET=1", "QA_MENU=1", "BENCHMARK=0"]
KNOBS = ("SCENERY_RECORD_SPLIT",)


def normalize(value, output, source):
    return value.replace(str(output), "<PROFILE>").replace(str(source), "<SOURCE>")


def source_hashes():
    paths = [DC/"game/Makefile", DC/"game/scenery_record_split.mk",
             DC/"game/platform/native_static.cpp", DC/"game/platform/native_ui.cpp",
             DC/"room/scenery_record_split.hpp",
             DC/"room/instanced_mesh.hpp", DC/"room/mesh_fastpath.hpp", DC/"room/mesh_fastpath_sched.hpp",
             DC/"game/world_census24.cpp", DC/"game/world_census24.mk", DC/"game/platform/include/world_census24.h",
             Path(__file__), DC/"tools/d367/ui_draw_lean/build_profile.py",
             DC/"tools/d367/world_submit_spike/build_profile.py",
             *sorted((DC/"game/platform/include").glob("scenery_*"))]
    return {str(p.relative_to(ROOT)): profile.sha(p) for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--toolchain-receipt", type=Path,
                        help="optional SDK restoration/provenance receipt to bind by SHA256")
    parser.add_argument("--syntax-only", action="store_true", help="Development preview: one enabled full TU, not an acceptance receipt")
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    builder = profile.Build(out)
    compiler = builder.run([cxx, "--version"], label="compiler").decode().splitlines()[0]
    verbose = subprocess.run([str(cxx), "-v"], text=True, capture_output=True)
    assert "15.2.0" in compiler and "Thread model: kos" in verbose.stderr, verbose.stderr
    linker = Path(str(cxx).removesuffix("g++")+"ld")
    linker_version = builder.run([linker, "--version"], label="linker").decode().splitlines()[0]
    assert "2.45.1" in linker_version, linker_version
    newlib = cxx.parent.parent/"sh-elf/include/_newlib_version.h"
    assert '#define _NEWLIB_VERSION "4.6.0"' in newlib.read_text(), "newlib version"
    for path, expected in ((kos, KOS_PIN), (sdk, SDK_PIN)):
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip() == expected
    frozen = source_hashes()
    tree = out/"baseline-tree"; tree.mkdir()
    archive = subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(tree, filter="data")
    profile.SPECIFICATIONS.update(ALL_UNITS)
    artifacts, profiles = {}, {}

    def derive(name, options, baseline=False, units=tuple(UNITS)):
        folder = out/name
        profile.PROFILES["selected"] = list(options)
        if baseline:
            with profile.source_tree(tree):
                flags, receipt = profile.derive(folder, cxx, kos, sdk, variants=["selected"], units=units)
        else:
            flags, receipt = profile.derive(folder, cxx, kos, sdk, variants=["selected"], units=units)
        profiles[name] = receipt
        return flags["selected"], receipt

    def compile_tu(name, unit, flags, baseline=False, explicit_zero=False):
        source = (tree if baseline else ROOT)/"port/dreamcast/game"/ALL_UNITS[unit][1]
        extra = ["-DRE4DC_"+knob+"=0" for knob in KNOBS] if explicit_zero else []
        common = [*flags, *extra, "-iquote", str(source.parent)]
        records = {}
        for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage"])):
            target = out/(name+"-"+unit+"."+suffix)
            builder.run([*common, "-x", "c++", "-", *phase, "-o", target], cwd=source.parent,
                        source=source.read_bytes(), label=name+"-"+unit+"-"+suffix)
            row = dict(bytes=target.stat().st_size, sha256=profile.sha(target))
            if suffix == "o":
                row.update(profile.sections(target))
                row["stack_usage"] = profile.stack_usage(target.with_suffix(".su"))
            records[suffix] = row
        artifacts.setdefault(name, {})[unit] = records
        return records

    if args.syntax_only:
        flags, receipt = derive("split-preview", MATCHED+["SCENERY_RECORD_SPLIT=1"], units=("native_static",))
        compile_tu("split-preview", "native_static", flags["native_static"])
        print("PASS enabled complete-TU preview")
        return

    off_comparisons, unaffected = 0, 0
    for configuration, surrounding in (("production", []), ("matched", MATCHED),
            ("build12-local", MATCHED+["SCENERY_LOCAL_INDEXED=1"]),
            ("build12-direct", MATCHED+["SCENERY_DIRECT_STRIPS=1"])):
        controls = {}
        for arm, extra in (("baseline", []), ("absent", []), ("zero", [k+"=0" for k in KNOBS])):
            name = configuration+"-"+arm
            flags, receipt = derive(name, surrounding+extra, arm == "baseline")
            controls[arm] = (flags, receipt)
            for unit in UNITS:
                if arm != "baseline":
                    base_flags = controls["baseline"][0][unit]
                    assert [normalize(x, out/(configuration+"-baseline"), tree) for x in base_flags] == [
                        normalize(x, out/name, ROOT) for x in flags[unit]], (name, unit, "Make OFF flags")
                    for before, after in ((controls["baseline"][1], receipt),):
                        def headers(r, root):
                            row = r["profiles"]["selected"][unit]
                            return {normalize(p, root, tree if r is before else ROOT): h
                                    for p, h in row["generated_headers"].items()}
                        assert headers(before, out/(configuration+"-baseline")) == headers(after, out/name), "generated headers"
                compile_tu(name, unit, flags[unit], arm == "baseline", arm == "zero")
                if arm != "baseline":
                    for suffix in ("ii", "o"):
                        assert (out/(name+"-"+unit+"."+suffix)).read_bytes() == (
                            out/(configuration+"-baseline-"+unit+"."+suffix)).read_bytes(), (name, unit, suffix, "OFF identity")
                        off_comparisons += 1
        if configuration == "matched": matched_controls = controls
        print("PASS OFF", configuration, flush=True)

    enabled = (("split", MATCHED+["SCENERY_RECORD_SPLIT=1"], tuple(UNITS)),
               ("split-composed", MATCHED+["SCENERY_RECORD_SPLIT=1", "SCENERY_SELECT_LEAN2=1",
                   "SCENERY_UV_SNAPSHOT=1", "SCENERY_EMIT_PREFETCH=1"], ("native_static",)),
               ("split-eager", MATCHED+["SCENERY_RECORD_SPLIT=1", "SCENERY_SELECT_ONLY=0",
                   "SCENERY_REPLAY_LEAN=0", "SCENERY_SUBMIT_BATCH=0", "SCENERY_UV_SNAPSHOT=0"], ("native_static",)),
               ("split-census", MATCHED+QA+["SCENERY_RECORD_SPLIT=1", "WORLD_CENSUS24=1"], tuple(ALL_UNITS)))
    census_flags = None
    for name, options, units in enabled:
        flags, receipt = derive(name, options, units=units)
        for unit in units:
            compile_tu(name, unit, flags[unit])
            if unit == "native_static":
                for knob in KNOBS:
                    assert sum(x.startswith("-DRE4DC_"+knob+"=") for x in flags[unit]) == 1
                if name == "split":
                    actual = [x for x in flags[unit] if not any(x.startswith("-DRE4DC_"+k+"=") for k in KNOBS)]
                    expected = matched_controls["absent"][0][unit]
                    assert [normalize(x, out/name, ROOT) for x in actual] == [
                        normalize(x, out/"matched-absent", ROOT) for x in expected], "ON only adds variant defines"
            elif unit == "native_ui" and name == "split":
                assert not any("RE4DC_"+k in x for k in KNOBS for x in flags[unit]), "define leaked to native_ui"
                for suffix in ("ii", "o"):
                    assert (out/(name+"-"+unit+"."+suffix)).read_bytes() == (out/("matched-baseline-"+unit+"."+suffix)).read_bytes()
                    unaffected += 1
            elif unit == "census":
                census_flags = flags[unit]
                assert census_flags.count("-DRE4DC_WORLD_CENSUS24=1") == 1
                assert census_flags.count("-DRE4DC_WORLD_CENSUS24_WINDOW=300") == 1
        print("PASS ON", name, flush=True)

    # Census is a fresh integration dependency. Resolve every new hook against
    # its real core, and verify the compiled observer preserves the loaded FPU.
    assert census_flags is not None
    assembly = out/"split-census-core.s"
    source = DC/"game/world_census24.cpp"
    builder.run([*census_flags, "-x", "c++", "-", "-S", "-o", assembly], cwd=source.parent,
                source=source.read_bytes(), label="census-assembly")
    floating = [line.strip() for line in assembly.read_text().splitlines()
                if re.match(r"\s+(?:f[a-z0-9./]*(?:\s|$)|(?:lds|sts)(?:\.l)?\s+.*(?:fpscr|fpul))", line)]
    assert not floating, ("compiled census core has FPU instructions", floating)
    linked = out/"split-census-partial.o"
    builder.run([linker, "-m", "shlelf", "-r", *[out/("split-census-"+u+".o") for u in ALL_UNITS], "-o", linked],
                label="census-partial-link")
    nm = Path(str(cxx).removesuffix("g++")+"nm")
    undefined = builder.run([nm, "-u", linked], label="census-undefined").decode()
    assert "_ZN5re4dc4wc24" not in undefined, "unresolved new census hooks"

    seed = profiles["matched-absent"]["profiles"]["selected"]["native_static"]["seed_command"]
    rejection = []
    invalid = [["SCENERY_RECORD_SPLIT=2"], ["SCENERY_RECORD_SPLIT=-1"],
        ["SCENERY_RECORD_SPLIT=1", "SCENERY_LOCAL_INDEXED=1"],
        ["SCENERY_RECORD_SPLIT=1", "SCENERY_DIRECT_STRIPS=1"]]
    required = ("NATIVE_MESH", "MESH_LOD", "PS2_WORLD_DRAW", "PS2_WORLD_MESH", "TA_DIRECT", "MESH_DIRECT", "IO_ALIGNED", "SCENERY_CHUNK", "PS2_WORLD_ROOMS")
    unsupported = ("WORLD_VERT", "SCENERY21_AB", "SCENERY_DEDUP", "SCENERY_CONE", "SCENERY_PIECE_STATE", "PS2_PVS", "PS2_INTERIOR_CULL", "WORLD_RECT21")
    invalid += [["SCENERY_RECORD_SPLIT=1", k+"=0"] for k in required]
    invalid += [["SCENERY_RECORD_SPLIT=1", k+"="+("3" if k == "SCENERY_DEDUP" else "1")] for k in unsupported]
    for index, assignments in enumerate(invalid):
        command = [*seed, *assignments]
        run = subprocess.run(command, cwd=DC/"game", text=True, capture_output=True)
        text = run.stdout+run.stderr
        (out/("reject-%02d.log" % index)).write_text(text)
        assert run.returncode != 0 and "***" in text, (assignments, text)
        rejection.append(dict(assignments=assignments, returncode=run.returncode,
                              error=next(line for line in text.splitlines() if "***" in line)))
    assert frozen == source_hashes(), "source changed during target gate"
    toolchain = None
    if args.toolchain_receipt:
        raw = json.loads(args.toolchain_receipt.read_text())
        toolchain = dict(path=str(args.toolchain_receipt), sha256=profile.sha(args.toolchain_receipt),
                         image=raw.get("image"), scope=raw.get("scope"), status=raw.get("status"))
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline, compiler=compiler,
        compiler_sha256=profile.sha(cxx), linker_sha256=profile.sha(linker),
        newlib_header_sha256=profile.sha(newlib), toolchain_provenance=toolchain,
        compiler_verbose=verbose.stderr, linker=linker_version, kos=KOS_PIN, sh4zam=SDK_PIN,
        source_sha256=frozen, off_identity_comparisons=off_comparisons,
        enabled_unaffected_tu_comparisons=unaffected, make_rejections=rejection,
        enabled_profiles=[x[0] for x in enabled], artifacts=artifacts,
        census_composition=dict(partial_link_sha256=profile.sha(linked), all_new_hooks_resolved=True,
            core_fpu_instructions=0, assembly_sha256=profile.sha(assembly),
            scope="Real native_static/native_ui/core objects; external KOS/libc callees and final game link excluded"),
        profile_receipts={k: str(out/k/"ui-profile.json") for k in profiles},
        matched_override_reason="Both arms set PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0: old mesh-bound cells/texture certificates are unqualified for alternate files; foliage mip requires rect21. Existing interior actor code is scoped by cull0; ENEMY_VIS_CULL retains its required actor knob2. Test assets must be the matching unremapped original-policy package, not a rect21 remap with a relabelled fingerprint.",
        limitations="Complete compiled TUs; no final game link, private asset admission, emulator image or console measurement.")
    (out/"build-controls.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: report[k] for k in ("status", "off_identity_comparisons", "enabled_unaffected_tu_comparisons", "enabled_profiles")}))


if __name__ == "__main__":
    main()
