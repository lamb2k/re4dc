#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <vector>
#include <string>
#include <sys/mman.h>
using u8=std::uint8_t;using s8=std::int8_t;using u16=std::uint16_t;using s16=std::int16_t;using u32=std::uint32_t;using s32=std::int32_t;using f32=float;
struct Vec{float x,y,z;};using Mtx=float[3][4];
#define PLACEMENT_NEW_DEFINED
#define RE4_MEM_LO 0x8c000000u
#define RE4_MEM_HI 0x8cffffffu
static unsigned checks,cases,mem_allocs,mem_frees,errors;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"CHECK %u line%d %s\n",checks,__LINE__,#x);std::abort();}}while(0)
static unsigned char*arena;static unsigned bump;
static void* host_alloc(unsigned n,int,int){++mem_allocs;CHECK(bump+n<0x10000);void*p=arena+bump;bump=(bump+n+31)&~31u;return p;}
static void Mem_free(void*){++mem_frees;}
static void* Debug_alloc(unsigned n,int){return host_alloc(n,0,0);}
static void Debug_free(void*p){Mem_free(p);}
static void memclr_asm(void*p,unsigned n){std::memset(p,0,n);}
#define MEM_ALLOC host_alloc
struct Logger{void err(int,int,const char*,...){++errors;}void warn(int,int,const char*,...){}} logger,*pLog=&logger;
extern "C" void re4dc_log(const char*,...){}
#include "manager_actual_host.h"
class cModel;class cLit;
#include "event_actual_declarations.inc"
#include "event_actual_offset_checks.inc"
static u32 raw_flags(const void*p){u32 v;std::memcpy(&v,(const unsigned char*)p+__builtin_offsetof(cUnit,be_flag),4);return v;}
static void raw_set(void*p,u32 v){std::memcpy((unsigned char*)p+__builtin_offsetof(cUnit,be_flag),&v,4);}
static unsigned table_ends,destructors,run_calls,begin_calls,cancel_calls;
static std::vector<u32> destructor_flags;
static std::vector<unsigned> destructor_types;
static bool fail_table,fail_total;
static bool EvtChk(u32 f,u32 mask){return (f&mask)!=0;}
static Event* slot(EventMgr&m,unsigned n){return reinterpret_cast<Event*>(reinterpret_cast<u8*>(m.pArray)+m.size*n);}
struct Global{u32 Stop_flg,Debug_flg[4];} global,*pG=&global;
struct Keys{u32 trg;} Key;
static void*EspEvModList[128];
int DatTbl::end(){++table_ends;if(pWork){auto*e=reinterpret_cast<Event*>(reinterpret_cast<unsigned char*>(this)-__builtin_offsetof(Event,ModTbl));destructor_flags.push_back(raw_flags(e));destructor_types.push_back(e->Type);++destructors;}pWork=nullptr;NumDatTbl=0;return 1;}
int DatTbl::init(int n){if(fail_table)return 0;NumDatTbl=n;pWork=reinterpret_cast<DatTblEntry*>(0x4000);return 1;}
int Event::CalMaxTotalFrame(int*a,int*b){*a=1;*b=1;return !fail_total;}
int Event::CalMaxFrame(int*a,int){*a=1;return 1;}
int EventMgr::GetFunc(void**out,char*){u32 zero=0;std::memcpy(out,&zero,4);return 0;}
static EvtHeader*header;
int EventMgr::GetEvd(void**out,char*,int){*out=header;return 1;}
void Event::DebugDisp(){++run_calls;}
void Event::ExeBeginEvt(Event*,int){++begin_calls;}
int Event::Run(){++run_calls;return 1;}
int Event::RunEvtCancel(){++cancel_calls;return 1;}
// External event-end service boundary; actual destroyNow/manager/destructors run.
int EventMgr::DelEvt(void*p,int){destroyNow(static_cast<Event*>(p));return 1;}
EventMgr EvtMgr;
#include "event_actual_methods.inc"
static int actual_failure_reader_scan(EventMgr&m,u32 base,u32 bytes){
    auto nArray=m.nArray;auto pArray=m.pArray;auto size=m.size;
    struct Unit{u32 m_size;} value{bytes};auto*current=&value;int borrowed=0;
#include "event_actual_reader_scan.inc"
    return borrowed;
}
class cSat:public cUnit{public:u8 m_Flag;int isAlive();};
#include "sat_actual_predicate.inc"
static void prepare(Event*e,const char*name="event"){
    std::strcpy(e->Name,name);e->StatusFlag=0x00800000|0x00100000;e->DelTimer=0;e->ModTbl.pWork=reinterpret_cast<DatTblEntry*>(0x4000);
}
static void empty(EventMgr&m){while(m.pAlive)m.destroyNow(m.pAlive);m.dieCheck();m.dieCheck();if(m.pArray)m.arrayFree();m.roomInit();bump=0;fail_table=fail_total=false;}
static void start(EventMgr&m,unsigned n=2){empty(m);CHECK(m.arrayAlloc(n)==1);CHECK(m.countActiveWork()==0);CHECK(m.pAlive==nullptr);++cases;}
static void flags_zero(const Event*e){CHECK(raw_flags(e)==0);}
static void destructor_observed(unsigned before,u32 flags){CHECK(destructors==before+1);CHECK(destructor_flags.back()==flags);CHECK(destructor_types.back()==0);}
static void direct_scans(EventMgr&m){
    ++cases;CHECK(m.Run()==1);CHECK(m.IsAliveEvt(reinterpret_cast<u32*>(const_cast<char*>("absent")),0,1)==0);CHECK(actual_failure_reader_scan(m,0x8c018000,0x100)==0);CHECK(m.DelAll()==1);
}
static int off_control(const char*mode){
    auto&m=EvtMgr;m.roomInit();bump=0;m.arrayAlloc(2);
    if(!std::strcmp(mode,"raw-count"))m.countActiveWork();
    else if(!std::strcmp(mode,"create"))m.create(0);
    else if(!std::strcmp(mode,"index"))m.create(0,0);
    else if(!std::strcmp(mode,"back"))m.createBack(0);
    else if(!std::strcmp(mode,"direct-del"))m.DelAll();
    else if(!std::strcmp(mode,"direct-alive"))m.IsAliveEvt(reinterpret_cast<u32*>(const_cast<char*>("none")),0,1);
    else if(!std::strcmp(mode,"reader"))actual_failure_reader_scan(m,0x8c018000,0x100);
    else {
        m.nArray=1;m.construct(slot(m,0),0);m.addListFront(slot(m,0));auto*e=slot(m,0);prepare(e);raw_set(e,0xa5a50001);
        if(!std::strcmp(mode,"immediate"))m.destroyNow(e);
        else if(!std::strcmp(mode,"deferred")){m.destroy(e);m.dieCheck();m.dieCheck();}
        else if(!std::strcmp(mode,"dead-count")){e->~Event();m.countActiveWork();}
        else std::abort();
    }
    std::fprintf(stderr,"UNEXPECTED_CONTROL_RETURN %s\n",mode);return 91;
}
int main(int argc,char**argv){
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x8c000000),0x20000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));CHECK(arena==reinterpret_cast<unsigned char*>(0x8c000000));header=reinterpret_cast<EvtHeader*>(arena+0x18000);std::memset(header,0,sizeof(*header));header->pacOfs=128;
    if(argc>1)return off_control(argv[1]);
