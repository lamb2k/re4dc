#!/usr/bin/env python3
"""Hosted whole-TU controls for ACTOR_SETUP_LEAN argument and submission state.

This executes production actor submission, meshlet selection, frame preparation,
lighting, clipping and output ownership. SH-4 AVK kernels and SQ transport have
explicit scalar host adapters. It compares every emitted TA word and every
controlled ownership/result event; it is not a console arithmetic/FPS test.
"""
import argparse
import hashlib
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
ACTOR = DC / "game/platform/native_actor_fast.cpp"


def body(text, prefix):
    start = text.index(prefix)
    brace = text.index("{", start)
    depth, end = 1, brace + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def host_source(source):
    """Only platform boundaries change; production control/setup bodies remain."""
    adaptations = {}
    before = "#if RE4DC_ACTOR_VTX_KERNEL && defined(__sh__) && RE4DC_ACTOR_ASM && !defined(ACTOR_TEST_XMTRX)"
    assert source.count(before) == 1
    source = source.replace(before, "#if RE4DC_ACTOR_VTX_KERNEL // hosted AVK ABI adapters")
    adaptations["avk_admission"] = before
    offsets = re.search(r'static_assert\(__builtin_offsetof\(AvkPos,.*?"avk_sh4.S AvkLight"\);', source, re.S)
    assert offsets
    adaptations["target_abi_assertions"] = offsets.group()
    source = source[:offsets.start()] + "// Target ABI offsets checked by the real SH-4 build.\n" + source[offsets.end():]
    meshlet = body(source, "inline void* emit_meshlet(")
    host_meshlet = meshlet.replace("#if RE4DC_AVK\n", "#if RE4DC_AVK && defined(__sh__)\n", 1)
    assert host_meshlet != meshlet
    host_meshlet = host_meshlet.replace('    static_assert(!SQ, "store queues are SH4 only");',
                                        "    // Host SQ adapter uses this existing portable copy verbatim.")
    source = source.replace(meshlet, host_meshlet)
    adaptations["meshlet_transport"] = "Existing production portable copy, including index EOL flags, for SQ and packet."
    sq = body(source, "inline std::uint32_t* emit_sq(")
    host_sq = '''inline std::uint32_t* emit_sq(std::uint32_t* sq, const pvr_vertex_t* cache, const u8* index, unsigned n) {
    auto* out = reinterpret_cast<pvr_vertex_t*>(sq);
    for (unsigned i = 0; i < n; ++i) {
        out[i] = cache[index[i] & 127u];
#if RE4DC_ACTOR_MOVCA
        out[i].flags = i + 1 == n ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
#else
        if (i + 1 == n) out[i].flags = PVR_CMD_VERTEX_EOL;
#endif
    }
    return sq + n * 8u;
}'''
    source = source.replace(sq, host_sq)
    adaptations["strip_transport"] = "SQ strip copy: all 8 words, final EOL, MOVCA command policy."
    return source, adaptations


PVR = '''#pragma once
#include <cstdint>
struct pvr_vertex_t { std::uint32_t flags; float x,y,z,u,v; std::uint32_t argb,oargb; };
struct pvr_poly_hdr_t { std::uint32_t words[8]; };
constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000u, PVR_CMD_VERTEX_EOL=0xf0000000u;
inline void pvr_prim(const void*, unsigned) {}
'''
SQ = '''#pragma once
#include <cstring>
inline void sq_fast_cpy(void* dst,const void* src,unsigned n){std::memcpy(dst,src,n*32u);}
inline void sq_flush(void*){}
'''


