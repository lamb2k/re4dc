#!/usr/bin/env python3
"""Build27 Make-derived SH4 identity, control composition and module wiring.

All six changed existing TUs are compared with the independent integration
baseline, absent/zero, for the eight old-WEP05/weapon-heap/archive-reuse settings.
Enabled compositions compile and relocatably link the real new module objects.
This is not a complete game link, asset/equip run or console qualification.
"""
import argparse
import importlib.util
import io
import itertools
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "6be0a66ab59fa597a55aae7379fb09777d357bc1"
KNOB = "WEP_MODULES_27"
MACRO = "RE4DC_" + KNOB
spec = importlib.util.spec_from_file_location("wep27_shared_gate", HERE.parent / "build24/build_controls.py")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)
profile = shared.profile
UNITS = {"modules": ("platform/modules.o", "platform/modules.cpp"),
         **{name: (f"src/game/{name}.o", f"../../../src/game/{name}.cpp")
            for name in ("read", "pl_wep", "item", "sscrn", "t_option")}}
profile.UNITS.update(UNITS)
COMPOSITIONS = {f"w{w}-h{h}-a{a}": ["NMR_POOL_LOD=0", f"WEAPON_WEP05={w}",
                                   f"WEAPON_HEAP4={h}", f"ARCHIVE_REUSE={a}"]
                for w, h, a in itertools.product((0, 1), repeat=3)}
OBJECT_FIELDS = ("MODULES", "MODULE_ARGS", "PLATFORM_OBJS", "GAME_OBJS", "GAME_LDFLAGS")


def probe(out, tree, kos, sdk, options):
    out.mkdir(parents=True, exist_ok=False)
    fields = (KNOB, "WEAPON_WEP05", "WEAPON_HEAP4", "ARCHIVE_REUSE", *OBJECT_FIELDS)
    query = out / "query.mk"
    query.write_text(".PHONY: b27-state\nb27-state:\n\t@:\n" + "\n".join(
        f"$(info B27_STATE {name}=$({name}))" for name in fields) + "\n")
    command, _ = profile.make_command(out, tree, kos, sdk, options, "b27-state")
    command[3:3] = ["-f", "Makefile", "-f", str(query)]
    result = subprocess.run(command, cwd=tree / "port/dreamcast/game", capture_output=True, text=True)
    output = result.stdout + result.stderr
    (out / "make.log").write_text(output)
    state = dict(line[len("B27_STATE "):].split("=", 1) for line in output.splitlines()
                 if line.startswith("B27_STATE "))
    return dict(command=command, returncode=result.returncode, state=state,
                error=output[-2000:] if result.returncode else None)


