#!/usr/bin/env python3
"""Render the actual paused QA census page using synthetic core observations.

Extracts the framebuffer/font and census-page functions from qa_menu.cpp;
links the real world_census24.cpp in its host test mode. Writes PPM captures
and a receipt outside the source tree. This is a layout/bounds check, not a
Dreamcast rendering or timing result. Pillow is optional (--png).
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    qa = DC / "game/qa_menu.cpp"
    core = DC / "game/world_census24.cpp"
    header = DC / "game/platform/include/world_census24.h"
    fixture = HERE / "qa_render_fixture.cpp"
    source = qa.read_text()
    colors = source[source.index("constexpr uint32_t kWhite"):
                    source.index("// ---------------------------------------------------------------- framebuffer text")]
    font = source[source.index("const uint8_t* glyph"):source.index("Fb fb_boot()")]
    page = source[source.index("unsigned census_page_rows"):
                  source.index("#endif\n\n// ---------------------------------------------------------------- menu")]
    generated = out / "qa_render.cpp"
    generated.write_text("#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n"
        "#include <string.h>\n#include <vector>\n#include \"world_census24.h\"\n" +
        colors + font + page + fixture.read_text())
    command = [args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-DRE4DC_WORLD_CENSUS24_HOST=1", "-I" + str(header.parent),
        str(generated), str(core), "-o", str(out / "qa-render")]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / "compile.log").write_text(result.stdout)
    if result.returncode: raise RuntimeError("host compile failed; see " + str(out / "compile.log"))
    layouts = []
    for width in (640, 320):
        for bpp in (2, 4):
            row = subprocess.check_output([str(out / "qa-render"), str(out / f"qa-{width}-{bpp}"),
                                           str(width), str(bpp)], text=True)
            layouts.append(json.loads(row))
    if args.png:
        from PIL import Image
        for path in out.glob("*.ppm"): Image.open(path).save(path.with_suffix(".png"))
    receipt = dict(status="PASS", scope=__doc__, command=command, layouts=layouts,
        source_sha256={str(path.relative_to(ROOT)): digest(path)
                       for path in (qa, core, header, fixture, Path(__file__).resolve())},
        extracted_sha256=digest(generated),
        captures={path.name: digest(path) for path in sorted(out.glob("*.ppm"))})
    (out / "qa-render.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", layouts=layouts)))


if __name__ == "__main__": main()
