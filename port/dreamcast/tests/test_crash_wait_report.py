#!/usr/bin/env python3
"""Exercise the actual stopped-screen formatter with synthetic KOS wait states.

Includes the complete show() body, a bounded framebuffer and a mapped fake
SH4 stack. This verifies that timed-main diagnostics and overlay relocation
context survive the 640x480 photograph layout; it does not reproduce a hang.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    screen = (ROOT / "port/dreamcast/game/platform/crash_screen.cpp").read_text()
    bridge = (ROOT / "port/dreamcast/game/sscrn_bridge.cpp").read_text()
    os_source = (ROOT / "port/dreamcast/game/platform/os.cpp").read_text()
    bodies = "\n".join(function(screen, s) for s in (
        "int collect(kthread_t* t, void*)", "void wait_detail(",
        "bool trace_waiter(", "void show("))
    brief = function(bridge, 'extern "C" void re4dc_subscreen_brief(')
    signal = function(os_source, "s32 OSSignalSemaphore(OSSemaphore* sem)")
    snapshot = screen[screen.index('struct MissingSnapshot {'):screen.index('void capture_missing(')]
    fixture = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <sys/mman.h>
#define RE4DC_SUBSCREEN_OVL 1
using u32 = unsigned;
constexpr unsigned kDescriptorBytes=64, kSsAramSize=0x300000;
bool swapped=false;
u32 area_lo=0x8c814940, ovl_image_bytes=126592;
extern "C" void re4dc_subscreen_brief(char*, unsigned) __attribute__((weak));
''' + brief + r'''
enum { STATE_WAIT=3, STATE_RUNNING=1, STATE_FINISHED=5, STATE_ZOMBIE=6 };
struct Context { unsigned long pc=0x8c2218fa,pr=0x8c112233,r[16]={}; };
struct kthread_t {
    int tid=0,state=STATE_WAIT;
    const char *label="", *wait_msg="thd_sleep";
    void* wait_obj=(void*)0xffffffff;
    uint64_t wait_timeout=150000;
    Context context;
};
kthread_t kernel, audio, game, reaper, watchdog;
kthread_t* thd_current=&watchdog;
std::vector<kthread_t*> all;
int thd_each(int(*cb)(kthread_t*,void*),void* p){for(auto* t:all)cb(t,p);return 0;}
constexpr int kGW=12,kGH=24;
int kW=640,kH=480,kCols=53,kRows=20;
struct Video { int width=640,height=480; } video;
Video* vid_mode=&video;
bool g_ready=true;
int g_shown=0,g_nthreads=0;
kthread_t* g_threads[24];
unsigned short framebuffer[640*480];
unsigned short* g_fb;
#define PVR_RAM_BASE ((uintptr_t)framebuffer)
#define PVR_GET(x) 0u
#define PVR_FB_ADDR 0
#define PVR_RAM_SIZE 0x800000u
unsigned long re4dc_stage=0x2003,re4dc_log_head=0;
constexpr unsigned kLogSize=0x10000;
char re4dc_logbuf[kLogSize]={};
unsigned re4dc_ui_frame(){return 15299;}
uint64_t timer_ms_gettime64(){return 100000;}
void re4dc_task_brief(char* out,unsigned size,const void*){snprintf(out,size," 0:02/21");}
std::vector<std::string> rows;
void put_text(int,int row,const char* text,unsigned short){
    assert(row>=0 && row<kRows);
    rows.push_back(std::string(text).substr(0,kCols));
}
''' + snapshot + r'''
struct pvr_stats_t {unsigned frame_count, vbl_count;};
int pvr_get_stats(pvr_stats_t* out){out->frame_count=17;out->vbl_count=1900;return 0;}
''' + bodies + r'''
#define RE4DC_CRASH_SCREEN 1
using s32=int;
struct OSThread {} g_mainThread, taskThread;
OSThread* threadOf(kthread_t* t){return t==&kernel?&g_mainThread:&taskThread;}
struct OSSemaphore { int count=0; };
using semaphore_t=OSSemaphore;
int re4dc_crashtest_block=0, native_sleeps=0, never_waits=0, wakes=0;
int irq_disable(){return 0;}
void irq_restore(int){}
void sem_init(semaphore_t* sem,int n){sem->count=n;}
void sem_wait(semaphore_t*){++never_waits;}
void thd_sleep(int ms){assert(ms==120000);++native_sleeps;}
void re4dc_log(const char*,...){}
void genwait_wake_one(OSSemaphore*){++wakes;}
void afterWake(){}
''' + signal + r'''
bool has(const std::string& text){for(const auto& row:rows)if(row==text)return true;return false;}
bool prefix(const std::string& text){for(const auto& row:rows)if(row.rfind(text,0)==0)return true;return false;}
int main(){
    char text[96];
    kernel.tid=1;kernel.label="[kernel]";
    audio.tid=5;audio.label="re4dc-au";
    game.tid=121;game.label="re4-task";game.wait_timeout=0;game.wait_msg="os-sema";
    reaper.tid=2;reaper.label="[reaper]";reaper.wait_timeout=0;
    watchdog.tid=7;watchdog.label="re4crash";watchdog.state=STATE_RUNNING;
    assert(trace_waiter(&kernel) && !trace_waiter(&audio) && trace_waiter(&game));
    assert(!trace_waiter(&reaper) && !trace_waiter(&watchdog));
    wait_detail(text,sizeof(text),&kernel,100000);
    assert(std::string(text)=="main pr 8c112233 wait +50000ms");
    wait_detail(text,sizeof(text),&kernel,200000);
    assert(std::string(text)=="main pr 8c112233 wait -50000ms");
    kernel.wait_timeout=0;
    wait_detail(text,sizeof(text),&kernel,200000);
    assert(std::string(text)=="main pr 8c112233 wait untimed");
    kernel.wait_timeout=UINT64_MAX;
    wait_detail(text,sizeof(text),&kernel,0);
    assert(std::string(text)=="main pr 8c112233 wait +18446744073709551615ms");
    assert(strlen(text)<=53);
    kernel.wait_timeout=150000;
    re4dc_subscreen_brief(text,sizeof(text));assert(!text[0]);
    swapped=true;
    re4dc_subscreen_brief(text,sizeof(text));
    assert(std::string(text)=="ss area 8c814940 overlay 8c814980+1ee80");
    char sentinel='x';re4dc_subscreen_brief(&sentinel,0);assert(sentinel=='x');
    void* memory=mmap((void*)0x8c010000,4096,PROT_READ|PROT_WRITE,
                      MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    assert(memory==(void*)0x8c010000);
    *(unsigned short*)0x8c010100=0x400b;  // jsr @r0, return address +4
    auto* stack=(unsigned long*)0x8c010200;
    for(unsigned i=0;i<8;++i)stack[i]=0x8c010104;
    kernel.context.r[15]=(unsigned long)stack;game.context.r[15]=(unsigned long)stack;
    all={&game,&audio,&watchdog,&reaper,&kernel};
    show("HANG","no new frame for 30 s",false);
    assert(has("ss area 8c814940 overlay 8c814980+1ee80"));
    assert(has("main pr 8c112233 wait +50000ms"));
    assert(prefix("bt1 ") && prefix("bt121 ") && !prefix("bt5 ") && !prefix("bt2 "));
    for(const auto& row:rows)if(row.rfind("bt",0)==0){
        auto at=row.find(' ');
        while(at!=std::string::npos){assert(row.size()-at>=7);at=row.find(' ',at+1);}
    }
    rows.clear();g_shown=0;swapped=false;kernel.wait_timeout=0;
    show("HANG","no new frame for 30 s",false);
    assert(has("main pr 8c112233 wait untimed") && !prefix("ss area "));
    assert(prefix("bt1 ") && prefix("bt121 "));
    rows.clear();g_shown=0;g_missing.valid=g_missing.pvr_valid=true;
    g_missing.ui=15299;g_missing.frames=12;g_missing.vbl=100;g_missing.pending=1;g_missing.ta_ready=-1;
    g_missing.vtx[0]=0x100000;g_missing.vtx[1]=0x180000;g_missing.vtx[2]=0x300000;g_missing.isp=0x400000;
    g_missing.opb[0]=0x8000;g_missing.opb[1]=0x3000;g_missing.opb[2]=0x10000;
    show("MISSING","native stream completion fence failed",false);
    assert(has("MISSING native stream completion fence failed"));
    assert(has("snap ui15299 pending1 ta-1") && has("pvr 12/17 vb 100/1900"));
    assert(has("vtx 100000/180000/300000 isp 400000"));
    assert(has("opb 008000/003000/010000 (pos raw)"));
    assert(prefix("bt1 ") && prefix("bt121 "));
    OSSemaphore sem;
    thd_current=&kernel;assert(OSSignalSemaphore(&sem)==0);
    thd_current=&game;assert(OSSignalSemaphore(&sem)==1);
    assert(!native_sleeps && !never_waits && wakes==2);
    re4dc_crashtest_block=1;thd_current=&kernel;
    OSSignalSemaphore(&sem);assert(re4dc_crashtest_block==1 && !never_waits);
    thd_current=&game;OSSignalSemaphore(&sem);
    assert(!re4dc_crashtest_block && never_waits==1 && !native_sleeps);
    re4dc_crashtest_block=2;OSSignalSemaphore(&sem);
    assert(re4dc_crashtest_block==2 && !native_sleeps);
    thd_current=&kernel;OSSignalSemaphore(&sem);
    assert(!re4dc_crashtest_block && native_sleeps==1 && never_waits==1);
    OSSignalSemaphore(&sem);assert(native_sleeps==1 && sem.count==7 && wakes==7);
    assert(munmap(memory,4096)==0);
    puts("PASS: timed/overdue/untimed reports, overlay context, screen bounds, full addresses, normal signals and both one-shot test modes");
}
'''
    with tempfile.TemporaryDirectory(prefix="re4dc-crash-report-") as tmp:
        cpp, binary = Path(tmp) / "fixture.cpp", Path(tmp) / "fixture"
        cpp.write_text(fixture)
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
