// Synthetic lifecycle oracle for the actual census core, not a copied model.
#include "world_census24.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <vector>
using namespace re4dc::wc24;
static uint64_t clock_value;
static uintptr_t thread_value=1;
static unsigned identity_value[7];
static std::vector<std::string> lines;
extern "C" uint64_t re4dc_wc24_test_clock(){return clock_value;}
extern "C" uintptr_t re4dc_wc24_test_thread(){return thread_value;}
extern "C" void re4dc_wc24_test_log(const char* line){lines.emplace_back(line);clock_value+=37;}
extern "C" void re4dc_wc24_identity(unsigned out[7]){memcpy(out,identity_value,sizeof(identity_value));}
static void advance(unsigned us){clock_value+=us;}
static void fresh(){reset();clock_value=0;thread_value=1;memset(identity_value,0,sizeof(identity_value));lines.clear();}
static Snapshot get(){Snapshot s{};assert(snapshot(&s));return s;}
static void empty_draw(unsigned tick,unsigned room=0x101){
    begin_tick(tick,room);decision(true);scene_finished();advance(100);end_tick();
}

static void denominators_and_exclusive_scopes(){
    fresh();
    for(unsigned tick=0;tick<600;++tick){
        begin_tick(tick,0x101);
        const bool draw=(tick&1)!=0;decision(draw);
        if(draw){
            {
                Scope world(NearOP,Other);
                {Scope select(Selection);advance(10);count(PickedIndexed,2);count(PickedPlain);count(PickedEmpty);}
                {Scope transform(Transform);advance(20);count(Transformed,8);}
                {Scope clip(Clip);advance(5);{Scope submit(Submit);advance(3);count(Corners,3);}}
                {Scope header(HeaderMaterial);advance(2);uint32_t h[4]={1,2,3,4};
                    submitted_header(h);submitted_header(h);h[3]=5;submitted_header(h);}
                {Scope submit(Submit);advance(7);count(Corners,7);count(StripInputs,12);}
                advance(4);
                // Background/IRQ-related callers cannot alter game-thread state.
                thread_value=2;{Scope other(FarTR,Transform);count(Transformed,9999);}
                {WaitScope unrelated(PvrWait);}thread_value=1;
            }
            {WaitScope wait(PvrWait);advance(11);{WaitScope nested(PvrWait);advance(3);}advance(2);}
            {WaitScope wait(VblankWait);advance(13);}
            {WaitScope wait(PaceWait);advance(17);}
            scene_finished();scene_finished(); // several scenes, one drawn tick
            decision_posted(true);
            pvr_event(1);pvr_event(1);pvr_event(6);pvr_event(7);pvr_event(8);
        }else{Scope world(NearOP,Selection);advance(1);}
        end_tick();advance(100); // tail/loop time belongs to this completed tick
    }
    begin_tick(600,0x101);
    Snapshot s=get();
    assert(s.sequence==1&&s.ticks==600&&s.drawn==300&&s.draw_attempts==300&&s.skipped==300);
    assert(s.scenes==600&&s.present_requests==300&&!s.discard_requests);
    assert(s.first_tick==0&&s.last_tick==599&&s.wall_us==89400&&s.max_tick_us==197);
    const uint64_t expected[PhaseCount]={3300,6000,1500,600,3000,1200};
    for(unsigned phase=0;phase<PhaseCount;++phase)assert(s.phase_us[NearOP][phase]==expected[phase]);
    assert(s.wait_us[PvrWait]==4800&&s.wait_us[VblankWait]==3900&&s.wait_us[PaceWait]==5100);
    assert(s.residual_us==60000&&!s.errors);
    const uint64_t counts[CounterCount]={2400,3000,900,600,600,300,300,3600};
    for(unsigned c=0;c<CounterCount;++c)assert(s.counters[NearOP][c]==counts[c]);
    for(unsigned p=1;p<PathCount;++p)for(unsigned c=0;c<CounterCount;++c)assert(!s.counters[p][c]);
    assert(s.presentation.flips==300&&s.presentation.intervals==299&&s.presentation.vblanks==600);
    assert(s.presentation.interval_us==298*299&&s.presentation.max_fields==2&&!s.presentation.gaps_over_two_fields);
    assert(lines.size()==1&&lines[0].size()<240&&lines[0].find("summary_overflow")==std::string::npos);
    char row[192];
    for(unsigned i=0;i<line_count();++i){const int n=format_line(i,row,sizeof(row));assert(n>=0&&n<int(sizeof(row)));}
    // The logger's 37 us are charged to the following measured interval.
    decision(true);scene_finished();end_tick();
    for(unsigned tick=601;tick<900;++tick)empty_draw(tick);
    begin_tick(900,0x101);s=get();assert(s.sequence==2&&s.wall_us==29900+37&&s.residual_us==29900+37);
    assert(lines.size()==2);
}

