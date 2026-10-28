#!/usr/bin/env python3
"""Exercise the actual QA protocol block against bounded synthetic providers.

Extracts source without repairing or normalizing it. Rendering, KOS scheduling,
network delivery and real disc fixtures are outside this host contract.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def function(source, name):
    match = re.search(r'(?m)^(?:[\w*]+\s+)+' + re.escape(name) + r'\([^\n;]*\)\s*\{', source)
    assert match, name
    start = match.start()
    at = source.index('{', start)
    depth = 0
    mode = 'code'
    while at < len(source):
        c = source[at]
        nxt = source[at:at+2]
        if mode == 'line':
            if c == '\n': mode = 'code'
        elif mode == 'comment':
            if nxt == '*/': mode = 'code'; at += 1
        elif mode in ('"', "'"):
            if c == '\\': at += 1
            elif c == mode: mode = 'code'
        elif nxt == '//': mode = 'line'; at += 1
        elif nxt == '/*': mode = 'comment'; at += 1
        elif c in ('"', "'"): mode = c
        elif c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if not depth: return source[start:at+1] + '\n'
        at += 1
    raise AssertionError(name)


PRELUDE = r'''
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <strings.h>
#include <cctype>
#include <cmath>
#include <climits>
#include <cstdint>
#include <deque>
#include <limits>
#include <random>
#include <string>
#include <vector>
#include "qa_link_review28.hpp"
#define RE4DC_QA_LINK_REVIEW28 1
#define RE4DC_QA_NAME "HOST28"
static char g_diag[DIAG_CAPACITY];
static unsigned g_diag_page=0;
static int g_diag_len=0,g_diag_stats=0;
static unsigned g_flags=0,re4dc_qa_shore_far_mm=0;
static char g_path[128];
static struct { char file[32],label[48]; } g_p[2]={{"r103.txt","BARN"},{"r101.txt","CROSS"}};
static int g_np=2;
static char re4dc_logbuf[65536];
static volatile unsigned long re4dc_log_head=0;
static uint64_t clock_ms=1000;
static bool link_up=true,heap_ok=true,max_counters=false;
static unsigned queued=0,skips=0,snapshots=0,game_calls=0,commands=0,maximum=0;
static std::vector<std::string> sent;
static std::deque<std::string> incoming;
static std::string fixture="clock tick\nwait 3\ngoto 0 0\n";
static std::string diag_source="RE4DCQA1\nfps=30.0\nms10=20\n";
static void snap_diag(){
    ++snapshots;g_diag_page=0;
    const unsigned n=std::min<unsigned>(diag_source.size(),sizeof(g_diag)-1);
    memcpy(g_diag,diag_source.data(),n);g_diag[n]=0;g_diag_stats=g_diag_len=int(n);
}
static void load_presets(){}
static void re4dc_log(const char*,...){}
static unsigned re4dc_quality_speed(){return 0;}
static void re4dc_speed_cycle(){}
static const char* speed_name(){return "OFF";}
static uint64_t timer_ms_gettime64(){return clock_ms;}
static uint64_t timer_us_gettime64(){return clock_ms*1000;}
static int re4dc_fixture_read(const char*,char* out,unsigned max){
    const unsigned n=std::min<unsigned>(max,fixture.size());memcpy(out,fixture.data(),n);return int(n);
}
static void re4dc_qalink_config(const char*,const char*,unsigned,unsigned){}
static int re4dc_qalink_start(){link_up=true;return 1;}
static void re4dc_qalink_stop(){link_up=false;}
static int re4dc_qalink_wanted(){return link_up;}
static int re4dc_qalink_up(){return link_up;}
static void re4dc_qalink_state_text(char* out,unsigned n){snprintf(out,n,"%s",link_up?"UP":"OFF");}
static void re4dc_qalink_counters(unsigned* tx,unsigned* rx,unsigned* dr,unsigned* q){*tx=*rx=*dr=UINT_MAX;*q=max_counters?UINT_MAX:queued;}
static unsigned re4dc_qalink_bulk_skips(){return UINT_MAX;}
static void re4dc_qalink_review_counters(unsigned* rx,unsigned* stall){*rx=*stall=UINT_MAX;}
static int re4dc_qalink_send(const void* data,unsigned n){
    assert(n<=1200);maximum=std::max(maximum,n);
    if(queued+n+2>4096)return 0;
    queued+=n+2;sent.emplace_back(static_cast<const char*>(data),n);return 1;
}
static int re4dc_qalink_send_bulk(const void* data,unsigned n){
    assert(n<=1200);maximum=std::max(maximum,n);
    if(!heap_ok || queued+n+2>2400){++skips;return 0;}
    return re4dc_qalink_send(data,n);
}
static int re4dc_qalink_recv(char* out,unsigned max){
    if(incoming.empty())return -1;
    const auto s=incoming.front();incoming.pop_front();assert(s.size()<max);
    memcpy(out,s.c_str(),s.size()+1);++commands;return int(s.size());
}
'''

TEST = r'''
static unsigned cases=0;
static int command(const std::string& s){std::vector<char> b(s.begin(),s.end());b.push_back(0);return link_command(b.data(),false);}
static void reset(){
    g_link={};g_drv={};g_review_snapshot={};g_review_log_started=false;
    link_up=heap_ok=true;max_counters=false;queued=skips=snapshots=game_calls=commands=0;clock_ms=1000;
    sent.clear();incoming.clear();re4dc_log_head=0;g_diag_page=7;
    diag_source="RE4DCQA1\nfps=30.0\nms10=20\n";
    g_link.cfg_read=true;g_link.next_ms=UINT_MAX;
}
static std::string body(const std::string& packet){const auto n=packet.find('\n');assert(n!=std::string::npos);return packet.substr(n+1);}
int main(){
    using re4dc::ql28::Snapshot;
    // Immutable T/D snapshots under actual link28 admission, including heap
    // refusal, slow service, zero bytes, boundary and full diagnostics lengths.
    unsigned retry_cases=0,attempts=0,refusals=0;
    for(char kind:{'T','D'})for(unsigned drain:{50U,300U,2000U})
    for(unsigned n:{0U,1U,1099U,1100U,1101U,3071U,7167U,8191U,12287U}){
        Snapshot<12672> msg;std::string input(n,'x');
        for(unsigned i=0;i<n;++i)input[i]=char(i%251U);
        memcpy(msg.text,input.data(),n);
        assert(!msg.begin('X',"id",n,1,2));
        assert(!msg.begin('D',"1234567890123456",n,1,2));
        assert(!msg.begin(kind,"id",12673U,1,2));
        assert(msg.begin(kind,"123456789012345",n,UINT_MAX,UINT_MAX));
        assert(!msg.begin(kind,"id",0,0,0));
        std::string joined;unsigned q=0,next=1;uint64_t last=0;bool tried=false;
        for(uint64_t ms=0;msg.pending && ms<90000;++ms){
            if(ms && ms%drain==0)q=0;
            const unsigned before=msg.offset;
            bool rejected=false;
            msg.step(ms,[&](const char* bytes,unsigned count){
                ++attempts;assert(count<=1200);maximum=std::max(maximum,count);
                if(tried)assert(ms-last>=50);tried=true;last=ms;
                if(ms<500 || q+count+2>2400){++refusals;rejected=true;return false;}
                const std::string packet(bytes,count);unsigned part,total;
                if(kind=='T'){
                    unsigned seq,stamp;assert(sscanf(packet.c_str(),"T %u %u %u/%u",&seq,&stamp,&part,&total)==4);
                    assert(seq==UINT_MAX && stamp==UINT_MAX);
                }else{
                    char id[32];assert(sscanf(packet.c_str(),"D %31s %u/%u",id,&part,&total)==3);
                    assert(!strcmp(id,"123456789012345"));
                }
                assert(part==next++ && total==(n?(n+1099)/1100:1));
                joined+=body(packet);q+=count+2;return true;
            });
            if(rejected)assert(msg.offset==before);
        }
        assert(!msg.pending && joined==input);++retry_cases;
        assert(msg.begin(kind,"id",n,1,2));msg.cancel();assert(!msg.pending && msg.offset==0);
        ++cases;
    }
    // Actual producer: all current diagnostic capacities, worst decimal link
    // fields and drive status. No cursor can use snprintf's unwritten length.
    reset();g_link.game=[](){++game_calls;};max_counters=true;
    diag_source="RE4DCQA1\n"+std::string(sizeof(g_diag)-11,'r')+"\n";
    g_drv.room=UINT_MAX;g_drv.x=-10000000;g_drv.y=10000000;g_drv.z=-10000000;
    g_drv.ang=-1000;g_drv.cam=1000;g_drv.cancels=UINT_MAX;
    link_telemetry();assert(g_review_snapshot.pending && g_review_snapshot.kind=='T');
    assert(g_review_snapshot.length<=sizeof(g_review_snapshot.text));
#if RE4DC_DRAW_FALLBACK_AUDIT || RE4DC_DRAW_SETUP_AUDIT || RE4DC_ACTOR_LIGHT_FAST_ONLY
    assert(g_diag_page==7);
#endif
    const std::string saved(g_review_snapshot.text,g_review_snapshot.length);
    assert(saved.find("rxdrop=4294967295 stall=4294967295")!=std::string::npos);
    assert(saved.find("drv room=")!=std::string::npos);
    link_telemetry();assert(snapshots==1 && game_calls==1);
    assert(saved==std::string(g_review_snapshot.text,g_review_snapshot.length));++cases;
    // A DIAG command preempts T exactly once, and another DIAG cannot overwrite
    // its data or identifier. Commands run before the next queued snapshot part.
    reset();g_link.game=[](){++game_calls;};link_telemetry();
    assert(g_review_snapshot.kind=='T');
    command("diag1 DIAG");assert(g_review_snapshot.kind=='D');
    const auto diag=std::string(g_review_snapshot.text,g_review_snapshot.length);
    const unsigned old_snapshots=snapshots;
    command("diag2 DIAG");assert(sent.back().find("A diag2 ERR DIAG busy")==0);
    assert(snapshots==old_snapshots && !strcmp(g_review_snapshot.id,"diag1"));
    assert(diag==std::string(g_review_snapshot.text,g_review_snapshot.length));
    incoming.push_back("ping1 PING hello");sent.clear();link_pump(false);
    assert(commands==1 && sent.front().find("A ping1 OK PONG hello")==0);
    assert(sent.back().find("D diag1 ")==0);++cases;
    // A full-size DIAG is streamed without losing parts to the 4KiB ring or
    // 2400-byte bulk cap. A failed attempt doesn't complete the request.
    reset();diag_source="RE4DCQA1\n"+std::string(sizeof(g_diag)-10,'z');command("full DIAG");
    const auto full=std::string(g_review_snapshot.text,g_review_snapshot.length);
    std::string joined;size_t seen=0;
    for(unsigned tick=0;g_review_snapshot.pending && tick<2000;++tick){
        if(tick%20==0)queued=0;
        clock_ms+=50;link_pump(false);
        while(seen<sent.size()){if(sent[seen][0]=='D')joined+=body(sent[seen]);++seen;}
    }
    assert(!g_review_snapshot.pending && joined==full);++cases;
    // Explicit diagnostics use allocation-free TX even while bulk telemetry
    // is denied by the KOS floor, but still reserve at most2400 queued bytes.
    reset();heap_ok=false;link_telemetry();link_pump(false);
    assert(g_review_snapshot.pending && sent.empty());
    command("low DIAG");link_pump(false);
    assert(!g_review_snapshot.pending && sent.back().find("D low ")==0);++cases;
    reset();command("queued DIAG");queued=2400;link_pump(false);
    assert(g_review_snapshot.pending && sent.empty());
    queued=0;clock_ms+=50;link_pump(false);
    assert(!g_review_snapshot.pending && sent.back().find("D queued ")==0);++cases;
    // Log retention: a denied admission keeps its sequence/cursor; later
    // overflow and budget pruning are counted when the newest bytes are sent.
    reset();memset(re4dc_logbuf,'a',sizeof(re4dc_logbuf));re4dc_log_head=1000;
    heap_ok=false;link_log();assert(!g_review_log_started && g_link.log_seq==0 && g_link.log_sent==0);
    heap_ok=true;link_log();assert(g_link.log_seq==1 && g_link.log_sent==1000);
    assert(sent.back().find("L 1 360\n")==0 && body(sent.back()).size()==640);
    re4dc_log_head=1100;heap_ok=false;link_log();assert(g_link.log_sent==1000);
    re4dc_log_head=100000;queued=0;heap_ok=true;link_log();
    assert(g_link.log_seq==2 && g_link.log_sent==100000 && sent.back().find("L 2 98360\n")==0);++cases;
    // Up to1800 actual recorded ticks: percentile/mean are unchanged even for
    // descending input (the old quadratic worst case). Compare an independent
    // std::sort result, never a copy of the new implementation.
    for(unsigned n:{1U,2U,30U,128U,300U,1800U}){
        reset();command("rec RECORD "+std::to_string(n));sent.clear();
        uint64_t t=100;record_tick(t);std::vector<unsigned> expected;
        for(unsigned i=0;i<n;++i){const unsigned us=1000+n-i;t+=us;expected.push_back(us);queued=0;record_tick(t);}
        std::sort(expected.begin(),expected.end());
        assert(g_link.rec_n==n && g_link.rec_left==0);
        assert(std::equal(expected.begin(),expected.end(),g_link.rec_us));
        unsigned long long sum=0;for(unsigned v:expected)sum+=v;
        char check[200];snprintf(check,sizeof(check),"RECORD ticks=%u mean_us=%u p50_us=%u p99_us=%u max_us=%u",n,
            unsigned(sum/n),expected[n/2],expected[(n*99)/100],expected.back());
        assert(sent.back().find(check)!=std::string::npos);++cases;
    }
    std::mt19937 rng(28);unsigned sort_cases=0;
    for(unsigned n:{0U,1U,2U,3U,4U,5U,30U,128U,300U,1800U})for(unsigned pattern=0;pattern<8;++pattern){
        std::vector<unsigned> values(n);
        for(unsigned i=0;i<n;++i)values[i]=pattern==0?i:pattern==1?n-i:pattern==2?0:pattern==3?UINT_MAX:rng();
        if(pattern==5){for(unsigned i=0;i<n;++i)values[i]=i;if(n>1)std::swap(values[n-1],values[n-2]);}
        if(pattern==6){for(unsigned i=0;i<n;++i)values[i]=i;if(n>1)std::swap(values[0],values[n-1]);}
        if(pattern==7){for(unsigned i=0;i<n;++i)values[i]=(i/4)%7;}
        auto expected=values;std::sort(expected.begin(),expected.end());
        re4dc::ql28::sort_ticks(values.data(),n);assert(values==expected);++sort_cases;++cases;
    }
    // Malformed coordinate commands never publish NaN/Inf/out-of-range state.
    reset();g_drv.free_now=true;
    for(const char* bad:{"nan","inf","-inf","1e99","10000001","-10000001","nope","3oops"}){
        command(std::string("bad GOTO ")+bad+" 0");assert(!g_drv.n && sent.back().find("A bad ERR")==0);++cases;
    }
    for(const char* bad:{"nan","inf","-inf","1e99","10000001","-10000001"}){
        command(std::string("bad TELEPORT POS ")+bad+" 0 0");assert(!g_drv.tpos_pending);++cases;
    }
    command("bad TELEPORT POS 0 0 0 inf");assert(!g_drv.tpos_pending);++cases;
    command("good TELEPORT POS -10000000 0 10000000 1.25");assert(g_drv.tpos_pending);++cases;
    fixture="wait 5\ngoto nan 0\n";command("s SCRIPT bad");assert(!g_drv.n && sent.back().find("A s ERR") ==0);++cases;
    reset();fixture="goto 0 0 1000000000\n";command("s SCRIPT huge");
    assert(g_drv.n==1 && drv_head()->ticks==1800);++cases;
    // Disconnect retires delayed commands, recordings, snapshots and driving.
    reset();g_drv.free_now=true;command("pad PAD A 0 72 100");command("d DIAG");
    g_drv.tpos_pending=true;g_link.pending=LA_TELEPORT;g_link.rec_left=10;link_up=false;
    unsigned short buttons=0; signed char x=0,y=0;unsigned char tr=0;
    re4dc_qa_drive_pad(&buttons,&x,&y,&tr,0);assert(buttons==0 && y==0);
    float pos[4];int angle=0;assert(!re4dc_qa_link_tpos(pos,&angle));
    link_pump(false);assert(!g_drv.n && !g_link.pending && !g_link.rec_left && !g_review_snapshot.pending);++cases;
    reset();g_drv.free_now=true;command("pad PAD A 0 72 100");
    re4dc_qa_drive_feed(0x103,std::numeric_limits<float>::infinity(),0,0,0,0,1);
    assert(!g_drv.n && !g_drv.free_now);++cases;
    printf("{\"status\":\"PASS\",\"cases\":%u,\"snapshot_retry_cases\":%u,\"attempts\":%u,\"refusals\":%u,\"sort_cases\":%u,\"max_datagram\":%u,\"diag_capacity\":%u}\n",
        cases,retry_cases,attempts,refusals,sort_cases,maximum,unsigned(sizeof(g_diag)));
}
'''


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--sanitize',action='store_true')
    args=ap.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    qa=DC/'game/qa_menu.cpp';header=DC/'game/platform/include/qa_link_review28.hpp'
    source=qa.read_text();start=source.index('enum { LA_NONE, LA_TELEPORT')
    end=source.index('\n#endif\n\nvoid draw_screen',start)
    block=source[start:end]
    endpoints='\n'.join(function(source,n) for n in ('re4dc_qa_drive_feed','re4dc_qa_link_tpos','re4dc_qa_drive_pad'))
    fixture=out/'menu_contract.cpp';fixture.write_text(PRELUDE+'\n'+block+'\n'+endpoints+'\n'+TEST)
    profiles=[('plain',3072,0,0,0),('light',4096,0,0,1),('fallback',7168,1,0,0),('setup',8192,0,1,0),('both',12288,1,1,1)]
    results=[]
    for name,capacity,dfa,dsa,light in profiles:
        exe=out/name
        cmd=['g++','-std=c++17','-O1','-g','-Wall','-Wextra',f'-I{header.parent}',f'-DDIAG_CAPACITY={capacity}',
             f'-DRE4DC_DRAW_FALLBACK_AUDIT={dfa}',f'-DRE4DC_DRAW_SETUP_AUDIT={dsa}',f'-DRE4DC_ACTOR_LIGHT_FAST_ONLY={light}',
             str(fixture),'-o',str(exe)]
        if args.sanitize:cmd[1:1]=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        build=subprocess.run(cmd,text=True,capture_output=True);(out/f'{name}-build.log').write_text(build.stdout+build.stderr)
        if build.returncode:raise RuntimeError((out/f'{name}-build.log').read_text())
        env=dict(os.environ)
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0' # ptrace sandbox cannot run LeakSanitizer
        run=subprocess.run([str(exe)],text=True,capture_output=True,env=env);(out/f'{name}-run.log').write_text(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError((out/f'{name}-run.log').read_text())
        result=json.loads(run.stdout);result['profile']=name;results.append(result)
    receipt={'status':'PASS','sanitized':args.sanitize,'leak_sanitizer':False,'scope':'Actual QA protocol block and driving entry points, synthetic bounded transport/clock/diagnostic/disc providers; no KOS, hardware or real assets.',
             'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (qa,header,Path(__file__))},'profiles':results}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
