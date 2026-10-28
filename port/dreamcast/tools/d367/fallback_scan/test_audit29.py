#!/usr/bin/env python3
"""Compile the actual Build29 counter core against a serialized host IRQ shim.

This proves counting/snapshot/formatting behavior, including concurrent worker
writers. It does not model the Dreamcast IRQ latency, game frames or device I/O.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
GAME = ROOT / "port/dreamcast/game"
FIXTURE = r'''
#include "platform/include/fallback_audit29.h"
#include <cassert>
#include <cstring>
#include <mutex>
#include <thread>
#include <vector>
#include <cstdio>
#include <cstdint>

static std::recursive_mutex irq_mutex;
static unsigned actor_resets;
extern "C" int irq_disable(void) { irq_mutex.lock(); return 7; }
extern "C" void irq_restore(int old) { assert(old==7); irq_mutex.unlock(); }
extern "C" void re4dc_fa29_actor_reset(void) { ++actor_resets; }
namespace f=re4dc::fa29;
int main() {
    f::Snapshot s{};
    f::reset(); assert(actor_resets==1); assert(!f::snapshot(&s));assert(!f::collecting());
    assert(!f::snapshot(nullptr)); assert(f::line_count()==1);
    f::hit(f::MotionKeyMiss); f::end_tick(); assert(!f::snapshot(&s));
    f::begin_tick(5,0x103); assert(actor_resets==2);assert(f::collecting());
    f::hit(f::MotionKeyMiss,3); f::hit(f::SoundRead,8192); f::end_tick();
    assert(f::snapshot(&s)); assert(s.tick==5 && s.room==0x103);assert(!f::collecting());
    assert(s.ticks==1 && s.draws==1 && s.draw_tick==5 && s.draw_valid==1);
    assert(s.totals[f::MotionKeyMiss]==3 && s.last_draw[f::SoundRead]==8192);
    f::hit(f::SoundRead,2048); // Outside the game tick: cumulative only.
    f::begin_tick(6,0x103); f::decision(false); f::hit(f::MotionKeyMiss,2); f::end_tick();
    assert(f::snapshot(&s)); assert(s.sequence==2 && s.ticks==2 && s.draws==1);
    assert(s.draw_tick==5 && s.last_draw[f::MotionKeyMiss]==3);
    assert(s.totals[f::MotionKeyMiss]==5 && s.totals[f::SoundRead]==10240);
    assert(s.outside_tick==1);
    f::pause();assert(!f::collecting()); f::hit(f::SoundRead,8192); f::begin_tick(7,0x104); f::end_tick();
    assert(f::snapshot(&s) && s.room==0x103 && s.sequence==2);
    f::resume(); f::begin_tick(8,0x103); f::hit(f::ClothLegacy); f::end_tick();
    assert(f::snapshot(&s) && s.draw_tick==8 && s.draws==2);
    assert(s.last_draw[f::MotionKeyMiss]==0 && s.last_draw[f::ClothLegacy]==1);
    f::begin_tick(9,0x104); f::decision(false); f::end_tick();
    assert(f::snapshot(&s) && s.room==0x104 && s.ticks==1 && s.draws==0);
    assert(!s.draw_valid && !s.totals[f::MotionKeyMiss]); assert(actor_resets==3);
    f::begin_tick(10,0x104);
    for(unsigned i=0;i<f::ReasonCount;++i){f::hit(f::Reason(i),UINT32_MAX);f::hit(f::Reason(i));}
    f::hit(f::Reason(-1));f::hit(f::Reason(f::ReasonCount));
    f::end_tick();assert(f::snapshot(&s) && s.overflow);
    for(unsigned i=0;i<f::ReasonCount;++i)assert(s.totals[i]==UINT32_MAX && s.last_draw[i]==UINT32_MAX);
    char line[192];unsigned bytes=0;
    for(unsigned i=0;i<f::line_count();++i){
        int n=f::format_line(i,line,sizeof(line));assert(n>0 && n<192);
        assert(unsigned(n)==std::strlen(line));bytes+=unsigned(n)+1;
        assert(f::format_line(i,line,1)==-1 && line[0]==0);
    }
    assert(f::format_line(f::line_count(),line,sizeof(line))==-1);
    assert(f::format_line(0,nullptr,192)==-1 && f::format_line(0,line,0)==-1);
    assert(std::strcmp(f::label(f::Reason(-1)),"invalid")==0);
    assert(std::strcmp(f::unit(f::SoundRead),"bytes_requested")==0);
    f::reset();f::begin_tick(11,0x103);
    std::vector<std::thread> workers;
    for(unsigned w=0;w<8;++w)workers.emplace_back([]{
        for(unsigned i=0;i<10000;++i){f::hit(f::SoundRead,2048);f::hit(f::SoundReadFail);}
    });
    for(auto& w:workers)w.join();
    f::end_tick();assert(f::snapshot(&s));
    assert(s.totals[f::SoundRead]==8*10000*2048U && s.totals[f::SoundReadFail]==80000);
    assert(s.last_draw[f::SoundRead]==s.totals[f::SoundRead] && !s.overflow);
    std::printf("{\"status\":\"PASS\",\"reasons\":%u,\"concurrent_hits\":160000,\"max_rows_bytes\":%u,\"snapshot_bytes\":%u}\n",
                unsigned(f::ReasonCount),bytes,unsigned(sizeof(s)));
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cxx", default="g++")
    ap.add_argument("--sanitize", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="fallback-audit29-") as tmp:
        tmp = Path(tmp)
        (tmp / "arch").mkdir()
        (tmp / "arch/irq.h").write_text('#pragma once\nextern "C" int irq_disable(void);\nextern "C" void irq_restore(int);\n')
        fixture = tmp / "fixture.cpp"
        fixture.write_text(FIXTURE)
        binary = tmp / "fixture"
        command = [args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pthread",
                   "-I" + str(tmp), "-I" + str(GAME), str(fixture), str(GAME / "fallback_audit29.cpp"), "-o", str(binary)]
        if args.sanitize:
            command[1:1] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
        subprocess.run(command, check=True)
        env = dict(os.environ)
        if args.sanitize:
            # This sandbox denies LSan's /proc/task traversal. ASan/UBSan stay
            # enabled; the production core has no allocator calls to audit.
            env["ASAN_OPTIONS"] = "detect_leaks=0"
        result = subprocess.run([str(binary)], check=True, text=True, capture_output=True, env=env)
        report = json.loads(result.stdout)
        report.update(sanitized=args.sanitize, leak_sanitizer=False, scope=__doc__, limitations="Host mutex substitutes only IRQ exclusion; target instructions, device and game behavior are separate gates. LSan is disabled because sandbox /proc task traversal is unavailable.")
        report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (Path(__file__), GAME/"fallback_audit29.cpp", GAME/"platform/include/fallback_audit29.h", GAME/"platform/include/fallback_audit29.def")}
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
