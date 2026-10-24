#!/usr/bin/env python3
"""Actual paused QA page/font with six-digit simulated PMU controls,320/640 pixels.

Uses the existing Build10 framebuffer capture/guard harness and Build14's real
census/observer test setup. Captures stay outside Git. This is a display and
buffer-bounds gate, never a Dreamcast event or timing result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    qa=DC/"game/qa_menu.cpp";core=DC/"game/world_census24.cpp";pmu=DC/"game/perf_phase_miss.cpp"
    header=DC/"game/platform/include/perf_phase_miss.h"
    controls=HERE/"check_core.cpp";render=HERE.parent/"build10/qa_render_fixture.cpp"
    source=qa.read_text()
    colors=source[source.index("constexpr uint32_t kWhite"):source.index("// ---------------------------------------------------------------- framebuffer text")]
    font=source[source.index("const uint8_t* glyph"):source.index("Fb fb_boot()")]
    page=source[source.index("unsigned census_page_rows"):source.index("#endif\n\n// ---------------------------------------------------------------- menu")]
    setup=controls.read_text().split("int main(",1)[0]
    capture=render.read_text();capture=capture[capture.index("    const int width = atoi"):]
    generated=out/"qa.cpp"
    generated.write_text(setup+colors+font+page+"\nint main(int argc,char** argv){\nif(argc!=4)return 1;\npartition();wc::pause();\n"+capture)
    command=["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror","-Wno-unused-function",
        "-DRE4DC_WORLD_CENSUS24=1","-DRE4DC_WORLD_CENSUS24_HOST=1","-DRE4DC_PERF_PHASE_MISS=1",
        "-DRE4DC_PERF_PHASE_MISS_HOST=1","-DRE4DC_PERF_PHASE_MISS_EVENT=37",
        "-I"+str(header.parent),str(generated),str(core),str(pmu),"-o",str(out/"qa")]
    run=subprocess.run(command,capture_output=True,text=True);(out/"compile.log").write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stderr)
    layouts=[]
    for width in (320,640):
        for bpp in (2,4):
            layouts.append(json.loads(subprocess.check_output([str(out/"qa"),str(out/f"qa-{width}-{bpp}"),str(width),str(bpp)],text=True)))
    inputs=(qa,core,pmu,header,header.parent/"perf_phase_accounting.hpp",header.parent/"world_census24.h",controls,render,Path(__file__))
    report=dict(status="PASS",scope=__doc__,layouts=layouts,command=command,
        source_sha256={str(x.relative_to(ROOT)):sha(x) for x in inputs},extracted_sha256=sha(generated),
        captures={x.name:sha(x) for x in sorted(out.glob("*.ppm"))},
        control_values=dict(resident=12,heavy=400000,qualification="SIMULATED"))
    (out/"qa-render.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",layouts=layouts)))
if __name__=="__main__":main()