def table_rows(path):
    text = path.read_text()
    start = text.index("g_modules[] = {")
    body = text[start:text.index("\n};", start)]
    return [(int(number), name) for number, name in re.findall(r'\{\s*(\d+)\s*,\s*"([^"]+)"', body)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root", "toolchain-receipt", "module-build"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--only", choices=("off", "on"))
    parser.add_argument("--composition", choices=tuple(COMPOSITIONS), help="Single preliminary composition; omit for authoritative full matrix")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    prefix = str(cxx).removesuffix("g++")
    builder = profile.Build(out)
    compiler = builder.run([cxx, "--version"], label="compiler").decode().splitlines()[0]
    linker = builder.run([prefix + "ld", "--version"], label="linker").decode().splitlines()[0]
    assert "15.2.0" in compiler and "2.45.1" in linker
    actual = json.loads(args.toolchain_receipt.read_text())
    known = json.loads((HERE.parent / "build24/receipts/toolchain.json").read_text())
    assert actual["image"] == known["image"]
    for path, digest in known["original_executable_sha256"].items():
        original = cxx.parents[5] / (path + ".real")
        if not original.exists():
            original = cxx.parents[5] / path
        assert profile.sha(original) == digest and actual["original_executable_sha256"][path] == digest
    for directory, pin in ((kos, "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"),
                           (sdk, "33fa4850cacb30dd0ad35485ef035526ec4ce782")):
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip() == pin
    modules = json.loads(args.module_build.read_text())
    assert modules["status"] == "PASS" and modules["baseline"] == BASELINE
    module_objects = []
    for mod in ("wep05", "wep06", "wep12"):
        path = Path(modules["modules"][mod]["object"])
        assert profile.sha(path) == modules["modules"][mod]["sha256"]
        module_objects.append(path)
    tree = out / "baseline-tree"
    tree.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", BASELINE], cwd=ROOT))) as archive:
        archive.extractall(tree, filter="data")
    sources = [(DC / "game" / source).resolve() for _, source in UNITS.values()]
    sources += [Path(__file__), DC / "game/Makefile", DC / "build-public.sh", DC / "tools/d367/rr/recipe.conf",
                DC / "tools/d367/kos_cache_audit/prepare.py", DC / "patches/kos-804b319-cache-p2.patch",
                DC / "tools/d367/build-r21.sh", *sorted((DC / "game").glob("*.mk"))]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in sources}
    artifacts, receipts, flags_by_profile, states, dependencies, links, wiring = {}, {}, {}, {}, {}, {}, {}
    comparisons = []
    cache_preparations = {}

    def compile_unit(name, unit, flags, sources, source_tree, zero=False):
        source = sources[unit]
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
            shutil.copytree(out / ("kos-cache-" + key), destination)
            for generated in (guards[0], destination / "tree/kernel/arch/dreamcast/include/arch/cache.h"):
                receipts[name]["profiles"][unit]["generated_headers"][str(generated)] = profile.sha(generated)
        common = [*flags[unit], *(["-D" + MACRO + "=0"] if zero else []), "-iquote", str(source.parent)]
        row = {}
        for suffix, phase in (("ii", ["-E", "-P"]),
                              ("o", ["-c", "-fstack-usage", "-MMD", "-MF", out / f"{name}-{unit}.d"])):
            target = out / f"{name}-{unit}.{suffix}"
            builder.run([*common, "-x", "c++", "-", *phase, "-o", target], cwd=source.parent,
                        source=source.read_bytes(), label=f"{name}-{unit}-{suffix}")
            row[suffix] = dict(bytes=target.stat().st_size, sha256=profile.sha(target))
            if suffix == "o":
                row[suffix].update(profile.sections(target), stack_usage=profile.stack_usage(target.with_suffix(".su")))
                deps = shared.dependencies(out / f"{name}-{unit}.d", source_tree, source.parent)
                dependencies.setdefault(name, {})[unit] = deps
                if source_tree == ROOT:
                    for path, digest in deps.items():
                        assert frozen.get(path, digest) == digest, (path, "source changed during gate")
                        frozen[path] = digest
        artifacts.setdefault(name, {})[unit] = row

    for kind, options in COMPOSITIONS.items():
        if args.composition and kind != args.composition:
            continue
        if args.only != "on":
            for arm in ("baseline", "absent", "zero"):
                name = kind + "-" + arm
                source_tree = tree if arm == "baseline" else ROOT
                extra = [KNOB + "=0"] if arm == "zero" else []
                flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk, options + extra,
                                                                tree=source_tree, units=tuple(UNITS))
                flags_by_profile[name] = flags
                for unit in UNITS:
                    if arm != "baseline":
                        left = [shared.normalized(x, out / (kind + "-baseline"), tree)
                                for x in flags_by_profile[kind + "-baseline"][unit]]
                        right = [shared.normalized(x, out / name, ROOT) for x in flags[unit]]
                        assert left == right, (name, unit, "Make flags changed with control disabled")
                    compile_unit(name, unit, flags, sources, source_tree, arm == "zero")
                    if arm != "baseline":
                        for suffix in ("ii", "o"):
                            assert (out / f"{name}-{unit}.{suffix}").read_bytes() == (
                                out / f"{kind}-baseline-{unit}.{suffix}").read_bytes(), (name, unit, suffix)
                            comparisons.append(dict(profile=kind, arm=arm, unit=unit, artifact=suffix, identical=True))
                states[name] = probe(out / (name + "-make"), source_tree, kos, sdk, options + extra)
                assert states[name]["returncode"] == 0, states[name]
                if arm != "baseline":
                    assert states[name]["state"][KNOB] == "0"
                    for field in OBJECT_FIELDS:
                        assert shared.normalized(states[name]["state"][field], out / (name + "-make"), ROOT) == shared.normalized(
                            states[kind + "-baseline"]["state"][field], out / (kind + "-baseline-make"), tree), (name, field)
                print("PASS", name, flush=True)
        if args.only != "off":
            name = kind + "-on"
            flags, receipts[name], sources = profile.derive(out / name, cxx, kos, sdk,
                                                            options + [KNOB + "=1"], units=tuple(UNITS))
            for unit in UNITS:
                assert "-D" + MACRO + "=1" in flags[unit], (name, unit, "enabled flag lost")
                compile_unit(name, unit, flags, sources, ROOT)
            table = table_rows(out / f"{name}-modules.ii")
            for row in ((67, "wep05"), (50, "wep06"), (56, "wep12")):
                assert table.count(row) == 1, (name, row, table)
                assert sum(number == row[0] for number, _ in table) == 1, (name, "duplicate module id", row)
            states[name] = probe(out / (name + "-make"), ROOT, kos, sdk, options + [KNOB + "=1"])
            assert states[name]["returncode"] == 0, states[name]
            selected = shlex.split(states[name]["state"]["MODULES"])
            for mod in ("wep05", "wep06", "wep12"):
                assert selected.count(mod) == 1, (name, mod, selected)
            generation = out / (name + "-modules")
            generation.mkdir()
            manifest = generation / "modules.mk"
            builder.run([sys.executable, DC / "game/tools/gen_modules.py", ROOT / "config/G4BE08/modules", ROOT,
                         generation, manifest, *shlex.split(states[name]["state"]["MODULE_ARGS"])], label=name + "-generate")
            manifest_text = manifest.read_text()
            for mod in ("wep05", "wep06", "wep12"):
                assert manifest_text.count("MODULE_OBJS += $(OBJDIR)/mod/" + mod + ".o\n") == 1
            combined = out / (name + "-combined.o")
            builder.run([prefix + "ld", "-m", "shlelf", "-r", *[out / f"{name}-{unit}.o" for unit in UNITS],
                         *module_objects, "-o", combined], label=name + "-partial-link")
            undefined = builder.run([prefix + "nm", "-u", "-C", combined], label=name + "-undefined").decode()
            bad = [line for line in undefined.splitlines() if any(token in line for token in
                ("weapon27", "wep27", "wep05_prolog", "wep05_epilog", "wep06_prolog", "wep06_epilog", "wep12_prolog", "wep12_epilog"))]
            assert not bad, (name, "new references unresolved", bad)
            links[name] = dict(sha256=profile.sha(combined), new_entry_and_admission_references_resolved=True,
                               scope="Relocatable link of six changed TUs and three real modules; inherited game/KOS imports remain explicit")
            wiring[name] = dict(table_rows=table, generated_manifest_sha256=profile.sha(manifest),
                                new_module_counts={mod: selected.count(mod) for mod in ("wep05", "wep06", "wep12")})
            print("PASS", name, flush=True)
    rejected = []
    for value in ("", "2", "0 1"):
        row = probe(out / ("reject-" + str(len(rejected))), ROOT, kos, sdk, ["NMR_POOL_LOD=0", KNOB + "=" + value])
        assert row["returncode"] != 0, (value, "invalid control accepted")
        rejected.append(dict(value=value, **row))
    assert frozen == {path: profile.sha(ROOT / path) for path in frozen}, "source changed during gate; rerun"
    report = dict(status="PASS", baseline=BASELINE, scope=__doc__, gate_half=args.only or "both",
                  knob=KNOB, source_sha256=frozen, compiler=compiler, compiler_path=str(cxx), linker=linker,
                  pinned_executable_sha256=known["original_executable_sha256"],
                  toolchain_receipt_sha256=profile.sha(args.toolchain_receipt),
                  cache_header_preparation=cache_preparations,
                  module_build_sha256=profile.sha(args.module_build), off_identity_comparisons=len(comparisons),
                  disabled_identity=comparisons, enabled_compositions=len(links), artifacts=artifacts,
                  profiles=receipts, dependency_sha256=dependencies, make_states=states,
                  partial_links=links, wiring=wiring, make_rejections=rejected,
                  validation_only_overrides=dict(NMR_POOL_LOD=0, reason="Public recipe lacks private Ganado assets; mirrored baseline/candidate override"),
                  limitations="Complete preprocessed/object identity without debug records; no final game image, private assets, physical console or gameplay acceptance. New module imports are qualified against baseline reference modules separately.")
    (out / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_comparisons=len(comparisons), enabled=len(links), receipt=str(out / "target-controls.json"))))


if __name__ == "__main__":
    main()