def decode_output(data):
    rows, offset = [], 0
    while offset < len(data):
        magic, case, nt, ne, nk, locks, unlocks = struct.unpack_from("<7I", data, offset)
        assert magic == 0x41435452 and locks == unlocks, (case, "record or ownership boundary")
        offset += 28
        ta = struct.unpack_from(f"<{nt}I", data, offset)
        offset += nt * 4
        events = struct.unpack_from(f"<{ne}I", data, offset)
        offset += ne * 4
        calls = struct.unpack_from(f"<{nk}I", data, offset)
        offset += nk * 4
        kernels, at = {}, 0
        while at < nk:
            kind = calls[at]
            assert kind in (1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16)
            kernels[kind] = kernels.get(kind, 0) + 1
            at += 4 if kind < 10 else 5
        assert at == nk
        rows.append(dict(case=case, ta_words=nt, controlled_state_words=ne,
                         controlled_state_events=ne // 3,
                         ownership_events=sum(1 for i in range(0, ne, 3) if 1 <= events[i] <= 9),
                         kernel_calls=kernels, locks=locks,
                         result_events=[list(events[i:i+3]) for i in range(0, ne, 3)
                                        if events[i] in (4, 5, 6, 90, 91, 92)],
                         ta_sha256=hashlib.sha256(struct.pack(f"<{nt}I", *ta)).hexdigest()))
    assert offset == len(data)
    assert len({r["case"] for r in rows}) == len(rows)
    return rows


