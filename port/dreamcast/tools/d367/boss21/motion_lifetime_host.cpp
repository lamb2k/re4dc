// Actual SDK allocator + source mem_alloc + bridge + native motion. No asset bytes.
#include <algorithm>
#include <atomic>
#include <cassert>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <future>
#include <functional>
#include <iostream>
#include <map>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include <kos.h>
#include "main_mem.h"
#include "dolphin/os/OSAlloc.h"
std::recursive_mutex host_irq;
thread_local unsigned host_irq_depth;
MemHeap Heap[13];
static u8 CurrentHeap=4,CurrentDbgHeap=4,Dalloc_flg=0;
static OSHeapDescriptor* HeapHead;
static OSHeapDescriptor heap_backup[13];
using u16=std::uint16_t;
extern "C" int __OSCurrHeap;
static std::vector<std::string> events;
static unsigned invalid_native_frees, invalid_source_frees;
static const void* source_archive_for_test;
extern "C" { int re4dc_diag; }
static std::atomic<unsigned> required_failures;
struct Logger { void err(int,int,const char*,...){++required_failures;} } logger,*pLog=&logger;
extern "C" {
void* OSInitAlloc(void*,void*,int);int OSCreateHeap(void*,void*);void OSDestroyHeap(int);int OSSetCurrentHeap(int);
int OSDisableInterrupts(){return irq_disable();}
int OSRestoreInterrupts(int old){irq_restore(old);return old;}
void OSReport(const char*,...){}
void memclr_asm(void* p,unsigned n){std::memset(p,0,n);}
}
u8 MemGetCurrentHeap(){return CurrentHeap;}
#include "native_motion.h"
#include "lifetime_actual_memory.inc"
#include "actual_motion_bridge.inc"
#include "actual_native_motion.inc"
struct Missing : std::runtime_error {using std::runtime_error::runtime_error;};
extern "C" void re4dc_log(const char*,...){}
extern "C" void re4dc_missing(const char* why){throw Missing(why);}
extern "C" int re4dc_static_heap_free(){int old=irq_disable();int n=OSCheckHeap(Heap[4].handle);irq_restore(old);return n;}
extern "C" unsigned re4dc_heap_largest_current(unsigned* total){
    int old=irq_disable();unsigned largest=0;*total=0;
    for(auto* c=HeapHead[Heap[4].handle].free;c;c=c->next){const unsigned n=c->size-32;*total+=n;largest=std::max(largest,n);}
    irq_restore(old);return largest;
}
static std::map<std::string,std::vector<unsigned char>> files;
static unsigned reads;
extern "C" unsigned re4dc_fixture_source_frame(){return 100;}
static std::function<void()> read_hook;
namespace re4dc::storage {
void Arena::init(std::uint8_t* p,std::size_t n){base_=p;capacity_=n;used_=0;}
ReadResult read_file(Arena& a,const char* path){
    if(read_hook)read_hook();
    const auto it=files.find(path);if(it==files.end())return {nullptr,0,"missing",0};
    assert(it->second.size()<=a.capacity());std::memcpy(a.base(),it->second.data(),it->second.size());++reads;
    return {a.base(),it->second.size(),nullptr,1};
}
}
static void put(std::vector<unsigned char>& b,unsigned o,unsigned v) { std::memcpy(b.data()+o,&v,4); }
struct ActualArchive {
    std::vector<unsigned char> archive;
    ActualArchive(const std::vector<unsigned>& sizes) {
        const unsigned n=sizes.size()+1,first=aligned(16+8*n),mtc=first+32*sizes.size(),rel=aligned(mtc+32+20*sizes.size()),bytes=rel+64;
        archive.resize(bytes);put(archive,0,n);put(archive,4,rel);
        for(unsigned i=0;i<sizes.size();++i) {
            std::vector<unsigned char> f(sizes[i],0);f[0]=1;f[2]=1;put(f,12,16);f.back()=static_cast<unsigned char>(i+1);
            const unsigned crc=net_crc32le(f.data(),f.size());unsigned fnv=2166136261U;for(auto v:f)fnv=(fnv^v)*16777619U;
            const unsigned off=first+32*i;put(archive,16+4*i,off);std::memcpy(archive.data()+16+4*n+4*i,"FCV",4);std::memcpy(archive.data()+off,f.data(),16);
            put(archive,mtc+32+20*i,off);put(archive,mtc+36+20*i,sizes[i]);put(archive,mtc+40+20*i,crc);put(archive,mtc+44+20*i,fnv);
            char path[64];std::snprintf(path,sizeof(path),"/cd/dc/mot/%08x-%08x.fcv",crc,fnv);files[path]=std::move(f);
        }
        put(archive,16+4*(n-1),mtc);std::memcpy(archive.data()+16+4*n+4*(n-1),"MTC",4);std::memcpy(archive.data()+mtc,"R4MOTBL\0",8);
        put(archive,mtc+8,2);put(archive,mtc+12,sizes.size());put(archive,mtc+16,20);put(archive,mtc+20,net_crc32le(archive.data()+mtc+32,20*sizes.size()));put(archive,mtc+24,bytes);put(archive,mtc+28,32768);
    }
    bool bind(){return re4dc_motion_bind(archive.data(),archive.size())==1;}
    ~ActualArchive(){re4dc_motion_unbind(archive.data());}
};
static int acquire_entry(Binding& b,unsigned i){unsigned* table=nullptr;int token=re4dc_motion_acquire(b.archive+word(record(b,i)),&table);assert(token&&table);return token;}

