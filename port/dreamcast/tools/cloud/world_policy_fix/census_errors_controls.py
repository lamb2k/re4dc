#!/usr/bin/env python3
"""Actual WC24 core error accounting/lifecycle, OFF/ON and ASan/UBSan pairs.

The unchanged core is included by the fixture; synthetic boundary injection
exercises count wrap without billions of calls. A fixed mutable clock and
thread edge permit exact original Snapshot comparisons. PM14 composition
uses its actual core and synthetic PRFC1 responses (SIMULATED, never hardware
qualification). No renderer, console timing or gameplay acceptance is claimed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
CORE=DC/"game/world_census24.cpp"
CASES=("empty","unspecified","typed-wait","repeat","different-contexts","spill","spill-sum-wrap","formatter",
    "clock-reverse","tick-reverse","phase-overrun","scope-depth","scope-order","scope-unclosed","counter-overflow",
    "foreign-owner","inactive","partial-restart","pause-before-seal","pause-keep","resume-fresh","identity-change",
    "window-continuity","first-evidence","bin-wrap","unknown-reason")
PMU_CASES=("pmu-composition","pause-before-seal","first-evidence")

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    watched=[CORE,DC/"game/platform/include/world_census24.h",DC/"game/platform/include/world_census24_errors.inc",
        DC/"game/perf_phase_miss.cpp",DC/"game/platform/include/perf_phase_miss.h",
        DC/"game/platform/include/perf_phase_accounting.hpp",HERE/"census_errors_check.cpp",Path(__file__)]
    frozen={str(p.relative_to(ROOT)):sha(p) for p in watched}
    env=dict(os.environ);env["ASAN_OPTIONS"]="detect_leaks=0"
    commands,observations,diags={}, {}, {}
    comparisons=0
    for sanitize in (False,True):
        mode="asan-ubsan" if sanitize else "normal"
        for pmu in (0,1):
            old=None
            for enabled in (0,1):
                label=f"{mode}-pmu{pmu}-errors{enabled}";binary=out/label
                command=["g++","-std=c++20","-O2","-ffp-contract=off","-Wall","-Wextra",
                    "-DRE4DC_WORLD_CENSUS24=1","-DRE4DC_WORLD_CENSUS24_HOST=1",
                    f"-DRE4DC_WORLD_CENSUS24_ERRORS={enabled}",f"-DRE4DC_PERF_PHASE_MISS={pmu}",
                    "-DRE4DC_PERF_PHASE_MISS_HOST=1",f'-DRE4DC_WORLD_CENSUS24_SOURCE="{CORE}"',
                    "-I"+str(DC/"game/platform/include"),str(HERE/"census_errors_check.cpp")]
                if pmu:command.append(str(DC/"game/perf_phase_miss.cpp"))
                command += ["-o",str(binary)]
                if sanitize:command[3:3]=["-fsanitize=address,undefined","-fno-omit-frame-pointer","-fno-pie","-no-pie"]
                run=subprocess.run(command,cwd=ROOT,capture_output=True,env=env)
                (out/(label+".compile.log")).write_bytes(run.stdout+run.stderr)
                assert run.returncode==0,(label,run.stderr.decode());commands[label]=command
                rows=[]
                for case in PMU_CASES if pmu else CASES:
                    run=subprocess.run([str(binary),case],cwd=ROOT,capture_output=True,env=env)
                    (out/(label+"-"+case+".stderr")).write_bytes(run.stderr)
                    assert run.returncode==0,(label,case,run.returncode,run.stderr.decode())
                    row=json.loads(run.stdout);assert row["case"]==case;rows.append(row)
                    diags[label+"-"+case]=run.stderr.decode()
                observations[label]=rows
                if enabled:
                    assert old==rows,(label,"original snapshot/aggregate changed")
                    comparisons+=len(rows)
                else:old=rows
            print("PASS",mode,"pmu",pmu,"paired cases",len(rows),flush=True)
    assert frozen=={str(p.relative_to(ROOT)):sha(p) for p in watched},"source changed during gate"
    result=dict(status="PASS",scope=__doc__,source_sha256=frozen,paired_cases=comparisons,
        core_cases=CASES,pmu_cases=PMU_CASES,asan=True,ubsan=True,leak_detection=False,
        compiler=subprocess.check_output(["g++","--version"],text=True).splitlines()[0],
        commands=commands,observations=observations,diagnostics=diags,
        original_snapshot_fields_equal=True,pmu_qualification="SIMULATED synthetic responses only")
    (out/"host-controls.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",paired_cases=comparisons)))

if __name__=="__main__":main()
