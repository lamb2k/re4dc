#include "include/gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
#include <cstdio>
#include <cstring>
#include <atomic>
extern "C" void re4dc_log(const char*, ...);
namespace re4dc_gcasset {
namespace {
constexpr unsigned CatalogLimit=16376,KindBytes=16,IdBytes=48,UnknownLimit=8;
#include "include/gc_asset_sha.inc"
unsigned char seen[2048];
AssetDescription unknown_assets[UnknownLimit];unsigned unknown_count,catalog_epoch;
CatalogReadAt catalog_read;void* catalog_context;unsigned catalog_bytes;
const CatalogRow* catalog;
unsigned catalog_rows, room, visit, wired, checked_mask, used, overflow, errors;
char scope_text[24];
unsigned emissions[ConsumerCount];
bool active,catalog_ok;
struct Queued { Consumer consumer; CheckedAsset asset;unsigned kind;Digest digest;unsigned room, visit; };
Queued queue[32];
std::atomic_flag queue_lock = ATOMIC_FLAG_INIT;
std::atomic<unsigned> queue_faults{0}, queue_active{0};
unsigned admission_room,admission_visit;bool admission_handoff;
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
#include "include/gc_asset_index.inc"
}
Digest fingerprint(const void* data, unsigned count) {
    IdentitySha hash;Digest result{};
    if(!data && count) { ++queue_faults;return result; }
    hash.update(data,count);hash.finish(result.bytes);return result;
}
bool fingerprint_read(Digest& out, Read read, void* context, unsigned count) {
    IdentitySha hash;unsigned char buffer[512];out={};
    while(count) {
        const unsigned take=count<sizeof buffer?count:sizeof buffer;
        if(!read || read(context,buffer,take)!=take) { ++queue_faults;return false; }
        hash.update(buffer,take);count-=take;
    }
    hash.finish(out.bytes);return true;
}
bool fingerprint_read_prefix(Digest& out,Digest& first,Read read,void* context,unsigned count,unsigned prefix){
    out={};first={};if(!prefix || prefix>count){++queue_faults;return false;}
    IdentitySha full,part;unsigned char buffer[512];
    while(count){const unsigned take=count<sizeof buffer?count:sizeof buffer;
        if(!read || read(context,buffer,take)!=take){++queue_faults;return false;}
        full.update(buffer,take);const unsigned n=prefix<take?prefix:take;
        if(n)part.update(buffer,n);
        prefix-=n;count-=take;
    }
    full.finish(out.bytes);part.finish(first.bytes);return true;
}
bool install(const CatalogRow* rows, unsigned count) {
    if(active) { ++errors;return false; }
    if(!new_catalog_epoch())return false;
    if(count>CatalogLimit || (count && !rows))return false;
    for(unsigned i=0;i<count;++i) {
        const CatalogRow& c=rows[i];
        if(!token(c.kind,KindBytes) || !token(c.id,IdBytes) || unsigned(c.provenance)>Authored)return false;
        for(unsigned j=0;j<i;++j)if(!std::strcmp(c.kind,rows[j].kind) && !std::strcmp(c.id,rows[j].id) &&
            !std::memcmp(c.digest.bytes,rows[j].digest.bytes,32))return false;
    }
    catalog=rows;catalog_rows=count;catalog_ok=true;return true;
}
bool install_index(CatalogReadAt read,void* context,unsigned bytes,const Digest& expected) {
    if(active){++errors;return false;}
    if(!new_catalog_epoch())return false;
    if(!read || bytes<128 || bytes>128+CatalogLimit*112)return false;
    IndexStream stream{read,context,0};Digest actual;
    if(!fingerprint_read(actual,index_stream_read,&stream,bytes) || std::memcmp(actual.bytes,expected.bytes,32))return false;
    unsigned char header[128];
    if(read(context,0,header,sizeof header)!=sizeof header || std::memcmp(header,"GCIDX001",8) ||
       index_word(header+8)!=1 || !index_word(header+12) || index_word(header+12)>CatalogLimit ||
       index_word(header+16)!=112 || index_word(header+20)!=128 ||
       bytes!=128+index_word(header+12)*112)return false;
    for(unsigned i=24;i<128;++i)if(header[i])return false;
    catalog_read=read;catalog_context=context;catalog_bytes=bytes;catalog_rows=index_word(header+12);
    AssetDescription previous{},current;
    for(unsigned i=0;i<catalog_rows;++i){
        if(!index_row(i,current) || (i && index_compare(previous,current.kind,current.id,current.digest)>=0)){
            catalog_read=nullptr;catalog_rows=catalog_bytes=0;return false;
        }
        previous=current;
    }
    catalog_ok=true;return true;
}
void retire_catalog(){
    if(active)unresolved(SourceGeometry,"catalog-retired-during-room");
    catalog_ok=false;catalog=nullptr;catalog_read=nullptr;catalog_rows=catalog_bytes=unknown_count=0;
}
CheckedAsset bind_checked(const char* kind,const char* id,const Digest& digest) {
    if(!catalog_ok || !token(kind,KindBytes) || !token(id,IdBytes))return {};
    unsigned index=catalog_rows;AssetDescription row;
    if(catalog_read) {
        unsigned lower=0,upper=catalog_rows;
        while(lower<upper) {
            const unsigned middle=(lower+upper)/2;
            if(!index_row(middle,row)){unresolved(SourceGeometry,"catalog-read");return {};}
            if(index_compare(row,kind,id,digest)<0)lower=middle+1;else upper=middle;
        }
        if(lower<catalog_rows) {
            if(!index_row(lower,row)){unresolved(SourceGeometry,"catalog-read");return {};}
            if(!index_compare(row,kind,id,digest))index=lower;
        }
    } else for(unsigned i=0;i<catalog_rows;++i)if(!std::strcmp(catalog[i].kind,kind) && !std::strcmp(catalog[i].id,id) &&
        !std::memcmp(catalog[i].digest.bytes,digest.bytes,32)){index=i;break;}
    if(index==catalog_rows) {
        unsigned i=0;
        for(;i<unknown_count;++i)if(!index_compare(unknown_assets[i],kind,id,digest))break;
        if(i==unknown_count) {
            if(unknown_count==UnknownLimit){++overflow;unresolved(SourceGeometry,"unknown-capacity");return {};}
            auto& unknown=unknown_assets[unknown_count++];unknown={};
            std::strcpy(unknown.kind,kind);std::strcpy(unknown.id,id);unknown.digest=digest;unknown.provenance=Unknown;
        }
        index=catalog_rows+i;
    }
    return {catalog_epoch<<14|index};
}
bool checked_current(CheckedAsset asset) {
    return catalog_ok && catalog_epoch && asset.value>>14==catalog_epoch &&
        (asset.value&16383U)<catalog_rows+unknown_count;
}
bool describe_checked(CheckedAsset asset,AssetDescription* out) {
    if(!out || !catalog_ok || asset.value>>14!=catalog_epoch || !catalog_epoch)return false;
    const unsigned index=asset.value&16383U;
    if(index<catalog_rows)return index_row(index,*out);
    if(index-catalog_rows>=unknown_count)return false;
    *out=unknown_assets[index-catalog_rows];return true;
}
static bool future_event(unsigned r,unsigned v){return admission_handoff && r==admission_room && v==admission_visit;}
static void begin_at(unsigned r,unsigned v,unsigned mask,bool startup,bool admit,bool handoff=false,bool transition=false,unsigned from=FromStartup,TransitionReason why=InitialRoom) {
    if(!handoff)queue_active.store(0);
    if(active) { ++errors;end(0); }
    room=r;visit=v;wired=mask;checked_mask=used=overflow=errors=0;
    std::memset(emissions,0,sizeof emissions);active=true;
    std::memset(seen,0,sizeof seen);
    errors=queue_faults.exchange(0);
    if(queue_lock.test_and_set(std::memory_order_acquire)) { ++errors;queue_active.store(0); }
    else {
        bool valid=true;
        if(handoff){
            valid=admission_handoff && admission_room==r && admission_visit==v;
            for(const auto& ticket:tickets)if(ticket.serial && (ticket.room!=r || ticket.visit!=v))valid=false;
            for(unsigned i=queue_head;i!=queue_tail;i=(i+1)%32)if(queue[i].room!=r || queue[i].visit!=v)valid=false;
        }else if(ticket_count || queue_head!=queue_tail)valid=false;
        if(!valid)++errors;
        admission_room=r;admission_visit=v;admission_handoff=false;
        queue_active.store(admit && valid);
        queue_lock.clear(std::memory_order_release);
    }
    if(transition)std::strcpy(scope_text,"phase=transition");
    else if(startup)std::strcpy(scope_text,"phase=startup");
    else std::snprintf(scope_text,sizeof scope_text,"room=%04x",room);
    if(transition){
        if((why==InitialRoom && from!=FromStartup) || (why==RoomRetire && from>0xffffU) || unsigned(why)>RoomRetire)
            unresolved(Ui,"transition-metadata");
        if(why==InitialRoom)re4dc_log("GC-ASSET-BEGIN v=1 %s visit=%u from_phase=startup transition_reason=initial-room wired=%03x required=%03x catalog=%u catalog_ok=%u\n",
            scope_text,visit,wired,Required,catalog_rows,unsigned(catalog_ok));
        else re4dc_log("GC-ASSET-BEGIN v=1 %s visit=%u from_room=%04x transition_reason=room-retire wired=%03x required=%03x catalog=%u catalog_ok=%u\n",
            scope_text,visit,from,wired,Required,catalog_rows,unsigned(catalog_ok));
        return;
    }
    re4dc_log("GC-ASSET-BEGIN v=1 %s visit=%u wired=%03x required=%03x catalog=%u catalog_ok=%u\n",
        scope_text,visit,wired,Required,catalog_rows,unsigned(catalog_ok));
}
void begin(unsigned r,unsigned v,unsigned mask){begin_at(r,v,mask,false,true);}
void begin_closed(unsigned r,unsigned v,unsigned mask){begin_at(r,v,mask,false,false);}
void begin_startup_closed(unsigned v,unsigned mask){begin_at(0,v,mask,true,false);}
void begin_room_handoff(unsigned r,unsigned v,unsigned mask){begin_at(r,v,mask,false,true,true);}
void begin_transition_handoff(unsigned v,unsigned mask,unsigned from,TransitionReason why){begin_at(0,v,mask,false,true,true,true,from,why);}
bool handoff_audio_admission(unsigned r,unsigned v){
    if(queue_lock.test_and_set(std::memory_order_acquire)){++queue_faults;queue_active.store(0);return false;}
    const bool valid=active && v>visit && !admission_handoff;
    if(valid){admission_room=r;admission_visit=v;admission_handoff=true;queue_active.store(1);}
    else{++queue_faults;queue_active.store(0);}
    queue_lock.clear(std::memory_order_release);return valid;
}
void open_audio_admission(){
    if(queue_lock.test_and_set(std::memory_order_acquire)){++queue_faults;return;}
    if(!active || ticket_count || queue_head!=queue_tail)++queue_faults;
    else queue_active.store(1);
    queue_lock.clear(std::memory_order_release);
}
AudioTicket audio_ticket() {
    if(queue_lock.test_and_set(std::memory_order_acquire)) { ++queue_faults;return {32,0}; }
    AudioTicket ticket{32,0};
    if(queue_active.load() && ticket_count<32 && ticket_serial!=0xffffffffU) {
        for(unsigned i=0;i<32;++i)if(!tickets[i].serial) {
            tickets[i]={++ticket_serial,admission_room,admission_visit};ticket={i,ticket_serial};++ticket_count;break;
        }
    } else ++queue_faults;
    queue_lock.clear(std::memory_order_release);return ticket;
}
void close_audio_admission() { queue_active.store(0);admission_handoff=false; }
static void enqueue(AudioTicket ticket, Consumer consumer, CheckedAsset asset,unsigned kind,const Digest* digest) {
    if(queue_lock.test_and_set(std::memory_order_acquire)) { ++queue_faults;return; }
    if(ticket.slot>=32 || !ticket.serial || tickets[ticket.slot].serial!=ticket.serial) {
        ++queue_faults;queue_lock.clear(std::memory_order_release);return;
    }
    const TicketSlot captured=tickets[ticket.slot];tickets[ticket.slot].serial=0;--ticket_count;
    if(unsigned(consumer)>=ConsumerCount) {
        ++queue_faults;queue_lock.clear(std::memory_order_release);return;
    }
    const unsigned next=(queue_tail+1)%32;
    if(next==queue_head) { ++queue_faults;queue_lock.clear(std::memory_order_release);return; }
    Queued& q=queue[queue_tail];q.consumer=consumer;q.asset=asset;q.kind=kind;
    if(digest)q.digest=*digest;
    q.room=captured.room;q.visit=captured.visit;queue_tail=next;
    queue_lock.clear(std::memory_order_release);
}
void queued_checked(AudioTicket ticket,Consumer consumer,CheckedAsset asset){enqueue(ticket,consumer,asset,0,nullptr);}
void queued_pending(AudioTicket ticket,Consumer consumer,PendingSound kind,const Digest& digest){
    if(unsigned(kind)<SoundMram || unsigned(kind)>StreamContainer){enqueue(ticket,consumer,{},0,nullptr);return;}
    enqueue(ticket,consumer,{},kind,&digest);
}
void pump() {
    for(;;) {
        if(queue_lock.test_and_set(std::memory_order_acquire)) { ++queue_faults;break; }
        if(queue_head==queue_tail) { queue_lock.clear(std::memory_order_release);break; }
        if(future_event(queue[queue_head].room,queue[queue_head].visit) &&
           (!active || queue[queue_head].room!=room || queue[queue_head].visit!=visit)){
            queue_lock.clear(std::memory_order_release);break;
        }
        const Queued q=queue[queue_head];queue_head=(queue_head+1)%32;queue_lock.clear(std::memory_order_release);
        if(!active || q.room!=room || q.visit!=visit) {
            if(active)++errors;else re4dc_log("GC-ASSET-ERROR v=1 why=audio-room-lifetime\n");
        } else if(q.kind){
            char id[65];hex(q.digest,id);id[40]=0;
            const char* kind=q.kind==SoundMram?"sound-mram":q.kind==SoundAram?"sound-aram":"sound-stream";
            emitted(q.consumer,kind,q.kind==StreamContainer?"aica-str-dat":id,q.digest);
        } else emitted_checked(q.consumer,q.asset);
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
void unresolved(Consumer consumer, const char* reason) {
    if(active)++errors;
    re4dc_log("GC-ASSET-ERROR v=1 why=%s consumer=%u\n",reason?reason:"missing-identity",unsigned(consumer));
}
void emitted(Consumer consumer, const char* kind, const char* id, const Digest& digest) {
    if(!active){re4dc_log("GC-ASSET-ERROR v=1 why=no-room\n");return;}
    emitted_checked(consumer,bind_checked(kind,id,digest));
}
void emitted_checked(Consumer consumer,CheckedAsset asset) {
    if(!active) { re4dc_log("GC-ASSET-ERROR v=1 why=no-room\n");return; }
    if(unsigned(consumer)>=ConsumerCount) { ++errors;return; }
    ++emissions[consumer];checked(consumer);
    const unsigned index=asset.value&16383U;
    if(!catalog_ok || !catalog_epoch || asset.value>>14!=catalog_epoch || index>=catalog_rows+unknown_count) {
        unresolved(consumer,"catalog-token");return;
    }
    if(seen[index/8]&(1U<<(index%8)))return;
    AssetDescription row;
    if(!describe_checked(asset,&row)){unresolved(consumer,"catalog-read");return;}
    seen[index/8]|=1U<<(index%8);
    if(row.provenance==PS2 || row.provenance==Authored)return;
    ++used;char sha[65];hex(row.digest,sha);
    re4dc_log("GC-ASSET v=1 %s visit=%u kind=%s id=%s sha256=%s provenance=%s consumer=%s action=emit\n",
        scope_text,visit,row.kind,row.id,sha,provenances[row.provenance],names[consumer]);
}
void end(unsigned frame) {
    if(!active) { re4dc_log("GC-ASSET-ERROR v=1 why=no-room-end\n");return; }
    if(!admission_handoff)queue_active.store(0);
    pump();
    if(queue_lock.test_and_set(std::memory_order_acquire))++errors;
    else {
        bool pending=false;
        for(const auto& ticket:tickets)if(ticket.serial && !future_event(ticket.room,ticket.visit))pending=true;
        for(unsigned i=queue_head;i!=queue_tail;i=(i+1)%32)if(!future_event(queue[i].room,queue[i].visit))pending=true;
        if(pending)++errors;
        queue_lock.clear(std::memory_order_release);
    }
    errors+=queue_faults.exchange(0);
    // re4dc_log has a 256-byte buffer. Both maximum-width rows fit, including
    // 32-bit counters; one long END row would silently truncate the gate.
    re4dc_log("GC-ASSET-COUNTS v=1 %s visit=%u source_geometry=%u texture=%u effect_picture=%u weapon=%u font=%u ui=%u sound_bank=%u sound_stream=%u movie=%u\n",
        scope_text,visit,
        emissions[0],emissions[1],emissions[2],emissions[3],emissions[4],emissions[5],emissions[6],emissions[7],emissions[8]);
    re4dc_log("GC-ASSET-END v=1 %s visit=%u frame=%u wired=%03x checked=%03x required=%03x unique=%u overflow=%u errors=%u catalog_ok=%u\n",
        scope_text,visit,frame,wired,checked_mask,Required,used,overflow,errors,unsigned(catalog_ok));
    active=false;
}
#if defined(RE4DC_GC_ASSET_TEST)
void queued(AudioTicket ticket, Consumer consumer, const char* kind, const char* id, const Digest& digest) {
    queued_checked(ticket,consumer,bind_checked(kind,id,digest));
}
void test_queue_lock(bool held) {
    if(held)queue_lock.test_and_set(std::memory_order_acquire);else queue_lock.clear(std::memory_order_release);
}
void test_max_counters() { for(auto& value:emissions)value=0xffffffffU;overflow=errors=0xffffffffU; }
#endif
}
#endif