#if RE4DC_EVENT_MANAGER_STORAGE_FLAGS
    auto&m=EvtMgr;
    CHECK(sizeof(u32)==4);CHECK(__builtin_offsetof(Event,be_flag)==__builtin_offsetof(cUnit,be_flag));CHECK(re4dcEventStorageFlags::offset==__builtin_offsetof(Event,be_flag));
    start(m);for(unsigned i=0;i<2;++i)flags_zero(slot(m,i));direct_scans(m);
    // Policy accesses only the four flag bytes, even with no live Event/vptr.
    auto*raw=slot(m,1);std::memset(raw,0xa7,sizeof(Event));std::vector<unsigned char>image(sizeof(Event));std::memcpy(image.data(),raw,sizeof(Event));u32 word=0x12340000;std::memcpy(image.data()+__builtin_offsetof(Event,be_flag),&word,4);re4dcEventStorageFlags::store(raw,word);CHECK(std::memcmp(image.data(),raw,sizeof(Event))==0);CHECK(re4dcEventStorageFlags::load(raw)==word);re4dcEventStorageFlags::set(raw,0x600);word|=0x600;std::memcpy(image.data()+__builtin_offsetof(Event,be_flag),&word,4);CHECK(std::memcmp(image.data(),raw,sizeof(Event))==0);re4dcEventStorageFlags::store(raw,0);CHECK(re4dcEventStorageFlags::alive(raw)==0);CHECK(m.countActiveWork()==0);++cases;direct_scans(m);
    // Front creation links only constructed objects; untouched second slot is raw.
    auto*a=m.create(7);CHECK(a==slot(m,0)&&a->Type==7&&a->effNo==0&&m.pAlive==a);CHECK(m.countActiveWork()==1);flags_zero(slot(m,1));prepare(a,"outer");
    a->StatusFlag=0x20000000;unsigned runs=run_calls;CHECK(m.Run()==1);CHECK(run_calls==runs+2&&m.pAlive==a&&raw_flags(a)==1);a->StatusFlag=0x80000;++cases;
    auto*b=m.create(9);CHECK(b==slot(m,1)&&m.pAlive==b&&b->pNext==a&&a->pNext==nullptr);prepare(b,"inner");CHECK(m.create(0)==nullptr);CHECK(m.countActiveWork()==2);++cases;
    // Same object bytes outside flag word remain as destructor leaves them.
    raw_set(b,0xa5a50001);unsigned d=destructors;u8 policy=m.flag;m.destroyNow(b);CHECK(m.flag==policy&&m.pAlive==a&&a->pNext==nullptr);destructor_observed(d,0xa5a50001);flags_zero(b);CHECK(m.countActiveWork()==1);++cases;
    b=m.create(11);CHECK(b==slot(m,1)&&b->Type==11&&m.pAlive==b&&b->pNext==a);prepare(b);raw_set(b,0x5a5a0001);d=destructors;m.destroy(b);CHECK(destructors==d&&m.pAlive==a&&raw_flags(b)==(0x5a5a0001|0x200));m.dieCheck();CHECK(destructors==d&&raw_flags(b)==(0x5a5a0001|0x600));m.dieCheck();destructor_observed(d,0x5a5a0601);flags_zero(b);CHECK(m.countActiveWork()==1);m.dieCheck();CHECK(destructors==d+1);++cases;
    m.destroyNow(a);flags_zero(a);direct_scans(m);
    // Indexed and back paths use the same Event storage policy and list ordering.
    start(m);b=m.create(3,1);CHECK(b==slot(m,1)&&m.pAlive==b);prepare(b);a=m.create(4,0);CHECK(a==slot(m,0)&&a->pNext==b&&m.pAlive==a);prepare(a);CHECK(m.create(2,0)==nullptr&&m.create(2,2)==nullptr);++cases;
    d=destructors;CHECK(m.DelAll()==1&&m.pAlive==nullptr&&m.flag==2);CHECK(destructors==d+2);flags_zero(a);flags_zero(b);++cases;
    start(m);b=m.createBack(5);CHECK(b==slot(m,1));prepare(b);a=m.createBack(6);CHECK(a==slot(m,0)&&m.pAlive==b&&b->pNext==a);prepare(a);CHECK(m.createBack(0)==nullptr);++cases;
    // Actual failed Event::init and actual SetEvt cleanup retain the other Event.
    start(m);a=m.create(0);prepare(a,"prior");a->StatusFlag=0x80000;a->pData=header;u32 oldflags=raw_flags(a);std::vector<unsigned char>prior(sizeof(Event));std::memcpy(prior.data(),a,sizeof(Event));
    fail_table=true;Event*out=reinterpret_cast<Event*>(0x1234);CHECK(m.SetEvt(const_cast<char*>("failed-table"),&out)==0&&out==nullptr);CHECK(m.pAlive==a&&raw_flags(a)==oldflags&&std::memcmp(prior.data(),a,sizeof(Event))==0);flags_zero(slot(m,1));++cases;
    fail_table=false;fail_total=true;d=destructors;CHECK(m.SetEvt(const_cast<char*>("failed-frame"),&out)==0&&out==nullptr);CHECK(m.pAlive==a&&std::memcmp(prior.data(),a,sizeof(Event))==0);destructor_observed(d,1);flags_zero(slot(m,1));++cases;
    fail_total=false;CHECK(m.SetEvt(const_cast<char*>("nested-success"),&out)==1&&out==slot(m,1));CHECK(out->StatusFlag&0x01000000);CHECK(m.pAlive==out&&out->pNext==a&&m.countActiveWork()==2);CHECK(actual_failure_reader_scan(m,u32(header),sizeof(*header))==1);++cases;
    CHECK(m.IsAliveEvt(reinterpret_cast<u32*>(const_cast<char*>("prior")),0,1)==1);CHECK(m.IsAliveEvt(reinterpret_cast<u32*>(const_cast<char*>("prior")),0,0)==0);CHECK(m.IsAliveEvt(reinterpret_cast<u32*>(const_cast<char*>("nested-success")),0,1)==1);++cases;
    m.destroyNow(out);CHECK(actual_failure_reader_scan(m,u32(header),sizeof(*header))==1);m.destroyNow(a);CHECK(actual_failure_reader_scan(m,u32(header),sizeof(*header))==0);direct_scans(m);
    // Destruction itself clears only601, then manager zeroes all32 flag bits.
    start(m,1);a=m.create(0);prepare(a);raw_set(a,0xa5a50601);d=destructors;a->~Event();destructor_observed(d,0xa5a50601);CHECK(raw_flags(a)==(0xa5a50601&~0x601u));raw_set(a,0);m.pAlive=nullptr;CHECK(m.countActiveWork()==0);++cases;
    // Non-Event policy still calls actual custom SAT predicate, including m_Flag4.
    cSat sat;sat.be_flag=1;sat.m_Flag=0;CHECK(re4dcManagerStorageFlags<cSat>::alive(&sat)==0);sat.m_Flag=4;CHECK(re4dcManagerStorageFlags<cSat>::alive(&sat)==1);sat.be_flag|=0x200;CHECK(re4dcManagerStorageFlags<cSat>::alive(&sat)==0);++cases;
    empty(m);CHECK(m.pArray==nullptr&&mem_allocs==mem_frees);std::printf("EVENT_STORAGE cases=%u checks=%u PASS\n",cases,checks);return 0;
#else
    return 92;
#endif
}
