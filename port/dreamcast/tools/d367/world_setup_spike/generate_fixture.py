#!/usr/bin/env python3
"""Generate actual full-TU selector fixture and deterministic adopted packages.

The target builder executes it using the retained SH4 compiler/opcode runner.
Production deliberately requires __sh__ for SCENERY_CHUNK; this generator does
not rewrite those hardware guards to manufacture a native host build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
SOURCE = DC / "game/platform/native_static.cpp"
from selection_cases import write_cases

def generate_source(path, source=SOURCE):
    source = Path(source)
    text = source.read_text()
    anchor = text.index("#if RE4DC_SCENERY_SELECT_ONLY\n            {")
    light_start = text.index("                ScenerySelector d{", anchor)
    light_end = text.index("                const auto& selected_part", light_start)
    preparation_start = text.index("#if RE4DC_PS2_VERTEX_ALPHA", light_end)
    preparation_end = text.index("#if RE4DC_PS2_INTERIOR_ACTORS", preparation_start)
    light = text[light_start:light_end] + text[preparation_start:preparation_end]
    full_start = text.index("#if RE4DC_PS2_VERTEX_ALPHA\n            const bool marked=", preparation_end)
    full_end = text.index("#if RE4DC_SCENERY_CHUNK\n            // SCENERY_CHUNK: select now", full_start)
    full = text[full_start:full_end]
    far_path = source.parent / "include/scenery_part_far.inc"
    far = far_path.read_text()
    full = full.replace('#include "include/scenery_part_far.inc"', far)
    light = light.replace('#include "include/scenery_part_far.inc"', far)
    template = (HERE / "selection_fixture.cpp.in").read_text()
    result = template.replace("@NATIVE_SOURCE@", str(source.resolve())).replace("@FULL_SETUP@", full).replace("@LIGHT_SETUP@", light)
    if "@FULL_SETUP@" in result or "@LIGHT_SETUP@" in result:
        raise ValueError("unexpanded fixture marker")
    Path(path).write_text(result)
    return dict(source=hashlib.sha256(text.encode()).hexdigest(),
                full_setup=hashlib.sha256(full.encode()).hexdigest(),
                light_setup=hashlib.sha256(light.encode()).hexdigest(),
                selector=hashlib.sha256((source.parent / "include/scenery_chunk_select.inc").read_bytes()).hexdigest(),
                fixture=hashlib.sha256(result.encode()).hexdigest())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--source", type=Path, default=SOURCE)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    out = args.output.resolve()
    fixture = out / "selection_fixture.cpp"
    hashes = generate_source(fixture, args.source)
    records = write_cases(out / "cases")
    report=dict(fixture=str(fixture), cases=str(out / "cases/cases.json"), count=len(records), hashes=hashes)
    (out / "fixture-inputs.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
