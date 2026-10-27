#!/usr/bin/env python3
"""Compact Build24 receipts without changing any measured/modelled values.

Repeated Make flags, recipe inputs and dependency sets are interned. Every
identity hash and cost/traffic value is retained. Large whole-TU static-stack
lists are represented by their original .su hash, maximum frame, count and
relevant observer/clip frames. Raw receipts remain in the run directory.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packed(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def intern(table, value, prefix):
    key = prefix + packed(value)[:16]
    assert key not in table or table[key] == value, "intern hash collision"
    table[key] = value
    return key


def normalize(value, replacements):
    if isinstance(value, str):
        for before, after in replacements:
            value = value.replace(before, after)
        return value
    if isinstance(value, list):
        return [normalize(item, replacements) for item in value]
    if isinstance(value, dict):
        return {normalize(key, replacements): normalize(item, replacements) for key, item in value.items()}
    return value


def compact_controls(raw, source):
    out = source.parent
    result = {key: value for key, value in raw.items()
              if key not in ("profiles", "dependency_sha256", "make_states", "make_rejections", "artifacts")}
    first = next(iter(next(iter(raw["profiles"].values()))["profiles"].values()))
    cxx = first["flags"][0]
    kos = next(flag.removeprefix("-I").removesuffix("/kernel/arch/dreamcast/include")
               for flag in first["flags"] if flag.endswith("/kernel/arch/dreamcast/include"))
    sdk = first["flags"][-2].removeprefix("-I").removesuffix("/include")
    roots = {"$SOURCE": str(ROOT), "$BASELINE": str(out / "baseline-tree"), "$OUTPUT": str(out),
             "$CXX": cxx, "$KOS": kos, "$SDK": sdk}
    replacements = sorted(((value, key) for key, value in roots.items()), key=lambda pair: -len(pair[0]))
    flags, recipes, profiles, dependencies, dependency_refs = {}, {}, {}, {}, {}
    for name, receipt in raw["profiles"].items():
        units = {}
        tree = out / "baseline-tree" if name.endswith("-baseline") else ROOT
        for unit, row in receipt["profiles"].items():
            normal = lambda value: normalize(value, [(str(out / name / unit), "$UNIT_OUTPUT"), (str(tree), "$TREE"), *replacements])
            units[unit] = dict(flags=intern(flags, normal(row["flags"]), "flags-"),
                               recipe=intern(recipes, normal(row["recipe_inputs"]), "recipe-"),
                               generated_headers=normal(row["generated_headers"]),
                               make_command_sha256=packed(normal(row["command"])))
        profiles[name] = dict(overrides=next(iter(receipt["profiles"].values()))["overrides"], units=units,
                              tree="$BASELINE" if name.endswith("-baseline") else "$SOURCE",
                              debug_records=False, private_assets_not_used=True,
                              explicit_zero_defines=name.endswith("-zero"))
    for name, units in raw["dependency_sha256"].items():
        dependency_refs[name] = {unit: intern(dependencies, values, "deps-") for unit, values in units.items()}
    artifacts = {}
    for name, units in raw["artifacts"].items():
        artifacts[name] = {}
        for unit, values in units.items():
            row, obj = dict(values), dict(values["o"])
            stack = obj.pop("stack_usage")
            obj.update(stack_usage_sha256=sha((out / (name + "-" + unit + ".su")).read_bytes()),
                       compiler_reported_function_count=len(stack),
                       max_function_frame_bytes=max((frame["bytes"] for frame in stack), default=0),
                       relevant_stack_frames=[frame for frame in stack if any(word in frame["function"]
                           for word in ("dsa24", "clip_strip", "Gather", "ModelRoot::Draw"))])
            row["o"] = obj
            artifacts[name][unit] = normalize(row, replacements)
    states = {}
    for name, row in raw["make_states"].items():
        state = row["state"]
        state_replacements = [(str(out / (name + "-make")), "$PROFILE"),
                              (str(out / "baseline-tree"), "$TREE"), (str(ROOT), "$TREE"), *replacements]
        states[name] = dict(returncode=row["returncode"],
                           controls={key: value for key, value in state.items() if key not in ("PLATFORM_OBJS", "GAME_LDFLAGS")},
                           normalized_platform_objects_sha256=packed(normalize(state["PLATFORM_OBJS"], state_replacements)),
                           normalized_game_ldflags_sha256=packed(normalize(state["GAME_LDFLAGS"], state_replacements)))
    identity = []
    for name, units in artifacts.items():
        if not name.endswith(("-absent", "-zero")):
            continue
        baseline = name.rsplit("-", 1)[0] + "-baseline"
        for unit, row in units.items():
            identity.append(dict(profile=name, unit=unit,
                                 preprocessed_identical=row["ii"]["sha256"] == artifacts[baseline][unit]["ii"]["sha256"],
                                 whole_object_identical=row["o"]["sha256"] == artifacts[baseline][unit]["o"]["sha256"]))
    result.update(path_placeholders=roots, flags=flags, recipe_inputs=recipes, profiles=profiles,
                  dependency_sets=dependencies, dependency_references=dependency_refs, artifacts=artifacts,
                  make_state_checks=states, identity_matrix=identity,
                  make_state_identity="The gate compared full PLATFORM_OBJS/GAME_LDFLAGS strings after source/profile path normalization. Object/preprocessed bytes were not normalized or stripped.",
                  make_rejections=[{**{key: value for key, value in row.items() if key in ("knob", "value", "prerequisite", "returncode")},
                                    "reason": "\n".join(line for line in (row.get("error") or "").splitlines() if "***" in line)}
                                   for row in raw["make_rejections"]],
                  compile_template=["$FLAGS", "$EXPLICIT_ZERO_DEFINES_IF_ZERO", "-iquote", "$SOURCE_PARENT", "-x", "c++", "-", "$PHASE", "-o", "$OUTPUT_FILE"],
                  phase_arguments=dict(preprocess=["-E", "-P"], object=["-c", "-fstack-usage", "-MMD", "-MF", "$DEPENDENCIES"]),
                  explicit_zero_defines=["-DRE4DC_" + name + "=0" for name in ("DRAW_SETUP_AUDIT", "ACTOR_CLIP_REUSE", "SCENERY_CLIP_GATHER")])
    assert all(row["preprocessed_identical"] and row["whole_object_identical"] for row in identity)
    return result


def compact_cost(raw):
    result = dict(raw)
    recipes = {}
    for name, configuration in result["configurations"].items():
        receipt = configuration.pop("profile_receipt")
        row = receipt["profiles"]["draw_setup_audit"]
        configuration["compile_profile"] = dict(overrides=row["overrides"], generated_headers=row["generated_headers"],
                                                make_command_sha256=packed(row["command"]),
                                                recipe=intern(recipes, row["recipe_inputs"], "recipe-"))
    result["recipe_inputs"] = recipes

    def cached(value):
        for kind in ("uncached", "store_queue"):
            assert all(number == 0 for number in value[kind].values())
        assert all(value["prefetch"][key] == 0 for key in ("requests", "unique_requested_lines", "sq_flush_requests"))
        return value["cached"]

    for row in result["cases"]:
        traffic = row["traffic"]
        row["traffic"] = dict(cached(traffic), demand_line_visits=traffic["demand_line_visits"],
                              repeated_demand_line_visits=traffic["repeated_demand_line_visits"],
                              regions={name: cached(value) for name, value in traffic["regions"].items()})
        row.pop("command", None)
        row["cold_icache"].pop("command", None)
    result["traffic_scope"] = "All accesses are synthetic cached RAM; zero uncached/SQ/prefetch accesses were asserted. Literal reads included, opcode fetches excluded. Demand lines are not cache misses."
    result["model_commands"] = dict(warm="hwsim --elf <model-address-view.elf> --out <case> --perfect-ic --perfect-dc --no-dma --sq-cost 0 <case.bin>",
                                    cold_i="hwsim --elf <model-address-view.elf> --out <case> --perfect-dc --no-dma --sq-cost 0 <case.bin>")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    raw = json.loads(source.read_text())
    assert raw["status"] == "PASS"
    result = compact_controls(raw, source) if "artifacts" in raw else compact_cost(raw)
    result["raw_receipt_sha256"] = sha(source.read_bytes())
    result["compactor_sha256"] = sha(Path(__file__).read_bytes())
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps(dict(status="PASS", input_bytes=source.stat().st_size, output_bytes=args.output.stat().st_size, output=str(args.output))))


if __name__ == "__main__":
    main()
