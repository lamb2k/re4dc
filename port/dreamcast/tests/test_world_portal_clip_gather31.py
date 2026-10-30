#!/usr/bin/env python3
"""Depth-safe oversized indexed gather through the production clipper and receipt."""
from pathlib import Path
import importlib.util
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
# Published current stream/owner parent; the original WIP referenced an unpublished object.
BASE = "750d9abafbafd96fd6a42d130aed1018d2e96db9"
NATIVE = ROOT / "port/dreamcast/game/platform/native_static.cpp"
TEMPLATE = ROOT / "port/dreamcast/tests/world_portal_clip_gather31/producer_fixture.cpp.in"
PROFILE_BUILDER = ROOT / "port/dreamcast/tools/cloud/build31/stream_portal_profile.py"
PROFILE_GATE = ROOT / "port/dreamcast/tests/test_world_portal_stream_profile31.py"


def run(args, **kw):
    result = subprocess.run([str(x) for x in args], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    if result.returncode:
        raise AssertionError(f"{result.returncode}: {' '.join(map(str, args))}\n{result.stdout}")
    return result.stdout


def extract_methods():
    path = ROOT / "port/dreamcast/tools/d367/world_submit_spike/check_runtime.py"
    spec = importlib.util.spec_from_file_location("world_clip_extract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = NATIVE.read_text()
    # clip_strip is an Emitter member, while stream_gather and the receipt
    # belong to MeshDraw. Keep the eligibility flag in the class whose method
    # updates it; the combined host fixture alone would not catch a misplaced
    # derived-only member.
    before_draw = source.split("\n};\nstruct Draw : Emitter", 1)
    assert len(before_draw) == 2
    emitter = before_draw[0].split("struct Emitter {", 1)[1]
    assert "bool portal_depth_safe_clip=true;" in emitter
    methods = {
        "CLIP_VERTEX": "void clip_vertex(const re4dc::render::StaticCorner& in,",
        "STREAM_GATHER": "__attribute__((noinline)) const re4dc::room::CompactVertex12* stream_gather(\n",
        "LEAN_FLUSH": "void lean_flush(",
        "STRIPS_LEAN": "const std::uint8_t* strips_lean(",
        "CLIP_STRIP": "template<class Vertex,class Index>\n    int clip_strip(",
    }
    bodies = {key: module.function(source, signature) for key, signature in methods.items()}
    bodies["CLIP_STRIP"] = bodies["CLIP_STRIP"].replace(
        "#endif\n                   const Index*", "                   const Index*", 1)
    assert "#endif\n                   const Index*" not in bodies["CLIP_STRIP"]
    bodies["PAGE_INPUTS"] = source.split("// PAGE31_INPUTS_BEGIN", 1)[1].split(
        "// PAGE31_INPUTS_END", 1)[0]
    bodies["RECEIPT"] = source.split("// PORTAL_COMPLETION_FLUSH_BEGIN", 1)[1].split(
        "// PORTAL_COMPLETION_FLUSH_END", 1)[0]
    return bodies


def producer(tmp):
    kos = tmp / "stubs/dc"
    kos.mkdir(parents=True)
    (tmp / "stubs/kos").mkdir()
    (tmp / "stubs/kos/fs.h").write_text(
        "#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    (kos / "pvr.h").write_text(
        "#pragma once\n#include <cstddef>\n#include <cstdint>\n"
        "struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n"
        "struct pvr_poly_hdr_t{std::uint32_t words[8];};\n"
        "#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n"
        "int pvr_prim(const void*,std::size_t);\n")
    source = TEMPLATE.read_text().replace("@ROOT@", str(ROOT))
    for key, body in extract_methods().items():
        source = source.replace("@" + key + "@", body)
    assert "@" not in source
    cpp = tmp / "producer.cpp"
    cpp.write_text(source)
    for pages in (1, 0):
        for sanitizer in (False, True):
            exe = tmp / f"producer-pages{pages}{'-san' if sanitizer else ''}"
            flags = (["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined", "-no-pie"]
                     if sanitizer else ["-O2", "-g0"])
            run(["g++", "-std=gnu++20", "-Wall", "-Wextra", "-Wno-unused-parameter",
                 f"-DRE4DC_WORLD_PAGES31={pages}", *flags,
                 "-I", tmp / "stubs", "-I", ROOT / "port/dreamcast/room",
                 "-I", ROOT / "port/dreamcast/game/platform/include",
                 "-I", ROOT / "port/dreamcast/tools/d367/world_scratch23/stubs",
                 cpp, ROOT / "port/dreamcast/room/pvr_geometry.cpp", "-o", exe])
            run([exe], env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                                UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1"))
    print("actual sparse gather/strip/clipper/page and direct receipt normal+ASan/UBSan pass")


def guards_and_off(tmp):
    current = NATIVE.read_text()
    old = run(["git", "show", f"{BASE}:port/dreamcast/game/platform/native_static.cpp"])
    def block(source):
        return "#ifndef RE4DC_WORLD_PORTAL_COMPLETION\n" + source.split(
            "#ifndef RE4DC_WORLD_PORTAL_COMPLETION", 1)[1].split(
            "#ifndef RE4DC_SCENERY_SUBMIT_BATCH", 1)[0] + "int admitted=1;\n"
    def pp(source, definitions=()):
        return subprocess.run(["g++", "-E", "-P", "-x", "c++", *definitions, "-"],
                              input=source, text=True, capture_output=True)
    assert pp(block(current)).stdout == pp(block(old)).stdout
    assert pp(block(current), ["-DRE4DC_WORLD_PORTAL_CLIP_GATHER31=0"]).stdout == pp(block(old)).stdout
    # The other three edited production regions retain complete OFF source
    # bytes after preprocessing, including whitespace and newlines.
    path = ROOT / "port/dreamcast/tools/d367/world_submit_spike/check_runtime.py"
    spec = importlib.util.spec_from_file_location("world_clip_off_extract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def slices(source):
        emitter = source.split("struct Emitter {", 1)[1].split("\n};\nstruct Draw : Emitter", 1)[0]
        return (
            emitter,
            module.function(source, "template<class Vertex,class Index>\n    int clip_strip(").replace(
                "#endif\n                   const Index*", "                   const Index*", 1),
            module.function(source, "[[gnu::always_inline]] void chunk_restart(){"),
            source.split("// PORTAL_COMPLETION_FLUSH_BEGIN", 1)[1].split(
                "// PORTAL_COMPLETION_FLUSH_END", 1)[0],
        )
    off_profile = ["-DRE4DC_WORLD_PORTAL_COMPLETION=1", "-DRE4DC_WORLD_PORTAL29=1",
                   "-DRE4DC_WORLD_PAGES31=1", "-DRE4DC_WORLD_PREPARED09=1",
                   "-DRE4DC_SCENERY_SUBMIT_BATCH=1", "-DRE4DC_PS2_PVS_BATCH_COMPOSE=1",
                   "-DRE4DC_PS2_PVS=1", "-DRE4DC_SCENERY_STREAM=1",
                   "-DRE4DC_WORLD_PORTAL_STREAM31=1",
                   "-DRE4DC_MESH_CLIP_LEAN=0", "-DRE4DC_MESH_CLIP_ACCEPT=0",
                   "-DRE4DC_WORLD_PORTAL_CLIP_GATHER31=0"]
    for index, (baseline, candidate) in enumerate(zip(slices(old), slices(current))):
        a, b = pp(baseline, off_profile), pp(candidate, off_profile)
        assert a.returncode == b.returncode == 0, (a.stderr, b.stderr)
        assert a.stdout == b.stdout, (index, len(a.stdout), len(b.stdout),
                                      next((i for i, pair in enumerate(zip(a.stdout, b.stdout))
                                            if pair[0] != pair[1]), None))
    definitions = {"WORLD_PORTAL_COMPLETION": 1, "WORLD_PORTAL29": 1,
                   "PS2_PVS_BATCH_COMPOSE": 1, "SCENERY_SUBMIT_BATCH": 1,
                   "SCENERY_STREAM": 1, "PS2_PVS": 1, "WORLD_PORTAL_STREAM31": 1,
                   "WORLD_PORTAL_CLIP_GATHER31": 1, "SCENERY_CLIP_GATHER": 1}
    def check(changes, valid):
        values = {**definitions, **changes}
        d = [f"-DRE4DC_{key}={value}" for key, value in values.items()]
        result = pp(block(current), d)
        assert (result.returncode == 0) == valid, (changes, result.stderr)
    check({}, True)
    for key, value in (("WORLD_PORTAL_CLIP_GATHER31", 0),
                       ("WORLD_PORTAL_CLIP_GATHER31", 2),
                       ("WORLD_PORTAL_STREAM31", 0),
                       ("SCENERY_CLIP_GATHER", 0),
                       ("SCENERY_CLIP_INDEXED26", 1),
                       ("CPU_BACKFACE", 2),
                       ("MESH_CLIP_LEAN", 1),
                       ("MESH_CLIP_ACCEPT", 1),
                       ("SCENERY_EMIT_PREFETCH", 1),
                       ("PS2_PVS", 0)):
        check({key: value}, False)
    for label, source in (("old", block(old)), ("current", block(current))):
        obj = tmp / f"guard-{label}.o"
        run(["g++", "-std=gnu++20", "-O2", "-g0", "-x", "c++", "-c", "-", "-o", obj], input=source)
    assert (tmp / "guard-old.o").read_bytes() == (tmp / "guard-current.o").read_bytes()
    print("source clip guard/refusals and exact OFF preprocessor/object pass")


def make_commands(tmp):
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    profile = load("world_clip_stream_profile31", PROFILE_BUILDER)
    gate = load("world_clip_stream_profile31_test", PROFILE_GATE)

    # Keep the release chain intact. The two clipper exclusions must be
    # explicit in both the matched stream control and the enabled candidate.
    common = ["MESH_CLIP_LEAN=0", "MESH_CLIP_ACCEPT=0"]
    control = profile.source_only_candidate(tmp, common)
    zero = profile.source_only_candidate(tmp, [*common, "WORLD_PORTAL_CLIP_GATHER31=0"])
    on = profile.source_only_candidate(tmp, [*common, "SCENERY_CLIP_GATHER=1",
                                              "WORLD_PORTAL_CLIP_GATHER31=1"])
    values = profile.resolved(on)
    assert {key: values.get(key) for key in (
        "PVR_PIPELINE", "PACE_CATCHUP", "PACE_TRANS_SKIP", "PACE_STEADY", "COARSE",
        "CPU_BACKFACE", "MESH_CLIP_LEAN", "MESH_CLIP_ACCEPT", "SCENERY_CLIP_GATHER",
        "WORLD_PORTAL_CLIP_GATHER31")} == dict(
            PVR_PIPELINE="2", PACE_CATCHUP="2", PACE_TRANS_SKIP="4063",
            PACE_STEADY="1", COARSE="1", CPU_BACKFACE="0",
            MESH_CLIP_LEAN="0", MESH_CLIP_ACCEPT="0",
            SCENERY_CLIP_GATHER="1", WORLD_PORTAL_CLIP_GATHER31="1")
    assert len(on) > 500, "release chain was shortened"
    native = "platform/native_static.o"
    native_source = "platform/native_static.cpp"
    def command(assignments, accepted):
        result = gate.make(tmp, assignments, native)
        assert (result.returncode == 0) == accepted, (assignments[-5:],
                                                       result.stdout[-2500:], result.stderr[-2500:])
        return gate.compile_args(result.stdout, native_source) if accepted else []
    old_args = command(control, True)
    zero_args = command(zero, True)
    assert old_args == zero_args
    assert not any("RE4DC_WORLD_PORTAL_CLIP_GATHER31" in arg for arg in old_args)
    enabled = command(on, True)
    assert enabled.count("-DRE4DC_WORLD_PORTAL_CLIP_GATHER31=1") == 1
    assert enabled.count("-DRE4DC_SCENERY_CLIP_GATHER=1") == 1
    assert enabled.count("-DRE4DC_WORLD_PORTAL_STREAM31=1") == 1
    assert enabled.count("-DRE4DC_WORLD_PORTAL_COMPLETION=1") == 1
    for fact in ("TA_DIRECT", "PS2_WORLD_HDR_CACHE", "MESH_FASTPATH", "PVR_STREAM"):
        assert enabled.count(f"-DRE4DC_{fact}=1") == 1, fact

    # Feed definitions from the actual primary Make native_static command to
    # the actual source guard, then use the stream gate's trans.cpp extraction.
    source = NATIVE.read_text()
    guard = "#ifndef RE4DC_WORLD_PORTAL_COMPLETION\n" + source.split(
        "#ifndef RE4DC_WORLD_PORTAL_COMPLETION", 1)[1].split(
            "#ifndef RE4DC_SCENERY_SUBMIT_BATCH", 1)[0] + "int admitted=1;\n"
    native_defs = [arg for arg in enabled if arg.startswith("-DRE4DC_")]
    checked = subprocess.run(["g++", "-E", "-P", "-x", "c++", *native_defs, "-"],
                             input=guard, text=True, capture_output=True)
    assert checked.returncode == 0, checked.stderr
    generated = gate.make(tmp, on, "pace.h", dry=False)
    assert generated.returncode == 0, generated.stderr[-2500:]
    trans_source = "../../../src/game/trans.cpp"
    good_trans = gate.compile_args(gate.accepted(tmp, on, "src/game/trans.o"), trans_source)
    gate.actual_trans_guard(tmp, good_trans, expected=True)
    bad_mask = [*on, "PACE_TRANS_SKIP=1"]
    bad_trans = gate.compile_args(gate.accepted(tmp, bad_mask, "src/game/trans.o"), trans_source)
    gate.actual_trans_guard(tmp, bad_trans, expected=False)
    old_pipeline = gate.make(tmp, [*on, "PVR_PIPELINE=1", "PACE_TRANS_SKIP=1"], native)
    assert old_pipeline.returncode != 0
    assert "PACE_STEADY / PACE_HOLD_LOG need PVR_PIPELINE=2" in old_pipeline.stderr
    no_catchup = gate.make(tmp, [*on, "PACE_CATCHUP=1"], native)
    assert no_catchup.returncode != 0 and "COARSE needs PACE_CATCHUP=2" in no_catchup.stderr

    for changes in (["WORLD_PORTAL_CLIP_GATHER31="],
                    ["WORLD_PORTAL_CLIP_GATHER31=%"],
                    ["WORLD_PORTAL_CLIP_GATHER31=0 1"],
                    ["WORLD_PORTAL_CLIP_GATHER31=2"],
                    ["WORLD_PORTAL_CLIP_GATHER31=1 "],
                    ["WORLD_PORTAL_CLIP_GATHER31=0 "],
                    ["WORLD_PORTAL_CLIP_GATHER31=1\t"],
                    ["WORLD_PORTAL_STREAM31=0"],
                    ["SCENERY_CLIP_GATHER=0"],
                    ["SCENERY_CLIP_INDEXED26=1"],
                    ["CPU_BACKFACE=2"],
                    ["MESH_CLIP_LEAN=1"],
                    ["MESH_CLIP_ACCEPT=1"],
                    ["SCENERY_EMIT_PREFETCH=1"]):
        command([*on, *changes], False)
    print("full release-chain primary Make clip OFF/ON/refusals and native source guard pass")
    print("actual trans.cpp COARSE/pacing guard current-mask pass; old-mask refusal pass")


def main():
    with tempfile.TemporaryDirectory(prefix="world-clip31-") as temp:
        tmp = Path(temp)
        producer(tmp)
        guards_and_off(tmp)
        make_commands(tmp)


if __name__ == "__main__":
    main()
