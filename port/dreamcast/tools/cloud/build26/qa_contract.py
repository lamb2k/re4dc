#!/usr/bin/env python3
"""Compile production counters, QA rows, framing and bounded telemetry on the host."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    qa=DC/'game/qa_menu.cpp';core=DC/'game/draw_fallback_audit.cpp'
    header=DC/'game/platform/include/draw_fallback_audit.h'
    telemetry=DC/'game/platform/include/draw_fallback_link26.hpp'
    source=qa.read_text()
    start=source.index('int addf(int at, const char* fmt, ...) __attribute__')
    addf=source[start:source.index('#if defined(RE4DC_WORLD_SCRATCH)',start)]
    start=source.index('#if defined(RE4DC_DRAW_FALLBACK_AUDIT)',source.index('void snap_diag()'))
    # The first occurrence is the actual rows; page reset uses a combined #if.
    rows=source[start:source.index('#endif',start)+len('#endif')]
    assert 'dfa26::format_line' in rows
    start=source.index('void link_send_parts(')
    parts=source[start:source.index('void link_telemetry()',start)]
    start=source.index('void link_telemetry()')
    telemetry_function=source[start:source.index('void link_log()',start)]
    fixture=out/'qa_contract.cpp'
    fixture.write_text(r'''#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <climits>
#include <string>
#include <vector>
#include "draw_fallback_audit.h"
#include "draw_fallback_link26.hpp"
static char g_diag[7168];
static std::vector<std::string> sent;
static struct { unsigned seq,cost_last; void (*game)(); } g_link{UINT_MAX,UINT_MAX,nullptr};
static unsigned g_diag_page=0,snapshots=0,game_calls=0;
static int g_diag_stats=0;
static re4dc::dfa26::Telemetry<sizeof(g_diag)+160> g_fallback_telemetry;
static void snap_diag(){
    ++snapshots;g_diag_page=0;
    std::strcpy(g_diag,"RE4DCQA1\nfixture=rows\n");g_diag_stats=int(std::strlen(g_diag));
}
static void re4dc_qalink_counters(unsigned* tx,unsigned* rx,unsigned* dr,unsigned* q){
    *tx=*rx=*dr=*q=UINT_MAX;
}
static unsigned re4dc_qalink_bulk_skips(){return UINT_MAX;}
static unsigned long long timer_ms_gettime64(){return UINT_MAX;}
static void link_send_text(const char* p,int n){assert(n>=0 && n<=1200);sent.emplace_back(p,n);}
// Existing part formatter uses an accepting transport. The production bounded
// producer below is separately exercised against link28's 2400-byte cap.
static void re4dc_qalink_send_bulk(const char* p,unsigned n){link_send_text(p,int(n));}
''' + addf + '\nstatic int audit_rows(){int a=0;\n' + rows + '\nreturn a;}\n' + parts + telemetry_function + r'''
int main(){
    using namespace re4dc::dfa26;
    Snapshot s{};
    reset();assert(!snapshot(&s));
    hit(TextureShape);assert(!snapshot(&s));
    assert(audit_rows()>0 && std::strstr(g_diag,"collecting complete tick"));
    begin_tick(7,0x103);hit(TextureShape,4);hit(TextureHandleMiss,9);
    assert(!snapshot(&s));end_tick();assert(snapshot(&s));
    assert(s.tick==7 && s.room==0x103 && s.drawn==1 && s.sequence==1);
    assert(s.items[TextureShape]==4 && s.items[TextureHandleMiss]==9);
    begin_tick(8,0x103);hit(TextureShape,17);pause();end_tick();
    assert(snapshot(&s) && s.tick==7 && s.items[TextureShape]==4);
    begin_tick(9,0x103);hit(TextureShape);end_tick();
    assert(snapshot(&s) && s.tick==7);resume();
    begin_tick(10,0x103);decision(false);end_tick();
    assert(snapshot(&s) && s.tick==10 && s.drawn==0 && s.items[TextureShape]==0);
    begin_tick(11,0x104);assert(!snapshot(&s));end_tick();
    assert(snapshot(&s) && s.room==0x104);
    // Every registry entry, maximum decimal fields, saturation and wrap.
    begin_tick(UINT_MAX,0xffff);
    for(unsigned i=0;i<ReasonCount;++i){
        hit(Reason(i),UINT_MAX);hit(Reason(i),1);hit(Reason(i),0);
        assert(std::strlen(label(Reason(i)))<=24);
        assert(*unit(Reason(i)));
    }
    end_tick();assert(snapshot(&s) && s.overflow==1);
    for(unsigned i=0;i<ReasonCount;++i)assert(s.items[i]==UINT_MAX);
    const int n=audit_rows();assert(n>0 && n<int(sizeof(g_diag)));
    assert(n<=int(sizeof(g_diag))-3072); // all new rows fit beside the old QA capacity
    for(unsigned i=0;i<ReasonCount;++i){
        const std::string field=std::string(label(Reason(i)))+"=4294967295";
        assert(std::strstr(g_diag,field.c_str()));
    }
    char row[192];unsigned max_row=0;
    for(unsigned i=0;i<line_count();++i){
        const int k=format_line(i,row,sizeof(row));assert(k>0 && k<192);
        if(unsigned(k)>max_row)max_row=unsigned(k);
    }
    assert(format_line(line_count(),row,sizeof(row))==-1);
    char tiny[2]={'x','y'};assert(format_line(1,tiny,sizeof(tiny))==-1 && tiny[1]==0);
    assert(format_line(0,nullptr,1)==-1 && format_line(0,row,0)==-1);
    unsigned maximum=0,cases=0;
    for(char kind:{'T','D'})for(unsigned len:{0U,1U,1099U,1100U,1101U,7167U,12287U}){
        const std::string input(len,'x');sent.clear();
        link_send_parts(kind,"123456789012345",input.data(),int(input.size()));
        std::string joined;
        for(const auto& d:sent){
            if(d.size()>maximum)maximum=unsigned(d.size());
            const auto split=d.find('\n');assert(split!=std::string::npos);
            joined+=d.substr(split+1);
        }
        assert(joined==input);++cases;
    }
    unsigned retry_cases=0,rejections=0,attempts=0,max_queued=0;
    for(unsigned drain_ms:{50U,300U,2000U})
    for(unsigned len:{0U,1U,1099U,1100U,1101U,7167U,12287U}){
        Telemetry<12448> pending;
        std::string input(len,'\0');
        for(unsigned i=0;i<len;++i)input[i]=char(i%251U);
        std::memcpy(pending.text,input.data(),len);
        assert(!pending.begin(12449U,1,2));
        assert(pending.begin(len,UINT_MAX,UINT_MAX));
        assert(!pending.begin(0,1,2)); // a new sample cannot replace queued parts
        unsigned queued=0,next_part=1;
        std::string joined;
        std::uint64_t last_attempt=0;
        bool had_attempt=false;
        for(std::uint64_t ms=0;pending.pending && ms<=60000U;++ms){
            if(ms && ms%drain_ms==0)queued=0; // drained datagrams, not a policy bypass
            const unsigned previous=pending.offset;
            bool rejected=false;
            const bool accepted=pending.step(ms,[&](const char* bytes,unsigned count){
                ++attempts;
                if(had_attempt)assert(ms-last_attempt>=50U);
                had_attempt=true;last_attempt=ms;
                assert(count<=1200U);
                if(count>maximum)maximum=count;
                // Initial heap refusal, then the exact bulk queue admission cap.
                if(ms<500U || queued+count+2U>2400U){
                    rejected=true;++rejections;return false;
                }
                const std::string d(bytes,count);
                unsigned seq=0,stamp=0,part=0,total=0;
                assert(std::sscanf(d.c_str(),"T %u %u %u/%u",&seq,&stamp,&part,&total)==4);
                assert(seq==UINT_MAX && stamp==UINT_MAX && part==next_part++);
                assert(total==(len?(len+1099U)/1100U:1U));
                const auto split=d.find('\n');assert(split!=std::string::npos);
                joined+=d.substr(split+1);
                queued+=count+2U;if(queued>max_queued)max_queued=queued;
                return true;
            });
            if(rejected)assert(!accepted && pending.offset==previous);
            if(!accepted)assert(pending.offset==previous);
        }
        assert(!pending.pending && joined==input && queued<=2400U);
        assert(!pending.step(60001U,[](const char*,unsigned){assert(false);return true;}));
        // Disconnect discards the pending snapshot; reconnect uses fresh identity.
        assert(pending.begin(len,42,12));pending.cancel();assert(!pending.pending);
        pending.text[0]='z';assert(pending.begin(1,43,13));
        assert(pending.step(0,[](const char* bytes,unsigned count){
            assert(std::string(bytes,count)=="T 43 13 1/1\nz");return true;
        }));
        ++retry_cases;
    }
    assert(rejections>0 && attempts>retry_cases && max_queued<=2400U);
    begin_tick(0,0xffff);end_tick();assert(snapshot(&s) && !s.overflow);
    for(unsigned i=0;i<ReasonCount;++i)assert(!s.items[i]);
    reset();assert(!snapshot(&s));
    // Actual telemetry function preserves a long-viewed menu page, and does
    // not refresh either game state or diagnostic bytes while parts are pending.
    g_link.game=[](){++game_calls;};
    g_diag_page=7;link_telemetry();
    assert(g_diag_page==7 && snapshots==1 && game_calls==1 && g_fallback_telemetry.pending);
    const std::string frozen(g_fallback_telemetry.text,g_fallback_telemetry.length);
    g_diag_page=3;link_telemetry();
    assert(g_diag_page==3 && snapshots==1 && game_calls==1);
    assert(frozen==std::string(g_fallback_telemetry.text,g_fallback_telemetry.length));
    assert(g_fallback_telemetry.step(0,[](const char*,unsigned){return true;}));
    assert(!g_fallback_telemetry.pending);
    g_diag_page=2;link_telemetry();
    assert(g_diag_page==2 && snapshots==2 && game_calls==2 && g_fallback_telemetry.sequence==1);
    std::printf("{\"status\":\"PASS\",\"reasons\":%u,\"row_bytes\":%d,\"max_row_bytes\":%u,\"framing_cases\":%u,\"backpressure_cases\":%u,\"bulk_attempts\":%u,\"bulk_refusals\":%u,\"max_queued_bytes\":%u,\"max_datagram_bytes\":%u,\"snapshot_bytes\":%u}\n",
        unsigned(ReasonCount),n,max_row,cases,retry_cases,attempts,rejections,max_queued,maximum,unsigned(sizeof(Snapshot)));
}
''')
    command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
             '-DRE4DC_DRAW_FALLBACK_AUDIT=1','-I'+str(header.parent),str(fixture),str(core),'-o',str(out/'qa_contract')]
    if args.sanitize:command[2:2]=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    subprocess.run(command,check=True,capture_output=True)
    env=None
    if args.sanitize:
        import os
        env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1')
    result=json.loads(subprocess.check_output([str(out/'qa_contract')],text=True,env=env))
    result.update(sanitized=args.sanitize,scope=__doc__,source_sha256={
        str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [qa,core,header,telemetry,Path(__file__),*sorted(header.parent.glob('draw_fallback_*.def'))]})
    (out/'qa-contract.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
