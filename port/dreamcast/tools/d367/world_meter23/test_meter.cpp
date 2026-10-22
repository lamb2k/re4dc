#define RE4DC_WORLD_DRAW_METER 1
#include "world_draw_meter.h"
#include <cassert>
#include <cstdio>
using namespace re4dc::worldmeter;
namespace re4dc { namespace worldmeter {
static unsigned fake_time=0, recorded=0;
unsigned clock_us() { return fake_time+=17; }
void record(Pass pass, unsigned start, unsigned end, bool ok, float view) {
    assert(pass==Opaque && start==17 && end==34 && ok && view==18750); ++recorded;
}
}}
static const Identity id{0x101,7};
static void passes(Meter& m, unsigned frame, unsigned scale=1, unsigned view=18750) {
    m.pass(frame,Opaque,0,1000*scale,true,view);
    m.pass(frame,PunchThrough,10000,10000+200*scale,true,25000);
    m.pass(frame,Translucent,20000,20000+300*scale,true,25000);
}
static void sample(Meter& m, unsigned f, unsigned cost=1, Identity owner=id, unsigned view=18750) {
    m.begin(f,owner,true,20,false); passes(m,f,cost,view); m.end(f,owner,true,true,20,false);
}
static void fill(Meter& m, unsigned start=1) { for(unsigned i=0;i<kWindow;++i)sample(m,start+i); }
int main() {
    unsigned calls=0;
    const int result=RE4DC_WORLD_MEASURE(Opaque,18750,++calls);
    assert(result==1 && calls==1 && recorded==1);
    Meter m;
    assert(!m.snapshot(id).valid); fill(m);
    auto s=m.snapshot(id); assert(s.valid && s.samples==60 && s.mean_us==1500 && s.peak_us==1500);
    assert(s.pass_us[Opaque]==1000 && s.pass_us[PunchThrough]==200 && s.pass_us[Translucent]==300);
    assert(s.first==1 && s.last==60 && s.room==0x101 && s.generation==7 && s.view_mm==18750);
    // Skipped ticks never call begin/end: frame IDs can have arbitrary gaps, with no zero-cost samples.
    Meter gaps;
    for(unsigned i=0;i<60;++i)sample(gaps,10+i*3);
    s=gaps.snapshot(id); assert(s.samples==60 && s.first==10 && s.last==187 && s.mean_us==1500);
    // The completed window is frozen while a following window fills.
    sample(m,61,2); assert(m.snapshot(id).last==60);
    for(unsigned i=62;i<=120;++i)sample(m,i,2);
    s=m.snapshot(id); assert(s.first==61 && s.last==120 && s.mean_us==3000);
    // Separate optional shell interval is counted once, not as an opaque child again.
    Meter shell;
    for(unsigned i=0;i<60;++i) {
        shell.begin(i,id,true,10,false); passes(shell,i);
        shell.pass(i,FarShell,0,400,true,18750); shell.end(i,id,true,true,10,false);
    }
    s=shell.snapshot(id); assert(s.mean_us==1900 && s.pass_us[FarShell]==400);
    assert(s.shell_frames==60 && s.shell_ok_frames==60);
    assert(s.far_mm[0]==18750 && s.far_mm[1]==25000 && s.far_mm[2]==25000);
    Meter shell_failed;
    for(unsigned i=0;i<60;++i) {
        shell_failed.begin(i,id,true,10,false); passes(shell_failed,i);
        shell_failed.pass(i,FarShell,0,400,false,18750); shell_failed.end(i,id,true,true,10,false);
    }
    s=shell_failed.snapshot(id); assert(s.valid && s.mean_us==1900 && s.shell_frames==60 && !s.shell_ok_frames);
    // Distinct option settings must never mix, even when a room exception uses the same far plane.
    Meter setting;
    for(unsigned i=0;i<60;++i) {
        setting.begin(i,id,true,10,false,2); passes(setting,i); setting.end(i,id,true,true,10,false);
    }
    assert(setting.snapshot(id,2).valid && !setting.snapshot(id,1).valid);
    setting.begin(61,id,true,10,false,1); passes(setting,61); setting.end(61,id,true,true,10,false);
    assert(!setting.snapshot(id,1).valid);
    // A PT/TR plane change also resets a window while opaque far stays identical.
    Meter plane; fill(plane); plane.begin(61,id,true,20,false); passes(plane,61);
    plane.end(61,id,true,true,20,false); assert(plane.snapshot(id).valid);
    plane.begin(62,id,true,20,false); plane.pass(62,Opaque,0,1000,true,18750);
    plane.pass(62,PunchThrough,0,200,true,18750); plane.pass(62,Translucent,0,300,true,18750);
    plane.end(62,id,true,true,20,false); assert(!plane.snapshot(id).valid);
    // Incomplete/no-world/failed/unpresented frames invalidate stale results.
    for(unsigned kind=0;kind<6;++kind) {
        Meter bad; fill(bad);
        bad.begin(61,id,true,20,false);
        if(kind!=0)bad.pass(61,Opaque,0,5,kind!=2,18750);
        if(kind>=2) {
            bad.pass(61,PunchThrough,0,10,true,25000);
            bad.pass(61,Translucent,0,10,true,25000);
        }
        if(kind==4)bad.pass(61,Opaque,0,5,true,18750);
        if(kind==5)bad.pass(61,FarShell,0,5,false,18750);
        bad.end(61,id,kind!=3,true,20,false); assert(!bad.snapshot(id).valid);
    }
    // Room/generation/view changes hide old windows immediately, even before the next full window.
    Meter reset; fill(reset);
    assert(!reset.snapshot({0x100,7}).valid && !reset.snapshot({0x101,8}).valid);
    reset.begin(61,{0x101,8},true,20,false); assert(!reset.snapshot(id).valid);
    reset.reset(); fill(reset); sample(reset,61,1,id,12500); assert(!reset.snapshot(id).valid);
    fill(reset,62); assert(reset.snapshot(id).view_mm==18750);
    reset.begin(122,id,true,20,false); passes(reset,122);
    reset.end(122,{0x100,8},true,true,20,false); assert(!reset.snapshot({0x100,8}).valid);
    // Missing end / unmatched frame boundaries cannot combine partial images.
    Meter missing; fill(missing); missing.begin(61,id,true,20,false); passes(missing,61);
    assert(!missing.snapshot(id).valid);
    missing.begin(62,id,true,20,false); passes(missing,62); missing.end(62,id,true,true,20,false);
    assert(!missing.snapshot(id).valid);
    // Unsigned timer and frame wraps are valid; a changed disc read total marks that frame.
    Meter wrap;
    for(unsigned i=0;i<60;++i) {
        const unsigned f=0xfffffff0u+i;
        wrap.begin(f,id,true,0xffffffffu,i==0);
        wrap.pass(f,Opaque,0xfffffff0u,0x10u,true,25000);
        wrap.pass(f,PunchThrough,0,10,true,25000); wrap.pass(f,Translucent,0,20,true,25000);
        wrap.end(f,id,true,i!=1,i==0?0u:0xffffffffu,false);
    }
    s=wrap.snapshot(id); assert(s.mean_us==62 && s.peak_us==62 && s.last==43);
    assert(s.read_frames==1 && s.stopped_frames==1 && !s.disc_known);
    // Peak is per complete drawn frame, not the largest individual pass.
    Meter peak;
    for(unsigned i=0;i<60;++i)sample(peak,i,i==59?2:1);
    assert(peak.snapshot(id).peak_us==3000 && peak.snapshot(id).mean_us==1525);
    puts("world meter: aggregation, shell, freeze, partial/no-world/failure, identity, view, skip, wrap and read flags PASS");
}
