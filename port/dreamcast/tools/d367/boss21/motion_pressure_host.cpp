// Exercises the actual native_motion.cpp implementation with synthetic FCVs.
// No game payloads, emulator, substitute eviction model or copied policy code.
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <cstdarg>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
#include "../../../game/platform/native_motion.cpp"

struct Missing : std::runtime_error { using std::runtime_error::runtime_error; };
static std::map<void*,unsigned> allocations;
static std::map<std::string,std::vector<unsigned char>> files;
static unsigned allocated,peak,reads;
static int heap_free=0;
static unsigned fail_allocations;
extern "C" void re4dc_log(const char*,...) {}
extern "C" void re4dc_missing(const char* s) { throw Missing(s); }
extern "C" int re4dc_motion_current_heap() { return 4; }
extern "C" int re4dc_static_heap_free() { return heap_free; }
extern "C" int re4dc_motion_owner_live(const void* p) { assert(allocations.count(const_cast<void*>(p)));return 1; }
extern "C" void* re4dc_motion_alloc(unsigned n) {
    if(fail_allocations){--fail_allocations;return nullptr;}
    void* p=nullptr;assert(!posix_memalign(&p,32,(n+31)&~31U));
    allocations[p]=n;allocated+=n;peak=std::max(peak,allocated);return p;
}
extern "C" void re4dc_motion_free(void* p) {
    if(!p)return;auto i=allocations.find(p);assert(i!=allocations.end());allocated-=i->second;allocations.erase(i);std::free(p);
}
namespace re4dc::storage {
void Arena::init(std::uint8_t* p,std::size_t n) { base_=p;capacity_=n;used_=0; }
ReadResult read_file(Arena& arena,const char* path) {
    auto i=files.find(path);if(i==files.end())return {nullptr,0,"missing",0};
    assert(i->second.size()<=arena.capacity());std::memcpy(arena.base(),i->second.data(),i->second.size());++reads;
    return {arena.base(),i->second.size(),nullptr,1};
}
}
static void put(std::vector<unsigned char>& b,unsigned o,unsigned v) { std::memcpy(b.data()+o,&v,4); }
struct Fixture {
    unsigned no;std::vector<unsigned char> archive,records;
    Fixture(unsigned index,const std::vector<unsigned>& sizes,unsigned slab=32416,bool bounded=false):no(index),archive(32+sizes.size()*32),records(sizes.size()*20) {
        auto& b=bindings[no];assert(!b.archive);b.archive=archive.data();b.bytes=archive.size();b.records=records.data();b.count=sizes.size();
        const unsigned meta=aligned(b.count*sizeof(Slot));b.slots=static_cast<Slot*>(re4dc_motion_alloc(meta));std::memset(b.slots,0,meta);stats.metadata_bytes+=meta;
        b.slab_bytes=slab;b.bounded=bounded;
        if(slab){for(auto*& p:b.slab)p=static_cast<unsigned char*>(re4dc_motion_alloc(slab));stats.metadata_bytes+=2*slab;}
        for(unsigned i=0;i<sizes.size();++i) {
            std::vector<unsigned char> f(sizes[i],0);f[0]=1;f[2]=1;put(f,12,16);f.back()=static_cast<unsigned char>(i+1);
            const unsigned crc=net_crc32le(f.data(),f.size());unsigned fnv=2166136261U;for(auto v:f)fnv=(fnv^v)*16777619U;
            put(records,20*i,32+i*32);put(records,20*i+4,sizes[i]);put(records,20*i+8,crc);put(records,20*i+12,fnv);
            std::memcpy(archive.data()+32+i*32,f.data(),16);char path[64];std::snprintf(path,sizeof(path),"/cd/dc/mot/%08x-%08x.fcv",crc,fnv);files[path]=std::move(f);
        }
    }
    void seed(unsigned i,bool slab=false,unsigned slab_index=0,bool pinned=false) {
        auto& b=bindings[no];const unsigned n=word(record(b,i)+4);assert(!b.slots[i].data);
        auto* p=slab?b.slab[slab_index]:static_cast<unsigned char*>(re4dc_motion_alloc(n));assert(!slab||n<=b.slab_bytes);
        std::memset(p,0,n);std::memcpy(p,archive.data()+32+i*32,16);
        b.slots[i]={p,unsigned(pinned),++stamp};b.resident+=n;stats.resident_bytes+=n;
    }
    void hot(unsigned i) { put(records,20*i+16,1);const auto n=word(record(bindings[no],i)+4);bindings[no].hot_bytes+=n;stats.hot_bytes+=n;seed(i); }
    ~Fixture() { auto& b=bindings[no];for(unsigned i=0;i<b.count;++i)b.slots[i].pins=0;release_binding(b); }
};
static void clean() { assert(allocations.empty());assert(!allocated);stats={};stamp=0;hold=false;files.clear();reads=peak=fail_allocations=0;heap_free=0; }
static void reserved_fill() {
    // The exact selected em12 hot entry byte sizes, metadata only (H050 census).
    std::vector<unsigned> sizes={22400,16608,17664,9152,13216,7840,9216,19648,17696,5632,20896,15648,5696,8640,18784,2304,320,224,5248,8352};const unsigned count=sizes.size();sizes.push_back(32416);sizes.push_back(32416);
    {
        Fixture f(0,sizes);for(unsigned i=0;i<count;++i)f.hot(i);
        assert(stats.resident_bytes==225184);const unsigned before=allocated;
        load(bindings[0],count);load(bindings[0],count+1);
#if RE4DC_MOTION_PRESSURE_BACKING
        assert(stats.evictions==0);assert(allocated==before);assert(stats.resident_bytes==290016);assert(pressure_heap_bytes()==225184);
        for(unsigned i=0;i<count;++i)assert(bindings[0].slots[i].data);
#else
        assert(stats.evictions>0); // proves the baseline regression is actually exercised
#endif
        std::cout<<"reserved-fill backing="<<RE4DC_MOTION_PRESSURE_BACKING<<" evictions="<<stats.evictions<<" bytes="<<allocated<<"\n";
    }clean();
}
#if RE4DC_MOTION_PRESSURE_BACKING
static void aggregate_heap_and_pins() {
    {
        Fixture a(0,{32768,32768,32768,32768,32768},32768),b(1,{32768,32768,32768,32768},32768);
        for(unsigned i=0;i<4;++i){a.seed(i);b.seed(i);}a.seed(4,true); // occupied fixed backing is outside heap cap
        auto& x=bindings[0];unsigned* table=nullptr;const int token=re4dc_motion_acquire(x.archive+word(record(x,0)),&table);
        assert(token&&x.slots[0].pins==1&&re4dc_motion_thread_busy(thd_current));const auto* pinned=x.slots[0].data;const auto* reserve=x.slots[4].data;
        assert(pressure_heap_bytes()==262144);pressure_room_for(32768);
        assert(stats.evictions==1);assert(x.slots[0].data==pinned);assert(x.slots[4].data==reserve);assert(pressure_heap_bytes()==229376);
        re4dc_motion_release(token);assert(!x.slots[0].pins&&!re4dc_motion_thread_busy(thd_current));
    }clean();
}
static void all_heap_pinned_and_hold() {
    {
        Fixture f(0,std::vector<unsigned>(8,32768));std::vector<int> tokens;
        for(unsigned i=0;i<8;++i){f.seed(i);unsigned* table=nullptr;tokens.push_back(re4dc_motion_acquire(bindings[0].archive+word(record(bindings[0],i)),&table));assert(tokens.back());}
        const unsigned before=allocated;bool rejected=false;
        try{pressure_room_for(32768);}catch(const Missing& e){rejected=std::string(e.what())=="motion pressure live leases exceed budget";}
        assert(rejected&&stats.evictions==0&&allocated==before);
        hold=true;auto* slots=bindings[0].slots;bindings[0].slots=reinterpret_cast<Slot*>(1);
        pressure_room_for(32768); // must return before touching suspended slot metadata
        bindings[0].slots=slots;hold=false;assert(stats.evictions==0&&allocated==before);
        for(int token:tokens)re4dc_motion_release(token);assert(!re4dc_motion_thread_busy(thd_current));
    }clean();
}
static void bounded_no_spill() {
    {
        Fixture f(0,{32768,32768,32768},32768,true);f.seed(0,true,0,true);f.seed(1,true,1,false);heap_free=1048576;
        const unsigned before=allocated;load(bindings[0],2);
        assert(allocated==before&&stats.evictions==1&&bindings[0].slots[0].data==bindings[0].slab[0]);
        assert(bindings[0].slots[2].data==bindings[0].slab[1]);
        bindings[0].slots[2].pins=1;bool rejected=false;
        try{load(bindings[0],1);}catch(const Missing& e){rejected=std::string(e.what())=="motion reserve slabs pinned";}
        assert(rejected&&allocated==before); // high free heap still cannot bypass strict v3 policy
    }clean();
}
static void cold_pool_keeps_cap() {
    {
        Fixture f(0,std::vector<unsigned>(11,32768),32768);for(unsigned i=0;i<8;++i)f.hot(i);
        f.seed(8,true,0);f.seed(9,true,1);heap_free=400000; // pool margin passes; spill margin does not
        const unsigned before=allocated;load(bindings[0],10);
        assert(pressure_heap_bytes()==262144&&stats.evictions==1&&allocated==before);
        assert(!reserved_data(bindings[0],bindings[0].slots[10].data));
    }clean();
}
static void allocation_failure_keeps_leases() {
    {
        Fixture f(0,std::vector<unsigned>(10,32768),32768);
        for(unsigned i=0;i<7;++i)f.hot(i);f.seed(7,true,0);f.seed(8,true,1);put(f.records,20*9+16,1);
        auto& b=bindings[0];unsigned* table=nullptr;
        const int token=re4dc_motion_acquire(b.archive+word(record(b,0)),&table);assert(token);
        const auto* pinned=b.slots[0].data;const auto* slab0=b.slots[7].data;const auto* slab1=b.slots[8].data;
        fail_allocations=1;load(b,9); // real allocation fails, then actual OOM eviction retries it
        assert(stats.evictions==1&&pressure_heap_bytes()==229376);
        assert(b.slots[0].data==pinned&&b.slots[7].data==slab0&&b.slots[8].data==slab1);
        assert(!fail_allocations);re4dc_motion_release(token);assert(!re4dc_motion_thread_busy(thd_current));
    }clean();
}
static void heap_load_keeps_cap() {
    {
        Fixture f(0,std::vector<unsigned>(9,32768),32768);for(unsigned i=0;i<8;++i)f.hot(i);put(f.records,20*8+16,1);
        const unsigned before=allocated;load(bindings[0],8);assert(pressure_heap_bytes()==262144&&stats.evictions==1);assert(allocated==before);
    }clean();
}
static void three_cold_loop(const std::vector<unsigned>& sizes) {
    {
        Fixture f(0,sizes);heap_free=93824;const unsigned before=allocated;
        for(unsigned cycle=0;cycle<20;++cycle)for(unsigned i=0;i<3;++i)load(bindings[0],i);
#if RE4DC_MOTION_RESERVE_PACK
        assert(stats.loads==3&&stats.evictions==0&&stats.hits==57);
#else
        assert(stats.loads==60&&stats.evictions==58);
#endif
        assert(allocated==before&&pressure_heap_bytes()==0);
        std::cout<<"three-cold pack="<<RE4DC_MOTION_RESERVE_PACK<<" loads="<<stats.loads<<" evictions="<<stats.evictions<<"\n";
    }clean();
}
#if RE4DC_MOTION_RESERVE_PACK
static void packed_coactive_pins() {
    {
        Fixture f(0,{11744,7744,12224,32384,16000});heap_free=93824;const unsigned before=allocated;
        auto& b=bindings[0];std::vector<int> tokens;std::vector<unsigned char*> pointers;std::vector<std::vector<unsigned char>> copies;
        for(unsigned i=0;i<4;++i) {
            unsigned* table=nullptr;tokens.push_back(re4dc_motion_acquire(b.archive+word(record(b,i)),&table));assert(tokens.back());
            pointers.push_back(b.slots[i].data);const unsigned bytes=word(record(b,i)+4);copies.emplace_back(b.slots[i].data,b.slots[i].data+bytes);
        }
        assert(b.slots[1].data==b.slab[0]+11744&&b.slots[2].data==b.slab[0]+19488);
        bool rejected=false;try{load(b,4);}catch(const Missing& e){rejected=std::string(e.what())=="motion reserve slabs pinned";}
        assert(rejected&&stats.evictions==0&&allocated==before);
        re4dc_motion_release(tokens.back());tokens.pop_back();load(b,4); // only the fourth unpinned clip can go
        assert(stats.evictions==1&&allocated==before&&b.slots[4].data==b.slab[1]);
        for(unsigned i=0;i<3;++i) {
            assert(b.slots[i].data==pointers[i]&&b.slots[i].pins==1);
            assert(!std::memcmp(b.slots[i].data,copies[i].data(),copies[i].size()));
            re4dc_motion_release(tokens[i]);
        }
        assert(!re4dc_motion_thread_busy(thd_current));
    }clean();
}
static void packed_holes_owners_and_retirement() {
    {
        Fixture f(0,{8000,8000,8000,8000,8192,16000,7008});auto& b=bindings[0];const unsigned before=allocated;
        for(unsigned i=0;i<5;++i)load(b,i);
        auto* neighbor=b.slots[2].data;std::vector<unsigned char> copy(neighbor,neighbor+8000);
        discard(b,1);load(b,6); // reuse an interior hole without moving its neighbors
        assert(b.slots[6].data==b.slab[0]+8000&&b.slots[2].data==neighbor&&allocated==before);
        assert(!std::memcmp(neighbor,copy.data(),copy.size()));f.seed(5);assert(pressure_heap_bytes()==16000);
        assert(re4dc_motion_evict_one()==16000&&re4dc_motion_evict_one()==0);assert(allocated==before);
        re4dc_motion_hold(1);assert(re4dc_motion_evict_one()==0);
        // The real bridge requires an allocation base, never an interior FCV.
        // The host owner mock asserts that rule during the actual resume recount.
        assert(re4dc_motion_forget_dead_heaps()==0&&!hold&&pressure_heap_bytes()==0);
        assert(b.slots[6].data==b.slab[0]+8000&&b.slots[2].data==neighbor);
    }clean(); // source retirement frees both slabs exactly once, no interior frees
}
static void packed_bad_read_keeps_backing() {
    for(unsigned fault=0;fault<3;++fault) {
        {
            Fixture f(0,{8000,8000});auto& b=bindings[0];load(b,0);const unsigned before=allocated;
            auto* e=f.records.data()+20;char path[64];std::snprintf(path,sizeof(path),"/cd/dc/mot/%08x-%08x.fcv",word(e+8),word(e+12));
            const char* expected="motion key read";
            if(fault==0)files.erase(path);
            if(fault==1){files[path].back()^=1;expected="motion identity/header mismatch";}
            if(fault==2) {
                auto payload=files[path];put(payload,12,payload.size());std::memcpy(f.archive.data()+64,payload.data(),16);
                const unsigned crc=net_crc32le(payload.data(),payload.size());unsigned fnv=2166136261U;for(auto v:payload)fnv=(fnv^v)*16777619U;
                put(f.records,28,crc);put(f.records,32,fnv);std::snprintf(path,sizeof(path),"/cd/dc/mot/%08x-%08x.fcv",crc,fnv);files[path]=std::move(payload);
                expected="motion key offset";
            }
            bool rejected=false;try{load(b,1);}catch(const Missing& e){rejected=std::string(e.what())==expected;}
            assert(rejected&&allocated==before&&b.slots[0].data==b.slab[0]&&!b.slots[1].data);
        }clean();
    }
}

#endif
#endif
int main(){reserved_fill();
#if RE4DC_MOTION_PRESSURE_BACKING
aggregate_heap_and_pins();all_heap_pinned_and_hold();bounded_no_spill();cold_pool_keeps_cap();heap_load_keeps_cap();allocation_failure_keeps_leases();
three_cold_loop({11744,7744,12224});three_cold_loop({22400,9152,17408});three_cold_loop({22400,9152,32416});
#if RE4DC_MOTION_RESERVE_PACK
packed_coactive_pins();packed_holes_owners_and_retirement();packed_bad_read_keeps_backing();
#endif
#endif
std::cout<<"native motion pressure cases PASS\n";}
