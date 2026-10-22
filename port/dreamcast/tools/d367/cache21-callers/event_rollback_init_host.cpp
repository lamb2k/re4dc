// Extends sealed 5d10f51e's actual-source init fixture; external services are counters.
#include <array>
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <new>
#include <string>
#include <vector>
#include <sys/mman.h>
using u8=std::uint8_t; using s8=std::int8_t; using u16=std::uint16_t;
using s16=std::int16_t; using u32=std::uint32_t; using s32=std::int32_t;
#define RE4_MEM_LO 0x8C000000
#define RE4_MEM_HI 0x8CFFFFFF
#define RE4DC_ALIVE_BUMP() ((void)0)
#define RE4DC_EVENT_FILE_FLAG 4
#define CMND_CLEAR_DATA 3
#define BitOn(v,bits) ((v)|=(bits))
#define BitOff(v,bits) ((v)&=~(bits))
#define EvtChk(v,bits) (((v)&(bits))!=0)
#include "init_actual_compile_contract.inc"
static std::map<std::string,unsigned> effects;
static std::vector<std::string> errors;
static std::string retired_name;
struct Logger {
    void err(int,int,const char* fmt,...) {
        char text[512]; va_list args; va_start(args,fmt); std::vsnprintf(text,sizeof(text),fmt,args); va_end(args);
        errors.emplace_back(text);
    }
    void warn(int,int,const char*,...) {}
    void mes(int,int,const char*,...) {}
} logger,*pLog=&logger;
void memclr_asm(void* p,unsigned n) { std::memset(p,0,n); }
static bool fail_table, mutate_after_total;
static std::vector<void*> table_blocks, debug_frees;
static void* host_table_alloc(unsigned n,int,int) {
    ++effects["table_alloc"];
    if(fail_table) return nullptr;
    void* p=std::calloc(1,n?n:1); assert(p); table_blocks.push_back(p); return p;
}
#define MEM_ALLOC host_table_alloc
static void Mem_free(void* p) {
    for(auto& block:table_blocks) if(block==p) { block=nullptr; ++effects["table_free"]; std::free(p); return; }
    std::abort();
}
static void Debug_free(void* p) { debug_frees.push_back(p); }
#include "init_actual_types.inc"
#include "init_actual_dattbl_decl.inc"
struct Vec { float x{},y{},z{}; };
struct cModel {};
struct cObj: cModel {};
struct cPlayer: cModel {
    Vec pos,ang;
    void zeroPartsPosInit(Vec*,Vec*) { ++effects["player_reset"]; }
    void endEvent0(int) { ++effects["player_end"]; }
    void move() { ++effects["player_move"]; }
} player,*pPL=&player;
struct Global { u32 Stop_flg{},Debug_flg[4]{},Status_flg[3]{},System_flg{},Disp_flg{}; } global,*pG=&global;
struct cUnit {
    u32 be_flag{}; cUnit* pNext{};
    cUnit()=default; explicit cUnit(u32 flag):be_flag(flag){}
    virtual ~cUnit() { be_flag&=~0x601; }
    int isAlive() { return (be_flag&0x201)==1; }
    static void operator delete(void*,std::size_t) {} // Source pool delete, host-width size ABI.
};
struct Event: cUnit {
    u8 Type{},EndRNo1{},Id{}; s8 EndRNo2{},EndRNo3{}; int effNo{};
    char Name[32]{}; EvtHeader* pData{}; EvtPacket* pPacket{}; EvtPacket* pPrevPacket{}; u32 StatusFlag{};
    DatTbl ModTbl; cModel* PPl{}; cModel* PModOya{};
    int NowTotalFrame{},MaxTotalFrame{},NowFrame{},MaxFrame{},NowCut{},MaxCut{},EmListNo{},TimerMes{},DelTimer{},ChangeNoStr{},ChangeNowCut{},funcMode{};
    void* pDatFog{}; void* pDatFocus{}; void* pLit{}; void* PFuncTbl{};
    int NowStr[2]{}; u32 SndId[2]{};
    explicit Event(u8); ~Event() override;
    int init(char*,EvtHeader*); void ExeEndEvt(Event*,u32); int ExeFunc(int,int);
    int CalMaxCut(int*); int CalMaxFrame(int*,int); int CalMaxTotalFrame(int*,int*);
    int actual_CalMaxTotalFrame(int*,int*);
};
static cModel* EspEvModList[128];
struct Camera {
    int IsMotionSet() { return 1; }
    void setMotionBaseMatPtr(void*) { ++effects["camera_base"]; }
    void Comeback(int) { ++effects["camera_return"]; }
} CamCtrl;
struct Lights {
    int roomLitCheck() { return 0; }
    void roomLitSet(int) { ++effects["light_set"]; }
    void update(int,int) { ++effects["light_update"]; }
} LightMgr;
struct Messages {
    void roomInit() { ++effects["message_init"]; }
    void loadStageFont() { ++effects["font_load"]; }
} cMes;
struct Objects { void destroy(cObj*) { ++effects["obj_destroy"]; } } ObjMgr;
static void OyaSetObj18(cObj*,int,int) { ++effects["obj_detach"]; }
static void DelObj18(cObj*) { ++effects["obj18_delete"]; }
static void MotionClear(cModel*,int) { ++effects["motion_clear"]; }
static void EspDataRelease(int,int,int) { ++effects["effect_release"]; }
static void EventAllEffDelete() { ++effects["all_effect_delete"]; }
#define SCC_BEHIND 0
static void SubCharCtrl(int,int) { ++effects["partner_return"]; }
static void EvtMesDeleteAll() { ++effects["event_messages"]; }
static void ShadowMemClear() { ++effects["shadow_clear"]; }
static void SubScreenWait(int) { ++effects["subscreen_wait"]; }
static void SndEventEnd() { ++effects["sound_end"]; }
static void OSReport(const char*,...) {}
static void SceEventStart(int) { ++effects["scenario_start"]; }
static void SceEventEnd(int) { ++effects["scenario_end"]; }
static void SceSleep(int) { ++effects["sleep"]; }
static int SceCheckEventStart() { return 1; }
static void FadeSetW(u32,int,int,int) { ++effects["fade"]; }
struct GXColor { u8 r,g,b,a; };
#define FADE_NO_ROOM 0
static void FadeKill(int) { ++effects["fade_kill"]; }
static void FadeSet(u32,GXColor*,GXColor*,int,int,int) { ++effects["fade"]; }
#include "init_actual_file_modes.inc"
static void* Debug_alloc(unsigned,int) { std::abort(); }
static int hdRead_malloc(const char*,void**,int,int);
#include "init_actual_native_file_methods.inc"
static unsigned char* arena;
static void*last_input_free;
static void Mem_free_h(void* p,int heap) {
    assert(heap==4 && (p==arena||p==arena+0x10000));last_input_free=p;
    ++effects["input_free"];assert(mprotect(p,4096,PROT_NONE)==0);
}
static void Debug_free_h(void* p,int heap) { Mem_free_h(p,heap); }
struct Controller { int m_nblock_read_stop{},dbgHeap{}; } DC;
struct AramBoundary { void DmaCancel(int) { std::abort(); } } Aram;
struct DvdBoundary { void ReadCancel(int,int){std::abort();} void ReadCheck(int,void*,void*,void*){std::abort();} } Dvd;
#include "init_actual_dataunit_decl.inc"
static cDataUnit loaded;
#if RE4DC_CABIN_SOURCE
static int re4dc_cabin_carrier_clear(void*);
static int re4dc_cabin_carrier_before_free(const void*);
static void re4dc_missing(const char*);
#endif
void cDataUnit::setLoadToMram(){std::abort();} void cDataUnit::setLoadToAram(){std::abort();}
int cDataUnit::setDelete(){std::abort();} void cDataUnit::checkCondition(){std::abort();}
#include "init_actual_dataunit_methods.inc"
struct ReadModule { void* pArc; };
static ReadModule* SearchEmModule(int){std::abort();}
static void MemorySwap(void*,u32,u32){std::abort();} static void EspEmDataSwapPop(int){std::abort();}
struct EventMgr {
    DatTbl EvdTbl,BinTbl,FuncTbl,ReadTbl; Event* pArray{}; u32 nArray{},size{};
    union {u32 NowExeEvtKey;char NowExeEvtName[48];}; u32 pUnit[32]{}; void*emWindowFcv[3]{}; EvtReadEm readEm[8]{};
    int SetBin(char*,void*,void*,int); int GetBin(void**,const char*,int); int DelBin(char*);
    int SetEvd(char*,void*,void*,int); int GetEvd(void**,char*,int); int DelEvd(char*); void ToolCoreEvdDel();
    int GetFunc(void**,char*); int SetFunc(char*,void*);
    int myRoomInit(); void ClearEmWindowFcv(); Event* create(int); int construct(Event*,u32); void destroyNow(Event*);
    int SetEvt(void*,u32*); int SetEvt(char*,Event**); int DelEvt(void*,int); int IsAliveEvt(u32*,int,int);
    int EvtReadExec(char*,int,u32); int EvtReadMram(char*,int,int*,int,u32); int EvtFree(char*); int GetRead(void**,int*,char*); int DelRead(char*);
    int GetZeroPartsWorldPos(cModel*,Vec*,Vec*) { std::abort(); }
} EvtMgr;
template<class T> struct cManager {
    T*pArray{};T*pAlive{};u32 nArray{},size{sizeof(T)},maxAlive{},warnDiv{8};u8 flag{2};const char*name{"fixture"};
    T*workAt(u32 no){return reinterpret_cast<T*>(reinterpret_cast<u8*>(pArray)+size*no);}
    bool prepareWork(u32 no,u32 count){return no<nArray && count<=nArray-no;}
    void memClear(T*p,u32 n){memclr_asm(p,n);}
    int construct(T*p,u32 id){return EvtMgr.construct(p,id);}
    void log(const char*,...){++effects["pool_log"];}
    T*create(int);u32 countActiveWork();void destroy(T*);void destroyNow(T*);
#include "init_actual_manager_inline.inc"
};
#include "init_actual_manager_methods.inc"
static cManager<Event> event_pool;
Event*EventMgr::create(int id){return event_pool.create(id);}
static void check_abandoned_binding(const Event*);
void EventMgr::destroyNow(Event*p){check_abandoned_binding(p);++effects["destroy_work"];retired_name=p->Name;event_pool.destroyNow(p);}
int EventMgr::GetRead(void**out,int*slot,char*name){u8 type=0;return ReadTbl.GetDat(out,&type,name,nullptr)&&ReadTbl.GetWkNo(slot,name);}
int EventMgr::EvtReadMram(char*,int em,int*out,int,u32){assert(em==0);++effects["input_read"];*out=int(reinterpret_cast<std::uintptr_t>(loaded.m_addr));return 1;}
#if RE4DC_CABIN_SOURCE
// Unit/allocation/module observers are explicit service boundaries. Carrier
// admission, exact-event unbind, and cabin audio callbacks are actual bodies.
static const void* observed_unit;static const void* observed_mram;static const void* observed_module;
static unsigned observed_bytes;static bool unit_valid,allocation_valid,module_valid;
extern "C" int re4dc_cabin_source_unit_valid(const void*u,unsigned,unsigned,unsigned n){return unit_valid&&u==observed_unit&&n==observed_bytes;}
extern "C" int re4dc_cabin_source_allocation(const void*p,unsigned n,int*heap){*heap=4;return allocation_valid&&p==observed_mram&&n==observed_bytes;}
extern "C" const void* re4dc_cabin_source_module(const void*,unsigned){return module_valid?observed_module:nullptr;}
static void re4dc_missing(const char*){++effects["missing_boundary"];}
static void re4dc_log(const char*,...){}
static int re4dc_movie_cabin_abort(unsigned){++effects["cabin_movie_abort"];return 1;}
static int re4dc_cabin_audio_owner_close(unsigned){++effects["cabin_audio_close"];return 1;}
static unsigned re4dc_cabin_audio_owner_open(const void*,unsigned){++effects["cabin_audio_open"];return 17;}
#include "init_actual_cabin_methods.inc"
// No selected case performs a module exchange; fail loudly if that external
// read-owner path is reached instead of claiming its separate contract tested.
static int re4dc_cabin_carrier_clear(void*){std::abort();}
static int re4dc_cabin_carrier_before_free(const void*){std::abort();}
static unsigned re4dc_cabin_carrier_reverse_token(const void*,const void*,const void*,unsigned,int*){std::abort();}
static int re4dc_cabin_carrier_reverse_complete(const void*,const void*,const void*,unsigned,int,unsigned){std::abort();}
#endif
static void check_abandoned_binding(const Event*p){
#if RE4DC_CABIN_SOURCE && RE4DC_EVD_START_CLEANUP
    // A failing work's accepted carrier must be unbound BEFORE its destructor
    // releases the table/storage. Other events' bindings must remain intact.
    for(const auto&c:carriers)assert(c.event!=p);
#else
    (void)p;
#endif
}
#include "init_actual_event_methods.inc"
int Event::CalMaxTotalFrame(int*outCut,int*outTotal) {
    const int result=actual_CalMaxTotalFrame(outCut,outTotal);
    if(result && mutate_after_total){++effects["injected_packet_mutation"];reinterpret_cast<EvtPacket*>(reinterpret_cast<u8*>(pData)+pData->pacOfs)->id=0x21;}
    return result;
}
#include "init_h064_header_constructor.inc"
static void end_handler(Event*,int){++effects["end_callback"];}
static std::array<DatTblEntry,32> parents,funcs;
static std::array<DatTblEntry,320> bins;
static std::array<DatTblEntry,8> reads;
static Event* pool;
static char file_name[]="event/evd/synthetic.evd";
static char event_name[]="event";
static char prior_name[]="prior.live";
static EvtHeader* prior;
static bool same_parent;
static EvtPacket* packets(EvtHeader*h){return reinterpret_cast<EvtPacket*>(reinterpret_cast<u8*>(h)+h->pacOfs);}
static void stream(EvtHeader*h,const std::string&stage){
    h->pacOfs=2048;h->pacSize=2*sizeof(EvtPacket);auto*p=packets(h);std::memset(p,0,2*sizeof(*p));
    p[0].id=8;p[0].size=sizeof(*p);p[0].val.no=3;p[1].id=0x1B;p[1].size=sizeof(*p);
    if(stage=="packet-id")p[0].id=0x21;
    if(stage=="camera-data"){p[0].id=6;std::strcpy(p[0].mod.name,"missing.fcv");}
}
static void setup(const std::string&stage,bool preexisting){
    for(auto&block:table_blocks) if(block){std::free(block);block=nullptr;}
    assert(mprotect(arena,0x20000,PROT_READ|PROT_WRITE)==0);
    auto*hdr=event_at(arena);prior=event_at(arena+0x10000);stream(hdr,stage);stream(prior,stage);
    parents={};bins={};funcs={};reads={};effects.clear();errors.clear();retired_name.clear();debug_frees.clear();global={};loaded={};DC={};last_input_free=nullptr;
    EvtMgr.EvdTbl.NumDatTbl=32;EvtMgr.EvdTbl.pWork=parents.data();EvtMgr.BinTbl.NumDatTbl=320;EvtMgr.BinTbl.pWork=bins.data();
    EvtMgr.FuncTbl.NumDatTbl=32;EvtMgr.FuncTbl.pWork=funcs.data();EvtMgr.ReadTbl.NumDatTbl=8;EvtMgr.ReadTbl.pWork=reads.data();
    memclr_asm(pool,2*sizeof(Event));new(&pool[0])Event(0);new(&pool[1])Event(0);pool[0].be_flag=0;
    event_pool={};event_pool.pArray=pool;event_pool.nArray=2;event_pool.pAlive=&pool[1];
    EvtMgr.pArray=pool;EvtMgr.nArray=2;EvtMgr.size=sizeof(Event);std::memset(EvtMgr.readEm,0,sizeof(EvtMgr.readEm));
    same_parent=preexisting;std::strcpy(pool[1].Name,preexisting?event_name:prior_name);pool[1].pData=prior;
    std::strcpy(EvtMgr.NowExeEvtName,pool[1].Name);
    fail_table=false;mutate_after_total=stage=="final-mutation";
    auto*incoming_parts=reinterpret_cast<EvtBinEntry*>(arena+hdr->binOfs);
    auto*prior_parts=reinterpret_cast<EvtBinEntry*>(reinterpret_cast<u8*>(prior)+prior->binOfs);
    std::strcpy(incoming_parts[1].name,"shared.bin");std::strcpy(prior_parts[1].name,"shared.bin");
    if(!preexisting)std::strcpy(prior_parts[0].name,"prior.bin");
    assert(EvtMgr.SetEvd(preexisting?event_name:prior_name,prior,arena+0x18000,2)==1);
    assert(EvtMgr.SetFunc(const_cast<char*>("evt__func"),reinterpret_cast<void*>(&end_handler))==1);
    loaded.m_addr=loaded.m_malloc_addr=arena;loaded.m_malloc_heap=4;loaded.m_be_flag=3;loaded.m_condition=2;loaded.m_size=4096;
    std::strcpy(loaded.m_name,file_name);assert(EvtMgr.ReadTbl.SetDat(file_name,&loaded,0,nullptr,2,nullptr)==1);
    global.Disp_flg=0x12340800;fail_table=stage=="model-table";
    for(unsigned i=0;i<128;++i)EspEvModList[i]=reinterpret_cast<cModel*>(arena+0x11000+i*4);
#if RE4DC_CABIN_SOURCE
    for(auto&c:carriers)c={};carrier_fault=false;cabin={};
    observed_unit=&loaded;observed_mram=prior;observed_module=arena+0x17000;observed_bytes=27456;
    unit_valid=allocation_valid=module_valid=true;
    // An unrelated running cabin must not receive this failed work's end.
    cabin.id=0x11c00;cabin.event=&pool[1];cabin.bound=true;cabin.audio=17;cabin.movie=23;
#endif
}
static unsigned matching_errors(const char*key){unsigned count=0;for(const auto&err:errors)count+=err.find(key)!=std::string::npos;return count;}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<u8*>(mmap(reinterpret_cast<void*>(0x90000000),0x20000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    pool=static_cast<Event*>(mmap(reinterpret_cast<void*>(0x8C100000),0x10000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000)&&pool==reinterpret_cast<void*>(0x8C100000));
    unsigned cases=0;
#if !RE4DC_EVD_START_CLEANUP
    // Preserve the original caller characterization as OFF controls. An ON
    // failed start preserves the live prior name, so EvtReadExec now waits for
    // that work; this fixture deliberately does not simulate its completion.
    for(const std::string stage:{"model-table","packet-id","camera-data","final-mutation"})for(bool existing:{false,true})for(u32 flags:{0U,2U,0x40U}){
        setup(stage,existing);++cases;
        assert(EvtMgr.EvtReadExec(file_name,0,flags)==1); // Actual caller still masks init failure.
        assert(!pool[0].isAlive()&&pool[1].isAlive()&&effects["destroy_work"]==1);
        const bool cleanup=RE4DC_EVD_START_CLEANUP;
        for(const char*effect:{"player_reset","partner_return","all_effect_delete","end_callback","subscreen_wait","sound_end"})assert(effects[effect]==unsigned(!cleanup));
        assert(effects["scenario_end"]==unsigned(!cleanup)+unsigned(!(flags&(2|0x40))));
        assert(cleanup?std::strcmp(EvtMgr.NowExeEvtName,pool[1].Name)==0:EvtMgr.NowExeEvtName[0]==0);
        assert(cleanup?global.Disp_flg==0x12340800:!(global.Disp_flg&0x800));
        assert(event_pool.pAlive==&pool[1]&&pool[1].pNext==nullptr&&event_pool.flag==2);
        const bool early=stage=="model-table";
        if(early){
            assert(matching_errors("cDatTbl::GetDatWkNo : memory failed")==unsigned(cleanup?0:96));
            assert(EvtMgr.EvdTbl.ChkDat(event_name)&&retired_name.empty()&&!effects["table_free"]);
            assert(debug_frees.empty());
        }else{
            assert(EvtMgr.EvdTbl.ChkDat(event_name)==int(cleanup)&&retired_name==event_name&&effects["table_free"]==1);
            if(existing&&!cleanup){assert(debug_frees.size()==1&&debug_frees[0]==arena+0x18000);}
            else assert(debug_frees.empty());
        }
        for(unsigned i=0;i<128;++i)
            assert(EspEvModList[i]==((early||cleanup)?reinterpret_cast<cModel*>(arena+0x11000+i*4):nullptr));
        if(!existing){
            assert(EvtMgr.EvdTbl.ChkDat(prior_name));
            assert(parents[0].Dat==prior&&parents[0].dat2==arena+0x18000&&parents[0].Count==1);
            void*bin=nullptr;u8 type=0;int slot=0;
            assert(EvtMgr.BinTbl.GetDat(&bin,&type,"shared.bin",&slot)&&bins[slot].Count==((early||cleanup)?2:1));
            assert(bin==reinterpret_cast<u8*>(prior)+1024);
            assert(EvtMgr.BinTbl.GetDat(&bin,&type,"prior.bin",&slot)&&bins[slot].Count==1&&bin==reinterpret_cast<u8*>(prior)+512);
            assert(EvtMgr.BinTbl.ChkDat("first.bin")==int(early||cleanup));
        }else if(!early&&!cleanup){
            assert(!EvtMgr.BinTbl.ChkDat("first.bin")&&!EvtMgr.BinTbl.ChkDat("shared.bin"));
        }
#if RE4DC_CABIN_SOURCE
        assert(cabin.event==&pool[1]&&cabin.audio==17&&!effects["cabin_audio_close"]&&!effects["cabin_audio_open"]);
#endif
        if(flags&(2|0x40)){assert(!effects["input_free"]&&loaded.m_addr==arena&&EvtMgr.ReadTbl.ChkDat(file_name));}
        else assert(effects["input_free"]==1&&!loaded.m_addr&&!EvtMgr.ReadTbl.ChkDat(file_name));
        assert(effects["injected_packet_mutation"]==(stage=="final-mutation"?1U:0U));
        std::cout<<"INIT_STAGE "<<stage<<" existing="<<existing<<" flags="<<flags<<" parent="<<EvtMgr.EvdTbl.ChkDat(event_name)<<" prior_work_alive=1 end_calls="<<effects["end_callback"]<<" lookup_errors="<<matching_errors("cDatTbl::GetDatWkNo : memory failed")<<" free_input="<<effects["input_free"]<<" PASS\n";
    }
    // Exhaustion is a separate failure: no initialization/end path executes.
    for(u32 flags:{0U,2U,0x40U}){
        setup("valid",true);++cases;pool[0].be_flag=1;std::strcpy(pool[0].Name,"occupied");std::strcpy(EvtMgr.NowExeEvtName,"");
        assert(EvtMgr.EvtReadExec(file_name,0,flags)==1&&effects["pool_log"]==1&&!effects["table_alloc"]&&!effects["end_callback"]);
        assert(pool[0].isAlive()&&pool[1].isAlive()&&EvtMgr.EvdTbl.ChkDat(event_name));
        assert(EspEvModList[0]==reinterpret_cast<cModel*>(arena+0x11000));
    }
    // A valid prior event can own the same pre-existing read. Model-table OOM
    // while starting another work must not turn that reader into free backing.
    for(u32 flags:{0U,2U,0x40U}){
        setup("model-table",true);++cases;
        loaded.m_addr=loaded.m_malloc_addr=prior;
        assert(EvtMgr.EvtReadExec(file_name,0,flags)==1&&pool[1].isAlive()&&pool[1].pData==prior);
        assert(EvtMgr.EvdTbl.ChkDat(event_name));
        assert(RE4DC_EVD_START_CLEANUP?std::strcmp(EvtMgr.NowExeEvtName,event_name)==0:EvtMgr.NowExeEvtName[0]==0);
        if(flags&(2|0x40))assert(!effects["input_free"]&&loaded.m_addr==prior);
        else assert(effects["input_free"]==1&&last_input_free==prior&&!loaded.m_addr);
    }
#endif
    // A malformed new incoming stream does not replace a complete valid owner.
    for(const std::string incoming:{"packet-id","camera-data"}){
        setup(incoming,true);++cases;stream(prior,"valid");
        assert(EvtMgr.SetEvt(arena,static_cast<u32*>(nullptr))==1&&pool[0].pData==prior);
        assert(parents[0].Dat==prior&&parents[0].Count==1&&!effects["end_callback"]);
        assert(pool[0].ModTbl.end()==1);pool[0].be_flag=0;
    }
    // Current Dreamcast host-file backend refuses even with source host mode on.
    for(u32 host_mode:{0U,0x20000U}){
        setup("valid",false);++cases;global.System_flg=host_mode;
        void*out=reinterpret_cast<void*>(1);const auto allocated=effects["table_alloc"];
        assert(HDReadDebugAlloc("x:/soft/room/missing.fcv",&out,1)==0&&!out&&effects["table_alloc"]==allocated);
    }
    // Real invalid-input return, outside valid SetEvt(data)'s address guard.
    setup("valid",false);++cases;assert(pool[0].init(event_name,reinterpret_cast<EvtHeader*>(0x1000))==0);
    assert(!pool[0].pData&&pool[0].Name[0]==0&&!effects["table_alloc"]&&!effects["end_callback"]);
    // Immutable valid data succeeds without normal end side effects.
    setup("valid",false);++cases;
    assert(EvtMgr.SetEvt(arena,static_cast<u32*>(nullptr))==1&&pool[0].isAlive());
    assert(effects["table_alloc"]==1&&!effects["end_callback"]&&std::strcmp(EvtMgr.NowExeEvtName,event_name)==0);
    assert(pool[0].StatusFlag&0x01000000);
    for(auto*p:EspEvModList)assert(!p);
    assert(pool[0].ModTbl.end()==1);pool[0].be_flag=0;
#if RE4DC_EVD_START_CLEANUP
    // Execute the real outer overload and actual failed-init destruction.
    // Snapshots precede the new admission, so shared-bin deltas must unwind.
    for(const std::string stage:{"model-table","packet-id","camera-data","final-mutation"})for(bool existing:{false,true}){
        setup(stage,existing);++cases;
        const auto saved_parents=parents;const auto saved_bins=bins;
        assert(!EvtMgr.SetEvt(arena,static_cast<u32*>(nullptr))&&!pool[0].isAlive()&&pool[1].isAlive());
        if(RE4DC_EVD_START_ROLLBACK||existing){
            assert(!std::memcmp(parents.data(),saved_parents.data(),sizeof(parents)));
            assert(!std::memcmp(bins.data(),saved_bins.data(),sizeof(bins)));
        }else assert(EvtMgr.EvdTbl.ChkDat(event_name));
        assert(!effects["input_free"]&&debug_frees.empty()&&!effects["end_callback"]&&!effects["scenario_end"]);
        assert(std::strcmp(EvtMgr.NowExeEvtName,pool[1].Name)==0&&effects["table_free"]==unsigned(stage!="model-table"));
        for(unsigned i=0;i<128;++i)assert(EspEvModList[i]==reinterpret_cast<cModel*>(arena+0x11000+i*4));
        fail_table=false;mutate_after_total=false;stream(existing?prior:reinterpret_cast<EvtHeader*>(arena),"valid");
        assert(EvtMgr.SetEvt(arena,static_cast<u32*>(nullptr))&&pool[0].isAlive());
        assert(pool[0].pData==(existing?prior:reinterpret_cast<EvtHeader*>(arena)));
        assert(EvtMgr.EvdTbl.ChkDat(event_name)&&!effects["end_callback"]&&!effects["scenario_end"]);
        EvtMgr.destroyNow(&pool[0]);
    }
    // Start by registered name so the outer caller cannot free the input. Only
    // failed init's local effects and immediate reuse of its slot are at issue.
    for(const std::string stage:{"model-table","packet-id","camera-data","final-mutation"})for(bool existing:{false,true}){
        setup(stage,existing);++cases;
        if(!existing)assert(EvtMgr.SetEvd(event_name,arena,nullptr,2)==1);
        const auto saved_parents=parents;const auto saved_bins=bins;
        global.System_flg=0x12340440;global.Status_flg[2]=0x008f0000;
        Event*out=reinterpret_cast<Event*>(1);
        assert(EvtMgr.SetEvt(event_name,&out)==0&&!out&&!pool[0].isAlive());
        assert(event_pool.pAlive==&pool[1]&&event_pool.flag==2&&pool[1].pNext==nullptr);
        assert(std::strcmp(EvtMgr.NowExeEvtName,pool[1].Name)==0);
        assert(global.System_flg==0x12340440&&global.Status_flg[2]==0x008f0000&&global.Disp_flg==0x12340800);
        assert(!std::memcmp(parents.data(),saved_parents.data(),sizeof(parents))&&!std::memcmp(bins.data(),saved_bins.data(),sizeof(bins)));
        assert(!effects["end_callback"]&&!effects["scenario_end"]&&!effects["player_reset"]&&!effects["input_free"]&&debug_frees.empty());
        assert(!effects["partner_return"]&&!effects["all_effect_delete"]&&!effects["sound_end"]&&!effects["subscreen_wait"]);
        assert(!matching_errors("cDatTbl::GetDatWkNo : memory failed"));
#if RE4DC_CABIN_SOURCE
        assert(cabin.event==&pool[1]&&cabin.audio==17&&cabin.bound&&!effects["cabin_audio_close"]&&!effects["cabin_audio_open"]);
#endif
        for(unsigned i=0;i<128;++i)assert(EspEvModList[i]==reinterpret_cast<cModel*>(arena+0x11000+i*4));
        assert(effects["table_free"]==unsigned(stage!="model-table"));
        fail_table=false;mutate_after_total=false;stream(existing?prior:reinterpret_cast<EvtHeader*>(arena),"valid");
        assert(EvtMgr.SetEvt(event_name,&out)==1&&out==&pool[0]&&out->isAlive()&&(out->StatusFlag&0x01000000));
        assert(event_pool.pAlive==out&&out->pNext==&pool[1]&&pool[1].isAlive());
        assert(std::strcmp(EvtMgr.NowExeEvtName,event_name)==0&&out->pData==(existing?prior:reinterpret_cast<EvtHeader*>(arena)));
        assert(!std::memcmp(parents.data(),saved_parents.data(),sizeof(parents))&&!std::memcmp(bins.data(),saved_bins.data(),sizeof(bins)));
        for(auto*p:EspEvModList)assert(!p);
        assert(!effects["end_callback"]&&!effects["scenario_end"]);
        EvtMgr.destroyNow(out); // Fixture disposal, not a newly invented runtime end path.
        assert(effects["table_free"]==unsigned(stage=="model-table"?1:2));
    }
#if RE4DC_CABIN_SOURCE
    char cabin_name[]="event/evd/r11cs00.evd";
    auto carrier_setup=[&](const std::string&stage,unsigned state){
        setup(stage,true);std::strcpy(parents[0].Name,cabin_name);
        cabin={};cabin.id=0x11c00;cabin.movie=23;
        auto&c=carriers[0];c.unit=&loaded;c.generation=41;c.logical=0x1000;c.bytes=observed_bytes;
        c.mram=prior;c.heap=4;c.backing_heap=4;c.module=observed_module;c.state=state;c.role=state==CarrierReady?1:0;
        auto&other=carriers[1];other.unit=arena+0x16000;other.generation=73;other.state=CarrierMram;other.event=&pool[1];other.readers=2;
    };
    for(const std::string stage:{"model-table","packet-id","camera-data","final-mutation"})for(unsigned state:{unsigned(CarrierMram),unsigned(CarrierReady)}){
        carrier_setup(stage,state);++cases;
        const auto saved_carriers=std::array<CabinCarrier,3>{carriers[0],carriers[1],carriers[2]};
        const auto saved_cabin=cabin;const auto saved_parents=parents;const auto saved_bins=bins;
        Event*out=reinterpret_cast<Event*>(1);
        assert(EvtMgr.SetEvt(cabin_name,&out)==0&&!out&&!pool[0].isAlive()&&pool[1].isAlive());
        assert(!std::memcmp(carriers,saved_carriers.data(),sizeof(carriers))&&!std::memcmp(&cabin,&saved_cabin,sizeof(cabin)));
        assert(!std::memcmp(parents.data(),saved_parents.data(),sizeof(parents))&&!std::memcmp(bins.data(),saved_bins.data(),sizeof(bins)));
        assert(!effects["cabin_audio_open"]&&!effects["cabin_audio_close"]&&!effects["cabin_movie_abort"]&&!effects["missing_boundary"]&&!effects["end_callback"]);
        assert(std::strcmp(EvtMgr.NowExeEvtName,pool[1].Name)==0);
        fail_table=false;mutate_after_total=false;stream(prior,"valid");
        assert(EvtMgr.SetEvt(cabin_name,&out)==1&&out==&pool[0]&&carriers[0].event==out);
        assert(cabin.event==out&&cabin.bound&&cabin.audio==17&&effects["cabin_audio_open"]==1);
        // Actual successful binding callbacks dispose the fixture's new binding;
        // normal source event completion/media transport is not simulated here.
        re4dc_cabin_carrier_event_deleted(out);re4dc_cabin_event_deleted(out);EvtMgr.destroyNow(out);
        assert(!carriers[0].event&&!cabin.event&&!cabin.audio&&effects["cabin_audio_close"]==1);
        assert(carriers[1].event==&pool[1]&&carriers[1].readers==2);
    }
    // Each actual carrier refusal precedes init, makes no ownership change and
    // retains another event's binding. Missing is an explicit halt boundary.
    for(unsigned refusal=0;refusal<12;++refusal){
        carrier_setup("valid",CarrierMram);++cases;
        auto&c=carriers[0];
        switch(refusal){
        case 0:carrier_fault=true;break;
        case 1:unit_valid=false;break;
        case 2:allocation_valid=false;break;
        case 3:module_valid=false;break;
        case 4:c.mram=arena;break;
        case 5:c.heap=3;break;
        case 6:c.event=&pool[1];break;
        case 7:c.state=CarrierReference;break;
        case 8:c.state=CarrierReady;c.role=0;break;
        case 9:c.state=CarrierPreparing;break;
        case 10:c.state=CarrierAbsent;break;
        case 11:c.unit=arena;break;
        }
        const auto saved_carriers=std::array<CabinCarrier,3>{carriers[0],carriers[1],carriers[2]};
        const auto saved_cabin=cabin;Event*out=reinterpret_cast<Event*>(1);
        assert(EvtMgr.SetEvt(cabin_name,&out)==0&&!out&&!pool[0].isAlive()&&pool[1].isAlive());
        assert(!std::memcmp(carriers,saved_carriers.data(),sizeof(carriers))&&!std::memcmp(&cabin,&saved_cabin,sizeof(cabin)));
        assert(!effects["table_alloc"]&&!effects["end_callback"]&&effects["missing_boundary"]==1);
        assert(std::strcmp(EvtMgr.NowExeEvtName,pool[1].Name)==0);
        for(unsigned i=0;i<128;++i)assert(EspEvModList[i]==reinterpret_cast<cModel*>(arena+0x11000+i*4));
    }
#endif
    // The local-failure guard must not bypass ordinary explicit event teardown.
    setup("valid",false);++cases;Event*started=nullptr;
    assert(EvtMgr.SetEvd(event_name,arena,nullptr,2)==1&&EvtMgr.SetEvt(event_name,&started)==1);
    assert(EvtMgr.DelEvt(started,0)==1&&!pool[0].isAlive()&&pool[1].isAlive());
    assert(effects["end_callback"]==1&&effects["scenario_end"]==1&&effects["player_reset"]==1&&effects["table_free"]==1);
    assert(!EvtMgr.EvdTbl.ChkDat(event_name)&&EvtMgr.EvdTbl.ChkDat(prior_name));
#endif
    for(auto&block:table_blocks)assert(!block);
    assert(mprotect(arena,0x20000,PROT_READ|PROT_WRITE)==0);
    // Global projected tables are static fixture storage, not owned allocations.
    EvtMgr.EvdTbl.pWork=EvtMgr.BinTbl.pWork=EvtMgr.FuncTbl.pWork=EvtMgr.ReadTbl.pWork=nullptr;
    std::cout<<"EVENT_START_CASES="<<cases<<" txn="<<RE4DC_EVD_ADMISSION_TXN<<" cleanup="<<RE4DC_EVD_START_CLEANUP<<" cabin="<<RE4DC_CABIN_SOURCE<<" PASS\n";
}
