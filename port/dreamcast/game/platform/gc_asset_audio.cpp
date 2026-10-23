#include "include/gc_asset_audio.h"
#if RE4DC_GC_ASSET_GATE
#include <atomic>
#include <cstring>
namespace re4dc_gcasset {
namespace {
#include "include/gc_asset_sha.inc"
struct Bank {
    std::atomic<unsigned> generation{0},bound{0},mram{0},aram{0};
    Digest pending[2]{};unsigned ready=0;
} banks[14];
std::atomic_flag records=ATOMIC_FLAG_INIT;
std::atomic<unsigned> faults{0};unsigned serial;
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void (*before_publish)();
#endif
struct Progress {
    const void* owner=nullptr;unsigned bank=0,part=0,total=0,consume=0,next=0,generation=0,hashed=0;
    IdentitySha hash;bool valid=false;
} progress;
void fault(){
    faults.fetch_add(1,std::memory_order_relaxed);progress.valid=false;
    if(progress.owner && progress.bank<14){banks[progress.bank].bound.store(0);banks[progress.bank].generation.store(0);}
}
CheckedAsset bind(const char* kind,const Digest& digest){
    constexpr char hex[]="0123456789abcdef";char id[41];
    for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
    return bind_checked(kind,id,digest);
}
}
void bank_begin(const void* owner,unsigned bank,unsigned part,unsigned bytes){
    if(progress.owner && progress.valid && progress.next!=progress.total)fault();
    progress={};
    if(bank<14)banks[bank].bound.store(0,std::memory_order_release);
    if(!owner || bank>=14 || (part!=1 && part!=2) || !bytes){if(bank<14)banks[bank].generation.store(0);fault();return;}
    if(records.test_and_set(std::memory_order_acquire)){banks[bank].generation.store(0);fault();return;}
    auto& b=banks[bank];b.bound.store(0,std::memory_order_release);
    if(serial==0xffffffffU){b.generation.store(0);records.clear(std::memory_order_release);fault();return;}
    b.generation.store(++serial,std::memory_order_release);
    if(part==1)b.ready=0;else b.ready&=1U;
    progress.owner=owner;progress.bank=bank;progress.part=part;progress.total=progress.consume=bytes;
    progress.generation=b.generation.load();progress.valid=true;
    records.clear(std::memory_order_release);
}
void bank_piece(const void* owner,unsigned part,unsigned offset,const void* data,unsigned bytes){
    auto& p=progress;
    if(!p.valid || owner!=p.owner || part!=p.part || offset!=p.next || !data || !bytes || bytes>p.total-p.next){fault();return;}
    // SND_PAD_SKIP deliberately does not read discarded GC-sized padding.
    // For prebuilt AIC1, hash exactly its consumed header + AICA image, not the
    // stale DVD_BUFF bytes passed through the padding-only transfer callback.
    if(!offset && part==2 && bytes>=96){
        unsigned magic,total;std::memcpy(&magic,data,4);std::memcpy(&total,static_cast<const unsigned char*>(data)+8,4);
        if(magic==0x31434941U){if(total>p.total-96){fault();return;}p.consume=96+total;}
    }
    const unsigned remaining=p.consume>offset?p.consume-offset:0,take=bytes<remaining?bytes:remaining;
    if(take){p.hash.update(data,take);p.hashed+=take;}p.next+=bytes;
}
void bank_end(const void* owner,unsigned part){
    auto& p=progress;
    if(!p.valid || owner!=p.owner || part!=p.part || p.next!=p.total || p.hashed!=p.consume){fault();return;}
    Digest digest;p.hash.finish(digest.bytes);p.valid=false;p.owner=nullptr;
    if(records.test_and_set(std::memory_order_acquire)){fault();return;}
    auto& b=banks[p.bank];
    if(b.generation.load()!=p.generation){records.clear(std::memory_order_release);fault();return;}
    b.pending[part-1]=digest;b.ready|=1U<<(part-1);records.clear(std::memory_order_release);
}
unsigned bank_generation(unsigned bank){return bank<14?banks[bank].generation.load(std::memory_order_acquire):0;}
void bank_pump(){
    const unsigned failed=faults.exchange(0);
    if(failed)unresolved(SoundBank,"bank-source-lifetime");
    for(unsigned bank=0;bank<14;++bank){
        if(records.test_and_set(std::memory_order_acquire)){faults.fetch_add(1);return;}
        auto& b=banks[bank];const unsigned generation=b.generation.load();const bool ready=b.ready==3 && b.bound.load()!=generation;
        Digest mram{},aram{};if(ready){mram=b.pending[0];aram=b.pending[1];}records.clear(std::memory_order_release);
        if(!ready)continue;
        const CheckedAsset m=bind("sound-mram",mram),a=bind("sound-aram",aram);
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
        if(before_publish){auto callback=before_publish;before_publish=nullptr;callback();}
#endif
        if(records.test_and_set(std::memory_order_acquire)){faults.fetch_add(1);continue;}
        if(b.generation.load()==generation && b.ready==3){
            b.mram.store(m.value);b.aram.store(a.value);b.bound.store(generation,std::memory_order_release);
        }
        records.clear(std::memory_order_release);
    }
}
AudioUse play_ticket(Consumer consumer,CheckedAsset asset){
    AudioUse use;use.consumer=consumer;use.count=1;use.assets[0]=asset;use.tickets[0]=audio_ticket();return use;
}
AudioUse bank_ticket(unsigned bank,unsigned generation){
    if(bank>=14 || !generation)return play_ticket(SoundBank,{});
    const auto& b=banks[bank];
    if(b.generation.load(std::memory_order_acquire)!=generation || b.bound.load(std::memory_order_acquire)!=generation)return play_ticket(SoundBank,{});
    const CheckedAsset m{b.mram.load()},a{b.aram.load()};
    if(b.generation.load(std::memory_order_acquire)!=generation || b.bound.load(std::memory_order_acquire)!=generation)return play_ticket(SoundBank,{});
    AudioUse use=play_ticket(SoundBank,m);use.count=2;use.assets[1]=a;use.tickets[1]=audio_ticket();return use;
}
void played(const AudioUse& use){
    for(unsigned i=0;i<use.count && i<2;++i)queued_checked(use.tickets[i],use.consumer,use.assets[i]);
}
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void audio_test_records_lock(bool held){if(held)records.test_and_set();else records.clear();}
void audio_test_before_publish(void (*callback)()){before_publish=callback;}
#endif
}
#endif