alignas(32) static unsigned char arena[2*1024*1024];
static void reset(){
    assert(!stats.metadata_bytes);assert(reinterpret_cast<std::uintptr_t>(arena)+sizeof(arena)<0xffffffffUL);
    std::memset(arena,0,sizeof(arena));
    auto* start=OSInitAlloc(arena,arena+sizeof(arena),13);HeapHead=reinterpret_cast<OSHeapDescriptor*>(arena);
    for(auto& h:Heap)h={-1,0,0,0,{}};
    const auto begin=(reinterpret_cast<std::uintptr_t>(start)+31)&~std::uintptr_t(31);
    const int handle=OSCreateHeap(reinterpret_cast<void*>(begin),arena+sizeof(arena));assert(handle>=0);
    Heap[4]={handle,unsigned(begin),unsigned(reinterpret_cast<std::uintptr_t>(arena+sizeof(arena))),0,{}};
    OSSetCurrentHeap(handle);CurrentHeap=CurrentDbgHeap=4;required_failures=0;stats={};stamp=0;hold=false;files.clear();reads=0;read_hook=nullptr; events.clear(); invalid_native_frees=invalid_source_frees=0;
#if RE4DC_MOTION_CAPACITY
    assert(!required_waiters);capacity_retiring=false;
#if RE4DC_MOTION_RESUME
    resume_journal={};resume_pending={};resume_pending_live=false;capacity_movie_owner=nullptr;
#endif
#endif
}
static void* trim_free(unsigned wanted){
    const unsigned available=re4dc_static_heap_free();assert(available>wanted+32);
    void* p=mem_alloc(available-wanted-32,nullptr,0,1,4);assert(p);assert(re4dc_static_heap_free()==int(wanted));return p;
}

