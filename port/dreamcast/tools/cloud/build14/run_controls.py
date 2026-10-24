#!/usr/bin/env python3
"""Build 14: actual observer/census, synthetic registers; no hardware qualification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]
CASES = ("partition", "pause-identity", "skipped", "continuity", "accounting", "wrap48", "lost-mode",
         "lost-clock", "lost-stop", "busy", "busy-stopped", "invalid-high", "invalid-reset",
         "invalid-clock", "no-contrast", "allocation", "census-fault", "unrun")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sanitize", action="store_true")
    p.add_argument("--kos-root", type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    sources = [DC/"game/world_census24.cpp",DC/"game/perf_phase_miss.cpp",HERE/"check_core.cpp"]
    headers = [DC/"game/platform/include"/n for n in
               ("world_census24.h","perf_phase_miss.h","perf_phase_accounting.hpp")]
    inputs = [*sources,*headers,Path(__file__)]
    hashes = {str(x.relative_to(ROOT)):sha(x) for x in inputs}
    env = dict(os.environ)
    if args.sanitize:env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS","")+":detect_leaks=0"
    commands,results = [],[]
    for event in (15,37):
        exe = out/f"controls-{event}"
        command = ["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror",
            "-DRE4DC_WORLD_CENSUS24_HOST=1","-DRE4DC_WORLD_CENSUS24=1",
            "-DRE4DC_PERF_PHASE_MISS_HOST=1","-DRE4DC_PERF_PHASE_MISS=1",f"-DRE4DC_PERF_PHASE_MISS_EVENT={event}",
            "-I"+str(headers[0].parent),*map(str,sources),"-o",str(exe)]
        if args.sanitize:command[3:3] = ["-fsanitize=address,undefined","-fno-omit-frame-pointer","-fno-pie","-no-pie"]
        run = subprocess.run(command,capture_output=True,text=True)
        (out/f"compile-{event}.log").write_text(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(run.stderr)
        commands.append(command)
        for case in CASES:
            run = subprocess.run([str(exe),case],env=env,capture_output=True,text=True)
            (out/f"event{event}-{case}.log").write_text(run.stdout+run.stderr)
            if run.returncode:raise RuntimeError(f"{event} {case}: {run.stdout}{run.stderr}")
            results.append(dict(event=event,case=case,result=run.stdout.strip()))
    # Extract the actual pinned KOS coherent-read function and drive the high
    # word across a low32 rollover. This proves the retry algorithm only.
    kos_source = args.kos_root/"kernel/arch/dreamcast/kernel/perfctr.c"
    text = kos_source.read_text()
    a = text.index("uint64_t perf_cntr_count(");b = text.index("\nvoid perf_cntr_timer_enable",a)
    body = text[a:b]
    fixture = out/"kos-count.cpp"
    fixture.write_text('''#include <stdint.h>
#include <assert.h>
using perf_cntr_t=unsigned;
static unsigned hi_values[4],lo_values[2],hi_at,lo_at;
static unsigned high(unsigned c){assert(c==1);return hi_values[hi_at++];}
static unsigned low(unsigned c){assert(c==1);return lo_values[lo_at++];}
#define PMCTR_HIGH(c) high(c)
#define PMCTR_LOW(c) low(c)
#define __predict_false(x) (x)
'''+body+'''
int main(){
hi_values[0]=hi_values[1]=7;lo_values[0]=11;
assert(perf_cntr_count(1)==((uint64_t(7)<<32)|11)&&hi_at==2&&lo_at==1);
hi_at=lo_at=0;hi_values[0]=7;hi_values[1]=hi_values[2]=hi_values[3]=8;
lo_values[0]=0xfffffffeU;lo_values[1]=3;
assert(perf_cntr_count(1)==((uint64_t(8)<<32)|3)&&hi_at==4&&lo_at==2);
}
''')
    command=["g++","-std=c++17","-O2","-Wall","-Wextra","-Werror",str(fixture),"-o",str(out/"kos-count")]
    subprocess.run(command,check=True);subprocess.run([str(out/"kos-count")],check=True)
    commands.append(command)
    assert hashes=={str(x.relative_to(ROOT)):sha(x) for x in inputs},"source changed"
    report=dict(status="PASS",scope=__doc__,source_sha256=hashes,sanitized=args.sanitize,
        commands=commands,cases=results,case_count=len(results),
        kos_read=dict(source=str(kos_source),sha256=sha(kos_source),extracted_sha256=hashlib.sha256(body.encode()).hexdigest(),
            controls=["stable high word","low32 rollover retries high-low-high"],hardware_proof=False),
        limits="Injected register responses and host memory accesses prove software accounting only. SIMULATED never becomes QUALIFIED. Actual console cache response is pending.")
    (out/"host-controls.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status="PASS",cases=len(results),sanitized=args.sanitize,receipt=str(out/"host-controls.json"))))

if __name__=="__main__":main()
