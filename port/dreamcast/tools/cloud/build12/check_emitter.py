#!/usr/bin/env python3
"""Build 12 actual-emitter TA/SQ equivalence and actual-reader refusal controls.

Reuses Build 5's source-extracted emitter and controlled hardware edges. The
new cases feed the real Python converter's files through the unchanged
chunk/borrow/clip/output bodies plus the new sequential direct helper.
Portable FP is not evidence of target FTRV/FSRRA equivalence or console cost.
With --census, the existing Build 10 active observer checks the real core's
packet accounting and phase partition, including the new fused-path inputs.
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
sys.path.insert(0, str(DC / "tools"))
sys.path.insert(0, str(HERE))
import scenery_data_variants as layout
from d367.visibility23 import metadata
from fixtures import package

spec = importlib.util.spec_from_file_location("build12_prior_geometry", HERE.parent / "build5/check_geometry.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
CENSUS = HERE.parent / "build10"
spec = importlib.util.spec_from_file_location("build12_census_geometry", CENSUS / "check_geometry.py")
census_geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census_geometry)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sources(census=False):
    text, values = census_geometry.sources() if census else prior.sources()
    raw = prior.original.STATIC.read_text()
    direct = prior.function(raw, "bool sequential_direct(")
    values["SEQUENTIAL_DIRECT"] = direct
    text = text.replace(values["BORROW"], values["BORROW"] + "\n#if RE4DC_SCENERY_DIRECT_STRIPS\n" + direct + "\n#endif")
    # Only the hardware commit is substituted. The emitter and transform call
    # remain exactly the current source bodies, with an observable real sink.
    hook = '''
static unsigned direct_commits;
static void fixture_direct_commit(std::uint32_t* slot){++direct_commits;sq_flush(slot);}
#define RE4DC_SCENERY_DIRECT_HOST_COMMIT(slot) fixture_direct_commit(slot)
#include "@ROOT@/port/dreamcast/room/scenery_data_variants.hpp"
#include "@ROOT@/port/dreamcast/room/scenery_direct_strips.hpp"
'''.replace("@ROOT@", str(ROOT))
    needle = '#include "' + str(DC / "room/mesh_fastpath_sched.hpp") + '"'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + "\n" + hook)
    text = text.replace("#define RE4DC_TA_HASH 1", "#define RE4DC_TA_HASH B12_TA_HASH")
    values["CRC"] = prior.function(raw, "std::uint32_t ps2_crc32(")
    extra = (HERE / "fixture_emitter.cpp.in").read_text()
    for key in ("CRC", "CHUNK_PART", "CHUNK_FLUSH"):
        extra = extra.replace("@" + key + "@", values[key])
    assert not re.search(r"@[A-Z_]+@", extra)
    start = text.index("static std::uint64_t digest(")
    text = text[:start] + extra + "\n" + text[start:]
    text = text.replace('const unsigned id=argc>1?', '''if(argc==6 && !std::strcmp(argv[1],"validate"))
        return fixture_validate(argv[2],unsigned(std::strtoul(argv[3],nullptr,10)),
            unsigned(std::strtoul(argv[4],nullptr,10)),unsigned(std::strtoul(argv[5],nullptr,10)));
    const unsigned id=argc>1?''')
    if census:
        head, seam, main = text.partition("int main(int argc,char** argv){")
        assert seam and main.count("queue_case(id);") == 2
        main = main.replace("queue_case(id);", "if(id>=200){assert(argc==4);variant_case(id,argv[2],argv[3]);}else queue_case(id);")
        text = head + seam + main
        checks = """if(direct_commits){
        assert(counts[Transformed]>=direct_commits && counts[StripInputs]>=direct_commits);
        assert(s.phase_us[NearOP][Transform]>0);
    }"""
        seam = "const auto* counts=s.counters[NearOP];"
        assert text.count(seam) == 1
        text = text.replace(seam, seam + "\n    " + checks)
        values["B12_CENSUS_ASSERTS"] = checks
    else:
        text = text.replace("if(id>=100){queue_case(id);report(id);return 0;}",
            "if(id>=200){assert(argc==4);variant_case(id,argv[2],argv[3]);report(id);return 0;}\n    "
            "if(id>=100){queue_case(id);report(id);return 0;}")
    values["B12_FIXTURE"] = extra
    return text, values


def execute(command, output, label, env=None, expected=0):
    result = subprocess.run([str(x) for x in command], cwd=ROOT, capture_output=True, env=env)
    if result.returncode != expected:
        (output / (label + ".failed.txt")).write_bytes(result.stdout + result.stderr)
        raise AssertionError((label, result.returncode, result.stderr.decode()))
    return result.stdout, result.stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--sanitize", action="store_true")
    ap.add_argument("--census", action="store_true", help="Link the real Build 10 core with an active world/tick scope")
    ap.add_argument("--reader-capacity-only", action="store_true",
                    help="Only actual-reader valid/capacity controls; does not repeat the geometry matrix")
    args = ap.parse_args()
    if args.reader_capacity_only and args.census:
        ap.error("--reader-capacity-only does not draw a census frame")
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    watched = [prior.original.STATIC, prior.original.SOURCE, Path(__file__), HERE / "fixture_emitter.cpp.in",
        HERE / "fixtures.py", DC / "tools/scenery_data_variants.py", prior.HERE / "check_geometry.py",
        prior.HERE / "fixture_geometry.cpp.in", prior.PRIOR / "fixture_boundary.cpp.in",
        CENSUS / "check_geometry.py", CENSUS / "fixture_census.cpp.in", census_geometry.CORE, census_geometry.HEADER,
        *[DC / "room" / x for x in ("scenery_data_variants.hpp", "scenery_direct_strips.hpp", "mesh_fastpath.hpp",
            "mesh_fastpath_sched.hpp", "instanced_mesh.hpp", "pvr_geometry.cpp", "pvr_geometry.hpp")]]
    hashes = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in watched}
    text, extracted = sources(args.census); source = out / "emitter.cpp"; source.write_text(text)
    (out / "shim/dc").mkdir(parents=True); (out / "shim/kos").mkdir()
    (out / "shim/dc/pvr.h").write_text("#pragma once\n")
    (out / "shim/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (out / "shim/dc/matrix.h").write_text('''#pragma once
using matrix_t=float[4][4];
static void mat_load(const matrix_t* m){std::memcpy(vp_host_xmtrx,*m,sizeof(matrix_t));}
static void mat_trans_nodiv(float& x,float& y,float& z,float& w){VP_FTRV(x,y,z,w);}
''')
    env = dict(os.environ)
    if args.sanitize:
        env["ASAN_OPTIONS"] = "detect_leaks=0" # managed /proc task inspection is unavailable
    files, stats = {}, {}
    for shape in ("compact", "reuse", "limit", "unused"):
        mesh, side = package(shape, 3); groups, _ = metadata.build(mesh, side, 2)
        files[shape], stats[shape] = {}, {}
        for variant in ("base", "local-indexed", "direct-strips"):
            m, g = mesh, groups
            if variant != "base":
                m, g, stats[shape][variant] = layout.convert(mesh, variant, side, groups)
            stem = out / (shape + "-" + variant)
            mp, gp = stem.with_suffix(".re4mesh"), stem.with_suffix(".r4sg")
            mp.write_bytes(m); gp.write_bytes(g); files[shape][variant] = (mp, gp)
    binaries, output_hashes, direct_counts, census_rows = {}, {}, {}, {}
    variant_outputs = {arm: [] for arm in ("off", "local", "direct", "hash")}
    arms = (("direct", 0, 1, 0),) if args.reader_capacity_only else (
        ("off", 0, 0, 0), ("local", 1, 0, 0), ("direct", 0, 1, 0), ("hash", 0, 1, 1))
    for arm, local, direct, diagnostic in arms:
        binary = out / arm
        command = ["g++", "-std=c++20", "-O2", "-ffp-contract=off", "-Wall", "-Wextra",
            "-DRE4DC_SCENERY_SUBMIT_BATCH=1", "-DRE4DC_SCENERY_REPLAY_LEAN=1", "-DRE4DC_SCENERY_UV_SNAPSHOT=1",
            "-DRE4DC_SCENERY_SELECT_ONLY=1", "-DRE4DC_SCENERY_SELECT_LEAN2=0", "-DRE4DC_SCENERY_EMIT_PREFETCH=0",
            f"-DRE4DC_SCENERY_LOCAL_INDEXED={local}", f"-DRE4DC_SCENERY_DIRECT_STRIPS={direct}",
            f"-DRE4DC_WORLD_CENSUS24={int(args.census)}", "-DRE4DC_WORLD_CENSUS24_HOST=1",
            f"-DB12_TA_HASH={diagnostic}", "-DCHECK_DIAGNOSTICS=0", "-I" + str(out / "shim"),
            "-I" + str(DC / "game/platform/include"), str(source)]
        if args.census:
            command.append(str(census_geometry.CORE))
        command += ["-o", str(binary)]
        if args.sanitize:
            command[3:3] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
        stdout, stderr = execute(command, out, arm + "-compile", env)
        (out / (arm + ".compile.log")).write_bytes(stdout + stderr); binaries[arm] = binary
    if args.reader_capacity_only:
        from fixtures import capacity
        observations = []
        for shape, variants in files.items():
            h = struct.unpack_from("<4s19I", variants["base"][0].read_bytes())
            for kind, variant in ((1, "local-indexed"), (2, "direct-strips")):
                execute([binaries["direct"], "validate", variants[variant][0], kind, h[2], h[3]], out,
                        f"valid-{shape}-{variant}", env)
                observations.append(dict(shape=shape, variant=variant, admitted=True))
        for count in (65536, 65537):
            raw, _ = capacity(count)
            h = struct.unpack_from("<4s19I", raw)
            source_bytes, source_crc = len(raw), h[3]
            mesh = bytearray(raw)
            struct.pack_into("<3I", mesh, 68, source_bytes, source_crc, layout.MARKERS["direct-strips"])
            mesh = bytes(mesh)
            path = out / f"capacity-{count}.re4mesh"; path.write_bytes(mesh)
            result = subprocess.run([str(binaries["direct"]), "validate", str(path), "2", str(source_bytes), str(source_crc)],
                                    cwd=ROOT, capture_output=True, env=env)
            expected = 0 if count == 65536 else 3
            assert result.returncode == expected, (count, result.returncode, result.stderr)
            if expected:
                assert result.stderr == b"VARIANT_REFUSAL variant meshlet id capacity\n", result.stderr
            observations.append(dict(meshlet_count=count, mesh_sha256=sha(mesh), mesh_bytes=len(mesh),
                                     admitted=not expected, refusal="variant meshlet id capacity" if expected else None))
        # Both referenced cluster ranges remain individually inside the part.
        # Only their combined maximum selected population distinguishes safe
        # overlap from a write beyond chunk_select's part-sized reservation.
        raw, _ = capacity(161)
        h = struct.unpack_from("<4s19I", raw)
        lod = list(layout.fmt.LOD_HEADER.unpack_from(raw, 80))
        cluster = raw[lod[3]:lod[3]+layout.fmt.CLUSTER.size]
        for selected in (80, 161):
            mesh = bytearray(raw)
            cluster_offset = len(mesh); mesh.extend(cluster+cluster)
            mesh.extend(bytes((-len(mesh)) % 32))
            new_lod = list(lod); new_lod[0] = 2; new_lod[3] = cluster_offset
            layout.fmt.LOD_HEADER.pack_into(mesh, 80, *new_lod)
            struct.pack_into("<I", mesh, lod[2]+4, 2)
            struct.pack_into("<I", mesh, lod[4]+4, selected)
            struct.pack_into("<II", mesh, 8, len(mesh), zlib.crc32(mesh[80:]))
            struct.pack_into("<3I", mesh, 68, len(raw), h[3], layout.MARKERS["direct-strips"])
            path = out / f"overlap-{selected}.re4mesh"; path.write_bytes(mesh)
            result = subprocess.run([str(binaries["direct"]), "validate", str(path), "2", str(len(raw)), str(h[3])],
                                    cwd=ROOT, capture_output=True, env=env)
            expected = 0 if selected == 80 else 3
            assert result.returncode == expected, (selected, result.returncode, result.stderr)
            if expected:
                assert result.stderr == b"VARIANT_REFUSAL variant pick capacity\n", result.stderr
            observations.append(dict(part_meshlets=161, worst_selected=2*selected, mesh_sha256=sha(mesh),
                                     admitted=not expected, refusal="variant pick capacity" if expected else None))
        for path, digest in hashes.items(): assert sha((ROOT/path).read_bytes()) == digest, (path, "source changed")
        report = dict(status="PASS", scope="Actual C++ reader only; eight valid small variants, uint16 meshlet-ID and per-part pick-reservation boundaries",
                      source_sha256=hashes, extracted_sha256={k: sha(v.encode()) for k, v in extracted.items()},
                      sanitized=args.sanitize, leak_detection=False if args.sanitize else None, observations=observations)
        (out / "reader-capacity-controls.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(dict(status="PASS", valid_variants=8, capacity_boundaries=2,
                              overlap_boundaries=2, sanitized=args.sanitize)))
        return
    # Unmarked packages must keep the entire existing 78-case contract.
    original = {}
    for arm in ("off", "local", "direct"):
        rows, locks = [], []
        for case in range(100, 178):
            stdout, stderr = execute([binaries[arm], case], out, f"{arm}-{case}", env)
            rows.append(stdout); locks.append(stderr)
        original[arm] = (rows, locks)
        output_hashes[arm + "-unmarked"] = sha(b"".join(rows))
        assert original[arm] == original["off"], (arm, "unmarked fallback changed")
    compared = 0
    for shape in files:
        for case in range(200, 260):
            reference = None
            for arm, variant in (("off", "base"), ("local", "local-indexed"), ("direct", "direct-strips")):
                stdout, stderr = execute([binaries[arm], case, *files[shape][variant]], out, f"{shape}-{arm}-{case}", env)
                assert len(stdout.splitlines()) == 3
                variant_outputs[arm].append(stdout)
                lock = re.findall(rb"(\d+) lock=(\d+) unlock=(\d+)", stderr)
                assert len(lock) == 1 and lock[0][1] == lock[0][2]
                match = re.search(rb"VARIANT \d+ direct=(\d+)", stderr); assert match
                n = int(match[1]); direct_counts[f"{shape}-{arm}-{case}"] = n
                matches = re.findall(rb"^WC24 (\{[^\n]+\})$", stderr, re.MULTILINE)
                assert len(matches) == int(args.census)
                if args.census:
                    observation = json.loads(matches[0])
                    census_rows[f"{shape}-{arm}-{case}"] = observation
                    if arm == "direct" and (case-200)//6 in (0, 8, 9):
                        assert observation["transformed"] == observation["strip_inputs"] == observation["corners"] == n
                if reference is None: reference = (stdout, lock)
                else:
                    if (stdout, lock) != reference:
                        (out / f"{shape}-{arm}-{case}.reference.txt").write_bytes(reference[0])
                        (out / f"{shape}-{arm}-{case}.actual.txt").write_bytes(stdout + stderr)
                        raise AssertionError((shape, arm, case, "TA/external accounting/SQ ownership changed"))
                    compared += 1
                scenario = (case-200)//6
                if arm == "direct":
                    if scenario in (1, 2, 3, 4, 5, 6): assert n == 0, (shape, scenario, "unsafe direct eligibility")
                    if scenario in (0, 8, 9): assert n > 0, (shape, scenario, "direct path was not exercised")
            # Same SDS1 file in TA_HASH diagnostic must preserve its ordinary
            # fallback and produce no direct commit. Its external diagnostic
            # counts differ, so compare TA words to the production reference.
            if case % 6 == 2:
                stdout, stderr = execute([binaries["hash"], case, *files[shape]["direct-strips"]], out,
                                          f"{shape}-hash-{case}", env)
                assert stdout.splitlines()[1] == reference[0].splitlines()[1]
                assert b"direct=0 " in stderr
                variant_outputs["hash"].append(stdout)
    # Actual C++ adoption/variant validation, including failures that ordinary
    # R4IM adoption alone would permit. CRC checks use the extracted production
    # CRC implementation, not a mirrored implementation in this fixture.
    raw, _ = package("compact", 3)
    source_h = struct.unpack_from("<4s19I", raw)
    good = files["compact"]["direct-strips"][0].read_bytes(); h = struct.unpack_from("<4s19I", good)
    bad = []
    for label, offset, value, form in (
        ("unknown-marker", 76, 0x11223344, "I"), ("wrong-source-size", 68, len(raw)+32, "I"),
        ("wrong-source-crc", 72, source_h[3]^1, "I"), ("bounds", h[12]+16, 65535, "H"),
        ("alias-local", h[12]+28, 0, "I"), ("bad-sequence", h[14]+1, 1, "B")):
        data = bytearray(good); struct.pack_into("<"+form, data, offset, value)
        struct.pack_into("<I", data, 12, zlib.crc32(data[80:])); bad.append((label, bytes(data)))
    data = bytearray(good); data[h[13]+6] ^= 1; bad.append(("body-crc", bytes(data)))
    validator = binaries["direct"]
    execute([validator, "validate", files["compact"]["direct-strips"][0], 2, len(raw), source_h[3]], out, "valid-admission", env)
    for name, data in bad:
        path = out / (name + ".re4mesh"); path.write_bytes(data)
        result = subprocess.run([str(validator), "validate", str(path), "2", str(len(raw)), str(source_h[3])],
                                cwd=ROOT, capture_output=True, env=env)
        assert result.returncode in (1, 2, 3), (name, "malformed candidate was admitted or crashed", result.stderr)
    for path, digest in hashes.items(): assert sha((ROOT/path).read_bytes()) == digest, (path, "source changed")
    report = dict(status="PASS", unmarked_cases=78, unmarked_comparisons=156, variant_comparisons=compared,
        malformed_reader_cases=len(bad), sanitized=args.sanitize, census_enabled=args.census,
        leak_detection=False if args.sanitize else None,
        source_sha256=hashes, extracted_sha256={k: sha(v.encode()) for k, v in extracted.items()},
        unmarked_output_sha256=output_hashes, direct_corner_commits=direct_counts, package_statistics=stats,
        variant_output_sha256={arm: sha(b"".join(rows)) for arm, rows in variant_outputs.items()}, census=census_rows,
        scope=__doc__)
    (out / "emitter-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", variant_comparisons=compared, unmarked_comparisons=156, malformed=len(bad))))


if __name__ == "__main__":
    main()
