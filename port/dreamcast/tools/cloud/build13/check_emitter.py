#!/usr/bin/env python3
"""Actual-emitter packet controls for ordinary and split meshlet records.

Reuse Build 5's source extraction and controlled texture/TA/SQ sink. Public
genuine exporter fixtures execute current gather, transform-call, clip,
replay and submission bodies. Compare every TA/accounting word and SQ
ownership trace within each size limit: split-off ordinary, split-on ordinary
fallback, split-on v4. Selection and queued camera/placement snapshots are
controlled inputs; the real selector is covered separately by the target lane.
Portable host FP does not prove SH4 FTRV/FSRRA or a game/console frame.
The primary ASan/UBSan+census run links the actual Build 10 core; its
synthetic clock proves accounting and phase partition only.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
BASE = "9b248c5b40a49e4c954ea834fdf665fdbbc314f0"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


prior = module("build13_prior_geometry", HERE.parent / "build5/check_geometry.py")
census_geometry = module("build13_census_geometry", HERE.parent / "build10/check_geometry.py")
reader = module("build13_reader_gate", HERE / "check_reader.py")
SCENARIOS = ("inside", "near-clip", "far-clip", "offscreen", "group0", "group1", "nr0",
             "low-tail", "mirror", "nonuniform", "missing-groups", "sparse-picks", "groups0-and2")
PROFILES = {
    "primary": dict(SCENERY_SELECT_ONLY=1, SCENERY_SUBMIT_BATCH=1, SCENERY_REPLAY_LEAN=1,
                    SCENERY_UV_SNAPSHOT=1, SCENERY_SELECT_LEAN2=0, SCENERY_EMIT_PREFETCH=0),
    "composed": dict(SCENERY_SELECT_ONLY=1, SCENERY_SUBMIT_BATCH=1, SCENERY_REPLAY_LEAN=1,
                     SCENERY_UV_SNAPSHOT=1, SCENERY_SELECT_LEAN2=1, SCENERY_EMIT_PREFETCH=1),
    "eager-off": dict(SCENERY_SELECT_ONLY=0, SCENERY_SUBMIT_BATCH=1, SCENERY_REPLAY_LEAN=1,
                      SCENERY_UV_SNAPSHOT=0, SCENERY_SELECT_LEAN2=0, SCENERY_EMIT_PREFETCH=0),
    "batch-off": dict(SCENERY_SELECT_ONLY=1, SCENERY_SUBMIT_BATCH=0, SCENERY_REPLAY_LEAN=1,
                      SCENERY_UV_SNAPSHOT=1, SCENERY_SELECT_LEAN2=0, SCENERY_EMIT_PREFETCH=0),
    "replay-off": dict(SCENERY_SELECT_ONLY=1, SCENERY_SUBMIT_BATCH=1, SCENERY_REPLAY_LEAN=0,
                       SCENERY_UV_SNAPSHOT=1, SCENERY_SELECT_LEAN2=0, SCENERY_EMIT_PREFETCH=0),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sources(census=False):
    text, values = census_geometry.sources() if census else prior.sources()
    raw = prior.original.STATIC.read_text()
    begin = raw.index("#if RE4DC_SCENERY_RECORD_SPLIT", raw.index("struct MeshDraw : Emitter {"))
    end = raw.index("    const std::uint32_t* lut;", begin)
    values["RECORD_MEMBER"] = raw[begin:end]
    old = "const re4dc::room::MeshPackage& package;const re4dc::room::MeshPart& part;"
    assert text.count(old) == 1
    text = text.replace(old, values["RECORD_MEMBER"])
    # The reusable boundary fixture defaults to the hashing diagnostic.
    # Exercise the production no-hash path in every Build 13 comparison.
    assert text.count("#define RE4DC_TA_HASH 1") == 1
    text = text.replace("#define RE4DC_TA_HASH 1", "#define RE4DC_TA_HASH 0")
    values["FIXTURE_TA_HASH"] = "#define RE4DC_TA_HASH 0"
    values["CRC"] = prior.function(raw, "std::uint32_t ps2_crc32(")
    values["GROUP_GATE"] = reader.group_gate(raw)
    extra = (HERE / "fixture_emitter.cpp.in").read_text()
    for key in ("CRC", "GROUP_GATE", "CHUNK_PART", "CHUNK_FLUSH", "REPORT_STATS"):
        extra = extra.replace("@" + key + "@", values[key])
    assert not re.search(r"@[A-Z_]+@", extra)
    start = text.index("static std::uint64_t digest(")
    text = text[:start] + extra + "\n" + text[start:]
    head, seam, main = text.partition("int main(int argc,char** argv){")
    assert seam and main.count("queue_case(id);") == (2 if census else 1)
    main = main.replace("queue_case(id);", "if(id>=200){assert(argc==5);layout_case(id,argv[2],argv[3],argv[4]);}else queue_case(id);")
    values["BUILD13_FIXTURE"] = extra
    return head + seam + main, values


def execute(command, output, label, env):
    result = subprocess.run([str(x) for x in command], cwd=ROOT, capture_output=True, env=env)
    if result.returncode:
        (output / (label + ".failed.txt")).write_bytes(result.stdout + result.stderr)
        raise AssertionError((label, result.returncode, result.stderr.decode()))
    return result.stdout, result.stderr


def cases(profile, fixtures):
    if profile == "primary":
        chosen, levels, scenarios = fixtures, range(4), range(len(SCENARIOS))
    elif profile in ("composed", "eager-off"):
        chosen = [f for f in fixtures if f["limit"] in (32, 256)]
        levels, scenarios = (0, 3), range(len(SCENARIOS))
    else:
        chosen = [f for f in fixtures if f["limit"] == 64]
        levels, scenarios = (0, 3), (0, 1, 4, 7, 11)
    for fixture in chosen:
        for scenario in scenarios:
            for draw_pass in range(3):
                for level in levels:
                    yield fixture, 200 + 12 * scenario + 4 * draw_pass + level


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--sanitize", action="store_true")
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--primary", action="store_true", help="Only primary profile (also implied by --sanitize)")
    a = ap.parse_args()
    if a.census and not a.sanitize:
        ap.error("Use --census with --sanitize for the one bounded active-observer gate")
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(a.fixtures.read_text()); fixtures = manifest["fixtures"]
    assert [f["limit"] for f in fixtures] == [32, 64, 128, 256]
    watched = [prior.original.STATIC, prior.original.SOURCE, Path(__file__), HERE / "fixture_emitter.cpp.in",
        HERE / "check_reader.py", prior.HERE / "check_geometry.py", prior.HERE / "fixture_geometry.cpp.in",
        prior.PRIOR / "fixture_boundary.cpp.in", prior.PRIOR / "check_geometry.py", prior.PRIOR / "check_runtime.py",
        DC / "tools/d367/world_submit_spike/check_runtime.py", census_geometry.HERE / "check_geometry.py",
        census_geometry.HERE / "fixture_census.cpp.in", census_geometry.CORE, census_geometry.HEADER,
        *[DC / "room" / name for name in ("scenery_record_split.hpp", "instanced_mesh.hpp", "mesh_fastpath.hpp",
             "mesh_fastpath_sched.hpp", "mesh_strip_lean.hpp", "pvr_geometry.cpp", "pvr_geometry.hpp",
             "static_room_prepare.hpp", "room_package.hpp")]]
    hashes = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in watched}
    fixture_hashes = {str(Path(f[k]).resolve()): sha(Path(f[k]).read_bytes())
                      for f in fixtures for k in ("ordinary", "split", "policy", "ordinary_groups", "split_groups")}
    text, extracted = sources(a.census); source = out / "emitter.cpp"; source.write_text(text)
    (out / "shim/dc").mkdir(parents=True); (out / "shim/kos").mkdir()
    (out / "shim/dc/pvr.h").write_text("#pragma once\n")
    (out / "shim/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (out / "shim/dc/matrix.h").write_text("""#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
