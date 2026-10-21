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
#include "capacity_actual_memory.inc"
#include "../../../game/motion_bridge.cpp"
#include "../../../game/platform/native_motion.cpp"
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
    OSSetCurrentHeap(handle);CurrentHeap=CurrentDbgHeap=4;required_failures=0;stats={};stamp=0;hold=false;files.clear();reads=0;read_hook=nullptr;
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
static void k05_sequential(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];assert(b.joined&&2*b.slab_bytes==64832);
        void* trim=trim_free(83168);
        for(unsigned c=0;c<20;++c)for(unsigned i=0;i<3;++i){const int t=acquire_entry(b,i);re4dc_motion_release(t);}
#if RE4DC_MOTION_CAPACITY
        assert(stats.loads==3&&stats.evictions==0&&b.resident==72224);
#else
        assert(stats.loads==60&&stats.evictions==58&&b.resident<=64832);
#endif
        std::cout<<"K05 capacity="<<RE4DC_MOTION_CAPACITY<<" loads="<<stats.loads<<" evictions="<<stats.evictions<<" resident="<<stats.resident_bytes<<" free="<<re4dc_static_heap_free()<<"\n";
        assert(!required_failures);OSFreeToHeap(Heap[4].handle,trim);
    }assert(!stats.metadata_bytes&&OSCheckHeap(Heap[4].handle)>0);
}

