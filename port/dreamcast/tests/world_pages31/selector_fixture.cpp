// The actual shared production selector is included twice: source and paged.
// Synthetic package bounds make every cluster/meshlet visit observable.
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include "../../game/platform/include/world_page31.hpp"
#define RE4DC_WORLD_PORTAL_COMPLETION 1
#include "../../game/platform/include/world_portal29.hpp"

struct Box { float bounds_min[3]{},bounds_max[3]{}; unsigned vertex_count=3; };
struct Level { unsigned first_meshlet=0,meshlet_count=0; float error=0; };
struct Cluster : Box { unsigned first_level=0,level_count=0; };
struct PartLod { unsigned first_cluster=0,cluster_count=0; };
struct Package {
    std::vector<Cluster> cs;std::vector<Level> ls;std::vector<Box> ms;
    PartLod part{};
    bool lod()const{return true;}
    const Cluster* clusters()const{return cs.data();}
    const Level* levels()const{return ls.data();}
    const Box* meshlets()const{return ms.data();}
    const PartLod* part_lods()const{return &part;}
    bool indexed(const Box&)const{return false;}
};
struct SourcePart { float projection[16]{},viewport[4]{}; unsigned cull=0; };
struct Pick { std::uint16_t let=65535; std::uint8_t nr=0,gmask=0,lo=0,hi=0,pad[2]{}; };
std::vector<unsigned char> mesh_visible,cluster_visible;
std::vector<unsigned> mesh_visits,cluster_visits;
namespace re4dc { namespace render {
struct DrawBounds { float lo[3],hi[3]; };
bool group_visible(const DrawBounds& b,const float*,const float*,const float*,float,float,unsigned){
    const unsigned n=unsigned(b.lo[0]);
    if(n>=100000U){const unsigned c=n-100000U;++cluster_visits[c];return cluster_visible[c]!=0;}
    ++mesh_visits[n];return mesh_visible[n]!=0;
}
}}
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
namespace re4dc { namespace wc24 {
enum Label { Selection, PickedIndexed, PickedPlain, PickedEmpty };
struct Scope { explicit Scope(Label){} };
unsigned counts[4]{};
void count(Label label,unsigned n){counts[label]+=n;}
}}
#endif
struct SelectStats { unsigned clusters_culled=0,clusters_visible=0,lod_draws[4]{},groups_culled=0; } stats;
namespace lean {
constexpr unsigned kMode=0;
struct SgPlane {};
struct LeanStats { unsigned skipped=0,cl_inside=0,sg_tests=0,sg_culled=0,sg_meshlets=0,sg_vskip=0; } st;
struct LeanCalls { unsigned calls=0; } lst;
template<class... Args> unsigned box_class(Args&&...){return 1;}
template<class... Args> int box_mask(Args&&...){return 0;}
template<class... Args> int box_mask_lean(Args&&...){return 0;}
template<class... Args> void sg_coef(Args&&...){}
template<class... Args> void sg_coef_lean(Args&&...){}
template<class... Args> unsigned sg_select(Args&&...){return 0;}
template<class... Args> unsigned sg_select_lean(Args&&...){return 0;}
}
int re4dc_sg_lean_on=0;

struct SelectorBase {
    using Pick=::Pick;
    const Package& package;const SourcePart& p;const float* mvq;
    float near=1,cull_far=100,lod_scale=1;
    unsigned part_index=0,sg_groups=0;const float* lean_am=nullptr;
    const std::uint8_t* sg=nullptr;const unsigned* ps2=nullptr;
    bool lean_inside=false,sg_coef_ok=false,sg_lp_ok=false;
    float sg_coef[40]{};lean::SgPlane sg_lp[5]{};
    SelectorBase(const Package& a,const SourcePart& b,const float* m):package(a),p(b),mvq(m){}
};
struct SourceSelector : SelectorBase {
    using SelectorBase::SelectorBase;
#define RE4DC_WORLD_PAGES31 0
#include "../../game/platform/include/scenery_chunk_select.inc"
#undef RE4DC_WORLD_PAGES31
};
struct PageSelector : SelectorBase {
    using SelectorBase::SelectorBase;
#define RE4DC_WORLD_PAGES31 1
#include "../../game/platform/include/scenery_chunk_select.inc"
#undef RE4DC_WORLD_PAGES31
};

