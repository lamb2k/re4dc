// Actual init/end/delete/manager/data-unit policy. External services are counters.
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
void EventMgr::destroyNow(Event*p){++effects["destroy_work"];retired_name=p->Name;event_pool.destroyNow(p);}
int EventMgr::GetRead(void**out,int*slot,char*name){u8 type=0;return ReadTbl.GetDat(out,&type,name,nullptr)&&ReadTbl.GetWkNo(slot,name);}
int EventMgr::EvtReadMram(char*,int em,int*out,int,u32){assert(em==0);++effects["input_read"];*out=int(reinterpret_cast<std::uintptr_t>(loaded.m_addr));return 1;}
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
}
static unsigned matching_errors(const char*key){unsigned count=0;for(const auto&err:errors)count+=err.find(key)!=std::string::npos;return count;}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<u8*>(mmap(reinterpret_cast<void*>(0x90000000),0x20000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    pool=static_cast<Event*>(mmap(reinterpret_cast<void*>(0x8C100000),0x10000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000)&&pool==reinterpret_cast<void*>(0x8C100000));
    unsigned cases=0;
    for(const std::string stage:{"model-table","packet-id","camera-data","final-mutation"})for(bool existing:{false,true})for(u32 flags:{0U,2U,0x40U}){
        setup(stage,existing);++cases;
        assert(EvtMgr.EvtReadExec(file_name,0,flags)==1); // Actual caller still masks init failure.
        assert(!pool[0].isAlive()&&pool[1].isAlive()&&effects["destroy_work"]==1);
        assert(effects["player_reset"]==1&&effects["partner_return"]==1&&effects["all_effect_delete"]==1);
        assert(effects["end_callback"]==1&&effects["subscreen_wait"]==1&&effects["sound_end"]==1);
        assert(EvtMgr.NowExeEvtName[0]==0 && !(global.Disp_flg&0x800));
        const bool early=stage=="model-table";
        if(early){
            assert(matching_errors("cDatTbl::GetDatWkNo : memory failed")==96);
            assert(EvtMgr.EvdTbl.ChkDat(event_name)&&retired_name.empty()&&!effects["table_free"]);
            assert(debug_frees.empty());
        }else{
            assert(!EvtMgr.EvdTbl.ChkDat(event_name)&&retired_name==event_name&&effects["table_free"]==1);
            if(existing){assert(debug_frees.size()==1&&debug_frees[0]==arena+0x18000);}
            else assert(debug_frees.empty());
        }
        for(unsigned i=0;i<128;++i)
            assert(EspEvModList[i]==(early?reinterpret_cast<cModel*>(arena+0x11000+i*4):nullptr));
        if(!existing){
            assert(EvtMgr.EvdTbl.ChkDat(prior_name));
            assert(parents[0].Dat==prior&&parents[0].dat2==arena+0x18000&&parents[0].Count==1);
            void*bin=nullptr;u8 type=0;int slot=0;
            assert(EvtMgr.BinTbl.GetDat(&bin,&type,"shared.bin",&slot)&&bins[slot].Count==(early?2:1));
            assert(bin==reinterpret_cast<u8*>(prior)+1024);
            assert(EvtMgr.BinTbl.GetDat(&bin,&type,"prior.bin",&slot)&&bins[slot].Count==1&&bin==reinterpret_cast<u8*>(prior)+512);
            assert(EvtMgr.BinTbl.ChkDat("first.bin")==int(early));
        }else if(!early){
            assert(!EvtMgr.BinTbl.ChkDat("first.bin")&&!EvtMgr.BinTbl.ChkDat("shared.bin"));
        }
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
        assert(EvtMgr.EvdTbl.ChkDat(event_name)&&EvtMgr.NowExeEvtName[0]==0);
        if(flags&(2|0x40))assert(!effects["input_free"]&&loaded.m_addr==prior);
        else assert(effects["input_free"]==1&&last_input_free==prior&&!loaded.m_addr);
    }
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
    assert(pool[0].ModTbl.end()==1);pool[0].be_flag=0;
    for(auto&block:table_blocks)assert(!block);
    assert(mprotect(arena,0x20000,PROT_READ|PROT_WRITE)==0);
    // Global projected tables are static fixture storage, not owned allocations.
    EvtMgr.EvdTbl.pWork=EvtMgr.BinTbl.pWork=EvtMgr.FuncTbl.pWork=EvtMgr.ReadTbl.pWork=nullptr;
    std::cout<<"EVENT_INIT_CASES="<<cases<<" txn="<<RE4DC_EVD_ADMISSION_TXN<<" PASS\n";
}