// Boundary instrumentation forwards to the actual release SDK allocator, even
// on a retired descriptor, to demonstrate its list mutation rather than invent
// a replacement allocator policy. Each case is an isolated process.
extern "C" void __real_OSFreeToHeap(int,void*);
extern "C" void __wrap_OSFreeToHeap(int h,void* p){
    assert(h>=0&&h<13);
    if(HeapHead[h].size<0){
        const bool native=p!=source_archive_for_test;
        if(native)++invalid_native_frees;else ++invalid_source_frees;
        events.push_back(native?"native-free-after-destroy":"source-free-after-destroy");
    }
    __real_OSFreeToHeap(h,p);
}
struct OSModuleHeader{};
#include "lifetime_read_module.inc"
static bool epilog_saw_binding;
static const void* epilog_archive;
static bool has_binding(const void* p){for(const auto& b:bindings)if(b.archive==p)return true;return false;}
static void DLL_Unlink(OSModuleHeader*){events.push_back("epilog");epilog_saw_binding=has_binding(epilog_archive);}
extern "C" void re4dc_effect_unbind(const void*){events.push_back("effect-unbind");}
extern "C" void re4dc_ui_unbind_enemy(const void*){events.push_back("ui-unbind");}
static void Debug_free(void* p){Debug_free_h(p,CurrentDbgHeap);}
ReadModule EmReadModule[4];
struct Global{unsigned Disp_flg;} global,*pG=&global;
#define BitSet(a,b) ((a)=(b))
#define BitOff(a,b) ((a)&=~(b))
static bool transport_ok;
static unsigned transport_calls;
static int readEmData(ReadModule* m,int,void* p,unsigned n){++transport_calls;if(!transport_ok)return 0;m->pArc=p;m->size=n;return 1;}
static void setEmModule(ReadModule*,int){}
#include "lifetime_actual_read.inc"
struct Loaded {
    ActualArchive donor;
    unsigned char* archive;
    explicit Loaded():donor({12032,7744,12224}){
        archive=(unsigned char*)mem_alloc(donor.archive.size(),"source module",0,1,4);assert(archive);
        std::memcpy(archive,donor.archive.data(),donor.archive.size());source_archive_for_test=archive;
        assert(re4dc_motion_bind(archive,donor.archive.size())==1);
        auto& m=EmReadModule[0];std::memset(&m,0,sizeof(m));m.pArc=archive;m.flag=4;m.size=donor.archive.size();
        const int t=acquire_entry(bindings[0],0);re4dc_motion_release(t);
    }
};
static void begin(){reset();for(auto& m:EmReadModule)std::memset(&m,0,sizeof(m));}
static int test_lifetime(const std::string& name){
    begin();
    if(name=="slot-failure"){
        for(auto& m:EmReadModule)m.pArc=arena;
        global.Disp_flg=0x12340800;transport_calls=0;assert(!readEm(1,nullptr,0));
        assert(global.Disp_flg==0xfffff7ff&&transport_calls==0);
        for(auto& m:EmReadModule)m.pArc=nullptr;
        transport_ok=false;global.Disp_flg=0x12340800;assert(!readEm(1,nullptr,0));
        assert(global.Disp_flg==0x12340800&&transport_calls==1);
        transport_ok=true;assert(readEm(1,arena,32)==arena&&global.Disp_flg==0x12340800);
        std::cout<<"slot-exhaustion: original0x12340800 becomes0xfffff7ff; transport-failure/success restore original PASS (defect reproduced)\n";return 0;
    }
    if(name=="bind-failure-retry"){
        ActualArchive a({12032,7744,12224});void*trim=trim_free(16000);const unsigned before=re4dc_static_heap_free();
        assert(!a.bind());assert(!stats.metadata_bytes&&!stats.resident_bytes&&!has_binding(a.archive.data()));
        assert(re4dc_static_heap_free()==int(before)&&required_failures>0&&invalid_native_frees==0);
        OSFreeToHeap(Heap[4].handle,trim);assert(a.bind());
        re4dc_motion_unbind(a.archive.data());assert(!stats.metadata_bytes&&OSCheckHeap(Heap[4].handle)>0);
        std::cout<<"native bind reserve failure: actual partial allocations unwind, same archive retry succeeds PASS; readEmData caller refusal is terminal\n";return 0;
    }
    Loaded m;
    const int handle=Heap[4].handle;
    if(name=="normal"){
        EmReadInit();assert(!stats.metadata_bytes&&invalid_native_frees==0&&invalid_source_frees==0);
        assert(OSCheckHeap(handle)>0);std::cout<<"normal InitModule: native/source allocations freed while owner live PASS\n";
    }else if(name=="reset"){
        MemClearAllHeap();assert(Heap[4].handle==-1&&HeapHead[handle].size==-1&&HeapHead[handle].free==nullptr);
        EmReadInit();assert(invalid_native_frees>=2);assert(HeapHead[handle].size==-1&&HeapHead[handle].free!=nullptr);
#if RE4DC_RESET_HEAP_FIX
        assert(invalid_source_frees==0);
#else
        assert(invalid_source_frees==1);
#endif
        assert(!stats.metadata_bytes);
        std::cout<<"destroy-before-InitModule fix="<<RE4DC_RESET_HEAP_FIX<<" native-after-destroy="<<invalid_native_frees<<" source-after-destroy="<<invalid_source_frees<<" actual-SDK disabled-descriptor relink PASS (defect reproduced)\n";
    }else if(name=="predrain-control"){
        re4dc_motion_retire_all();assert(!stats.metadata_bytes);MemClearAllHeap();EmReadInit();
        assert(!invalid_native_frees);
#if RE4DC_RESET_HEAP_FIX
        assert(!invalid_source_frees);
#else
        assert(invalid_source_frees==1);
#endif
        std::cout<<"explicit pre-destroy retire positive control: no native invalid free PASS; test call only, no runtime repair\n";
    }else if(name=="pin-live"||name=="pin-reset"){
        const int token=acquire_entry(bindings[0],0);bool failed=false;
        if(name=="pin-reset"){MemClearAllHeap();assert(Heap[4].handle==-1&&stats.pinned_bytes>0);}
        try{EmReadInit();}catch(const Missing& e){failed=true;assert(std::string(e.what()).find("pinned")!=std::string::npos);}
        assert(failed&&!invalid_native_frees);
        if(name=="pin-live")assert(Heap[4].handle==handle&&HeapHead[handle].size>0);
        re4dc_motion_release(token);EmReadInit();
        if(name=="pin-reset")assert(invalid_native_frees>=2);else assert(!invalid_native_frees);
        std::cout<<name<<": unbind pin guard triggers "<<(name=="pin-reset"?"AFTER heap destroyed (defect reproduced)":"BEFORE live-heap frees (positive control)")<<" PASS\n";
    }else if(name=="borrowed-header"){
        auto& b=bindings[0];const void* header=b.archive+word(record(b,0));
        unsigned* proxy=(unsigned*)((const unsigned char*)header+12);unsigned* work=proxy;
        {Re4dcMotionLease scoped(header,&work,proxy);assert(scoped.external()&&work!=proxy&&stats.pinned_bytes>0);}
        assert(work==proxy&&!stats.pinned_bytes);EmReadInit();
        unsigned* table=nullptr;assert(re4dc_motion_acquire(header,&table)==0&&table==nullptr&&work==proxy);
        std::cout<<"borrowed FCV: scoped pin ends/restores proxy; unbind removes binding but does not clear caller raw header/table PASS; no evaluator-after-free or gameplay overlap claimed\n";
    }else if(name=="epilog-order"){
        EmReadModule[0].flag|=2;EmReadModule[0].pModule=(OSModuleHeader*)arena;epilog_archive=m.archive;epilog_saw_binding=true;
        EmReadInit();assert(!epilog_saw_binding);assert(events.size()==9&&events[0]=="epilog"&&events[1]=="effect-unbind"&&events[2]=="ui-unbind");
        std::cout<<"InitModule DLL boundary observes native binding already removed; injected observer, not selected gameplay callback PASS\n";
    }else assert(false);
    return 0;
}
int main(int argc,char**argv){assert(argc==2);try{return test_lifetime(argv[1]);}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
