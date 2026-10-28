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
               StreamGatherVertices, Unsupported,
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
               // XLU28: on-screen pixels (screen-clamped, front faces of
               // culled parts) per list class, the triangles measured, and
               // the OCC28 coarse depth-grid verdicts for TR/PT triangles.
               AreaOpaque, AreaPunch, AreaTranslucent, AreaTriangles,
               OccTested, OccHidden, OccTestedPixels, OccHiddenPixels, OccLost,
#endif
               CounterCount };
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    uint32_t sampled;  // XLU28: drawn ticks whose areas/OCC were measured
#endif
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

#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
// XLU28 (draw_setup_audit.mk DRAW_SETUP_AUDIT_XLU=1): who sends see-through
// content and how many pixels it covers. Area = triangle area after clamping
// each corner to the 640x480 screen (an estimate, not a rasteriser), front
// faces only for culled parts (backface_emit.hpp's sign rule), strip parity
// kept. Classes: 0 opaque, 1 punch-through, 2 translucent.
namespace x28 {
enum Class { Op, Pt, Tr };
// Areas and OCC run on one drawn tick in DRAW_SETUP_AUDIT_XLU_EVERY (set at
// begin_tick); rows divide by the sampled ticks. Model rows run every tick.
extern bool sample;
[[gnu::always_inline]] inline float cx(float v){return v<0.0f?0.0f:(v>640.0f?640.0f:v);}
[[gnu::always_inline]] inline float cy(float v){return v<0.0f?0.0f:(v>480.0f?480.0f:v);}
// Facing area from clamped corners: sign = +1/-1 strip parity; keep = 0 both
// faces (|area|), +1 cull 1 (area>0 kept), -1 cull 2 (area<0 kept).
[[gnu::always_inline]] inline float facing(float ax,float ay,float bx,float by,float qx,float qy,float sign,float keep){
    const float a=((bx-ax)*(qy-ay)-(by-ay)*(qx-ax))*sign;
    if(keep==0.0f)return __builtin_fabsf(a)*0.5f;
    const float k=a*keep;return k>0.0f?k*0.5f:0.0f;
}
[[gnu::always_inline]] inline float keep_of(unsigned cull){return cull==1?1.0f:cull==2?-1.0f:0.0f;}
void add(unsigned cls,float area,unsigned triangles);
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
// OCC28: opaque triangles fill a 40x30 grid (16x16 px cells) with the
// farthest corner depth (PVR z = 1/w: larger is nearer); TR/PT triangles are
// recorded and tested at the tick's end against every cell of their box.
void occ(unsigned cls,float ax,float ay,float az,float bx,float by,float bz,float qx,float qy,float qz,float area);
// Opaque triangles under 128 px rarely cover a 16x16 cell: they are not occluders.
#define RE4DC_X28_OCC(cls,a,b,q,f) do{if((f)>((cls)?0.0f:128.0f))::re4dc::dsa24::x28::occ(cls,(a).x,(a).y,(a).z,(b).x,(b).y,(b).z,(q).x,(q).y,(q).z,f);}while(0)
#else
#define RE4DC_X28_OCC(cls,a,b,q,f) do{}while(0)
#endif
// One strip of n indices into v (index & mask). Each corner is clamped once.
template<class V,class I> inline void strip(unsigned cls,unsigned cull,const V* v,const I* idx,unsigned n,unsigned mask){
    if(!sample||n<3)return;
    const float keep=keep_of(cull);
    float sum=0.0f,sign=1.0f;
    const V* pa=&v[idx[0]&mask];const V* pb=&v[idx[1]&mask];
    float ax=cx(pa->x),ay=cy(pa->y),bx=cx(pb->x),by=cy(pb->y);
    for(unsigned t=2;t<n;++t){
        const V* pq=&v[idx[t]&mask];
        const float qx=cx(pq->x),qy=cy(pq->y);
        const float f=facing(ax,ay,bx,by,qx,qy,sign,keep);
        sum+=f;RE4DC_X28_OCC(cls,*pa,*pb,*pq,f);
        ax=bx;ay=by;bx=qx;by=qy;pa=pb;pb=pq;sign=-sign;
    }
    add(cls,sum,n-2);
}
// An actor meshlet: strips end at an index with bit 7 set.
template<class V> inline void meshlet(unsigned cls,unsigned cull,const V* v,const uint8_t* idx,unsigned count){
    if(!sample)return;
    unsigned a=0;
    for(unsigned k=0;k<count;++k)if(idx[k]&128U){strip(cls,cull,v,idx+a,k+1-a,127U);a=k+1;}
    if(a<count)strip(cls,cull,v,idx+a,count-a,127U);
}
// Prepared vertices: strips end at an EOL flags word (eol).
template<class V> inline void packet(unsigned cls,unsigned cull,const V* v,unsigned n,uint32_t eol){
    if(!sample)return;
    const float keep=keep_of(cull);
    float sum=0.0f,sign=1.0f,ax=0,ay=0,bx=0,by=0;unsigned run=0,tris=0;
    for(unsigned i=0;i<n;++i){
        const float qx=cx(v[i].x),qy=cy(v[i].y);
        if(++run>=3U){
            const float f=facing(ax,ay,bx,by,qx,qy,sign,keep);
            sum+=f;++tris;RE4DC_X28_OCC(cls,v[i-2],v[i-1],v[i],f);sign=-sign;
        }
        ax=bx;ay=by;bx=qx;by=qy;
        if(v[i].flags==eol){run=0;sign=1.0f;}
    }
    add(cls,sum,tris);
}
// Per-model rows: the outermost model scope owns the time and counters.
void model_enter(const void* model);
void model_leave();
// Light path of the current part: 0 probe, 1 build_lights fold, 2 exact
// per-vertex evaluator, 3 constant (flat); lights = lights in the set.
void light(unsigned path,unsigned lights);
struct ModelScope{
    explicit ModelScope(const void* m){model_enter(m);}
    ~ModelScope(){model_leave();}
    ModelScope(const ModelScope&)=delete;ModelScope& operator=(const ModelScope&)=delete;
};
}
#endif
} }
#endif
