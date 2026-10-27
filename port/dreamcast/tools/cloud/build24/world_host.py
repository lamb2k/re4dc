#!/usr/bin/env python3
"""Check Build24 subset gathering through the production world clip consumer.

The real R4IM reader adopts synthetic indexed packages, the new helper fills
the existing local corner slots, and exact extracted Emitter corner/clip_strip
bodies run against both full and subset gathers. Only projection and the packet
sink use host adapters. No game data, console timing or whole-renderer claim.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

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
    helper = module("world24_extract", DC / "tools/d367/world_submit_spike/check_runtime.py")
    begin = source.index("    float u(float value)const")
    end = source.index("    // 1 emitted/culled", begin)
    clip = helper.function(source, "    int clip_strip(")
    # Both direct streamed consumers must request every clipped strip, even
    # after base became non-null from a previous partial gather.
    for name in ("strips_bf_sq", "strips_lean"):
        start = source.index("const std::uint8_t* " + name + "(")
        body = helper.function(source[start:], "const std::uint8_t* " + name + "(")
        assert "base=stream_gather(base,s,n);" in body, name
        assert "if(!base)base=stream_gather();" in body, name
    assert source.count("base=stream_gather(base,s,n);") == 2
    assert "stream_clip_gather.begin();" in source
    assert "RE4DC_SCENERY_DEDUP==3" in source[:source.index("#include \"include/scenery_clip_gather.hpp\"")]
    return {"DECODE": source[begin:end], "CLIP": "template<class Vertex,class Index>\n" + clip}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sanitizer", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__), HERE / "world_fixture.cpp.in",
        DC / "game/platform/native_static.cpp", DC / "game/platform/include/scenery_clip_gather.hpp",
        DC / "room/instanced_mesh.hpp", DC / "room/pvr_geometry.hpp", DC / "room/pvr_geometry.cpp",
        DC / "room/static_room_prepare.hpp", DC / "room/room_package.hpp",
        DC / "tools/d367/world_submit_spike/check_runtime.py"]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    source = (HERE / "world_fixture.cpp.in").read_text()
    extracted = extract()
    for key, value in extracted.items():
        source = source.replace("@" + key + "@", value)
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
        host_adapters={"projection": "Same scalar 1/abs(z) projection for both arms; SH4 fsrra is not emulated.",
            "packet": "Same bounded scratch and explicit flush refusal for both arms; no real TA/SQ owner.",
            "matrix": "Unused mat_trans_nodiv stub; tested production clip_vertex uses explicit mvq."})
    (out / "world-host.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", configurations=len(rows),
        comparisons=sum(row["clip_comparisons"] for row in rows),receipt=str(out / "world-host.json"))))


if __name__ == "__main__":
    main()
