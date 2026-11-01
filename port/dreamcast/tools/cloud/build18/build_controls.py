#!/usr/bin/env python3
"""Complete native_ui/ui_bridge SH4 OFF identity and Build18 enabled gates.

Profiles come from the current public recipe and actual Makefile. Both an
absent knob and explicit0 must match the archived integration base in whole
preprocessed output and whole object bytes, with no debug records emitted.
The layout probe reads real production types/constants from a separate object;
no final game link, private game data or owner rendering is exercised.
"""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "74154cae31b48ac6b15bfd6699a221da295cda63"
KOS_PIN = "804b3195ebd1a06a27cc2b3a5eacf7a2429040a3"
SDK_PIN = "33fa4850cacb30dd0ad35485ef035526ec4ce782"
spec = importlib.util.spec_from_file_location("fx18_make", HERE / "build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)


def source_paths():
    paths = [DC / "game/Makefile", DC / "game/mendezfx.mk", DC / "game/ui_bridge.cpp",
             DC / "game/platform/native_ui.cpp", DC / "game/platform/include/fx_r200_entry_cap.h",
             HERE / "build_profile.py", Path(__file__), HERE / "layout_probe.cpp.in",
             DC / "tools/d367/ui_draw_lean/build_profile.py", DC / "tools/d367/world_submit_spike/build_profile.py"]
    paths += sorted((DC / "game/platform/include").glob("native_effect*.inc"))
    paths += [DC / "game/platform/include/native_flashlight_pool.inc"]
    return paths


def hashes():
    return {str(path.relative_to(ROOT)): profile.sha(path) for path in source_paths()}


def normalized(value, output, tree):
    return value.replace(str(output), "<PROFILE>").replace(str(tree), "<SOURCE>")


def symbol_bytes(path, wanted):
    data = path.read_bytes()
    assert data[:6] == b"\x7fELF\x01\x01"
    shoff = struct.unpack_from("<I", data, 32)[0]
    shsize, shnum = struct.unpack_from("<HH", data, 46)
    sections = [struct.unpack_from("<10I", data, shoff + i * shsize) for i in range(shnum)]
    for section in sections:
        if section[1] != 2:
            continue
        strings = sections[section[6]]
        names = data[strings[4]:strings[4] + strings[5]]
        for at in range(section[4], section[4] + section[5], section[9]):
            name, value, size, _, _, index = struct.unpack_from("<IIIBBH", data, at)
            name = names[name:names.index(0, name)].decode()
            if name == wanted:
                target = sections[index]
                return data[target[4] + value:target[4] + value + size]
    raise AssertionError((path, "missing symbol", wanted))


def dependencies(path, tree, cwd):
    body = path.read_text().replace("\\\n", " ").split(":", 1)[1]
    result = {}
    for word in shlex.split(body):
        source = Path(word)
        if not source.is_absolute():
            source = cwd / source
        source = source.resolve()
        if source.is_file() and source.is_relative_to(tree):
            result[str(source.relative_to(tree))] = profile.sha(source)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root", "toolchain-receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--baseline", default=BASELINE)
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
    for folder, pin in ((kos, KOS_PIN), (sdk, SDK_PIN)):
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip() == pin
    frozen = hashes()
    tree = out / "baseline-tree"
    tree.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", args.baseline], cwd=ROOT))) as archive:
        archive.extractall(tree, filter="data")
    artifacts, profiles, flags_by_name, states, links, closure = {}, {}, {}, {}, {}, {}
    comparisons = 0
    for kind, options in profile.PROFILES.items():
        for arm, extra in (("baseline", []), ("absent", []), ("zero", ["FX_R200_ENTRY_CAP=0"]),
                           ("enabled", ["FX_R200_ENTRY_CAP=1"])):
            if kind == "slab-alias" and arm == "enabled":
                continue  # Enabled zero room spill is rejected below.
            name = kind + "-" + arm
            src_tree = tree if arm == "baseline" else ROOT
            flags, receipt, sources = profile.derive(out / name, cxx, kos, sdk, options + extra, tree=src_tree)
            profiles[name], flags_by_name[name] = receipt, flags
            artifacts[name], closure[name] = {}, {}
            for unit, source in sources.items():
                if arm in ("absent", "zero"):
                    left = [normalized(x, out / (kind + "-baseline"), tree) for x in flags_by_name[kind + "-baseline"][unit]]
                    right = [normalized(x, out / name, ROOT) for x in flags[unit]]
                    assert left == right, (name, unit, "Make flags differ")
                common = [*flags[unit], *(["-DRE4DC_FX_R200_ENTRY_CAP=0"] if arm == "zero" else []),
                          "-iquote", str(source.parent)]
                row = {}
                for suffix, phase in (("ii", ["-E", "-P"]), ("o", ["-c", "-fstack-usage", "-MMD", "-MF", out / f"{name}-{unit}.d"])):
                    target = out / f"{name}-{unit}.{suffix}"
                    builder.run([*common, "-x", "c++", "-", *phase, "-o", target],
                                cwd=source.parent, source=source.read_bytes(), label=f"{name}-{unit}-{suffix}")
                    row[suffix] = dict(bytes=target.stat().st_size, sha256=profile.sha(target))
                    if suffix == "o":
                        row[suffix].update(profile.sections(target), stack_usage=profile.stack_usage(target.with_suffix(".su")))
                        closure[name][unit] = dependencies(out / f"{name}-{unit}.d", src_tree, source.parent)
                    if arm in ("absent", "zero"):
                        assert target.read_bytes() == (out / f"{kind}-baseline-{unit}.{suffix}").read_bytes(), (name, unit, suffix, "OFF mismatch")
                        comparisons += 1
                artifacts[name][unit] = row
            state = profile.probe(out / (name + "-make"), src_tree, kos, sdk, options + extra)
            assert state["returncode"] == 0, state
            states[name] = state
            if arm in ("absent", "zero"):
                assert state["state"]["FX_R200_ENTRY_CAP"] == "0"
                for field in ("PLATFORM_OBJS", "GAME_LDFLAGS"):
                    assert normalized(state["state"][field], out / (name + "-make"), ROOT) == normalized(
                        states[kind + "-baseline"]["state"][field], out / (kind + "-baseline-make"), tree), (name, field)
            if arm == "enabled":
                combined = out / (name + "-combined.o")
                builder.run([prefix + "ld", "-m", "shlelf", "-r", *[out / f"{name}-{unit}.o" for unit in profile.UNITS],
                             "-o", combined], label=name + "-partial-link")
                undefined = builder.run([prefix + "nm", "-u", "-C", combined], label=name + "-undefined").decode()
                defined = builder.run([prefix + "nm", "--defined-only", combined], label=name + "-defined").decode()
                assert "re4dc_room_id_now" not in undefined, undefined
                assert sum(line.endswith(" _re4dc_room_id_now") for line in defined.splitlines()) == 1
                assert "re4dc::fx_r200" not in undefined, undefined
                links[name] = dict(sha256=profile.sha(combined), live_room_getter_defined_once=True,
                                   scope="Relocatable native_ui + ui_bridge link; ordinary game/KOS dependencies remain unresolved")
            print("PASS", name, flush=True)
    rejected = []
    for i, options in enumerate((["FX_R200_ENTRY_CAP=2"], ["FX_R200_ENTRY_CAP=-1"],
                                 ["FX_R200_ENTRY_CAP=1", "FX_ROOM_SPILL_KB=0"])):
        state = profile.probe(out / f"reject-{i}", ROOT, kos, sdk, options)
        assert state["returncode"] != 0, (options, "invalid configuration accepted")
        rejected.append(dict(value=" ".join(options), **state))
    source = DC / "game/platform/native_ui.cpp"
    layout_obj = out / "production-layout.o"
    export = (HERE / "layout_probe.cpp.in").read_bytes()
    builder.run([*flags_by_name["recipe24-enabled"]["native_ui"], "-iquote", str(source.parent), "-x", "c++", "-",
                 "-c", "-o", layout_obj], cwd=source.parent, source=source.read_bytes() + b"\n" + export, label="layout")
    names = ("tail_state", "context", "deferred_part", "sprite_node", "sprite_packet", "line_packet",
             "haze_oct_packet", "trim_oct_packet", "ui_quad", "frame_storage", "model_slab", "model_tail",
             "model_packets", "model_preparation", "model_metadata", "model_static_light", "sprite_cap", "queue_margin", "room_spill_kib")
    raw = symbol_bytes(layout_obj, "_fixture_fx18_layout")
    assert len(raw) == 4 * len(names), len(raw)
    layout = dict(zip(names, struct.unpack("<" + "I" * len(names), raw)))
    assert layout["model_tail"] == 8192 and layout["room_spill_kib"] == 24
    assert hashes() == frozen, "production/gate sources changed; rerun"
    report = dict(status="PASS", scope=__doc__, baseline=args.baseline, source_sha256=frozen,
        compiler=compiler, compiler_sha256=profile.sha(cxx), linker=linker, kos=KOS_PIN, sdk=SDK_PIN,
        toolchain_receipt=dict(path=str(args.toolchain_receipt), sha256=profile.sha(args.toolchain_receipt)),
        off_identity_comparisons=comparisons, artifacts=artifacts, profile_receipts=profiles,
        dependency_sha256=closure, make_states=states, partial_links=links, make_rejections=rejected,
        production_layout=dict(bytes=layout, object_sha256=profile.sha(layout_obj),
            source_sha256=profile.sha(source), exporter_sha256=profile.sha(HERE / "layout_probe.cpp.in")),
        limitations="Complete target translation units and whole-object OFF identity without debug records. No final game ELF/full-image identity, target console execution, heap/owner-render measurement, private game data, or PVR result.")
    (out / "target-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", off_comparisons=comparisons, profiles=list(profile.PROFILES), receipt=str(out / "target-controls.json"))))


if __name__ == "__main__":
    main()
