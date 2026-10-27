#ifndef RE4DC_DRAW_SETUP_AUDIT_H
#define RE4DC_DRAW_SETUP_AUDIT_H

// Build 24. Include only behind RE4DC_DRAW_SETUP_AUDIT so the absent/zero
// translation units remain byte-identical. All clock/PMU hooks are integer-only.
#include <stdint.h>

namespace re4dc { namespace dsa24 {
enum Path { WorldOpaque, WorldTranslucent, Shell, ModelList, FrameBegin,
            RenderOther, OtherDraw, PathCount };
enum Phase { Work, Clip, Submit, PhaseCount };
enum Counter { Models, Parts, TrianglesIn, TrianglesOut, ClipTriangles,
               ClipRebuilds, ClipStrips, XluSubmitted, XluViewOverlap,
               StreamGatherVertices, Unsupported, CounterCount };
enum Error { ClockReversed=1, ScopeOrder=2, Overflow=4, Incomplete=8,
             WrongThread=16, InvalidPhase=32 };
enum { IdentityWords=7, NoToken=UINT32_MAX };

struct Snapshot {
    uint32_t sequence, identity[IdentityWords], first_tick, last_tick;
    uint32_t ticks, drawn, attempts, scenes, skipped, errors;
    uint32_t pm_event, pm_qualification, pm_samples, pm_gaps, pm_wraps;
    uint64_t wall_us, setup_us, render_us, max_tick_us;
    uint64_t phase_us[PathCount][PhaseCount];
    uint64_t phase_events[PathCount][PhaseCount];
    uint64_t counters[PathCount][CounterCount];
    uint64_t outside_us, outside_events;
};

// Complete begin-to-next-begin windows. An identity/menu/reset boundary drops
// unfinished data. "drawn" counts ticks with a finished PVR scene, including a
// later discard; "scenes" separately retains multiple finishes in one tick.
void begin_tick(uint32_t tick, uint32_t room);
void end_tick();
void decision(bool draw_attempt);
void scene_finished();
void pause();
void resume();
void reset();
void begin_setup();
void end_setup();
uint32_t enter(Path, Phase=Work);
uint32_t enter(Phase);
void leave(uint32_t token);
void set_phase(Phase);
void count(Counter, uint32_t amount=1);
void fault(Error);

class Scope {
    uint32_t token_;
    Scope(const Scope&)=delete;
    Scope& operator=(const Scope&)=delete;
public:
    explicit Scope(Path p, Phase q=Work):token_(enter(p,q)){}
    explicit Scope(Phase q):token_(enter(q)){}
    ~Scope(){leave(token_);}
    void phase(Phase q){set_phase(q);}
};

// The actual Render() call, distinct from the legacy "setup" interval which
// also contains Render_before, input/debug and ordering-table clears.
uint64_t render_begin();
void render_end(uint64_t stamp);
class RenderScope {
    uint64_t stamp_;
    Scope scope_;
    RenderScope(const RenderScope&)=delete;
    RenderScope& operator=(const RenderScope&)=delete;
public:
    RenderScope():stamp_(render_begin()),scope_(RenderOther){}
    ~RenderScope(){render_end(stamp_);}
};

int snapshot(Snapshot*);
unsigned line_count();
int format_line(unsigned row, char* out, unsigned capacity);
int summary(char* out, unsigned capacity);
} }
#endif