static void add_cluster(Package& p,unsigned count,unsigned alt=0){
    const unsigned c=p.cs.size();Cluster cl{};cl.bounds_min[0]=cl.bounds_max[0]=float(100000U+c);
    cl.first_level=p.ls.size();cl.level_count=alt?2:1;
    auto add_level=[&](unsigned n,float error){
        Level lv{unsigned(p.ms.size()),n,error};p.ls.push_back(lv);
        for(unsigned i=0;i<n;++i){Box m{};m.bounds_min[0]=m.bounds_max[0]=float(p.ms.size());p.ms.push_back(m);}
    };
    add_level(count,0);if(alt)add_level(alt,20);
    p.cs.push_back(cl);p.part.cluster_count=p.cs.size();
}
struct Result { std::vector<std::pair<unsigned,unsigned>> picks;std::vector<unsigned> pages,visits,clusters;
                SelectStats counters;lean::LeanStats lean_stats;bool complete=false;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                unsigned census[4]{};
#endif
};
static Result run(const Package& p,bool paged,unsigned mode,float scale=1,bool stop_after_first=false,
                  bool hide_last=false,unsigned capacity=320){
    mesh_visible.assign(p.ms.size(),mode==2);
    if(mode==1 && !mesh_visible.empty())mesh_visible.back()=1;
    cluster_visible.assign(p.cs.size(),1);
    if(hide_last && !cluster_visible.empty())cluster_visible.back()=0;
    mesh_visits.assign(p.ms.size(),0);cluster_visits.assign(p.cs.size(),0);
    stats={};lean::st={};lean::lst={};
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    for(unsigned& n:re4dc::wc24::counts)n=0;
#endif
    const float mvq[12]={0,0,0,0,0,0,0,0,0,0,0,-10};SourcePart part{};
    Result r;
    if(!paged){
        SourceSelector s(p,part,mvq);s.lod_scale=scale;
        std::vector<Pick> picks(p.ms.size()+1);
        const unsigned n=s.chunk_select(picks.data());
        for(unsigned i=0;i<n;++i)r.picks.push_back({picks[i].let,picks[i].nr});
    }else{
        PageSelector s(p,part,mvq);s.lod_scale=scale;
        re4dc::page31::Cursor cursor{};
        re4dc::page31::Part proof(0,p.ms.size());
        assert(capacity>0 && capacity<=320);
        for(unsigned guard=0;guard<p.ms.size()+p.cs.size()+2;++guard){
            std::vector<Pick> picks(capacity+2);picks[0].let=picks[capacity+1].let=65535;
            const auto page=s.chunk_select(picks.data()+1,capacity,cursor);
            assert(page.count<=capacity && picks[0].let==65535 && picks[capacity+1].let==65535);
            r.pages.push_back(page.count);
            for(unsigned i=0;i<page.count;++i)r.picks.push_back({picks[i+1].let,picks[i+1].nr});
            proof.selected(picks.data()+1,page.count);
            if(page.count)proof.emitted(1,true,page.count,page.count);
            if(stop_after_first){assert(!page.done);break;}
            if(page.done){r.complete=proof.complete(0) && proof.published;break;}
            assert(guard<p.ms.size()+p.cs.size()+1);
        }
    }
    r.visits=mesh_visits;r.clusters=cluster_visits;r.counters=stats;r.lean_stats=lean::st;
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    for(unsigned i=0;i<4;++i)r.census[i]=re4dc::wc24::counts[i];
#endif
    return r;
}
static void equal(const Package& p,unsigned mode,float scale=1,bool hide_last=false){
    const auto source=run(p,false,mode,scale,false,hide_last),pages=run(p,true,mode,scale,false,hide_last);
    assert(source.picks==pages.picks && source.visits==pages.visits && source.clusters==pages.clusters);
    assert(source.counters.clusters_culled==pages.counters.clusters_culled);
    assert(source.counters.clusters_visible==pages.counters.clusters_visible);
    for(unsigned i=0;i<4;++i)assert(source.counters.lod_draws[i]==pages.counters.lod_draws[i]);
    assert(source.counters.groups_culled==pages.counters.groups_culled);
    assert(source.lean_stats.skipped==pages.lean_stats.skipped);
    assert(source.lean_stats.cl_inside==pages.lean_stats.cl_inside);
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    for(unsigned i=0;i<4;++i)assert(source.census[i]==pages.census[i]);
#endif
    bool full=source.picks.size()==p.ms.size();
    for(unsigned i=0;i<source.picks.size();++i)full=full && source.picks[i].first==i && source.picks[i].second==0xffU;
    assert(pages.complete==full);
}
static void receipts(){
    assert(re4dc::page31::indexable(65535U-320U,321U));
    assert(!re4dc::page31::indexable(65536U-320U,321U));
    assert(!re4dc::page31::indexable(65536U,1U));
    std::array<Pick,321> picks{};
    for(unsigned i=0;i<picks.size();++i){picks[i].let=i;picks[i].nr=0xffU;}
    re4dc::page31::Part part(0,picks.size());
    part.selected(picks.data(),320);part.emitted(1,true,320,320);
    assert(!part.complete(0)); // a first published page is never a whole-part receipt
    part.selected(picks.data()+320,1);part.emitted(1,true,1,1);
    auto complete=re4dc::portal29::Completion::emitted(part.result(),part.published,
                                                        part.input,part.output,part.complete(0));
    assert(complete.witnessed());
    re4dc::page31::Part refused(0,picks.size());
    refused.selected(picks.data(),320);refused.emitted(0,false,320,0);
    refused.selected(picks.data()+320,1);refused.emitted(1,true,1,1);
    assert(!re4dc::portal29::Completion::emitted(refused.result(),refused.published,
                                                  refused.input,refused.output,refused.complete(0)).witnessed());
    picks[320].nr=0;
    re4dc::page31::Part clipped(0,picks.size());
    clipped.selected(picks.data(),picks.size());clipped.emitted(1,true,321,321);
    assert(!clipped.complete(0));
    picks[320].nr=0xffU;picks[320].let=319;
    re4dc::page31::Part duplicate(0,picks.size());
    duplicate.selected(picks.data(),picks.size());duplicate.emitted(1,true,321,321);
    assert(!duplicate.complete(0));
}
int main(){
    receipts();
    for(unsigned n: {319U,320U,321U,641U}){
        Package p;add_cluster(p,n);
        for(unsigned mode=0;mode<3;++mode)equal(p,mode);
        if(n==321){
            auto all=run(p,true,2);assert((all.pages==std::vector<unsigned>{320,1}));
            auto none=run(p,true,0);assert((none.pages==std::vector<unsigned>{0}));
            auto one=run(p,true,1);assert((one.pages==std::vector<unsigned>{1}));
            auto abort=run(p,true,2,1,true);assert(abort.picks.size()==320 && abort.visits[320]==0);
        }
    }
    Package boundary;add_cluster(boundary,320);add_cluster(boundary,1);
    equal(boundary,2);
    assert((run(boundary,true,2).pages==std::vector<unsigned>{320,1}));
    equal(boundary,2,1,true);
    assert((run(boundary,true,2,1,false,true).pages==std::vector<unsigned>{320,0}));
    Package empty_end;add_cluster(empty_end,320);add_cluster(empty_end,0);
    equal(empty_end,2);
    const auto empty_final=run(empty_end,true,2);
    assert((empty_final.pages==std::vector<unsigned>{320,0}) && empty_final.complete);
    Package lod;add_cluster(lod,320,1);add_cluster(lod,1);
    equal(lod,2,1);equal(lod,2,0);
    Package small;add_cluster(small,10);
    assert((run(small,true,2,1,false,false,7).pages==std::vector<unsigned>{7,3}));
    assert(run(small,true,2,1,false,false,1).pages.size()==10);
    std::puts("production selector pages: 319/320/321/641, 0/1/all, cluster/LOD, final/abort pass");
}
