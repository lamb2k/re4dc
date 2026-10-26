#!/usr/bin/env python3
"""Make the target receipts reviewable without embedding repeated Make expansions.

Raw logs/objects stay in the qualification output directory. Compiler flags
are losslessly interned after documented path placeholders; compilation is
fully specified by flags plus the command template. No result or timing value
is recomputed or rounded.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(value).hexdigest()


def packed_hash(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def compact_controls(raw, source):
    out = source.parent
    first = raw["profile_receipts"]["recipe24-enabled"]["profiles"]["native_ui"]
    # Compiler-expanded flags contain absolute paths; preserve how to restore
    # them without repeating each output root in every command.
    actual_cxx = next(x["argv"][0] for x in json.loads((out / "build-commands.json").read_text())
                      if str(x["argv"][0]).endswith("sh-elf-g++"))
    source_root = next(x[2:] for x in first["flags"] if x.startswith("-I") and x.endswith("/port/dreamcast/game/platform/include"))
    source_root = source_root.removesuffix("/port/dreamcast/game/platform/include")
    kos_root = next(x for x in first["flags"] if x.endswith("/kernel/arch/dreamcast/include") and not x.startswith("-I")).removesuffix("/kernel/arch/dreamcast/include")
    sdk_root = first["flags"][-2].removeprefix("-I").removesuffix("/include")
    roots = {"$CXX": actual_cxx, "$CC": actual_cxx.removesuffix("g++") + "gcc", "$KOS_ROOT": kos_root,
             "$SDK_ROOT": sdk_root, "$SOURCE_ROOT": source_root, "$BASELINE_ROOT": str(out / "baseline-tree"), "$OUTPUT": str(out)}
    flagsets, recipes, profiles = {}, {}, {}

    def intern(table, value, prefix):
        for key, known in table.items():
            if known == value:
                return key
        key = prefix + str(len(table) + 1)
        table[key] = value
        return key

    for name, receipt in raw["profile_receipts"].items():
        old = name.endswith("-baseline")
        root = roots["$BASELINE_ROOT"] if old else roots["$SOURCE_ROOT"]
        unit_rows = {}
        for unit, row in receipt["profiles"].items():
            unit_root = str(out / name / unit)
            replacements = [(unit_root, "$UNIT_OUTPUT"), (root, "$TREE"), (kos_root, "$KOS_ROOT"), (sdk_root, "$SDK_ROOT")]
            def normal(value):
                if isinstance(value, str):
                    for before, after in replacements:
                        value = value.replace(before, after)
                    return value
                if isinstance(value, list):
                    return [normal(x) for x in value]
                if isinstance(value, dict):
                    return {normal(k): normal(v) for k, v in value.items()}
                return value
            values = normal(row["flags"])
            # All actual flags remain present; only duplicate arrays become references.
            flags_id = intern(flagsets, values, "flags")
            recipe_id = intern(recipes, normal(row["recipe_inputs"]), "recipe")
            unit_rows[unit] = dict(flags=flags_id, compiler="$CXX",
                                  language="c++", recipe=recipe_id,
                                  normalized_make_command_sha256=packed_hash(normal(row["command"])))
            if "generated_source_sha256" in row:
                unit_rows[unit]["generated_source_sha256"] = row["generated_source_sha256"]
            if row.get("generated_headers"):
                unit_rows[unit]["generated_headers"] = normal(row["generated_headers"])
        profiles[name] = dict(tree="$BASELINE_ROOT" if old else "$SOURCE_ROOT",
                              output="$OUTPUT/" + name, overrides=receipt["profiles"]["native_ui"]["overrides"],
                              define_zero_during_compile=name.endswith("-zero"), units=unit_rows)
    artifacts = {}
    for name, units in raw["artifacts"].items():
        artifacts[name] = {}
        for unit, original in units.items():
            row = dict(original)
            obj = dict(row["o"])
            stack = obj.pop("stack_usage")
            su = out / (name + "-" + unit + ".su")
            obj["stack_usage_file_sha256"] = digest(su.read_bytes())
            obj["compiler_reported_functions"] = len(stack)
            obj["max_function_frame_bytes"] = max((x["bytes"] for x in stack), default=0)
            wanted = ("fx_r200", "reset_deferred", "re4dc_room_id_now", "re4dc_effect_sprite", "re4dc_effect_line", "re4dc_effect_haze", "re4dc_effect_stage1", "re4dc_effect_strip", "re4dc_effect_quad", "re4dc_effect_mesh21", "constprop(unsigned int, unsigned char*&, unsigned int*&)")
            obj["relevant_stack_frames"] = [x for x in stack if any(word in x["function"] for word in wanted)]
            row["o"] = obj
            artifacts[name][unit] = row
    identity = []
    for kind in (name.removesuffix("-baseline") for name in raw["artifacts"] if name.endswith("-baseline")):
        for arm in ("absent", "zero"):
            for unit in ("native_ui", "ui_bridge"):
                identity.append(dict(profile=kind, arm=arm, unit=unit,
                    preprocessed_identical=raw["artifacts"][kind + "-" + arm][unit]["ii"]["sha256"] == raw["artifacts"][kind + "-baseline"][unit]["ii"]["sha256"],
                    whole_object_identical=raw["artifacts"][kind + "-" + arm][unit]["o"]["sha256"] == raw["artifacts"][kind + "-baseline"][unit]["o"]["sha256"]))
    keep = ("status", "scope", "baseline", "source_sha256", "compiler", "compiler_sha256", "linker",
            "toolchain_receipt", "kos", "sdk", "off_identity_comparisons", "partial_links", "production_layout", "limitations")
    result = {k: raw[k] for k in keep}
    result.update(path_placeholders=roots, flags=flagsets, recipe_inputs=recipes, profiles=profiles,
        compile_template=["$COMPILER", "$FLAGS...", "$EXPLICIT_ZERO_DEFINE_IF_ZERO...", "-iquote", "$SOURCE_PARENT", "-x", "$LANGUAGE", "-", "$PHASE...", "-o", "$OUTPUT_FILE"],
        phase_arguments=dict(preprocess=["-E", "-P"], object=["-c", "-fstack-usage"]),
        explicit_zero_define=["-DRE4DC_FX_R200_ENTRY_CAP=0"],
        source_inputs=dict(native_ui="$TREE/port/dreamcast/game/platform/native_ui.cpp", ui_bridge="$TREE/port/dreamcast/game/ui_bridge.cpp"),
        identity_scope="Complete preprocessed and complete ELF object bytes. No debug records were emitted in any arm. Source bytes supplied on stdin; include directory preserved with -iquote. Only paths were normalized for comparing Make flags; object bytes were never normalized or stripped.",
        identity_matrix=identity, artifacts=artifacts,
        make_state_checks={name: dict(returncode=row["returncode"], knobs={k: v for k,v in row["state"].items() if k not in ("PLATFORM_OBJS", "GAME_LDFLAGS")}) for name,row in raw["make_states"].items()},
        make_state_identity="The raw gate asserted identical PLATFORM_OBJS and GAME_LDFLAGS after source/output path normalization for every absent/zero arm.",
        make_rejections=[dict(value=row["value"], returncode=row["returncode"],
                             reason="\n".join(x for x in row["error"].splitlines() if "***" in x)) for row in raw["make_rejections"]])
    dependency_sets = {}
    dependency_refs = {}
    for name, units in raw["dependency_sha256"].items():
        dependency_refs[name] = {unit: intern(dependency_sets, values, "dependencies") for unit,values in units.items()}
    result["dependency_sets"] = dependency_sets
    result["dependencies_by_profile"] = dependency_refs
    return result


def compact_cost(raw):
    result = dict(raw)
    receipt = result.pop("profile_receipt")
    result["compile_profiles"] = {unit: dict(flags=row["flags"], overrides=row["overrides"],
        normalized_make_command_sha256=packed_hash(row["command"])) for unit,row in receipt["profiles"].items()}
    result["recipe_inputs"] = receipt["profiles"]["native_ui"]["recipe_inputs"]
    # These fixtures map only cached synthetic RAM. Verify the omitted
    # zero categories, then retain every load/store/byte/line value once.
    def cached(value):
        for kind in ("uncached", "store_queue"):
            assert all(number == 0 for number in value[kind].values())
        assert all(value["prefetch"][key] == 0 for key in
                   ("requests", "unique_requested_lines", "sq_flush_requests"))
        return value["cached"]
    for row in result["cases"]:
        traffic = row["traffic"]
        row["traffic"] = dict(cached(traffic),
            demand_line_visits=traffic["demand_line_visits"],
            repeated_demand_line_visits=traffic["repeated_demand_line_visits"],
            regions={name: cached(value) for name,value in traffic["regions"].items()})
        row.pop("command", None)
        row["cold_icache"].pop("command", None)
    result["traffic_scope"] = dict(all_accesses_to_cached_synthetic_ram=True,
        uncached_accesses=0, store_queue_accesses=0, prefetch_requests=0,
        notes="Instruction fetches excluded; literal loads included. Architectural 32-byte demand lines are not measured cache misses or bus transfers.")
    result["model_commands"] = dict(warm="hwsim --elf <model-address-view.elf> --out <case> --perfect-ic --perfect-dc --no-dma --sq-cost 0 <case.bin>",
        cold_i="hwsim --elf <model-address-view.elf> --out <case-cold-icache> --perfect-dc --no-dma --sq-cost 0 <case.bin>",
        note="Unmodified actual instruction traces; each trace SHA256 is retained per case.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = args.input.resolve()
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS"
    result = compact_controls(raw, source) if "artifacts" in raw else compact_cost(raw)
    result["raw_receipt_sha256"] = digest(source.read_bytes())
    result["compactor_sha256"] = digest(Path(__file__).read_bytes())
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status="PASS", input_bytes=source.stat().st_size, output_bytes=args.output.stat().st_size, output=str(args.output))))


if __name__ == "__main__":
    main()
