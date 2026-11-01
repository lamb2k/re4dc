#!/usr/bin/env python3
"""Run complete recovered Thompson units with bounded synthetic game services.

The target module gate separately checks the real headers, ABI and localization.
This fixture keeps original function bodies; one effect-owner pointer-to-int
cast is widened in the temporary host copy because the host has 64-bit pointers.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
SOURCES={"ENTRY":ROOT/"src/wep12/wep12.cpp",
         "OBJECT":ROOT/"src/wep12/objTompson.cpp",
         "MACHINE":ROOT/"src/wep/pl_machine.cpp"}
HEADERS="wep_mod light esp item motion snd pad rnd atari player pl_wep global main joy cam_ctrl math_sub".split()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--sanitize",action="store_true")
    args=p.parse_args()
    prefix=HERE/"weapon_fixture_prefix.hpp"
    template=HERE/"wep12_fixture.cpp.in"
    with tempfile.TemporaryDirectory(prefix="wep12-host-") as tmp:
        work=Path(tmp)
        for name in HEADERS:
            (work/(name+".h")).write_text('#include '+json.dumps(str(prefix))+'\n')
        cpp=template.read_text().replace("@PREFIX@",str(prefix))
        rewrites=0
        for name,source in SOURCES.items():
            text=source.read_text()
            rewrites+=text.count("(int) this")
            text=text.replace("(int) this","(std::intptr_t) this")
            copy=work/(name.lower()+".cpp")
            copy.write_text(text)
            cpp=cpp.replace("@"+name+"@",str(copy))
        assert rewrites==1,"Review any new pointer-width adaptation explicitly"
        generated=work/"fixture.cpp";generated.write_text(cpp)
        exe=work/"fixture"
        command=["g++","-std=c++17","-O2","-g","-fno-pie","-no-pie",
                 "-D_prolog=wep12_prolog","-D_epilog=wep12_epilog",
                 "-D_unresolved=wep12_unresolved","-I",str(work),str(generated),"-o",str(exe)]
        if args.sanitize:
            command[1:1]=["-fsanitize=address,undefined","-fno-omit-frame-pointer"]
        build=subprocess.run(command,text=True,capture_output=True)
        if build.returncode:
            print(build.stdout+build.stderr,end="")
            build.check_returncode()
        env=dict(os.environ)
        if args.sanitize: env["ASAN_OPTIONS"]="detect_leaks=0"
        run=subprocess.run([str(exe)],text=True,capture_output=True,env=env)
        print(run.stdout+run.stderr,end="");run.check_returncode()
    inputs=list(SOURCES.values())+[prefix,template,Path(__file__).resolve(),ROOT/"config/G4BE08/modules.py"]
    receipt={"status":"PASS","scope":"Complete wep12 entry/object and shared machine source with synthetic host services; not real ABI, assets, sound or gameplay acceptance.",
             "sanitizer":"address,undefined" if args.sanitize else None,
             "result":run.stdout.strip(),
             "host_adaptations":["u32 is uintptr_t in the synthetic header; pointer-admission range accepts live host objects.",
                                 "One (int) this effect-owner cast becomes intptr_t in a temporary source copy.",
                                 "All external game services and class layout are synthetic; real source headers/ABI are qualified separately on SH-4."],
             "source_sha256":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2)+"\n")


if __name__=="__main__":main()