""")
    env = dict(os.environ)
    if a.sanitize:
        env["ASAN_OPTIONS"] = "detect_leaks=0"  # managed /proc task inspection unavailable
    profiles = ("primary",) if a.primary or a.sanitize else tuple(PROFILES)
    commands, observations, output_hashes, census_rows = {}, {}, {}, {}
    comparisons = unmarked_comparisons = 0
    coverage = {"near_clipped": 0, "far_clipped": 0, "offscreen_culled": 0, "indexed_picks": 0,
                "partial_nonempty": 0, "low_tail_aborts": 0, "low_tail_reserve_refusals": 0}

    def observe(binary, label, case, *paths):
        stdout, stderr = execute([binary, case, *paths], out, label, env)
        assert len(stdout.splitlines()) == 3, (label, "missing packet/state output")
        locks = re.findall(rb"^(\d+) lock=(\d+) unlock=(\d+)$", stderr, re.MULTILINE)
        assert len(locks) == 1 and int(locks[0][0]) == case and locks[0][1] == locks[0][2], (label, stderr)
        row = None
        if case >= 200:
            matches = re.findall(rb"^LAYOUT (\{[^\n]+\})$", stderr, re.MULTILINE)
            assert len(matches) == 1, (label, stderr)
            row = json.loads(matches[0]); observations[label] = row
        matches = re.findall(rb"^WC24 (\{[^\n]+\})$", stderr, re.MULTILINE)
        assert len(matches) == int(a.census), (label, stderr)
        if a.census:
            census_rows[label] = json.loads(matches[0])
        return stdout, locks, row

    for profile in profiles:
        binaries = {}
        for enabled in (0, 1):
            label = f"{profile}-split{enabled}"; binary = out / label
            command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
                *(f"-DRE4DC_{name}={value}" for name, value in PROFILES[profile].items()),
                f"-DRE4DC_SCENERY_RECORD_SPLIT={enabled}", f"-DRE4DC_WORLD_CENSUS24={int(a.census)}",
                "-DRE4DC_WORLD_CENSUS24_HOST=1", "-DCHECK_DIAGNOSTICS=0", "-I" + str(out / "shim"),
                "-I" + str(DC / "game/platform/include"), str(source)]
            if a.census:
                command.append(str(census_geometry.CORE))
            command += ["-o", str(binary)]
            if a.sanitize:
                command[3:3] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
            stdout, stderr = execute(command, out, label + "-compile", env)
            (out / (label + ".compile.log")).write_bytes(stdout + stderr)
            commands[label] = command; binaries[enabled] = binary
        digests = {arm: hashlib.sha256() for arm in ("off", "fallback", "split", "legacy-off", "legacy-on")}
        for case in range(100, 178):
            before = observe(binaries[0], f"{profile}-legacy-off-{case}", case)
            after = observe(binaries[1], f"{profile}-legacy-on-{case}", case)
            assert before[:2] == after[:2], (profile, case, "legacy packet/accounting/SQ mismatch")
            digests["legacy-off"].update(before[0]); digests["legacy-on"].update(after[0]); unmarked_comparisons += 1
        count = 0
        for fixture, case in cases(profile, fixtures):
            before = None
            for arm, enabled, kind in (("off", 0, "ordinary"), ("fallback", 1, "ordinary"), ("split", 1, "split")):
                label = f"{profile}-{fixture['limit']}-{arm}-{case}"
                actual = observe(binaries[enabled], label, case, fixture[kind], fixture[kind + "_groups"], fixture["policy"])
                digests[arm].update(actual[0])
                if before is None:
                    before = actual
                    row = actual[2]; scenario = row["scenario"]
                    coverage["indexed_picks"] += row["indexed_picks"]
                    coverage["partial_nonempty"] += row["partial_nonempty"]
                    if scenario == 1: coverage["near_clipped"] += row["strips_clipped"]
                    if scenario == 2: coverage["far_clipped"] += row["strips_clipped"]
                    if scenario == 3: coverage["offscreen_culled"] += row["strips_culled"]
                    if scenario == 7:
                        coverage["low_tail_aborts"] += row["aborts"]
                        coverage["low_tail_reserve_refusals"] += row["reserve_rejects"]
                else:
                    if before != actual:
                        (out / (label + ".reference.txt")).write_bytes(before[0])
                        (out / (label + ".actual.txt")).write_bytes(actual[0])
                        raise AssertionError((label, "TA/accounting/SQ or work counts differ"))
                    comparisons += 1; count += 1
        # CRC-correct but semantically invalid R4SG takes the actual loader's
        # missing-group fallback and must preserve every packet and state word.
        if profile == "primary":
            fixture = next(f for f in fixtures if f["limit"] == 64)
            groups = bytearray(Path(fixture["split_groups"]).read_bytes())
            end = struct.unpack_from("<H", groups, 44)[0]; assert end > 4
            struct.pack_into("<H", groups, 44, end - 1)
            struct.pack_into("<I", groups, 28, zlib.crc32(groups[32:]))
            malformed = out / "semantic-strip-boundary.r4sg"; malformed.write_bytes(groups)
            case = 200 + 13 * 12
            before = observe(binaries[0], "malformed-reference", case, fixture["ordinary"], "-", fixture["policy"])
            after = observe(binaries[1], "malformed-fallback", case, fixture["split"], malformed, fixture["policy"])
            assert before[:2] == after[:2], "malformed R4SG changed fallback packets/accounting/SQ"
            assert after[2]["group_error"] == "split group strip boundary"
            comparisons += 1; count += 1
        output_hashes[profile] = {arm: digest.hexdigest() for arm, digest in digests.items()}
        print(json.dumps(dict(profile=profile, status="PASS", comparisons=count, unmarked=78)), flush=True)
    assert all(coverage[name] > 0 for name in ("near_clipped", "far_clipped", "offscreen_culled", "indexed_picks", "partial_nonempty")), coverage
    assert coverage["low_tail_aborts"] and coverage["low_tail_reserve_refusals"], coverage
    assert hashes == {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in watched}, "source changed during gate"
    assert all(sha(Path(p).read_bytes()) == value for p, value in fixture_hashes.items()), "fixture changed during gate"
    report = dict(status="PASS", base=BASE, scope=__doc__, sanitized=a.sanitize, census_enabled=a.census,
        leak_detection=False if a.sanitize else None, comparisons=comparisons, unmarked_comparisons=unmarked_comparisons,
        malformed_group_fallback_cases=1, profiles={p: PROFILES[p] for p in profiles}, scenarios=SCENARIOS,
        source_sha256=hashes, extracted_sha256={k: sha(v.encode()) for k, v in extracted.items()},
        generated_source_sha256=sha(text.encode()), fixture_manifest_sha256=sha(a.fixtures.read_bytes()),
        fixture_sha256=fixture_hashes, commands=commands, coverage=coverage,
        output_sha256=output_hashes, observations=observations, census=census_rows,
        no_cross_limit_packet_comparison=True,
        host_compiler=subprocess.check_output(["g++", "--version"], text=True).splitlines()[0])
    (out / "emitter-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", comparisons=comparisons, unmarked_comparisons=unmarked_comparisons,
                         sanitized=a.sanitize, census=a.census)))


if __name__ == "__main__":
    main()
