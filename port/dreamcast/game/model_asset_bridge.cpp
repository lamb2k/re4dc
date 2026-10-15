// Asset-lifetime adapter for the source's accepted model registrations.
// Reuses the original OT and archive owner; no second visibility/model registry.
#include "model.h"
#include "trans.h"
#include "trans_ot.h"
#include "native_model.h"
#include "re4dc_platform.h"
#include <cstdint>
#ifndef RE4DC_COPY_LEAN
#define RE4DC_COPY_LEAN 0 // obj/frontend30.h (D367 frontend30)
#endif
#ifndef RE4DC_FRONT_LEAN
#define RE4DC_FRONT_LEAN 0
#endif
#ifndef RE4DC_OT_MASK
#define RE4DC_OT_MASK 0
#endif
#if RE4DC_OT_MASK == 2
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" unsigned re4dc_otm_exec_skips,re4dc_otm_exec_mismatch;   // trans_ot.cpp
#endif
#ifndef RE4DC_MODEL_WALK_CHECK
#define RE4DC_MODEL_WALK_CHECK 0
#endif
#if RE4DC_MODEL_WALK_CHECK
// MODEL_WALK_CHECK=1 (mcheck.mk; debug only, default 0): the test 11 console fault (read address error in
// walk_signature, node pointer 0x4125a0c3, at the end of every radio call). Flycast reads any address, so the
// broken chain is found by checking it: every OT table's chain (node: main RAM, aligned; a ModelRender entry's
// cModel and its info chain) at named points of the frame (re4dc_ot_check, main.cpp / sscrn.cpp) and before the
// walks below, which then skip a broken table. "MWC bad" lines name the first bad link with the previous node,
// the last model entry and the newest entries of that chain; "MWC sweeps" counts.
#include "global.h"
#include <string.h>
#include <stdio.h>
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" void* GetPrimBuff(int size);
extern "C" int re4dc_ss_ui_order();
namespace walkcheck {
unsigned sweeps,bad_total,reported,broken;   // broken: tables found broken by the last sweep
bool ram(const void* p,unsigned bytes){
    const std::uintptr_t a=reinterpret_cast<std::uintptr_t>(p);
    return a>=0x8c000000u && a+bytes<=0x8d000000u && !(a&3);
}
// Where p lies: B<t> bucket array of table t, P prim buffer (+offset), W sub screen window (pStFnt, 3 MiB), R RAM.
void loc(const void* p,char* out){
    const unsigned a=unsigned(reinterpret_cast<std::uintptr_t>(p));
    for(unsigned t=0;t<OT_MAX;++t){
        const unsigned lo=unsigned(reinterpret_cast<std::uintptr_t>(g_OtWork[t].list)),hi=lo+g_OtWork[t].max*sizeof(OtData);
        if(lo && a>=lo && a<hi){out[0]='B';out[1]=char('a'+t);out[2]=0;return;}
    }
    const unsigned pb=unsigned(pG->prim_cnt),pe=pb+unsigned(pG->nPrim)*2;
    if(pb && a>=pb && a<pe){out[0]='P';out[1]=0;return;}
    const unsigned wb=unsigned(reinterpret_cast<std::uintptr_t>(pG->pStFnt));
    if(wb && a>=wb && a<wb+0x300000u){out[0]='W';out[1]=0;return;}
    out[0]=a>=0x8c000000u && a<0x8d000000u?'R':'X';out[1]=0;
}
struct Seen { const OtData* node; void* data; void* func; unsigned kind; };
// Checks table t's chain; false (and one report while reported < 24) on the first bad link.
bool check_table(unsigned t,const char* where){
    const auto& ot=g_OtWork[t];
    if(!ot.list || !ot.max)return true;
    constexpr unsigned kRing=12;
    Seen ring[kRing];unsigned nseen=0,idx=0;
    const OtData* prev=nullptr;const OtData* lastm=nullptr;
    const OtData* node=&ot.list[ot.max-1];
    const char* what=nullptr;unsigned val=0;
    while(node){
        if(!ram(node,sizeof(OtData))){what="node";val=unsigned(reinterpret_cast<std::uintptr_t>(node));break;}
        if(node->data){
            ring[nseen%kRing]={node,node->data,reinterpret_cast<void*>(node->func),node->kind};++nseen;
            if(node->func==(void (*)(void*))ModelRender){
                const auto* model=static_cast<const cModel*>(node->data);
                if(!ram(model,sizeof(cModel))){what="model";val=unsigned(reinterpret_cast<std::uintptr_t>(model));break;}
                unsigned n=0;
                for(const auto* info=model->pModelInfo;info;info=info->pList){
                    if(!ram(info,0x18) || ++n>512){what="info";val=unsigned(reinterpret_cast<std::uintptr_t>(info));break;}
                }
                if(what)break;
                lastm=node;
            }
        }
        prev=node;node=node->next;
        if(++idx>200000){what="loop";val=idx;break;}
    }
    if(!what)return true;
    ++bad_total;
#if RE4DC_MODEL_WALK_CHECK >= 2
    // MODEL_WALK_CHECK=2 (console locator): stop at the first bad link with where / table / what on the stop screen.
    {
        const OtData* at=(what[0]=='n' || what[0]=='l')?prev:node;
        char why[80];
        snprintf(why,sizeof(why),"MWC %s t%u %s %08x at %08x d%08x n%08x f%08x f%u",where,t,what,val,
                 unsigned(reinterpret_cast<std::uintptr_t>(at)),at?unsigned(reinterpret_cast<std::uintptr_t>(at->data)):0u,
                 at?unsigned(reinterpret_cast<std::uintptr_t>(at->next)):0u,
                 at?unsigned(reinterpret_cast<std::uintptr_t>(at->func)):0u,unsigned(pG->Frame_cnt));
        re4dc_log("%s\n",why);
        re4dc_missing(why);
    }
#endif
    if(reported>=24)return false;
    ++reported;
    char l1[4],l2[4];
    re4dc_log("MWC bad at=%s f=%u room=%03x ss=%d t=%u models=%d i=%u what=%s val=%08x bad_total=%u\n",where,
              unsigned(pG->Frame_cnt),unsigned(pG->room_id),re4dc_ss_ui_order(),t,int(g_OtModels>>t&1),idx,what,val,bad_total);
    if(prev){
        loc(prev,l1);
        const unsigned* w=reinterpret_cast<const unsigned*>(prev);
        re4dc_log("MWC prev node=%08x[%s] data=%08x func=%08x next=%08x kind=%04x words %08x %08x %08x %08x\n",
                  unsigned(reinterpret_cast<std::uintptr_t>(prev)),l1,unsigned(reinterpret_cast<std::uintptr_t>(prev->data)),
                  unsigned(reinterpret_cast<std::uintptr_t>(prev->func)),unsigned(reinterpret_cast<std::uintptr_t>(prev->next)),
                  unsigned(prev->kind),w[4],w[5],w[6],w[7]);
    }
    if(what[0]!='n' && what[0]!='l'){   // the bad model / info belongs to this node
        const auto* model=static_cast<const cModel*>(node->data);
        loc(node,l1);loc(model,l2);
        re4dc_log("MWC owner node=%08x[%s] model=%08x[%s] func=%08x kind=%04x\n",unsigned(reinterpret_cast<std::uintptr_t>(node)),l1,
                  unsigned(reinterpret_cast<std::uintptr_t>(model)),l2,unsigned(reinterpret_cast<std::uintptr_t>(node->func)),unsigned(node->kind));
    }
    if(lastm){
        const auto* m=static_cast<const cModel*>(lastm->data);
        const unsigned* w=reinterpret_cast<const unsigned*>(m);
        loc(m,l1);
        re4dc_log("MWC lastmodel node=%08x model=%08x[%s] kindid=%u be=%08x info=%08x w0=%08x %08x %08x %08x\n",
                  unsigned(reinterpret_cast<std::uintptr_t>(lastm)),unsigned(reinterpret_cast<std::uintptr_t>(m)),l1,
                  unsigned(m->kindid),unsigned(m->be_flag),unsigned(reinterpret_cast<std::uintptr_t>(m->pModelInfo)),w[0],w[1],w[2],w[3]);
    }
    re4dc_log("MWC prim base=%08x n=%u cur=%08x win=%08x\n",unsigned(pG->prim_cnt),unsigned(pG->nPrim),
              unsigned(reinterpret_cast<std::uintptr_t>(GetPrimBuff(0))),unsigned(reinterpret_cast<std::uintptr_t>(pG->pStFnt)));
    const unsigned first=nseen>kRing?nseen-kRing:0;
    for(unsigned k=first;k<nseen;++k){
        const Seen& s=ring[k%kRing];
        loc(s.node,l1);loc(s.data,l2);
        re4dc_log("MWC chain %u node=%08x[%s] data=%08x[%s] func=%08x kind=%04x\n",k,unsigned(reinterpret_cast<std::uintptr_t>(s.node)),l1,
                  unsigned(reinterpret_cast<std::uintptr_t>(s.data)),l2,unsigned(reinterpret_cast<std::uintptr_t>(s.func)),s.kind);
    }
    return false;
}
unsigned sweep(const char* where){
    unsigned b=0;
    for(unsigned t=0;t<OT_MAX;++t)if(!check_table(t,where))b|=1u<<t;
    ++sweeps;
    if(sweeps%1800==0)re4dc_log("MWC sweeps=%u bad_total=%u\n",sweeps,bad_total);
    return b;
}
}
namespace walkcheck {
// Sub screen close: every OT entry made before SubScreenExitCore (ssexit0) is compared after it (ssexit1). The
// window restore puts the area's bytes back as they were at open: an entry inside the area is overwritten.
struct Snap { const OtData* node; void* data; void* func; const OtData* next; unsigned t; };
Snap snap[512];
unsigned nsnap;
bool in_buckets(const void* p){
    const unsigned a=unsigned(reinterpret_cast<std::uintptr_t>(p));
    for(unsigned t=0;t<OT_MAX;++t){
        const unsigned lo=unsigned(reinterpret_cast<std::uintptr_t>(g_OtWork[t].list)),hi=lo+g_OtWork[t].max*sizeof(OtData);
        if(lo && a>=lo && a<hi)return true;
    }
    return false;
}
void snapshot(const char* where){
    nsnap=0;unsigned inwin=0,inprim=0,nodes=0;
    const unsigned wb=unsigned(reinterpret_cast<std::uintptr_t>(pG->pStFnt));
    for(unsigned t=0;t<OT_MAX;++t){
        const auto& ot=g_OtWork[t];
        if(!ot.list || !ot.max)continue;
        unsigned guard=0;
        for(const OtData* n=&ot.list[ot.max-1];n && ram(n,sizeof(OtData)) && guard<200000;n=n->next,++guard){
            if(in_buckets(n))continue;
            ++nodes;
            char l[4];loc(n,l);
            if(l[0]=='W')++inwin;
            if(l[0]=='P')++inprim;
            if(nsnap<512)snap[nsnap++]={n,n->data,reinterpret_cast<void*>(n->func),n->next,t};
        }
    }
    const unsigned b0=unsigned(reinterpret_cast<std::uintptr_t>(g_OtWork[0].list));
    re4dc_log("MWC snap at=%s f=%u nodes=%u in_prim=%u in_window=%u prim=%08x+%x buckets0=%08x window=%08x+300000 cur=%08x\n",where,
              unsigned(pG->Frame_cnt),nodes,inprim,inwin,unsigned(pG->prim_cnt),unsigned(pG->nPrim),b0,wb,
              unsigned(reinterpret_cast<std::uintptr_t>(GetPrimBuff(0))));
}
void compare(const char* where){
    unsigned changed=0,logged=0;
    for(unsigned i=0;i<nsnap;++i){
        const Snap& s=snap[i];
        const OtData* n=s.node;
        if(n->data==s.data && reinterpret_cast<void*>(n->func)==s.func && n->next==s.next)continue;
        ++changed;
        if(logged++<12){
            char l[4];loc(n,l);
            re4dc_log("MWC clobbered at=%s t=%u node=%08x[%s] data %08x->%08x func %08x->%08x next %08x->%08x\n",where,s.t,
                      unsigned(reinterpret_cast<std::uintptr_t>(n)),l,unsigned(reinterpret_cast<std::uintptr_t>(s.data)),
                      unsigned(reinterpret_cast<std::uintptr_t>(n->data)),unsigned(reinterpret_cast<std::uintptr_t>(s.func)),
                      unsigned(reinterpret_cast<std::uintptr_t>(n->func)),unsigned(reinterpret_cast<std::uintptr_t>(s.next)),
                      unsigned(reinterpret_cast<std::uintptr_t>(n->next)));
        }
    }
    re4dc_log("MWC compare at=%s entries=%u changed=%u\n",where,nsnap,changed);
}
}
namespace walkcheck {
unsigned dump_left;   // sweeps still to list after a sub screen close
void dump(const char* where){
    unsigned lines=0;
    for(unsigned t=0;t<OT_MAX;++t){
        const auto& ot=g_OtWork[t];
        if(!ot.list || !ot.max)continue;
        unsigned guard=0;
        for(const OtData* n=&ot.list[ot.max-1];n && ram(n,sizeof(OtData)) && guard<200000;n=n->next,++guard){
            if(in_buckets(n) && !n->data)continue;
            if(lines++<60){
                char l1[4],l2[4];loc(n,l1);loc(n->data,l2);
                re4dc_log("MWC list at=%s f=%u t=%u node=%08x[%s] data=%08x[%s] func=%08x kind=%04x next=%08x\n",where,
                          unsigned(pG->Frame_cnt),t,unsigned(reinterpret_cast<std::uintptr_t>(n)),l1,
                          unsigned(reinterpret_cast<std::uintptr_t>(n->data)),l2,unsigned(reinterpret_cast<std::uintptr_t>(n->func)),
                          unsigned(n->kind),unsigned(reinterpret_cast<std::uintptr_t>(n->next)));
            }
        }
    }
    re4dc_log("MWC list at=%s f=%u entries=%u\n",where,unsigned(pG->Frame_cnt),lines);
}
}
extern "C" void re4dc_ot_check(const char* where);
// scheduler.cpp: after each task slot of TaskScheduler.
extern "C" void re4dc_ot_check_task(unsigned slot){
    static char w[12];
    snprintf(w,sizeof(w),"task%u",slot);
    re4dc_ot_check(w);
}
#if defined(RE4DC_DEAD_STACK_POISON) && RE4DC_DEAD_STACK_POISON
extern "C" void re4dc_poison_own_stack(unsigned bytes);  // platform/os.cpp (debug only)
#endif
extern "C" void re4dc_ot_check(const char* where){
#if defined(RE4DC_DEAD_STACK_POISON) && RE4DC_DEAD_STACK_POISON
    if(!strcmp(where,"top") || !strcmp(where,"rdone"))re4dc_poison_own_stack(6144);
#endif
    if(walkcheck::dump_left && strcmp(where,"clear")){--walkcheck::dump_left;walkcheck::dump(where);}
    if(!strcmp(where,"ssexit1"))walkcheck::dump_left=7;
    if(!strcmp(where,"ssexit0"))walkcheck::snapshot(where);
    walkcheck::sweep(where);
    if(!strcmp(where,"ssexit1")){walkcheck::compare(where);walkcheck::snapshot("ssexit1");}
}
#endif
#if RE4DC_FRONT_LEAN && RE4DC_D349_RENDERER_STACK
extern "C" int re4dc_model_asset_update_idle();
namespace {
// Identity of what the registration walk below would visit: every accepted
// model registration and drawn info in walk order, with the words that decide
// a part's plan request (static eligibility). Part streams are immutable per
// ModelData. Equal signature + an idle plan owner = the walk installs nothing.
struct WalkSignature { unsigned a,b,n; bool operator==(const WalkSignature& o)const{return a==o.a&&b==o.b&&n==o.n;} };
WalkSignature last_walk{0,0,~0U};
#if RE4DC_OT_MASK == 2
unsigned otm_calls,otm_mismatch;
#endif
#if RE4DC_OT_MASK
// GAME_OT_MASK: `tables` limits the walk to tables holding a model entry (a table without one adds
// nothing to the signature); all tables otherwise.
WalkSignature walk_signature(unsigned tables=~0U){
#else
WalkSignature walk_signature(){
#endif
    WalkSignature s{2166136261U,0x9e3779b9U,0};
#if RE4DC_MODEL_PREP_KEEP
    // MODEL_PREP_KEEP: the same registrations in another OT order are the same walk once the plan owner is idle
    // (every part hits or keeps its stable negative outcome; demand counts are order-free). Each model's words
    // (its info chain in chain order) hash on their own; the models combine by sum and xor.
    WalkSignature h{0,0,0};
    auto mix=[&](unsigned w){h.a=(h.a^w)*16777619U;h.b=(h.b+w)*0x85ebca6bU;h.b^=h.b>>13;++h.n;};
    auto model_done=[&](){s.a+=h.a*0x9e3779b1U+(h.b^h.n);s.b^=(h.b+0x7f4a7c15U)*0xc2b2ae35U^h.a;s.n+=h.n;h={2166136261U,0x9e3779b9U,0};};
    h={2166136261U,0x9e3779b9U,0};
#else
    auto mix=[&](unsigned w){s.a=(s.a^w)*16777619U;s.b=(s.b+w)*0x85ebca6bU;s.b^=s.b>>13;++s.n;};
#endif
    for(unsigned priority=0;priority<2;++priority)for(unsigned table=0;table<OT_MAX;++table){
        const auto& ot=g_OtWork[table];
#if RE4DC_OT_MASK
        if(!ot.list || !ot.max || !(tables>>table&1))continue;
#else
        if(!ot.list || !ot.max)continue;
#endif
#if RE4DC_MODEL_WALK_CHECK
        if(walkcheck::broken>>table&1)continue;
#endif
        for(auto* node=&ot.list[ot.max-1];node;node=node->next){
            if(!node->data || node->func!=(void (*)(void*))ModelRender)continue;
            auto* model=static_cast<cModel*>(node->data);
            if((model->kindid<=1)!=(priority==0) || model->invisible_factor*model->invisible_factor2==0.f)continue;
            mix(unsigned(reinterpret_cast<std::uintptr_t>(model)));mix(model->be_flag&0x4000);mix(model->kindid);
            for(auto* info=model->pModelInfo;info;info=info->pList){
                if(!(info->be_flag&8))continue;
                mix(unsigned(reinterpret_cast<std::uintptr_t>(info)));
                mix(unsigned(reinterpret_cast<std::uintptr_t>(info->pData)));mix(info->be_flag&2);
            }
#if RE4DC_MODEL_PREP_KEEP
            model_done();
#endif
        }
    }
    return s;
}
}
#endif
extern "C" void re4dc_prepare_model_assets(){
#if RE4DC_D349_RENDERER_STACK
    if(!re4dc_model_diagnostic_enabled())return;
#if RE4DC_MODEL_WALK_CHECK
    walkcheck::broken=walkcheck::sweep("walk");
#endif
#if RE4DC_FRONT_LEAN
    // Same registrations as the last walk and nothing pending in the plan
    // owner: every part would hit (or keep its negative admission) again.
    {
#if RE4DC_OT_MASK == 2
        const WalkSignature now=walk_signature();
        if(!(walk_signature(g_OtModels)==now) && otm_mismatch++<4)re4dc_log("OTM signature mismatch: models=%08x\n",(unsigned)g_OtModels);
        if(++otm_calls%600==0){
            re4dc_log("OTM calls=%u sig_mismatch=%u exec_skips=%u exec_mismatch=%u models=%08x used=%08x\n",
                otm_calls,otm_mismatch,re4dc_otm_exec_skips,re4dc_otm_exec_mismatch,(unsigned)g_OtModels,(unsigned)g_OtUsed);
        }
#elif RE4DC_OT_MASK
        const WalkSignature now=walk_signature(g_OtModels);
#else
        const WalkSignature now=walk_signature();
#endif
        const bool idle=re4dc_model_asset_update_idle()!=0;
#if RE4DC_MODEL_PREP_KEEP
        // A dropped image (pace skip) leaves no model OT: on an idle owner the walk would only zero the demand
        // counts, which nothing reads before the next begin_asset_update zeroes them again. Keep the drawn walk's
        // signature, so the next drawn tick over the same registrations skips its walk too.
        if(idle && now.n==0)return;
#endif
        const bool same=now==last_walk;
        last_walk=now;
        if(idle && same)return;
    }
#endif
    re4dc_model_begin_asset_update(); // acknowledge source owner/publication changes
    const auto previous=*re4dc_model_draw_plan_stats();
    unsigned models=0,parts=0,prepared=0,rejected=0;
    // main.cpp: Render_before -> Render -> ClearOt -> tasks -> Trans. These are
    // the already accepted registrations for this render, not all resident BINs.
    // Prefer measured actor working sets for finite metadata admission only;
    // source draw order, update eligibility and resource ownership are unchanged.
    for(unsigned priority=0;priority<2;++priority)for(unsigned table=0;table<OT_MAX;++table){
        const auto& ot=g_OtWork[table];
        if(!ot.list || !ot.max)continue;
#if RE4DC_OT_MASK == 1
        if(!(g_OtModels>>table&1))continue;   // no model entry in this table since its clear
#endif
#if RE4DC_MODEL_WALK_CHECK
        if(walkcheck::broken>>table&1)continue;
#endif
        for(auto* node=&ot.list[ot.max-1];node;node=node->next){
            // Empty bucket sentinels do not initialize func. Check data first.
            if(!node->data || node->func!=(void (*)(void*))ModelRender)continue;
            auto* model=static_cast<cModel*>(node->data);
            if((model->kindid<=1)!=(priority==0) || model->invisible_factor*model->invisible_factor2==0.f)continue;
            for(auto* info=model->pModelInfo;info;info=info->pList){
                if(!(info->be_flag&8))continue;
                const auto* d=info->pData;
                if(!re4dc_model_owned_source(d,sizeof(ModelData)))continue;
                if(d->shift>30 || !d->nVtx || !d->nNrm)continue;
                ++models;
                auto* part=d->pParts;
#if RE4DC_COPY_LEAN
                // Every word the plan request reads is assigned per part below:
                // one zero-initialised view instead of a ~300-byte memset per part.
                Re4dcModelPart p{};
#endif
                for(unsigned i=0;i<d->displist_num;++i){
                    if(!re4dc_model_owned_source(part,sizeof(ModelPart))){++rejected;break;}
                    if(part->size>1024*1024 || !re4dc_model_owned_source(part+1,part->size)){++rejected;break;}
#if !RE4DC_COPY_LEAN
                    Re4dcModelPart p{};
#endif
                    p.part=part;p.stream=(const unsigned char*)(part+1);
                    p.stream_bytes=part->size;p.position_count=d->nVtx;p.normal_count=d->nNrm;
                    p.flags=d->flags;p.positions=(const unsigned char*)d->vtxOrig;
                    p.position_stride=8;p.shift=d->shift;
                    // Bounds qualify only when the eventual rigid draw uses
                    // these immutable positions and this quantization scale.
                    const bool rigid=(model->be_flag&0x4000) ||
                        (d->weight_palette_num<=1 && d->weight_ext_num<=0xff && !(info->be_flag&2) && d->nParts==1);
                    p.static_geometry=rigid && model->kindid==2 && !d->shapeOfs && !(info->be_flag&2);
                    const int result=re4dc_model_prepare_draw_plan(&p);
                    ++parts;if(result>0)++prepared;else if(result<0)++rejected;
                    part=(ModelPart*)((unsigned char*)(part+1)+part->size);
                }
            }
        }
    }
    re4dc_model_finish_asset_update(); // publish local admission after every accepted registration
    const auto* stats=re4dc_model_draw_plan_stats();
    if(stats->installs!=previous.installs || stats->invalid!=previous.invalid)re4dc_log("native source OT asset update: models=%u parts=%u prepared=%u rejected=%u metadata=%u/%u decoded_total=%u\n",
              models,parts,prepared,rejected,stats->used,stats->capacity,stats->source_bytes);
#endif
}
