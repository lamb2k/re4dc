#pragma once
// Diagnostic only. Included in one TU when SCENERY_EMIT_CENSUS is nonzero.
// No rendering decisions, allocations, package writes or lock acquisition.
namespace scenery_emit_census {
struct Counts {
    unsigned plain=0,indexed=0,pv=0,iv=0,empty=0,izero=0,ev=0,whole=0,partial=0,span=0,bad=0;
    Counts& operator+=(const Counts& r){
        plain+=r.plain;indexed+=r.indexed;pv+=r.pv;iv+=r.iv;empty+=r.empty;izero+=r.izero;ev+=r.ev;
        whole+=r.whole;partial+=r.partial;span+=r.span;bad+=r.bad;return *this;
    }
};
struct State {
    unsigned frame=0,room=0,begun=0,ended=0,flush=0;
    bool captured=false,done=false;
    unsigned* attempts=nullptr;
};
static State state;
inline void pick_attempt(){if(state.attempts)++*state.attempts;}
inline void counts(const char* kind,unsigned frame,unsigned pass,unsigned flush,unsigned slot,const Counts& c){
    re4dc_log("WEC23 %s f=%u p=%u q=%u s=%u plain=%u indexed=%u pv=%u iv=%u zero=%u iz=%u zv=%u whole=%u partial=%u span=%u bad=%u\n",
        kind,frame,pass,flush,slot,c.plain,c.indexed,c.pv,c.iv,c.empty,c.izero,c.ev,c.whole,c.partial,c.span,c.bad);
}
struct Pass {
    bool active=false;unsigned frame=0,pass=0;int result=-1;
    Pass(unsigned f,unsigned room,unsigned p):frame(f),pass(p){
        if(state.captured && !state.done && (f!=state.frame || room!=state.room)){
            re4dc_log("WEC23 FRAME_END f=%u room=%03x begun=%x ended=%x flushes=%u complete=0\n",state.frame,state.room,state.begun,state.ended,state.flush);
            state.done=true;
        }
        if(!state.captured && p==0 && f>=unsigned(RE4DC_SCENERY_EMIT_CENSUS)){
            state.captured=true;state.frame=f;state.room=room;
            re4dc_log("WEC23 BEGIN f=%u room=%03x threshold=%u\n",f,room,unsigned(RE4DC_SCENERY_EMIT_CENSUS));
        }
        active=state.captured && !state.done && f==state.frame && room==state.room && p<3;
        if(active){
            re4dc_log("WEC23 PASS_BEGIN f=%u p=%u duplicate=%u\n",frame,pass,unsigned((state.begun&(1U<<pass))!=0));
            state.begun|=1U<<pass;
        }
    }
    ~Pass(){
        if(!active)return;
        state.ended|=1U<<pass;
        re4dc_log("WEC23 PASS_END f=%u p=%u result=%d\n",frame,pass,result);
        if(pass==2){
            re4dc_log("WEC23 FRAME_END f=%u room=%03x begun=%x ended=%x flushes=%u complete=%u\n",
                frame,state.room,state.begun,state.ended,state.flush,unsigned(state.begun==7 && state.ended==7));
            state.done=true;
        }
    }
};
template<class Package,class Part,class Pick> struct Flush {
    struct Progress {unsigned attempts=0;int result=2;}; // 2: not attempted, 1: completed, 0: fallback, -1: aborted
    Progress progress[48]{};
    const Package& package;const Part* parts;const Pick* picks;
    unsigned n,np,frame,pass,id=0;bool active;unsigned* previous;
    Flush(const Pass& scope,const Package& pkg,const Part* p,unsigned count,const Pick* pk,unsigned picked):
        package(pkg),parts(p),picks(pk),n(count),np(picked),frame(scope.frame),pass(scope.pass),
        active(scope.active && (count || picked)),previous(state.attempts){
        if(active)id=++state.flush;
    }
    void start(unsigned slot){
        if(active && slot<48)state.attempts=&progress[slot].attempts;
    }
    void finish(unsigned slot,int result){
        if(active && slot<48)progress[slot].result=result;
        state.attempts=previous;
    }
    Counts selected(const Part& p)const{
        Counts out;
        if(p.first>np || p.count>np-p.first){++out.bad;return out;}
        for(unsigned i=0;i<p.count;++i){
            const auto& pk=picks[p.first+i];
            if(pk.let>=package.header().meshlet_count){++out.bad;continue;}
            const auto& l=package.meshlets()[pk.let];const bool indexed=(l.strip_count&0x8000U)!=0;
            if(indexed){++out.indexed;out.iv+=l.vertex_count;}else{++out.plain;out.pv+=l.vertex_count;}
            if(pk.nr==0xffU){++out.whole;out.span+=l.vertex_count;}
            else if(!pk.nr){++out.empty;if(indexed){++out.izero;out.ev+=l.vertex_count;}}
            else{++out.partial;if(pk.lo>pk.hi || pk.hi>=l.vertex_count)++out.bad;else out.span+=pk.hi-pk.lo+1U;}
        }
        return out;
    }
    ~Flush(){
        state.attempts=previous;
        if(!active)return;
        Counts sum;unsigned selected_total=0,attempts=0,complete=0,fallback=0,aborted=0,untried=0;
        re4dc_log("WEC23 FLUSH_BEGIN f=%u p=%u q=%u parts=%u picks=%u overflow=%u\n",frame,pass,id,n,np,unsigned(n>48));
        for(unsigned j=0;j<n && j<48;++j){
            const auto& p=parts[j];const auto& pr=progress[j];const Counts c=selected(p);sum+=c;selected_total+=p.count;attempts+=pr.attempts;
            if(pr.result==2)++untried;else if(pr.result>0)++complete;else if(!pr.result)++fallback;else ++aborted;
            re4dc_log("WEC23 PART f=%u p=%u q=%u s=%u placement=%u part=%u first=%u picks=%u tried=%u result=%d crc=%08x fnv=%08x\n",
                frame,pass,id,j,p.placement,p.index,p.first,p.count,pr.attempts,pr.result,p.key[0],p.key[1]);
            counts("PART_COUNTS",frame,pass,id,j,c);
        }
        counts("FLUSH_COUNTS",frame,pass,id,0,sum);
        re4dc_log("WEC23 FLUSH_END f=%u p=%u q=%u picks=%u sum=%u tried=%u completed=%u fallback=%u aborted=%u untried=%u\n",
            frame,pass,id,np,selected_total,attempts,complete,fallback,aborted,untried);
    }
};
}
