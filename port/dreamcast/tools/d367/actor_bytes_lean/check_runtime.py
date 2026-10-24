#!/usr/bin/env python3
"""Production-TU differential fixtures for ACTOR_BYTES_LEAN retained ARGB.

Derives render macros from the current public Make profile. Explicit host
adapters replace SH-4 AVK/SQ transport and several target-only boundaries;
this verifies integer/cache/submission logic, not SH-4 floating-point output.
The exact target instruction/body check and off identity are separate receipts.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASE_FIXTURE = HERE.parent / "actor_setup_lean/fixture_actor.cpp.in"
spec = importlib.util.spec_from_file_location("actor_setup_runtime", HERE.parent / "actor_setup_lean/check_runtime.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
ACTOR = setup.ACTOR


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_macros(row):
    """GCC applies command-line -D before forced includes, regardless of order."""
    macros, includes = {}, []
    flags = iter(row["flags"])
    for flag in flags:
        if flag == "-include":
            includes.append(Path(next(flags)))
        elif flag.startswith("-DRE4DC_"):
            name, equal, value = flag[2:].partition("=")
            macros[name] = value if equal else "1"
    for path in includes:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            match = re.fullmatch(r"#define\s+(RE4DC_\w+)\s+(.+)", line)
            assert match, (str(path), "unsupported generated header", line)
            macros[match[1]] = match[2]
    return macros


def fixture_text():
    source = BASE_FIXTURE.read_text()
    # This remains the established whole-production-TU fixture; only add the
    # controlled model class and MOVCA discard boundary needed by this lane.
    old = "unsigned locks=0, unlocks=0;"
    assert source.count(old) == 1
    source = source.replace(old, old + "\nunsigned model_class=0;")
    old = 'extern "C" int re4dc_actor_model_class(const void*,const void*){return 0;}'
    assert source.count(old) == 1
    source = source.replace(old, 'extern "C" int re4dc_actor_model_class(const void*,const void*){return check::model_class;}')
    old = "ta.clear();events.clear();calls.clear();sources.clear();locks=unlocks=0;"
    assert source.count(old) == 1
    source = source.replace(old, old + "model_class=0;")
    # A MOVCA cache miss can invalidate any retained word in that output line.
    # Poison ARGB in the host position adapter to force the guarded fallback;
    # this is an adversarial boundary test, not a hardware MOVCA emulator.
    old = "assert(done);i+=done;"
    assert source.count(old) == 1
    source = source.replace(old, '''assert(done);
#if RE4DC_ACTOR_MOVCA
        for(unsigned j=i;j<i+done;++j)dst[j].argb=0x12bad00du;
#endif
        i+=done;''')
    main = source.index("int main(){")
    source = source[:main] + (HERE / "fixture_actor_bytes.cpp.in").read_text() + "\n" + source[main:]
    old = '    std::fprintf(stderr,"cases=%u ta_words=%u\\n",check::count_case,check::total_words);'
    assert source.count(old) == 1
    source = source.replace(old, "    check::bytes_cases();\n" + old)
    return source


# Diagnostic observability and platform substitutions are explicit. Public
# actor lighting, crowd, skin, palette and kernel admissions otherwise remain.
HOST_OVERRIDES = {
    "RE4DC_ACTOR_ASM": 0,             # hosted AVK adapters, portable fallback
    "RE4DC_COARSE_GATE_ONCE": 0,      # SH-4-only inline-assembly fog proof
    "RE4DC_RIGID_CHUNK": 0,           # external chunk/SQ backend, unchanged by this patch
    "RE4DC_ACTOR_LOD_BUDGET": 0,      # synthetic prebuilt LOD fixtures, no conversion workload
    "RE4DC_ACTOR_STATS_LEAN": 0,      # admission assertions need real diagnostic counters
}


def configurations(mode):
    rows = [dict(setup=s, direct=d, cone=c, avk=1, no_clear=1, movca=0, uv16=0, char_chunk=0)
            for s, d, c in itertools.product((0, 1), (0, 1), (0, 1, 2))]
    if mode == "smoke":
        return rows[3:4]
    if mode == "sanitizer":
        return [dict(setup=1, direct=1, cone=2, avk=2, no_clear=1, movca=0, uv16=0, char_chunk=0)]
    if mode == "negative":
        return [dict(setup=1, direct=1, cone=0, avk=1, no_clear=1, movca=0,
                     uv16=0, char_chunk=0, negative=kind)
                for kind in ("skipped-growth", "inherited-prefix", "omitted-half")]
    extras = [dict(setup=1, direct=1, cone=2, avk=2, no_clear=1, movca=0, uv16=0, char_chunk=0),
              dict(setup=1, direct=1, cone=0, avk=1, no_clear=0, movca=0, uv16=0, char_chunk=0),
              dict(setup=1, direct=1, cone=0, avk=1, no_clear=1, movca=1, uv16=0, char_chunk=0),
              dict(setup=1, direct=1, cone=0, avk=1, no_clear=1, movca=0, uv16=1, char_chunk=0),
              dict(setup=1, direct=1, cone=0, avk=1, no_clear=1, movca=0, uv16=0, char_chunk=1)]
    return extras if mode == "extras" else rows + extras


def coverage(data):
    """Read assertion-backed fixture tags without modifying production bodies."""
    counts = {"new_part_colour_changes": 0, "new_frame_colour_changes": 0,
              "window_colour_changes": 0, "half_post_parts_verified": 0,
              "half_post_vertices_verified": 0, "prefix_sweeps": 0}
    half_cases, offset = set(), 0
    while offset < len(data):
        magic, case, nt, ne, nk, locks, unlocks = struct.unpack_from("<7I", data, offset)
        assert magic == 0x41435452 and locks == unlocks
        offset += 28 + nt * 4
        events = struct.unpack_from(f"<{ne}I", data, offset)
        offset += (ne + nk) * 4
        for i in range(0, ne, 3):
            tag, a, b = events[i:i+3]
            if tag == 100:
                assert a != b
                counts["new_part_colour_changes"] += 1
            elif tag == 101:
                assert a != b
                counts["new_frame_colour_changes"] += 1
            elif tag == 102:
                assert a > 1
                counts["window_colour_changes"] += 1
            elif tag == 103:
                assert a == 1 and b
                counts["half_post_parts_verified"] += a
                counts["half_post_vertices_verified"] += b
                half_cases.add(case)
            elif tag == 104:
                assert a == 128 and b == 12
                counts["prefix_sweeps"] += 1
    assert offset == len(data)
    counts["half_post_cases"] = sorted(half_cases)
    return counts


def mutate(source, name):
    """Bounded controls: these deliberately break only the new retained-colour invariant."""
    if name == "skipped-growth":
        old, new = "if (n <= flat_primed) return;", "if (flat_primed) return;"
        assert source.count(old) == 1
    elif name == "inherited-prefix":
        old = "e.direct = true; e.sq = w.sq; e.primed = w.primed;"
        new = old + "\n#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA\n        e.flat_primed = w.primed;\n#endif"
        assert source.count(old) == 1
    elif name == "omitted-half":
        old = "flat_argb = (flat_argb & 0xFF000000U) | ((flat_argb >> 1) & 0x007F7F7FU);"
        new = "flat_argb = flat_argb; // deliberately omit the retained half_post fold"
        assert source.count(old) == 2
    else:
        raise AssertionError(name)
    return source.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("all", "smoke", "extras", "sanitizer", "negative"), default="all")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    profiles = json.loads(args.profile.read_text())
    headers = out / "host/dc"
    headers.mkdir(parents=True)
    (headers / "pvr.h").write_text(setup.PVR)
    (headers / "sq.h").write_text(setup.SQ)
    original_source = ACTOR.read_bytes()
    source, adaptations = setup.host_source(original_source.decode())
    (out / "native_actor_original.cpp").write_bytes(original_source)
    (out / "native_actor_host.inc").write_text(source)
    (out / "executed_driver.py").write_bytes(Path(__file__).read_bytes())
    (out / "executed_extension.cpp.in").write_bytes((HERE / "fixture_actor_bytes.cpp.in").read_bytes())
    fixture = out / "fixture.cpp"
    fixture.write_text(fixture_text())
    rows = []
    for config in configurations(args.mode):
        negative = config.get("negative")
        profile_key = f's{config["setup"]}-d{config["direct"]}-c{min(config["cone"],1)}'
        public = profiles["profiles"][profile_key]
        macros = profile_macros(public)
        overrides = dict(HOST_OVERRIDES)
        overrides.update(RE4DC_ACTOR_SETUP_LEAN=config["setup"], RE4DC_ACTOR_DIRECT=config["direct"],
            RE4DC_ACTOR_BACKFACE_CONE=config["cone"], RE4DC_COARSE_ONE_SUBMIT=config["direct"] and not config["uv16"],
            RE4DC_ACTOR_VTX_KERNEL=config["avk"], RE4DC_ACTOR_LIGHT_N16=config["avk"],
            RE4DC_ACTOR_NO_CLEAR=config["no_clear"], RE4DC_ACTOR_MOVCA=config["movca"],
            RE4DC_ACTOR_UV16=config["uv16"], RE4DC_CHAR_CHUNK=config["char_chunk"])
        macros.update({key: str(int(value)) if isinstance(value, bool) else str(value) for key, value in overrides.items()})
        pair = []
        label = "-".join(f"{k}{v}" for k, v in config.items())
        for lean in (0, 1):
            macros["RE4DC_ACTOR_BYTES_LEAN"] = str(lean)
            name = label + f"-bytes{lean}"
            binary = out / name
            hosted = mutate(source, negative) if negative and lean else source
            (out / "native_actor_host.inc").write_text(hosted)
            command = ["g++", "-std=c++20", "-O2", "-fno-fast-math", "-ffp-contract=off",
                "-ffunction-sections", "-fdata-sections", "-Wall", "-Wextra",
                *(f"-D{k}={v}" for k, v in sorted(macros.items())),
                "-I" + str(out / "host"), "-I" + str(DC / "game/platform"),
                "-I" + str(DC / "game/platform/include"), "-I" + str(DC / "room"),
                str(fixture), str(DC / "room/pvr_geometry.cpp"), str(DC / "room/source_lighting.cpp"),
                "-Wl,--gc-sections", "-o", str(binary)]
            if args.mode == "sanitizer":
                command[1:1] = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all"]
                command[command.index("-O2")] = "-O1"
            run = subprocess.run(command, capture_output=True)
            (out / (name + ".compile.log")).write_bytes(run.stdout + run.stderr)
            assert run.returncode == 0, (name, run.stderr.decode())
            environment = os.environ.copy()
            if args.mode == "sanitizer":
                environment["ASAN_OPTIONS"] = "detect_leaks=0"
            run = subprocess.run([str(binary)], capture_output=True, env=environment)
            (out / (name + ".stdout")).write_bytes(run.stdout)
            (out / (name + ".stderr")).write_bytes(run.stderr)
            if negative and lean:
                assert run.returncode == 0 or (run.returncode == -6 and b"Assertion" in run.stderr), (name, run.stderr.decode())
                assert run.returncode or run.stdout != pair[0], (name, "negative control was not detected")
                rows.append(dict(config=config, lean=lean, expected_failure=True, returncode=run.returncode,
                    hosted_source_sha256=hashlib.sha256(hosted.encode()).hexdigest(),
                    stderr=run.stderr.decode(), command=command))
                continue
            assert run.returncode == 0, (name, run.returncode, run.stderr.decode())
            pair.append(run.stdout)
            cases = setup.decode_output(run.stdout)
            coarse = bool(config["direct"] and not config["uv16"])
            assert len(cases) == (185 if coarse else 174)
            if not config["char_chunk"] and not config["uv16"] and not config["movca"]:
                setup.validate_coverage(cases, config["direct"], config["cone"])
            focused = {case["case"]: case for case in cases if case["case"] >= 300}
            assert len(focused) == (35 if coarse else 32)
            assert all(case["ta_words"] > 24 for case in focused.values())
            if coarse:
                assert all(focused[360 + i]["locks"] == 2 for i in range(3))
            covered = coverage(run.stdout)
            assert covered["new_part_colour_changes"] == covered["new_frame_colour_changes"] == covered["prefix_sweeps"] == 32
            assert covered["window_colour_changes"] == (2 if coarse else 0)
            headroom = macros.get("RE4DC_LEON_LIGHT_HEADROOM", "0") != "0"
            expected_half_parts = (9 if coarse else 4) if headroom else 0
            assert covered["half_post_parts_verified"] == expected_half_parts
            rows.append(dict(config=config, lean=lean, profile=profile_key, host_overrides=overrides,
                output_sha256=hashlib.sha256(run.stdout).hexdigest(), output_bytes=len(run.stdout),
                cases=cases, coverage=covered, command=command))
        if not negative:
            assert pair[0] == pair[1], (label, "TA, ownership/result or controlled state differs")
    receipt = dict(status="PASS", scope=__doc__, base_fixture=str(BASE_FIXTURE.relative_to(ROOT)),
        base_fixture_sha256=sha(BASE_FIXTURE), extension_fixture_sha256=sha(out / "executed_extension.cpp.in"),
        driver_sha256=sha(out / "executed_driver.py"), composed_fixture_sha256=sha(fixture),
        source_sha256=hashlib.sha256(original_source).hexdigest(),
        profile_sha256=sha(args.profile), recipe_inputs=profiles["recipe_inputs"], adaptations=adaptations,
        fixture_adaptations=["Controlled model class reaches production crowd-flat/headroom paths",
            "MOVCA host adapter poisons cached ARGB after positions to exercise required fallback"],
        configurations=rows, sanitizers="address,undefined; detect_leaks=0" if args.mode == "sanitizer" else None)
    (out / "runtime_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", configurations=len(rows), receipt=str(out / "runtime_receipt.json"))))


if __name__ == "__main__":
    main()
