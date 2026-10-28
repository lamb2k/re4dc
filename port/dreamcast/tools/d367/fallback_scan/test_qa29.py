#!/usr/bin/env python3
"""Bound real Build29 QA composition, review28 T/D delivery and old T regression.

Uses production row loops, addf, paging, core formatters and actor formatter.
The old non-audit rows/logs reserve their complete pre-audit 3072-byte capacity.
No rendering, network timing, KOS scheduling or hardware behavior is simulated.
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
ROOT = HERE.parents[4]
GAME = ROOT / "port/dreamcast/game"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PRELUDE = r'''
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <climits>
#include <cstdint>
#include <string>
#include <vector>
#include "platform/include/fallback_actor_audit29.hpp"
#include "platform/include/actor_light_fast_only.h"
#include "platform/include/draw_fallback_link26.hpp"
#include "platform/include/qa_link_review28.hpp"
extern "C" int irq_disable(void){return 7;}
extern "C" void irq_restore(int mask){assert(mask==7);}
extern "C" uint64_t re4dc_dsa24_test_clock(){return 0;}
extern "C" uintptr_t re4dc_dsa24_test_thread(){return 1;}
extern "C" void re4dc_dsa24_test_identity(unsigned* out){memset(out,0,7*sizeof(unsigned));}
extern "C" void re4dc_dsa24_test_log(const char*){}
extern "C" unsigned re4dc_dsa28_model_key(const void*){return 0;}
#include "draw_setup_audit.cpp"
#include "draw_fallback_audit.cpp"
#include "fallback_audit29.cpp"
static re4dc::fa29actor::State actors;
extern "C" unsigned re4dc_fa29_actor_line_count(){return re4dc::fa29actor::line_count(actors);}
extern "C" int re4dc_fa29_actor_format_line(unsigned row,char* out,unsigned cap){return re4dc::fa29actor::format_line(actors,row,out,cap);}
extern "C" void re4dc_fa29_actor_reset(){actors={};}
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
extern "C" void re4dc_actor_light25_snapshot(Re4dcActorLight25Stats* out){memset(out,255,sizeof(*out));}
#endif
static unsigned rendered_chars;
struct Fb{int w,h;};
static const unsigned kCyan=0;
static void fb_text(const Fb&,int,int,int,int,unsigned,const char* text){rendered_chars+=unsigned(strlen(text));}
static struct {unsigned room;int alive,heap4;char preset[24];} g_game;
#define RE4DC_QA_NAME "QA29_MAXIMUM_FIELDS_0123456789012345678901234567890123456789012345"
static char g_log[20][97];static int g_nlog;
static void snap_log(){g_nlog=20;for(auto& row:g_log){memset(row,'L',72);row[72]=0;}memcpy(g_log[19],"TAIL_LOG29",10);}
static int re4dc_qa_speed(unsigned* v){v[0]=v[1]=v[2]=UINT_MAX;return 1;}
static int re4dc_tick_log_snapshot(const char** names,unsigned* avg,unsigned*,int max,unsigned* seq){
    static const char* keys[]={"logic","EspMove","EspTrans","objTrans","ShadowTrans","MirrorTrans","ClothTrans","trans","post","cpu","remain","total","wopq","wxlu","wshell","wall","setup","vopq","vxlu","vshell","topq","iopq","tpt","ipt","ttr","itr"};
    const int n=int(sizeof(keys)/sizeof(*keys));assert(max>=n);*seq=UINT_MAX;
    for(int i=0;i<n;++i){names[i]=keys[i];avg[i]=UINT_MAX-1000U;}return n;
}
static int re4dc_world_meter_geometry_supported(){return 1;}
static int re4dc_world_meter_window(unsigned* v){for(unsigned i=0;i<11;++i)v[i]=UINT_MAX;return 1;}
static const char* wm_opq_name(){return "12.5 M";}
static const char* wm_xlu_name(){return "12.5 M";}
static const char* wm_shell_name(){return "GAME";}
static int re4dc_view_dist_get(){return 2;}
static void re4dc_ps2_pvs_state(unsigned* v){for(unsigned i=0;i<4;++i)v[i]=UINT_MAX;}
static void re4dc_pvs23_receipt_state(unsigned* v){for(unsigned i=0;i<5;++i)v[i]=UINT_MAX;}
static void re4dc_kos_heap_state(unsigned* f,unsigned* u,unsigned* b){*f=*u=*b=UINT_MAX;}
static void re4dc_vram_pages_census(unsigned* v){for(unsigned i=0;i<16;++i)v[i]=UINT_MAX;}
static unsigned re4dc_vram_fail_rooms(unsigned* lr,unsigned* ln,unsigned* rr,unsigned* rc,unsigned max){*lr=*ln=UINT_MAX;for(unsigned i=0;i<max;++i)rr[i]=rc[i]=UINT_MAX;return max;}
static void re4dc_disc_meter_totals(unsigned* r,unsigned long long* b,unsigned long long* us){*r=UINT_MAX;*b=static_cast<unsigned long long>(UINT_MAX)<<10;*us=static_cast<unsigned long long>(UINT_MAX)*1000;}
static unsigned long re4dc_fx_esp_live[32];
'''

TEST = r'''
static unsigned row_bytes(unsigned (*count)(),int (*format)(unsigned,char*,unsigned),unsigned* maximum){
    char row[320];unsigned bytes=0;
    for(unsigned i=0;i<count();++i){
        const int n=format(i,row,sizeof(row));
        assert(n>0 && unsigned(n)<sizeof(row) && unsigned(n)==strlen(row));
        bytes+=unsigned(n)+1;*maximum=std::max(*maximum,unsigned(n));
    }
    return bytes;
}
int main(){
    namespace d=re4dc::dfa26;namespace f=re4dc::fa29;namespace a=re4dc::fa29actor;namespace s=re4dc::dsa24;
    d::begin_tick(UINT_MAX,UINT_MAX);f::begin_tick(UINT_MAX,UINT_MAX);
    for(unsigned i=0;i<d::ReasonCount;++i){d::hit(d::Reason(i),UINT_MAX);d::hit(d::Reason(i));}
    for(unsigned i=0;i<f::ReasonCount;++i){f::hit(f::Reason(i),UINT_MAX);f::hit(f::Reason(i));}
    d::end_tick();f::end_tick();
    // Direct fixture access gives the unchanged production formatters their
    // largest unsigned fields, without billions of live console events.
    d::sealed.sequence=UINT_MAX;
    f::state.sealed.sequence=f::state.sealed.ticks=f::state.sealed.draws=f::state.sealed.outside_tick=UINT_MAX;
    memset(&actors,255,sizeof(actors));actors.used=a::Capacity;
    memset(&s::sealed,255,sizeof(s::sealed));s::sealed.drawn=1;s::sealed.ticks=1;s::have_sealed=true;
#if RE4DC_DSA_XLU28
    s::sealed.sampled=1;s::nmtop=s::ModelTop;
    memset(s::mtop,255,sizeof(s::mtop));
    for(unsigned i=0;i<s::ModelTop;++i)s::mtop[i].xpx=4294967040.0f;
#endif
    unsigned max_row=0;
    const unsigned dfa_bytes=row_bytes(d::line_count,d::format_line,&max_row);
    const unsigned fa_bytes=row_bytes(f::line_count,f::format_line,&max_row);
    const unsigned actor_bytes=row_bytes(re4dc_fa29_actor_line_count,re4dc_fa29_actor_format_line,&max_row);
    const unsigned dsa_bytes=row_bytes(s::line_count,s::format_line,&max_row);
    assert(actor_bytes<=65U*192U); // source-bound all-32-row decimal maximum
    // The actual snap_diag uses all WORLD_METER rows, max-width source fields,
    // a63-byte build name, a23-byte preset and20 complete72-column log lines.
    const unsigned audit_bytes=unsigned(append_audit_rows(0));
    memset(g_game.preset,'P',23);g_game.preset[23]=0;g_game.room=UINT_MAX;g_game.alive=g_game.heap4=INT_MIN;
    for(auto& v:re4dc_fx_esp_live)v=UINT32_MAX;
    snap_diag();assert(g_diag_len<int(sizeof(g_diag))-1 && strstr(g_diag,"TAIL_LOG29"));
    const unsigned actual_snapshot_bytes=unsigned(g_diag_len);
    assert(actual_snapshot_bytes>=audit_bytes && actual_snapshot_bytes-audit_bytes<=3071U);
    memset(g_diag,'b',3071);g_diag[3071]=0;
    // Include a line delimiter so paging can reconstruct all audit text.
    g_diag[7]='\n';g_diag[3070]='\n';
    const int bytes=append_audit_rows(3071);
    assert(bytes>3071 && bytes<int(sizeof(g_diag))-1);
    const int final=addf(bytes,"COMPLETE_BUILD29_SENTINEL\n");
    assert(final==bytes+int(strlen("COMPLETE_BUILD29_SENTINEL\n")) && strlen(g_diag)==unsigned(final));
    assert(strstr(g_diag,"COMPLETE_BUILD29_SENTINEL\n"));
    g_diag_len=g_diag_stats=final;
    for(unsigned i=0;i<d::ReasonCount;++i)assert(strstr(g_diag,(std::string(d::label(d::Reason(i)))+"=4294967295").c_str()));
    for(unsigned i=0;i<f::ReasonCount;++i)assert(strstr(g_diag,(std::string(f::label(f::Reason(i)))+"=4294967295").c_str()));
    assert(strstr(g_diag,"F29P n=31 ") && strstr(g_diag,"F29L n=31 "));
    // Actual diagnostic paging visits every non-header, non-newline byte.
    Fb fb{640,480};unsigned expected=unsigned(final)-7;
    for(int i=7;i<final;++i)if(g_diag[i]=='\n')--expected;
    for(unsigned page=0;page<diag_pages(fb);++page)diag_rows(fb,page*diag_page_rows(fb),true);
    assert(rendered_chars==expected);
    // Review28 T and D are the supported FA29 link routes. Old T remains a
    // component regression check only; the old fire-and-forget D producer is
    // deliberately rejected by fallback_audit29.mk when QA_LINK is enabled.
    unsigned max_datagram=0,cases=0,refusals=0;
    const std::string input(g_diag,unsigned(final));
    for(unsigned mode:{0U,1U,2U})for(unsigned drain:{50U,300U,2000U}){
        const bool review=mode!=0;
        re4dc::dfa26::Telemetry<sizeof(g_diag)+160> old;
        re4dc::ql28::Snapshot<sizeof(g_diag)+384> newer;
        if(review){memcpy(newer.text,input.data(),input.size());assert(newer.begin(mode==1?'T':'D',"fa29",input.size(),UINT_MAX,UINT_MAX));}
        else{memcpy(old.text,input.data(),input.size());assert(old.begin(input.size(),UINT_MAX,UINT_MAX));}
        unsigned queued=0;std::string joined;
        for(uint64_t ms=0;(review?newer.pending:old.pending)&&ms<120000;ms+=50){
            if(ms && ms%drain==0)queued=0;
            auto send=[&](const char* p,unsigned n){
                assert(n<=1200);max_datagram=std::max(max_datagram,n);
                if(ms<500 || queued+n+2>2400){++refusals;return false;}
                const std::string packet(p,n);const auto cut=packet.find('\n');assert(cut!=std::string::npos);
                joined+=packet.substr(cut+1);queued+=n+2;return true;
            };
            if(review)newer.step(ms,send);else old.step(ms,send);
        }
        assert(!(review?newer.pending:old.pending) && joined==input);++cases;
    }
    printf("{\"status\":\"PASS\",\"capacity\":%u,\"actual_snapshot_bytes\":%u,\"actual_non_audit_bytes\":%u,\"bytes_including_sentinel\":%d,\"headroom\":%u,\"dfa_bytes\":%u,\"fa29_bytes\":%u,\"actor_bytes\":%u,\"dsa_bytes\":%u,\"max_row_bytes\":%u,\"pages\":%u,\"transport_cases\":%u,\"refusals\":%u,\"max_datagram_bytes\":%u}\n",
        unsigned(sizeof(g_diag)),actual_snapshot_bytes,actual_snapshot_bytes-audit_bytes,final,unsigned(sizeof(g_diag))-1-unsigned(final),dfa_bytes,fa_bytes,actor_bytes,dsa_bytes,max_row,diag_pages(fb),cases,refusals,max_datagram);
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--sanitize", action="store_true")
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    qa = GAME / "qa_menu.cpp"
    source = qa.read_text()
    old = load("fa29_menu28", ROOT / "port/dreamcast/tools/cloud/build28/menu_contract.py")
    start = source.index("#if defined(RE4DC_DRAW_FALLBACK_AUDIT)", source.index("QaGame g_game;"))
    storage = source[start:source.index("constexpr int kLogLines", start)]
    start = source.index("int addf(int at, const char* fmt, ...) __attribute__")
    addf = source[start:source.index("#if defined(RE4DC_WORLD_SCRATCH)", start)]
    start = source.index("#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY)", source.index("void snap_diag()"))
    rows = source[start:source.index("#if defined(RE4DC_WORLD_METER)", start)]
    assert "fa29::format_line" in rows and "dsa24::format_line" in rows
    paging = "\n".join(old.function(source, name) for name in ("diag_page_rows", "diag_rows", "diag_pages"))
    (out / "arch").mkdir()
    (out / "arch/irq.h").write_text('#pragma once\nextern "C" int irq_disable(void);\nextern "C" void irq_restore(int);\n')
    fixture = out / "qa29.cpp"
    fixture.write_text(PRELUDE + storage + addf + "\nint append_audit_rows(int a){\n" + rows + "\nreturn a;}\n" + old.function(source,"snap_diag") + paging + TEST)
    profiles = (("standalone", 0, 0, 0, 0), ("composed", 1, 1, 1, 0), ("composed-occ", 1, 1, 1, 1))
    results = []
    for name, dsa, xlu, fast, occ in profiles:
        binary = out / name
        command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wno-address", "-Wno-misleading-indentation",
                   "-I" + str(out), "-I" + str(GAME), "-DRE4DC_FALLBACK_AUDIT29=1", "-DRE4DC_DRAW_FALLBACK_AUDIT=1",
                   "-DRE4DC_WORLD_METER=1",
                   "-DRE4DC_DRAW_SETUP_AUDIT_HOST=1", "-DRE4DC_DRAW_SETUP_AUDIT=" + str(dsa),
                   "-DRE4DC_DSA_XLU28=" + str(xlu), "-DRE4DC_DSA_OCC28=" + str(occ),
                   "-DRE4DC_ACTOR_LIGHT_FAST_ONLY=" + str(fast), str(fixture), "-o", str(binary)]
        if args.sanitize:
            command[1:1] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-fno-pie", "-no-pie"]
        build = subprocess.run(command, text=True, capture_output=True)
        (out / (name + "-build.log")).write_text(build.stdout + build.stderr)
        if build.returncode:
            raise RuntimeError(build.stderr)
        env = dict(os.environ)
        if args.sanitize:
            env["ASAN_OPTIONS"] = "detect_leaks=0"
        run = subprocess.run([str(binary)], text=True, capture_output=True, env=env)
        (out / (name + "-run.log")).write_text(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
        results.append(dict(profile=name, **json.loads(run.stdout)))
    sources = [qa, GAME / "fallback_audit29.cpp", GAME / "draw_fallback_audit.cpp", GAME / "draw_setup_audit.cpp", Path(__file__)]
    sources += [GAME / "platform/include" / name for name in ("fallback_actor_audit29.hpp", "draw_fallback_link26.hpp", "qa_link_review28.hpp")]
    report = dict(status="PASS", sanitized=args.sanitize, leak_sanitizer=False, scope=__doc__, profiles=results,
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (out / "qa29.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
