#include "include/gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
#include <cstdio>
#include <cstring>
#include <new>
#include <cstdlib>
#include <algorithm>
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
unsigned catalog_faults; // bounded reason/owned-or-unowned bits; never a row cache
bool active,catalog_ok;
struct Queued { Consumer consumer; CheckedAsset asset;unsigned kind;Digest digest;unsigned room, visit; };
static_assert(sizeof(Queued)==52,"tenth consumer must not grow audio queue events");
Queued queue[32];
std::atomic_flag queue_lock = ATOMIC_FLAG_INIT;
std::atomic<unsigned> queue_faults{0}, queue_active{0};
unsigned admission_room,admission_visit;bool admission_handoff;
unsigned queue_head, queue_tail;
struct TicketSlot { unsigned serial, room, visit; };
TicketSlot tickets[32];unsigned ticket_serial, ticket_count;
const char* names[] = {"source_geometry", "texture", "effect_picture", "weapon", "font", "ui", "sound_bank", "sound_stream", "movie", "motion"};
static_assert(sizeof(names)/sizeof(*names)==ConsumerCount,"complete consumer protocol names");
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
enum CatalogFault : unsigned { CatalogRetired=1, CatalogRead=2, CatalogCapacity=4 };
void catalog_fault(unsigned reason){
    if(active){++errors;catalog_faults|=reason;}
    else catalog_faults|=reason<<8;
}
void catalog_fault_flush(){
    const unsigned pending=catalog_faults;catalog_faults=0;
    const char* reasons[]={"catalog-retired-during-room","catalog-read","unknown-capacity"};
    for(unsigned i=0;i<3;++i){
        if(pending&(1U<<i))re4dc_log("GC-ASSET-ERROR v=2 why=%s consumer=%u %s visit=%u\n",reasons[i],unsigned(SourceGeometry),scope_text,visit);
        if(pending&(1U<<(i+8)))re4dc_log("GC-ASSET-ERROR v=2 why=%s consumer=%u unowned=1\n",reasons[i],unsigned(SourceGeometry));
    }
}
#include "include/gc_asset_index.inc"
}
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
// GC_ASSET_PROF: every hash call >= 20 ms is logged with its caller and size.
}
#include <arch/timer.h>
namespace re4dc_gcasset {
struct HashProf {
    const char* what;void* caller;unsigned bytes;unsigned long long t0;
    static unsigned long long total_us,total_bytes;static unsigned calls;
    HashProf(const char* w,void* c,unsigned n):what(w),caller(c),bytes(n),t0(timer_us_gettime64()){}
    ~HashProf(){
        const unsigned long long us=timer_us_gettime64()-t0;total_us+=us;total_bytes+=bytes;++calls;
        if(us>=20000 || !(calls&15))re4dc_log("GC-ASSET-PROF hash=%s caller=%p bytes=%u us=%llu total_calls=%u total_us=%llu total_bytes=%llu\n",
            what,caller,bytes,us,calls,total_us,total_bytes);
    }
};
unsigned long long HashProf::total_us,HashProf::total_bytes;unsigned HashProf::calls;
#define RE4DC_GCA_HASH_PROF(w,n) HashProf hash_prof(w,__builtin_return_address(0),n)
#else
#define RE4DC_GCA_HASH_PROF(w,n) ((void)0)
#endif
static_assert(sizeof(IdentitySha)<=sizeof(DigestStream::opaque) && alignof(IdentitySha)<=4,"digest stream storage");
void digest_begin(DigestStream& s){new (s.opaque) IdentitySha();}
void digest_update(DigestStream& s,const void* data,unsigned count){reinterpret_cast<IdentitySha*>(s.opaque)->update(data,count);}
Digest digest_finish(DigestStream& s){Digest out{};reinterpret_cast<IdentitySha*>(s.opaque)->finish(out.bytes);return out;}
Digest fingerprint(const void* data, unsigned count) {
    RE4DC_GCA_HASH_PROF("ram",count);
    IdentitySha hash;Digest result{};
    if(!data && count) { ++queue_faults;return result; }
    hash.update(data,count);hash.finish(result.bytes);return result;
}
bool fingerprint_read(Digest& out, Read read, void* context, unsigned count) {
    RE4DC_GCA_HASH_PROF("read",count);
    IdentitySha hash;unsigned char buffer[512];out={};
    while(count) {
        const unsigned take=count<sizeof buffer?count:sizeof buffer;
        if(!read || read(context,buffer,take)!=take) { ++queue_faults;return false; }
        hash.update(buffer,take);count-=take;
    }
    hash.finish(out.bytes);return true;
}
bool fingerprint_read_prefix(Digest& out,Digest& first,Read read,void* context,unsigned count,unsigned prefix){
    RE4DC_GCA_HASH_PROF("read-prefix",count);
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
namespace {
// One sequential pass (gc-catalog24b): hash, validate and build the sparse index
// from the catalog bytes in any chunking. Same accept/reject verdicts as the old
// hash-then-row-by-row passes; nothing is published unless the pin matches.
struct InstallParse {
    unsigned bytes=0,seen=0,rows=0,block_rows=0,row=0,carry=0,texn=0;bool bad=false,want_tex=false;
    TexEntry* tex=nullptr;
    ~InstallParse(){std::free(tex);}
    unsigned char header[128];unsigned char part[112];
    IdentitySha hash;AssetDescription previous{},current;
    void header_done(){
        if(std::memcmp(header,"GCIDX001",8) || index_word(header+8)!=1 || !index_word(header+12) ||
           index_word(header+12)>CatalogLimit || index_word(header+16)!=112 || index_word(header+20)!=128 ||
           bytes!=128+index_word(header+12)*112){bad=true;return;}
        for(unsigned i=24;i<128;++i)if(header[i]){bad=true;return;}
        rows=index_word(header+12);block_rows=rows<=SparseKeys*BufferRows?BufferRows:2*BufferRows;
        if(want_tex && !(tex=static_cast<TexEntry*>(std::malloc(rows*sizeof(TexEntry)))))bad=true;
    }
    void row_done(){
        if(row>=rows || !index_decode_row(part,current) ||
           (row && index_compare(previous,current.kind,current.id,current.digest)>=0)){bad=true;return;}
        if(!(row%block_rows))sparse_prefix(current.kind,current.id,current.digest,sparse_key[row/block_rows]);
        if(tex && !std::strcmp(current.kind,"texture")){auto& e=tex[texn++];std::memcpy(e.prefix,current.digest.bytes,4);e.row=(unsigned short)row;}
        previous=current;++row;
    }
    void feed(const unsigned char* p,unsigned n){
        if(bad)return;
        hash.update(p,n);
        while(n && !bad){
            if(seen<128){
                const unsigned take=128-seen<n?128-seen:n;
                std::memcpy(header+seen,p,take);seen+=take;p+=take;n-=take;
                if(seen==128)header_done();
                continue;
            }
            const unsigned take=112-carry<n?112-carry:n;
            std::memcpy(part+carry,p,take);carry+=take;p+=take;n-=take;
            if(carry==112){row_done();carry=0;}
        }
    }
    bool complete(const Digest& expected){
        if(bad || seen!=128 || row!=rows || carry)return false;
        Digest actual;hash.finish(actual.bytes);
        return !std::memcmp(actual.bytes,expected.bytes,32);
    }
};
void install_sink(void* context,const unsigned char* data,unsigned n){static_cast<InstallParse*>(context)->feed(data,n);}
}
bool install_index(CatalogReadAt read,void* context,unsigned bytes,const Digest& expected) {
    return install_index_stream(nullptr,nullptr,read,context,bytes,expected);
}
bool install_index_stream(CatalogStream stream,void* stream_context,CatalogReadAt read,void* context,unsigned bytes,const Digest& expected) {
    if(active){++errors;return false;}
    if(!new_catalog_epoch())return false;
    const unsigned epoch=catalog_epoch;
    if(!read || bytes<128 || bytes>128+CatalogLimit*112)return false;
    tex_table_free();
    InstallParse parse;parse.bytes=bytes;parse.want_tex=read!=nullptr;
    if(stream){
        // Bulk sequential reader (the disc adapter's 16 KiB storage reads).
        if(!stream(stream_context,install_sink,&parse) || !index_generation(epoch))return false;
    } else for(unsigned at=0;at<bytes;){
        const unsigned n=bytes-at<sizeof block_buffer?bytes-at:unsigned(sizeof block_buffer);
        if(index_read_at(read,context,epoch,at,block_buffer,n)!=n)return false;
        parse.feed(block_buffer,n);at+=n;
    }
    if(!parse.complete(expected) || !index_generation(epoch))return false;
    const unsigned rows=parse.rows,block_rows=parse.block_rows;
    sparse_block_rows=block_rows;sparse_blocks=(rows+block_rows-1)/block_rows;
    // Do not publish provisional globals or overwrite a newer callback install.
    if(active || !index_generation(epoch))return false;
    catalog_read=read;catalog_context=context;catalog_bytes=bytes;catalog_rows=rows;
    std::sort(parse.tex,parse.tex+parse.texn,tex_less);
    if(parse.tex && parse.texn){void* shrunk=std::realloc(parse.tex,parse.texn*sizeof(TexEntry));if(shrunk)parse.tex=static_cast<TexEntry*>(shrunk);}
    tex_table=parse.tex;tex_count=parse.texn;parse.tex=nullptr;
    if(tex_table && !desc_ring)desc_ring=static_cast<DescEntry*>(std::calloc(DescRing,sizeof(DescEntry)));
    if(desc_ring)for(unsigned i=0;i<DescRing;++i)desc_ring[i].value=0;
    catalog_ok=true;return true;
}
unsigned catalog_generation(){return catalog_ok?catalog_epoch:0;}
void retire_catalog(){
    // Invalidate before diagnostics/callbacks; a returned old row cannot become
    // current again, even if a callback installs a fresh catalog immediately.
    (void)new_catalog_epoch();
    if(active)catalog_fault(CatalogRetired);
}
CheckedAsset bind_checked(const char* kind,const char* id,const Digest& digest) {
    if(!catalog_ok || !token(kind,KindBytes) || !token(id,IdBytes))return {};
    const unsigned epoch=catalog_epoch,rows=catalog_rows;
    // Result cache (16 x 104 B = 1664 B BSS): repeated binds of the same identity
    // (sound key-ons pumped every event, movie/model rebinds) skip the disc search.
    // Tokens are epoch-tagged, so a retired/replaced catalog never hits.
    struct BindCache{char kind[16],id[48];Digest digest;unsigned value;};
    static BindCache bind_cache[16];static unsigned bind_cache_next;
    for(const auto& c:bind_cache)if(c.value && c.value>>14==epoch && !std::strcmp(c.kind,kind) && !std::strcmp(c.id,id) &&
        !std::memcmp(c.digest.bytes,digest.bytes,32))return {c.value};
    struct CacheStore{const char* k;const char* i;const Digest& d;
        void operator()(CheckedAsset a)const{if(!a.value)return;auto& c=bind_cache[bind_cache_next++&15];
            std::strcpy(c.kind,k);std::strcpy(c.id,i);c.digest=d;c.value=a.value;}} store{kind,id,digest};
    const CheckedAsset result=[&]()->CheckedAsset{
    unsigned index=rows;AssetDescription row;
    if(catalog_read) {
        unsigned found=rows;
        const bool tex=tex_table && !std::strcmp(kind,"texture");
        const SparseResult result=tex?tex_find(id,digest,epoch,found,row):sparse_find(kind,id,digest,epoch,found);
        if(tex && result==SparseFound)desc_store(epoch<<14|found,row);
        if(!catalog_ok || !index_generation(epoch))return {};
        if(result==SparseFault){catalog_fault(CatalogRead);return {};}
        if(result==SparseFound)index=found;
        (void)row;
    } else for(unsigned i=0;i<rows;++i)if(!std::strcmp(catalog[i].kind,kind) && !std::strcmp(catalog[i].id,id) &&
        !std::memcmp(catalog[i].digest.bytes,digest.bytes,32)){index=i;break;}
    if(!catalog_ok || !index_generation(epoch))return {};
#if defined(RE4DC_GC_ASSET_HARVEST) && RE4DC_GC_ASSET_HARVEST
    // GC_ASSET_HARVEST=1 (offline catalog harvest build, never a gate run): log
    // each catalog miss and return no token; no quarantine slot, no fault, so the
    // run keeps reaching later identities. build_catalog.py --harvest reviews them.
    if(index==rows) {
        char hex[65];
        for(unsigned b=0;b<32;++b)::snprintf(hex+2*b,3,"%02x",unsigned(digest.bytes[b]));
        re4dc_log("GC-ASSET-HARVEST v=1 kind=%s id=%s sha256=%s\n",kind,id,hex);
        return {};
    }
#endif
    if(index==rows) {
        unsigned i=0;
        for(;i<unknown_count;++i)if(!index_compare(unknown_assets[i],kind,id,digest))break;
        if(i==unknown_count) {
            if(unknown_count==UnknownLimit){++overflow;catalog_fault(CatalogCapacity);return {};}
            auto& unknown=unknown_assets[unknown_count++];unknown={};
            std::strcpy(unknown.kind,kind);std::strcpy(unknown.id,id);unknown.digest=digest;unknown.provenance=Unknown;
        }
        index=rows+i;
    }
    if(!catalog_ok || !index_generation(epoch))return {};
    return {epoch<<14|index};
    }();
    if(catalog_ok && index_generation(epoch))store(result);
    return result;
}
bool checked_current(CheckedAsset asset) {
    return catalog_ok && index_generation(catalog_epoch) && asset.value>>14==catalog_epoch &&
        (asset.value&16383U)<catalog_rows+unknown_count;
}
bool describe_checked(CheckedAsset asset,AssetDescription* out) {
    if(!out)return false;
    *out={};
    if(!checked_current(asset))return false;
    const unsigned epoch=catalog_epoch,rows=catalog_rows,index=asset.value&16383U;
    AssetDescription row{};
    if(index<rows){if(!desc_find(asset.value,row) && !index_row(index,row))return false;}
    else {
        if(index-rows>=unknown_count)return false;
        row=unknown_assets[index-rows];
    }
    if(!index_generation(epoch) || !checked_current(asset))return false;
    *out=row;return true;
}
static bool future_event(unsigned r,unsigned v){return admission_handoff && r==admission_room && v==admission_visit;}
static void begin_at(unsigned r,unsigned v,unsigned mask,bool startup,bool admit,bool handoff=false,bool transition=false,unsigned from=FromStartup,TransitionReason why=InitialRoom) {
    if(!handoff)queue_active.store(0);
    if(active) { ++errors;end(0); }
    catalog_fault_flush(); // before old visit/scope fields can be reset
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
    else std::sprintf(scope_text,"room=%04x",room); // at most 13 bytes plus NUL in scope_text[24]
    if(transition){
        if((why==InitialRoom && from!=FromStartup) || (why==RoomRetire && from>0xffffU) || unsigned(why)>RoomRetire)
            unresolved(Ui,"transition-metadata");
        if(why==InitialRoom)re4dc_log("GC-ASSET-BEGIN v=2 %s visit=%u from_phase=startup transition_reason=initial-room wired=%03x required=%03x catalog=%u catalog_ok=%u\n",
            scope_text,visit,wired,Required,catalog_rows,unsigned(catalog_ok));
        else re4dc_log("GC-ASSET-BEGIN v=2 %s visit=%u from_room=%04x transition_reason=room-retire wired=%03x required=%03x catalog=%u catalog_ok=%u\n",
            scope_text,visit,from,wired,Required,catalog_rows,unsigned(catalog_ok));
        return;
    }
    re4dc_log("GC-ASSET-BEGIN v=2 %s visit=%u wired=%03x required=%03x catalog=%u catalog_ok=%u\n",
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
            if(active)++errors;else re4dc_log("GC-ASSET-ERROR v=2 why=audio-room-lifetime\n");
        } else if(q.kind){
            char id[65];hex(q.digest,id);id[40]=0;
            const char* kind=q.kind==SoundMram?"sound-mram":q.kind==SoundAram?"sound-aram":"sound-stream";
            emitted(q.consumer,kind,id,q.digest);   // sound-stream: one row per AIS1 entry, id = digest prefix
        } else emitted_checked(q.consumer,q.asset);
    }
    const unsigned faults=queue_faults.exchange(0);
    if(active)errors+=faults;
    else if(faults)re4dc_log("GC-ASSET-ERROR v=2 why=unowned-audio count=%u\n",faults);
    catalog_fault_flush();
}
void checked(Consumer consumer) {
    if(!active)return;
    if(unsigned(consumer)>=ConsumerCount) { ++errors;return; }
    checked_mask |= 1U << consumer;
}
void unresolved(Consumer consumer, const char* reason) {
    if(active)++errors;
    re4dc_log("GC-ASSET-ERROR v=2 why=%s consumer=%u\n",reason?reason:"missing-identity",unsigned(consumer));
}
void emitted(Consumer consumer, const char* kind, const char* id, const Digest& digest) {
    if(!active){re4dc_log("GC-ASSET-ERROR v=2 why=no-room\n");return;}
    if(consumer==Motion){unresolved(Motion,"motion-unwired");return;}
    emitted_checked(consumer,bind_checked(kind,id,digest));
}
void emitted_checked(Consumer consumer,CheckedAsset asset) {
    if(!active) { re4dc_log("GC-ASSET-ERROR v=2 why=no-room\n");return; }
    if(unsigned(consumer)>=ConsumerCount) { ++errors;return; }
    // No reviewed Motion producer receipt exists: fail before catalog IO,
    // Seen or PS2 suppression. Its zero counter is not a zero-use assertion.
    if(consumer==Motion){unresolved(Motion,"motion-unwired");return;}
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
    re4dc_log("GC-ASSET v=2 %s visit=%u kind=%s id=%s sha256=%s provenance=%s consumer=%s action=emit\n",
        scope_text,visit,row.kind,row.id,sha,provenances[row.provenance],names[consumer]);
}
void end(unsigned frame) {
    if(!active) { re4dc_log("GC-ASSET-ERROR v=2 why=no-room-end\n");return; }
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
    re4dc_log("GC-ASSET-COUNTS v=2 %s visit=%u source_geometry=%u texture=%u effect_picture=%u weapon=%u font=%u ui=%u sound_bank=%u sound_stream=%u movie=%u motion=%u\n",
        scope_text,visit,
        emissions[0],emissions[1],emissions[2],emissions[3],emissions[4],emissions[5],emissions[6],emissions[7],emissions[8],emissions[9]);
    re4dc_log("GC-ASSET-END v=2 %s visit=%u frame=%u wired=%03x checked=%03x required=%03x unique=%u overflow=%u errors=%u catalog_ok=%u\n",
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
unsigned test_catalog_rows(unsigned count){const unsigned old=catalog_rows;catalog_rows=count;return old;}
#endif
}
#endif
