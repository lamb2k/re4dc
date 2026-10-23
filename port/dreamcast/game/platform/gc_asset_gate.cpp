#include "include/gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
#include <cstdio>
#include <cstring>
#include <atomic>
extern "C" void re4dc_log(const char*, ...);
namespace re4dc_gcasset {
namespace {
constexpr unsigned Capacity = 1024, KindBytes = 24, IdBytes = 80;
#include "include/gc_asset_sha.inc"
struct Seen { unsigned char signature[16]; };
static_assert(sizeof(Seen)==16,"GC asset seen-table budget");
Seen seen[Capacity];
const CatalogRow* catalog;
unsigned catalog_rows, room, visit, wired, checked_mask, used, overflow, errors;
unsigned emissions[ConsumerCount];
bool active, catalog_ok = true;
struct Queued { Consumer consumer; char kind[KindBytes], id[IdBytes]; Digest digest; unsigned room, visit; };
Queued queue[32];
std::atomic_flag queue_lock = ATOMIC_FLAG_INIT;
std::atomic<unsigned> queue_faults{0}, queue_active{0};
unsigned queue_head, queue_tail;
struct TicketSlot { unsigned serial, room, visit; };
TicketSlot tickets[32];unsigned ticket_serial, ticket_count;
const char* names[] = {"source_geometry", "texture", "effect_picture", "weapon", "font", "ui", "sound_bank", "sound_stream", "movie"};
const char* provenances[] = {"unknown", "gc", "ps2", "authored"};
bool token(const char* p, unsigned limit) {
    if(!p || !*p)return false;
    unsigned n = 0;
    for(; p[n]; ++n) {
        const unsigned char c = p[n];
        if(n + 1 >= limit || !((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
            c == '/' || c == '.' || c == '_' || c == ':' || c == '-'))return false;
    }
    return true;
}
void hex(const Digest& digest, char out[65]) {
    const char* alphabet = "0123456789abcdef";
    for(unsigned i=0;i<32;++i) { out[2*i]=alphabet[digest.bytes[i]>>4];out[2*i+1]=alphabet[digest.bytes[i]&15]; }
    out[64]=0;
}
Provenance resolve(const char* kind, const char* id, const Digest& digest) {
    if(!catalog_ok)return Unknown;
    for(unsigned i=0;i<catalog_rows;++i) {
        const CatalogRow& c=catalog[i];
        if(!std::strcmp(c.kind,kind) && !std::strcmp(c.id,id) && !std::memcmp(c.digest.bytes,digest.bytes,32))return c.provenance;
    }
    return Unknown;
}
}
Digest fingerprint(const void* data, unsigned count) {
    IdentitySha hash;Digest result{};
    if(!data && count) { ++queue_faults;return result; }
    hash.update(data,count);hash.finish(result.bytes);return result;
}
bool install(const CatalogRow* rows, unsigned count) {
    if(active) { ++errors;return false; }
    catalog=nullptr;catalog_rows=0;catalog_ok=false;
    if(count>65536 || (count && !rows))return false;
    for(unsigned i=0;i<count;++i) {
        const CatalogRow& c=rows[i];
        if(!token(c.kind,KindBytes) || !token(c.id,IdBytes) || unsigned(c.provenance)>Authored)return false;
        for(unsigned j=0;j<i;++j)if(!std::strcmp(c.kind,rows[j].kind) && !std::strcmp(c.id,rows[j].id) &&
            !std::memcmp(c.digest.bytes,rows[j].digest.bytes,32))return false;
    }
    catalog=rows;catalog_rows=count;catalog_ok=true;return true;
}
void begin(unsigned r, unsigned v, unsigned mask) {
    if(active) { ++errors;end(0); }
    room=r;visit=v;wired=mask;checked_mask=used=overflow=errors=0;
    std::memset(emissions,0,sizeof emissions);active=true;
    errors=queue_faults.exchange(0);
    if(queue_lock.test_and_set(std::memory_order_acquire)) { ++errors;queue_active.store(0); }
    else {
        if(ticket_count || queue_head!=queue_tail)++errors;
        queue_active.store(ticket_count==0 && queue_head==queue_tail);
        queue_lock.clear(std::memory_order_release);
    }
    re4dc_log("GC-ASSET-BEGIN v=1 room=%04x visit=%u wired=%03x required=%03x catalog=%u catalog_ok=%u\n",
        room,visit,wired,Required,catalog_rows,unsigned(catalog_ok));
}
AudioTicket audio_ticket() {
    if(queue_lock.test_and_set(std::memory_order_acquire)) { ++queue_faults;return {32,0}; }
    AudioTicket ticket{32,0};
    if(queue_active.load() && ticket_count<32 && ticket_serial!=0xffffffffU) {
        for(unsigned i=0;i<32;++i)if(!tickets[i].serial) {
            tickets[i]={++ticket_serial,room,visit};ticket={i,ticket_serial};++ticket_count;break;
        }
    } else ++queue_faults;
    queue_lock.clear(std::memory_order_release);return ticket;
}
void close_audio_admission() { queue_active.store(0); }
void queued(AudioTicket ticket, Consumer consumer, const char* kind, const char* id, const Digest& digest) {
    if(queue_lock.test_and_set(std::memory_order_acquire)) { ++queue_faults;return; }
    if(ticket.slot>=32 || !ticket.serial || tickets[ticket.slot].serial!=ticket.serial) {
        ++queue_faults;queue_lock.clear(std::memory_order_release);return;
    }
    const TicketSlot captured=tickets[ticket.slot];tickets[ticket.slot].serial=0;--ticket_count;
    if(unsigned(consumer)>=ConsumerCount || !token(kind,KindBytes) || !token(id,IdBytes)) {
        ++queue_faults;queue_lock.clear(std::memory_order_release);return;
    }
    const unsigned next=(queue_tail+1)%32;
    if(next==queue_head) { ++queue_faults;queue_lock.clear(std::memory_order_release);return; }
    Queued& q=queue[queue_tail];q.consumer=consumer;std::strcpy(q.kind,kind);std::strcpy(q.id,id);q.digest=digest;
    q.room=captured.room;q.visit=captured.visit;queue_tail=next;
    queue_lock.clear(std::memory_order_release);
}
void pump() {
    for(;;) {
        if(queue_lock.test_and_set(std::memory_order_acquire)) { ++queue_faults;break; }
        if(queue_head==queue_tail) { queue_lock.clear(std::memory_order_release);break; }
        const Queued q=queue[queue_head];queue_head=(queue_head+1)%32;queue_lock.clear(std::memory_order_release);
        if(!active || q.room!=room || q.visit!=visit) {
            if(active)++errors;else re4dc_log("GC-ASSET-ERROR v=1 why=audio-room-lifetime\n");
        } else emitted(q.consumer,q.kind,q.id,q.digest);
    }
    const unsigned faults=queue_faults.exchange(0);
    if(active)errors+=faults;
    else if(faults)re4dc_log("GC-ASSET-ERROR v=1 why=unowned-audio count=%u\n",faults);
}
void checked(Consumer consumer) {
    if(!active)return;
    if(unsigned(consumer)>=ConsumerCount) { ++errors;return; }
    checked_mask |= 1U << consumer;
}
void emitted(Consumer consumer, const char* kind, const char* id, const Digest& digest) {
    if(!active) { re4dc_log("GC-ASSET-ERROR v=1 why=no-room\n");return; }
    if(unsigned(consumer)>=ConsumerCount || !token(kind,KindBytes) || !token(id,IdBytes)) { ++errors;return; }
    ++emissions[consumer];checked(consumer);
    const Provenance p=resolve(kind,id,digest);
    // Even PS2 emissions contribute consumer liveness. Their payload verdict
    // comes only from the exact catalog match above, never the exception list.
    if(p==PS2 || p==Authored)return;
    IdentitySha hash;hash.update(kind,std::strlen(kind)+1);hash.update(id,std::strlen(id)+1);hash.update(digest.bytes,32);
    unsigned char signature[32];hash.finish(signature);
    unsigned i=0;for(;i<used;++i)if(!std::memcmp(seen[i].signature,signature,16))break;
    if(i<used)return;
    if(used==Capacity) { ++overflow;return; }
    std::memcpy(seen[used++].signature,signature,16);
    char sha[65];hex(digest,sha);
    re4dc_log("GC-ASSET v=1 room=%04x visit=%u kind=%s id=%s sha256=%s provenance=%s consumer=%s action=emit\n",
        room,visit,kind,id,sha,provenances[p],names[consumer]);
}
void end(unsigned frame) {
    if(!active) { re4dc_log("GC-ASSET-ERROR v=1 why=no-room-end\n");return; }
    queue_active.store(0);pump();
    if(queue_lock.test_and_set(std::memory_order_acquire))++errors;
    else {
        if(ticket_count || queue_head!=queue_tail)++errors;
        queue_lock.clear(std::memory_order_release);
    }
    errors+=queue_faults.exchange(0);
    re4dc_log("GC-ASSET-END v=1 room=%04x visit=%u frame=%u wired=%03x checked=%03x required=%03x unique=%u overflow=%u errors=%u catalog_ok=%u source_geometry=%u texture=%u effect_picture=%u weapon=%u font=%u ui=%u sound_bank=%u sound_stream=%u movie=%u\n",
        room,visit,frame,wired,checked_mask,Required,used,overflow,errors,unsigned(catalog_ok),
        emissions[0],emissions[1],emissions[2],emissions[3],emissions[4],emissions[5],emissions[6],emissions[7],emissions[8]);
    active=false;
}
#if defined(RE4DC_GC_ASSET_TEST)
void test_queue_lock(bool held) {
    if(held)queue_lock.test_and_set(std::memory_order_acquire);else queue_lock.clear(std::memory_order_release);
}
#endif
}
#endif