#if RE4DC_MOTION_CAPACITY
static unsigned overflow_count(){unsigned n=0;for(const auto& b:bindings)if(b.archive)for(unsigned i=0;i<b.count;++i)n+=overflow_key(b,i);return n;}
static void valid_heap(){assert(OSCheckHeap(Heap[4].handle)>=0);}
static void k05_coactive_and_required_pin_wait(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);
        std::vector<int> tokens;std::vector<unsigned char*> pointers;std::vector<std::vector<unsigned char>> content;
        for(unsigned i=0;i<3;++i){tokens.push_back(acquire_entry(b,i));pointers.push_back(b.slots[i].data);content.emplace_back(pointers.back(),pointers.back()+word(record(b,i)+4));}
        assert(stats.pinned_bytes==72224&&overflow_count()==1&&pressure_heap_bytes()==17408);
        void* fill=trim_free(64);std::atomic<void*> worker_owner{nullptr};
        auto request=std::async(std::launch::async,[&]{worker_owner=thd_current;return mem_alloc(17408,"required pin wait",0,1,4);});
        assert(request.wait_for(std::chrono::milliseconds(30))==std::future_status::timeout);
        assert(worker_owner.load()&&re4dc_motion_thread_busy(worker_owner));
        for(unsigned i=0;i<3;++i){assert(b.slots[i].data==pointers[i]&&b.slots[i].pins==1);assert(!std::memcmp(pointers[i],content[i].data(),content[i].size()));}
        for(auto token:tokens)re4dc_motion_release(token);
        assert(request.wait_for(std::chrono::seconds(2))==std::future_status::ready);void* need=request.get();assert(need&&!required_failures);
        assert(stats.evictions==1&&overflow_count()==0&&b.slots[0].data==pointers[0]&&b.slots[1].data==pointers[1]);
        assert(!re4dc_motion_thread_busy(worker_owner));OSFreeToHeap(Heap[4].handle,need);OSFreeToHeap(Heap[4].handle,fill);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }assert(!stats.metadata_bytes);std::cout<<"coactive72224/pointer-stability/required-pin-wait/cancellation-owner pass\n";
}
static void required_lock_busy_read(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);
        for(unsigned i=0;i<2;++i){auto t=acquire_entry(b,i);re4dc_motion_release(t);}
        std::mutex m;std::condition_variable cv;bool in_read=false,allow_read=false,in_eval=false,allow_release=false;
        read_hook=[&]{std::unique_lock<std::mutex> l(m);in_read=true;cv.notify_all();cv.wait(l,[&]{return allow_read;});};
        auto consumer=std::async(std::launch::async,[&]{const int token=acquire_entry(b,2);{std::unique_lock<std::mutex> l(m);in_eval=true;cv.notify_all();cv.wait(l,[&]{return allow_release;});}re4dc_motion_release(token);});
        {std::unique_lock<std::mutex> l(m);assert(cv.wait_for(l,std::chrono::seconds(2),[&]{return in_read;}));}
        auto request=std::async(std::launch::async,[&]{return mem_alloc(70000,"required lock busy",0,1,4);});
        assert(request.wait_for(std::chrono::milliseconds(20))==std::future_status::timeout);
        {std::lock_guard<std::mutex> l(m);allow_read=true;cv.notify_all();}
        {std::unique_lock<std::mutex> l(m);assert(cv.wait_for(l,std::chrono::seconds(2),[&]{return in_eval;}));}
        assert(request.wait_for(std::chrono::milliseconds(20))==std::future_status::timeout);
        {std::lock_guard<std::mutex> l(m);allow_release=true;cv.notify_all();}
        consumer.get();assert(request.wait_for(std::chrono::seconds(2))==std::future_status::ready);void* need=request.get();assert(need&&!required_failures);
        read_hook=nullptr;assert(stats.loads==3&&stats.evictions==1&&overflow_count()==0);OSFreeToHeap(Heap[4].handle,need);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }std::cout<<"lock-busy/inflight-read/published-pin/drain-before-retry pass\n";
}
static void concurrent_required_allocators(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);
        for(unsigned i=0;i<3;++i){auto t=acquire_entry(b,i);re4dc_motion_release(t);}void* fill=trim_free(64);
        std::vector<std::future<void*>> jobs;std::atomic<unsigned> ready{0};std::atomic<bool> go{false};
        for(unsigned i=0;i<8;++i)jobs.push_back(std::async(std::launch::async,[&]{++ready;while(!go)std::this_thread::yield();return mem_alloc(2000,"concurrent required",0,1,4);}));
        while(ready!=8)std::this_thread::yield();go=true;std::vector<void*> results;
        for(auto& j:jobs){assert(j.wait_for(std::chrono::seconds(2))==std::future_status::ready);auto* p=j.get();assert(p);results.push_back(p);}
        assert(!required_failures&&stats.evictions==1&&!overflow_count());valid_heap();
        std::vector<std::future<void>> frees;for(auto* p:results)frees.push_back(std::async(std::launch::async,[p]{OSFreeToHeap(Heap[4].handle,p);}));for(auto& f:frees)f.get();
        OSFreeToHeap(Heap[4].handle,fill);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }std::cout<<"eight-concurrent-required-allocators/exact-owner/list-coalescing pass\n";
}
static void binding_admission_reclaims_without_recursion(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);
        for(unsigned i=0;i<3;++i){auto t=acquire_entry(b,i);re4dc_motion_release(t);}assert(overflow_count()==1);
        void* fill=trim_free(64);
        {ActualArchive incoming({320,320});assert(incoming.bind());assert(!overflow_count()&&!required_failures&&stats.evictions==1);}
        assert(!b.slots[2].data&&b.slots[0].data&&b.slots[1].data);OSFreeToHeap(Heap[4].handle,fill);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }std::cout<<"new-binding-metadata/reserve-admission/in-place-reclaim/no-recursive-lock pass\n";
}
static void fragmentation_and_original_failure(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);
        for(unsigned i=0;i<3;++i){auto t=acquire_entry(b,i);re4dc_motion_release(t);}
        // A live source block separates the reclaimable payload from the tail.
        void* barrier=mem_alloc(4096,"live source barrier",0,1,4);assert(barrier);void* fill=trim_free(64);
        void* too_large=mem_alloc(20000,"real fragmented failure",0,1,4);assert(!too_large&&required_failures==1&&!overflow_count());
        unsigned total;const unsigned largest=re4dc_heap_largest_current(&total);assert(largest<20032&&total<20032);valid_heap();
        OSFreeToHeap(Heap[4].handle,barrier);void* retry=mem_alloc(20000,"source barrier released",0,1,4);assert(retry&&required_failures==1);
        OSFreeToHeap(Heap[4].handle,retry);OSFreeToHeap(Heap[4].handle,fill);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }std::cout<<"fragmentation/exhaustive-overflow-reclaim/original-required-failure pass\n";
}
static void aggregate_cap_and_pins(){
    reset();{
        ActualArchive a(std::vector<unsigned>(11,32768));assert(a.bind());auto& b=bindings[0];void* trim=trim_free(400000);std::vector<int> tokens;
        for(unsigned i=0;i<10;++i)tokens.push_back(acquire_entry(b,i));
        assert(overflow_count()==8&&pressure_heap_bytes()==262144&&stats.pinned_bytes==327680);
        bool rejected=false;try{acquire_entry(b,10);}catch(const Missing& e){rejected=std::string(e.what())=="motion reserve slabs pinned";}
        assert(rejected&&pressure_heap_bytes()==262144&&overflow_count()==8&&!required_failures);
        for(auto t:tokens)re4dc_motion_release(t);auto t=acquire_entry(b,10);re4dc_motion_release(t);assert(pressure_heap_bytes()<=262144);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }std::cout<<"unchanged262144-aggregate/pinned-cap/fallback pass\n";
}
static void failed_read_hold_strict_and_retire(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);
        for(unsigned i=0;i<2;++i){auto t=acquire_entry(b,i);re4dc_motion_release(t);}auto saved=files;files.clear();
        bool failed=false;try{acquire_entry(b,2);}catch(const Missing& e){failed=std::string(e.what())=="motion key read";}
        assert(failed&&!overflow_count()&&re4dc_static_heap_free()==83168&&b.slots[0].data&&b.slots[1].data&&!required_failures);files=std::move(saved);
        auto t=acquire_entry(b,2);re4dc_motion_release(t);const auto* p=b.slots[2].data;assert(overflow_count()==1);
        re4dc_motion_hold(1);assert(!re4dc_motion_capacity_retire());assert(b.slots[2].data==p&&overflow_count()==1);re4dc_motion_forget_dead_heaps();
        assert(re4dc_motion_capacity_retire()&&!overflow_count()&&capacity_retiring&&re4dc_static_heap_free()==83168);
        auto one=acquire_entry(b,2);re4dc_motion_release(one);assert(!overflow_count()); // retiring cannot refill a loan
        OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];b.bounded=true;void* trim=trim_free(83168);
        for(unsigned i=0;i<3;++i){auto t=acquire_entry(b,i);re4dc_motion_release(t);}assert(!overflow_count()&&stats.loads==3&&stats.evictions==1);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }std::cout<<"failed-read/hold/strict-bounded/retire-owner/no-refill pass\n";
}
#if RE4DC_MOTION_RESUME
static void movie_loans_keep_owner_tickets(){
    for(unsigned background=0;background<2;++background){
        reset();{
            ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);
            for(unsigned i=0;i<3;++i){auto t=acquire_entry(b,i);re4dc_motion_release(t);}
            re4dc_motion_movie_begin();void* need;
            if(background)need=std::async(std::launch::async,[]{return mem_alloc(70000,"background during movie",0,1,4);}).get();
            else need=mem_alloc(70000,"movie own staging",0,1,4);
            assert(need&&!overflow_count()&&!required_failures);re4dc_motion_movie_finish(0);
            assert(resume_pending.contains(0,2)==!background);
            OSFreeToHeap(Heap[4].handle,need);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
        }
    }std::cout<<"movie-owned-overflow-loan-ticket/background-pressure-not-ticket pass\n";
}
#endif
static void unsupported_contexts_do_not_deadlock(){
    reset();{
        ActualArchive a({22400,32416,17408});assert(a.bind());auto& b=bindings[0];void* trim=trim_free(83168);std::vector<int> tokens;
        for(unsigned i=0;i<3;++i)tokens.push_back(acquire_entry(b,i));void* fill=trim_free(64);const auto* p=b.slots[2].data;
        assert(!mem_alloc(17000,"unsupported same evaluator",0,1,4));assert(required_failures==1&&b.slots[2].data==p&&b.slots[2].pins==1&&overflow_count()==1);
        for(auto t:tokens)re4dc_motion_release(t);int old=irq_disable();assert(!mem_alloc(17000,"unsupported masked IRQ",0,1,4));irq_restore(old);
        assert(required_failures==2&&b.slots[2].data==p&&overflow_count()==1&&!required_waiters);OSFreeToHeap(Heap[4].handle,fill);OSFreeToHeap(Heap[4].handle,trim);valid_heap();
    }std::cout<<"unsupported-same-evaluator/masked-IRQ-decline (source closure required) pass\n";
}
#endif
int main(){k05_sequential();
#if RE4DC_MOTION_CAPACITY
k05_coactive_and_required_pin_wait();required_lock_busy_read();concurrent_required_allocators();binding_admission_reclaims_without_recursion();fragmentation_and_original_failure();aggregate_cap_and_pins();failed_read_hold_strict_and_retire();unsupported_contexts_do_not_deadlock();
#if RE4DC_MOTION_RESUME
movie_loans_keep_owner_tickets();
#endif
#endif
std::cout<<"actual source/SDK capacity checks pass\n";}