def validate_coverage(rows, direct, cone):
    by_case = {r["case"]: r for r in rows}
    # These assertions prevent a silently declining fixture from satisfying
    # differential equality without reaching the changed setup paths.
    assert by_case[0]["kernel_calls"] == {3: 8, 12: 8}
    assert by_case[12]["kernel_calls"] == {1: 8, 11: 9}, "s8 light palette stop/resume not reached"
    assert by_case[36]["kernel_calls"] == {1: 8, 14: 9}, "n16 light palette stop/resume not reached"
    assert by_case[140]["kernel_calls"] == {} and by_case[140]["ta_words"] == 8
    if cone:
        assert by_case[141]["ta_words"] == 8, "all-rejected cone path not reached"
        assert by_case[141]["kernel_calls"] == ({3: 8} if cone == 2 else {})
    assert by_case[210]["kernel_calls"] == {12: 16, 3: 24}, "bake-before-position not reached"
    assert by_case[230]["kernel_calls"] == {3: 7, 12: 7}, "LOD prefixes / collapsed meshlet not reached"
    assert [4, 3, 0] in by_case[124]["result_events"], "nonstreaming capacity failure not reached"
    assert [4, 0, 0] in by_case[125]["result_events"], "streaming packet flush path did not succeed"
    if direct:
        assert [6, 0, 0] in by_case[129]["result_events"], "direct capacity abort not reached"
        assert by_case[150]["locks"] == 1, "coarse chunks did not share their direct window"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true", help="One baseline compilation during fixture development")
    parser.add_argument("--extra-only", action="store_true", help="Only diagnostic and NO_CLEAR=0 compatibility pairs")
    parser.add_argument("--sanitizer", action="store_true", help="Bounded diagnostic off/on pair under ASan and UBSan")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    headers = out / "host/dc"
    headers.mkdir(parents=True)
    (headers / "pvr.h").write_text(PVR)
    (headers / "sq.h").write_text(SQ)
    original_source = ACTOR.read_bytes()
    source, adaptations = host_source(original_source.decode())
    (out / "native_actor_original.cpp").write_bytes(original_source)
    (out / "native_actor_host.inc").write_text(source)
    fixture = out / "fixture.cpp"
    fixture.write_text((HERE / "fixture_actor.cpp.in").read_text())
    configs = [(d, c, l, 1, 1) for d, c, l in itertools.product((0, 1), (0, 1, 2), (0, 1))]
    extras = [(1, 2, lean, 2, 1) for lean in (0, 1)] + [(1, 0, lean, 1, 0) for lean in (0, 1)]
    configs = [(0, 0, 0, 1, 1)] if args.smoke else extras if args.extra_only else configs + extras
    if args.sanitizer:
        configs = [(1, 2, lean, 2, 1) for lean in (0, 1)]
    rows, baseline = [], {}
    for direct, cone, lean, diagnostic, no_clear in configs:
        label = f"direct{direct}-cone{cone}-avk{diagnostic}-noclear{no_clear}-lean{lean}"
        binary = out / label
        defines = {
            "RE4DC_ACTOR_SETUP_LEAN": lean, "RE4DC_ACTOR_DIRECT": direct,
            "RE4DC_ACTOR_BACKFACE_CONE": cone, "RE4DC_COARSE_ONE_SUBMIT": direct,
            "RE4DC_ACTOR_VTX_KERNEL": diagnostic, "RE4DC_ACTOR_ASM": 0,
            "RE4DC_AVK_RIGID6": 1, "RE4DC_ACTOR_LIGHT_N16": diagnostic,
            "RE4DC_ACTOR_NO_CLEAR": no_clear, "RE4DC_ACTOR_MOVCA": 0,
            "RE4DC_ACTOR_LOD_BUDGET": 0, "RE4DC_NATIVE_ACTOR_SKIN": 1,
            "RE4DC_NATIVE_ACTOR_SKIN_LAZY": 1,
            "RE4DC_ACTOR_PRELIT": 1, "RE4DC_ACTOR_EXACT_FAST": 1,
            "RE4DC_ACTOR_PROBE_LIGHT": 1, "RE4DC_LEON_SOURCE_LIGHT": 1,
            "RE4DC_LEON_LIGHT_HEADROOM": 1, "RE4DC_LEON_LIGHT_FILL": 45,
        }
        command = ["g++", "-std=c++20", "-O2", "-fno-fast-math", "-ffp-contract=off",
                   "-ffunction-sections", "-fdata-sections", "-Wall", "-Wextra",
                   *(f"-D{k}={v}" for k, v in defines.items()),
                   "-I" + str(out / "host"), "-I" + str(DC / "game/platform"),
                   "-I" + str(DC / "game/platform/include"), "-I" + str(DC / "room"),
                   str(fixture), str(DC / "room/pvr_geometry.cpp"),
                   str(DC / "room/source_lighting.cpp"), "-Wl,--gc-sections", "-o", str(binary)]
        if args.sanitizer:
            command[1:1] = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all"]
            command[command.index("-O2")] = "-O1"
        run = subprocess.run(command, capture_output=True)
        (out / (label + ".compile.log")).write_bytes(run.stdout + run.stderr)
        assert run.returncode == 0, (label, run.stderr.decode())
        environment = os.environ.copy()
        if args.sanitizer:
            # This runner cannot enumerate /proc tasks for LeakSanitizer. The
            # address/undefined-behaviour checks remain enabled and fail closed.
            environment["ASAN_OPTIONS"] = "detect_leaks=0"
        run = subprocess.run([str(binary)], capture_output=True, env=environment)
        (out / (label + ".stdout")).write_bytes(run.stdout)
        (out / (label + ".stderr")).write_bytes(run.stderr)
        assert run.returncode == 0, (label, run.returncode, run.stderr.decode())
        if not lean:
            baseline[direct, cone, diagnostic, no_clear] = run.stdout
        else:
            assert run.stdout == baseline[direct, cone, diagnostic, no_clear], (label, "TA or controlled state words differ")
        cases = decode_output(run.stdout)
        assert len(cases) == (150 if direct else 142)
        validate_coverage(cases, direct, cone)
        rows.append(dict(direct=direct, cone=cone, lean=lean,
                         diagnostic=diagnostic, no_clear=no_clear,
                         sha256=hashlib.sha256(run.stdout).hexdigest(),
                         output_bytes=len(run.stdout), cases=cases, command=command))
    receipt = dict(status="PASS", scope=__doc__, adaptations=adaptations, configurations=rows,
                   sanitizers=("address,undefined; detect_leaks=0 (runner /proc limitation)" if args.sanitizer else None),
                   source_sha256=hashlib.sha256(original_source).hexdigest(),
                   fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (out / "check-runtime.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", configurations=len(rows), receipt=str(out / "check-runtime.json"))))


if __name__ == "__main__":
    main()
