#!/usr/bin/env python3
"""Compare direct indexed world clipping with whole and subset gathers.

Reuses Build24's synthetic authenticated R4IM packages and packet assertions.
The decoder and clip_strip body are extracted from the current production TU;
the same real pvr_geometry.cpp is used in both arms. Projection and bounded
packet ownership use the explicit Build24 host adapters. No game data or
console timing is claimed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract():
    source = (DC / "game/platform/native_static.cpp").read_text()
    helper = module("world26_extract", DC / "tools/d367/world_submit_spike/check_runtime.py")
    first = source.index("    float u(float value)const")
    last = source.index("    // 1 emitted/culled", first)
    clip = helper.function(source, "    int clip_strip(Source base,")
    # The actual signature selects Source only under the new flag. The function
    # body is copied byte-for-byte; the fixture declares the enabled signature.
    clip = ("template<class Source,class Index>\n"
            "int clip_strip(Source base,const re4dc::room::CompactBatch& batch,\n"
            "               const Index* index,unsigned count)" + clip[clip.index("{"):])
    for name in ("strips_bf_sq", "strips_lean"):
        body = helper.function(source, "const std::uint8_t* " + name + "(")
        assert "result=clip_stream_strip(base,batch,s,n);" in body, name
    stream = helper.function(source, "int clip_stream_strip(")
    assert "package.vertices()+l.first_vertex,package.pool_offsets(l)" in stream
    assert "return clip_strip(source,batch,indices,count);" in stream
    assert "return clip_strip(base,batch,indices,count);" in stream
    return {"DECODE": source[first:last], "CLIP": clip, "STREAM": stream}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sanitizer", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    prior = HERE.parent / "build24"
    inputs = [Path(__file__), prior / "world_fixture.cpp.in", prior / "world_host.py",
        DC / "game/platform/native_static.cpp",
        DC / "game/platform/include/scenery_clip_indexed26.hpp",
        DC / "game/platform/include/scenery_clip_gather.hpp",
        DC / "room/instanced_mesh.hpp", DC / "room/pvr_geometry.hpp", DC / "room/pvr_geometry.cpp",
        DC / "room/static_room_prepare.hpp", DC / "room/room_package.hpp",
        DC / "tools/d367/world_submit_spike/check_runtime.py"]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    source = (prior / "world_fixture.cpp.in").read_text()
    source = source.replace('#include "@DC@/game/platform/include/scenery_clip_gather.hpp"',
        '#include "@DC@/game/platform/include/scenery_clip_gather.hpp"\n'
        '#include "@DC@/game/platform/include/scenery_clip_indexed26.hpp"')
    old = "const int rb=b.clip_strip(local.corners,batch,strip.data(),strip.size());"
    new = ("const re4dc::scenery_clip26::Indexed<CompactVertex12> direct{src,off};\n"
           "                const int rb=b.clip_strip(direct,batch,strip.data(),strip.size());")
    assert source.count(old) == 1
    source = source.replace(old, new)
    extracted = extract()
    for key in ("DECODE", "CLIP"):
        source = source.replace("@" + key + "@", extracted[key])
    source = source.replace("@DC@", str(DC))
    (out / "fixture.cpp").write_text(source)
    (out / "host/dc").mkdir(parents=True)
    (out / "host/dc/pvr.h").write_text("#pragma once\n#include <cstddef>\n#include <cstdint>\n"
        "struct pvr_vertex_t {std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n"
        "struct pvr_poly_hdr_t {std::uint32_t words[8];};\n"
        "#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n"
        "int pvr_prim(const void*,std::size_t);\n")
    (out / "host/dc/matrix.h").write_text("#pragma once\ninline void mat_trans_nodiv(float&,float&,float&,float&){}\n")
    (out / "host/kos").mkdir()
    (out / "host/kos/fs.h").write_text("#pragma once\nusing file_t=int;\n#define FILEHND_INVALID (-1)\n")
    rows = []
    for lean, accept in ((0, 0), (1, 0), (1, 1)):
        name = f"lean{lean}-accept{accept}"
        command = ["g++", "-std=c++20", "-O2", "-fno-fast-math", "-ffp-contract=off",
            "-Wall", "-Wextra", "-D__sh__=1", "-DRE4DC_HW_LEAN=1",
            "-DRE4DC_PS2_VERTEX_ALPHA=1", "-DRE4DC_COPY_LEAN=1",
            f"-DRE4DC_MESH_CLIP_LEAN={lean}", f"-DRE4DC_MESH_CLIP_ACCEPT={accept}",
            "-I" + str(out / "host"), "-I" + str(DC / "room"),
            str(out / "fixture.cpp"), str(DC / "room/pvr_geometry.cpp"), "-o", str(out / name)]
        if args.sanitizer:
            command[1:1] = ["-fsanitize=address,undefined", "-fno-sanitize-recover=all"]
            command[command.index("-O2")] = "-O1"
        built = subprocess.run(command, capture_output=True)
        (out / (name + ".compile.log")).write_bytes(built.stdout + built.stderr)
        assert built.returncode == 0, (name, built.stderr.decode())
        env = os.environ.copy()
        env["ASAN_OPTIONS"] = "detect_leaks=0"
        run = subprocess.run([str(out / name)], capture_output=True, env=env)
        (out / (name + ".stdout")).write_bytes(run.stdout)
        (out / (name + ".stderr")).write_bytes(run.stderr)
        assert run.returncode == 0, (name, run.returncode, run.stderr.decode())
        rows.append(dict(configuration=name, command=command, **json.loads(run.stdout)))
    assert hashes == {str(p.relative_to(ROOT)): sha(p) for p in inputs}, "sources changed; rerun"
    report = dict(status="PASS", scope=__doc__, source_sha256=hashes, configurations=rows,
        extracted_sha256={k: hashlib.sha256(v.encode()).hexdigest() for k, v in extracted.items()},
        sanitizer="address,undefined" if args.sanitizer else None,
        host_adapters={"projection": "Same scalar 1/abs(z) projection; SH4 fsrra is not emulated.",
            "packet": "Same bounded scratch and explicit flush refusal; no real TA/SQ owner.",
            "matrix": "Unused mat_trans_nodiv stub; production clip_vertex uses explicit mvq."})
    (out / "world-host.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", configurations=len(rows),
        comparisons=sum(row["clip_comparisons"] for row in rows), receipt=str(out / "world-host.json"))))


if __name__ == "__main__":
    main()
