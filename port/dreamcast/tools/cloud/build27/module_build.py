#!/usr/bin/env python3
"""Compile and partially link the actual generated Build27 weapon modules.

The existing gen_modules.py source selection, rename definitions, state linker
script, intra-module alias generator and objcopy export policy are retained.
Make supplies each complete source command. Reference wep02/wep11 modules are
built for an explicit import-set comparison; that comparison is not a complete
game link or proof that an unresolved external provider executes correctly.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import struct
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASELINE = "6be0a66ab59fa597a55aae7379fb09777d357bc1"
spec = importlib.util.spec_from_file_location("wep27_profile", HERE.parent / "build18/build_profile.py")
profile = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile
spec.loader.exec_module(profile)
spec = importlib.util.spec_from_file_location("wep27_generator", DC / "game/tools/gen_modules.py")
generator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = generator
spec.loader.exec_module(generator)
spec = importlib.util.spec_from_file_location("wep27_dependencies", HERE.parent / "build24/build_controls.py")
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)
MODULES = ("wep05", "wep06", "wep12", "wep02", "wep11")


def section_details(path):
    data = path.read_bytes()
    assert data[:6] == b"\x7fELF\x01\x01"
    offset = struct.unpack_from("<I", data, 32)[0]
    stride, count, names_index = struct.unpack_from("<3H", data, 46)
    sections = [struct.unpack_from("<10I", data, offset + i * stride) for i in range(count)]
    strings = sections[names_index]
    names = data[strings[4]:strings[4] + strings[5]]
    rows = []
    for row in sections:
        if not row[2] & 2:
            continue
        name = names[row[0]:].split(b"\0", 1)[0].decode()
        category = "bss" if row[1] == 8 else "text" if row[2] & 4 else "data" if row[2] & 1 else "rodata"
        rows.append(dict(name=name, bytes=row[5], alignment=row[8], category=category))
    return dict(rows=rows, **{key + "_bytes": sum(row["bytes"] for row in rows if row["category"] == key)
                             for key in ("text", "rodata", "data", "bss")})


def symbols(builder, prefix, path, label):
    body = builder.run([prefix + "nm", "-P", path], label=label).decode()
    result = {}
    for line in body.splitlines():
        words = line.split()
        if len(words) >= 2:
            result[words[0]] = dict(type=words[1], value=int(words[2], 16) if len(words) > 2 else None,
                                    size=int(words[3], 16) if len(words) > 3 else None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "sh4-cxx", "kos-root", "sdk-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cxx, kos, sdk = args.sh4_cxx.resolve(), args.kos_root.resolve(), args.sdk_root.resolve()
    prefix = str(cxx).removesuffix("g++")
    builder = profile.Build(out)
    work = out / "profile"
    work.mkdir()
    objdir = work / "obj"
    manifest = objdir / "modules.mk"
    generator_command = [sys.executable, DC / "game/tools/gen_modules.py", ROOT / "config/G4BE08/modules",
                         ROOT, objdir, manifest, *MODULES]
    builder.run(generator_command, label="generate")
    sources = [Path(__file__), DC / "game/tools/gen_modules.py", DC / "game/tools/gen_aliases.py",
               ROOT / "config/G4BE08/modules.py", DC / "game/Makefile", DC / "build-public.sh",
               DC / "tools/d367/rr/recipe.conf", DC / "tools/d367/build-r21.sh",
               *sorted((DC / "game").glob("*.mk"))]
    for mod in MODULES:
        sources += [ROOT / "config/G4BE08/modules" / mod / "splits.txt"]
        sources += [ROOT / source for source in generator.units(str(ROOT / "config/G4BE08/modules"), mod)[1]]
    frozen = {str(path.relative_to(ROOT)): profile.sha(path) for path in set(sources)}
    options = ["NMR_POOL_LOD=0", "WEP_MODULES_27=1"]
    results, profiles, dependencies = {}, {}, {}
    for mod in MODULES:
        objects, stack = [], []
        units = generator.units(str(ROOT / "config/G4BE08/modules"), mod)[1]
        for source in [*units, "unresolved.cpp"]:
            is_stub = source == "unresolved.cpp"
            target = f"mod/{mod}/" + ("unresolved.o" if is_stub else source[:-4] + ".o")
            source_path = objdir / "mod" / mod / source if is_stub else ROOT / source
            relative = str(source_path) if is_stub else "../../../" + source
            key = mod + "-" + source.replace("/", "-").removesuffix(".cpp")
            seed, recipe = profile.make_command(work, ROOT, kos, sdk, options,
                                                objdir / "platform/native_static.o")
            with profile.profile.source_tree(ROOT):
                flags, row = profile.profile.helpers.expand(work, cxx, sdk,
                    kos / "kernel/arch/dreamcast/include", dict(command=seed), key, target, relative)
            # GAME_O2=hot names a fixed subset (including wep02). Other weapon
            # modules retain the actual GAME_OPT=-O1 recipe, including wep11.
            optimization = [flag for flag in flags if re.fullmatch(r"-O(?:[0123gsz]|fast)", flag)][-1]
            profiles[key] = dict(row, recipe_inputs=recipe, overrides=options, final_optimization=optimization)
            obj = objdir / target
            obj.parent.mkdir(parents=True, exist_ok=True)
            builder.run([*flags, "-fstack-usage", "-MMD", "-MF", obj.with_suffix(".d"),
                         "-c", source_path, "-o", obj], cwd=DC / "game", label=key)
            objects.append(obj)
            stack.extend(profile.stack_usage(obj.with_suffix(".su")))
            dependencies[key] = shared.dependencies(obj.with_suffix(".d"), ROOT, DC / "game")
            for path, digest in dependencies[key].items():
                assert frozen.get(path, digest) == digest, (path, "dependency changed during build")
                frozen[path] = digest
        partial = objdir / "mod" / (mod + ".o.tmp")
        script = objdir / "mod" / mod / "state.ld"
        builder.run([prefix + "ld", "-r", "-d", "--force-group-allocation", "-EL", "-T", script,
                     "-o", partial, *objects], label=mod + "-partial")
        info = symbols(builder, prefix, partial, mod + "-partial-symbols")
        sections = section_details(partial)
        assert not any(re.match(r"\.(ctors|dtors|init_array|fini_array)", row["name"]) for row in sections["rows"])
        assert not any(row["type"] == "C" for row in info.values()), "common outside REL state span"
        defined = sorted(name for name, row in info.items() if row["type"] in "TDBWRV")
        undefined = sorted(name for name, row in info.items() if row["type"] == "U" and name not in defined)
        definitions = out / (mod + ".def")
        definitions.write_text("\n".join(defined) + "\n")
        demangled = builder.run([prefix + "c++filt"], source=definitions.read_bytes(), label=mod + "-demangle").decode().splitlines()
        pairs = out / (mod + ".pairs")
        pairs.write_text("".join(name + "\t" + dem + "\n" for name, dem in zip(defined, demangled)))
        missing = out / (mod + ".undef")
        missing.write_text("\n".join(undefined) + "\n")
        aliases = out / (mod + ".aliases.ld")
        builder.run([sys.executable, DC / "game/tools/gen_aliases.py", missing, pairs, aliases], label=mod + "-aliases")
        partial2 = partial.with_suffix(".tmp2")
        builder.run([prefix + "ld", "-r", "-EL", "-o", partial2, partial, aliases], label=mod + "-alias-link")
        partial2.replace(partial)
        exports = ["_" + mod + "_" + name for name in ("prolog", "epilog")]
        exports += ["_re4dc_mod_" + mod + "_" + name for name in ("data", "data_end", "bss", "bss_end", "pristine")]
        result = objdir / "mod" / (mod + ".o")
        builder.run([prefix + "objcopy", *[word for name in exports for word in ("-G", name)], partial, result],
                    label=mod + "-localize")
        info = symbols(builder, prefix, result, mod + "-symbols")
        actual_exports = sorted(name for name, row in info.items() if row["type"].isupper() and row["type"] != "U")
        assert actual_exports == sorted(exports), (mod, actual_exports)
        state = {name: info["_re4dc_mod_" + mod + "_" + name]["value"]
                 for name in ("data", "data_end", "bss", "bss_end", "pristine")}
        results[mod] = dict(object=str(result), sha256=profile.sha(result), sources=units,
            sections=section_details(result), stack_usage=stack, state=state,
            writable_data_bytes=state["data_end"] - state["data"],
            writable_bss_bytes=state["bss_end"] - state["bss"],
            pristine_copy_bytes=state["data_end"] - state["data"],
            imports=sorted(name for name, row in info.items() if row["type"] == "U"), exports=actual_exports,
            generated_manifest_sha256=profile.sha(manifest), state_script_sha256=profile.sha(script),
            intra_module_aliases=aliases.read_text(), allocated=profile.sections(result))
        print("PASS module", mod, flush=True)
    reference_imports = set(results["wep02"]["imports"]) | set(results["wep11"]["imports"])
    for mod in MODULES[:3]:
        results[mod]["imports_not_in_reference_union"] = sorted(set(results[mod]["imports"]) - reference_imports)
        assert not results[mod]["imports_not_in_reference_union"], (mod, "new external imports require provider qualification")
    assert frozen == {name: profile.sha(ROOT / name) for name in frozen}, "source changed during build; rerun"
    report = dict(status="PASS", baseline=BASELINE, scope=__doc__, modules=results, profiles=profiles,
                  dependency_sha256=dependencies,
                  source_sha256=frozen, generator_command=[str(x) for x in generator_command],
                  limitations="Generated public source modules only; no game assets, final game link, missing-symbol success stubs or console execution. External imports remain explicit and must be qualified by providers or baseline comparison separately. BSS totals include pristine data backing reserved by the unchanged generator.")
    (out / "module-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", modules=len(results), receipt=str(out / "module-build.json"))))


if __name__ == "__main__":
    main()