static void identity_pause_and_partial_ticks(){
    fresh();for(unsigned tick=0;tick<300;++tick)empty_draw(tick);begin_tick(300,0x101);
    assert(get().sequence>=1);const unsigned old_sequence=get().sequence;
    {Scope world(NearOP,Transform);advance(200);pause();advance(1000000);resume();}
    assert(get().sequence==old_sequence); // sealed page survives menu pause
    // A page flip between leaving the menu and the next complete tick is not
    // part of either collection. Resume must leave the GPU collector unarmed.
    pvr_event(1);pvr_event(6);pvr_event(7);pvr_event(8);
    empty_draw(301); // paused partial tick never reaches the new collection
    for(unsigned tick=302;tick<601;++tick)empty_draw(tick);
    begin_tick(601,0x101);Snapshot s=get();
    assert(s.ticks==300&&s.drawn==300&&s.wall_us==30000&&!s.errors);
    assert(!s.presentation.vblanks&&!s.presentation.flips&&!s.presentation.render_starts&&!s.presentation.render_dones);
    ++identity_value[6];begin_tick(602,0x101);assert(!snapshot(nullptr));
    for(unsigned tick=603;tick<903;++tick)empty_draw(tick);
    begin_tick(903,0x101);s=get();assert(s.identity[7]==1&&s.ticks==300);
    begin_tick(904,0x103);assert(!snapshot(nullptr)); // room epoch cannot reuse old numbers
    reset();assert(!snapshot(nullptr));
}

static void faults_overflow_and_cadence(){
    fresh();uint32_t stale=0;
    for(unsigned tick=0;tick<300;++tick){
        begin_tick(tick,0x101);decision(true);
        if(!tick){
            stale=enter(NearTR,Transform);count(Transformed,UINT32_MAX);count(Transformed,1);fault();
            advance(10); // deliberately leak scope: next begin must flag it
        }else if(tick==1){leave(stale);}
        scene_finished();decision_posted(false);
        pvr_event(1);pvr_event(1);if(tick==1){pvr_event(1);pvr_event(1);}
        advance(100);pvr_event(8);end_tick();
    }
    begin_tick(300,0x101);Snapshot s=get();
    assert(s.errors==3); // overflow, explicit unsupported path, unbalanced scope
    assert(s.counters[NearTR][Transformed]==UINT32_MAX);
    assert(s.discard_requests==300&&s.presentation.flips==300); // independent sources
    assert(s.presentation.gaps_over_two_fields==1&&s.presentation.max_fields==4);
    char tiny[40];summary(tiny,sizeof(tiny));assert(tiny[sizeof(tiny)-1]==0||strlen(tiny)<sizeof(tiny));
}

int main(){
    denominators_and_exclusive_scopes();
    identity_pause_and_partial_ticks();
    faults_overflow_and_cadence();
    puts("PASS: drawn/tick denominators, exclusive nesting, owner thread, emitted counts, actual-flip cadence, identity/pause, errors, logging attribution");
}
