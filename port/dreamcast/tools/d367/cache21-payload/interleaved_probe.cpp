#include <algorithm>
#include <cstring>
#include <cstdio>
#include <cassert>
#include <cstdint>
#include <vector>
#include <cstdarg>
#define RE4DC_TEX_PACK 1
#define RE4DC_TEX_RESIDENT 1
#define RE4DC_UI_VRAM 1
#define RE4DC_PROFILE_SCOPE(x)
#define RE4DC_PROFILE_COUNT(x,n)
#define RE4DC_TEXCHK_FAIL(k,w)
#define RE4DC_TEXCHK_BIND(e)
#define RE4DC_FX_EVICTED()
#define RE4DC_HOLD_EVICTED(e)
#define RE4DC_ENTRY_PINNED(e) false
#define RE4DC_CORE_PINNED(e) false
#define RE4DC_TEX_PATH(p,k) std::strcpy(p,"member")
#define RE4DC_TOUCH(e) ((e).frame=frame)
#define RE4DC_GAD_HIT(k)
using file_t=int;
constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
int fs_open(const char*,int){return 1;} void fs_close(int){}
struct Key {unsigned crc,fnv;bool operator==(const Key& b)const{return crc==b.crc&&fnv==b.fnv;}};
namespace re4dc {namespace texture {constexpr unsigned kPayloadVq=1;}}
struct Re4dcUiImage {void* pixels;unsigned width,height,format;};
unsigned image_size(const Re4dcUiImage&){return 16;}
bool image_key(const Re4dcUiImage&,Key&){return false;}
unsigned calls,evictions,closes,frame,used,peak,reclaimed,vram_rejects,vram_retries,loads,pack_error_skips;
void(*during_open)(); void(*after_find)();
const char* injected="streamed texture upload read failed";
struct Package {
 const char* err=nullptr;
 struct H{unsigned texture_count=1,data_size=16;} h;
 struct T{unsigned payload=0,data_size=16,width=8,height=8;} tx;
 bool open_streamed_at(const char*,unsigned offset,unsigned){++calls;if(during_open){auto callback=during_open;during_open=nullptr;callback();}injected=((offset-8192)/2048)%128==0?"streamed texture upload read failed":nullptr;err=nullptr;return true;}
 bool open_streamed(const char*){++calls;return true;}
 const char* error()const{return err;}
 const H& header()const{return h;}
 bool upload(){if(injected){err=injected;return false;}return true;}
 bool release_payload(){return true;}
 unsigned vram_bytes()const{return 16;}
 unsigned metadata_bytes()const{return 16;}
 const T* textures()const{return &tx;}
 void close(){++closes;}
};
struct Entry {Package package;Key key{};unsigned frame=0;bool valid=false;} entries[4];
Key missing_keys[16]{};unsigned nmissing=0;
constexpr unsigned vram_budget=4096;
using pvr_ptr_t=void*; void* pvr_mem_malloc(unsigned){return (void*)1;} void pvr_mem_free(void*){}
unsigned pvr_mem_available(){return 8192;}
int re4dc_ui_heap_free(){return 4096;}
void close_entry(Entry& e){if(e.valid){++evictions;e.valid=false;used-=16;}e.package.close();}

using mutex_t = int;
#define MUTEX_INITIALIZER 0
static int locks = 0;
void mutex_lock(mutex_t*) { ++locks; }
void mutex_unlock(mutex_t*) { --locks; }
static char last_log[512];
static unsigned logs = 0;
void re4dc_log(const char* f, ...) {
    va_list a; va_start(a, f); std::vsnprintf(last_log, sizeof(last_log), f, a); va_end(a); ++logs;
}

static std::vector<unsigned char> disk;
static bool present = true;
static unsigned reads = 0, fail_reads = 0, fail_at = ~0U;  // fail the next fail_reads reads (at fail_at, or any)
static unsigned now = 1000;                                   // the UI frame passed to find()
namespace re4dc::texture {
enum class RangeRead { ok, absent, io_error, short_file };
RangeRead read_file_range(const char*, std::uint32_t off, void* dst, std::uint32_t n, unsigned long long* total) {
    if (!present) return RangeRead::absent;
    if (total) *total = disk.size();
    ++reads;
    if (std::uint64_t(off) + n > disk.size()) return RangeRead::short_file;   // as texture_package.cpp: size, not I/O
    if (fail_reads && (fail_at == ~0U || fail_at == off)) { --fail_reads; return RangeRead::io_error; }
    std::memcpy(dst, disk.data() + off, n);
    return RangeRead::ok;
}
}  // namespace re4dc::texture
namespace {
#if RE4DC_TEX_PAYLOAD_RETRY
#include "texpack_payload_retry.inc"
#endif
#include "texpack_index.inc"
}

static void put(unsigned at, unsigned v) { for (unsigned i = 0; i < 4; ++i) disk.at(at + i) = (unsigned char)(v >> (8 * i)); }
static unsigned get(unsigned at) { return disk[at] | disk[at + 1] << 8 | disk[at + 2] << 16 | unsigned(disk[at + 3]) << 24; }
static unsigned crc_of(unsigned at, unsigned n) {
    unsigned c = 0xffffffffU;
    for (unsigned i = 0; i < n; ++i) { c ^= disk[at + i]; for (int b = 0; b < 8; ++b) c = (c >> 1) ^ (0xedb88320U & (0U - (c & 1U))); }
    return ~c;
}
static unsigned nsec(unsigned n) { return (n * 16 + 2047) / 2048; }
// A pack of n entries: key i = {i+1, 0x100+i}, each a 100-byte package at its own 2048-byte block.
static void make(unsigned n) {
    const unsigned data = 2048 + 2048 * nsec(n);
    disk.assign(data + 2048 * n, 0);
    std::memcpy(disk.data(), "RE4PAK1", 8);
    put(8, 1); put(12, n); put(16, 2048); put(20, data);
    for (unsigned i = 0; i < n; ++i) {
        const unsigned e = 2048 + 16 * i;
        put(e, i + 1); put(e + 4, 0x100 + i); put(e + 8, data + 2048 * i); put(e + 12, 100);
    }
    put(24, crc_of(2048, 2048 * nsec(n)));
}
static void recrc() { put(24, crc_of(2048, 2048 * nsec(get(12) > 8192 ? 1 : get(12)))); }
static void reset() {
    texpack::state = texpack::kUntried; texpack::cached = ~0U;
    texpack::count = texpack::data_offset = texpack::sectors = texpack::hits = texpack::misses = texpack::errors = 0;
    texpack::attempts = texpack::streak = texpack::room_gen = texpack::attempt_gen = texpack::retry_at = 0;
    texpack::bad_sector = ~0U; texpack::bad_until = 0; texpack::pack_bytes = 0;
    std::memset(texpack::first, 0, sizeof(texpack::first));
    present = true; reads = fail_reads = 0; fail_at = ~0U; now = 1000;
}
static texpack::Result find(unsigned crc, unsigned fnv, unsigned* off = nullptr) {
    unsigned o = 0, s = 0;
    const texpack::Result r = texpack::find({crc, fnv}, o, s, now);
    if (off) *off = o;
    assert(locks == 0);
    return r;
}


#include "actual_load_interleaved.inc"
int main(){reset();make(300);Re4dcUiImage image{(void*)1,8,8,1};
 const unsigned good_ids[]={1,129,257},bad_ids[]={0,128,256};
 auto key=[](unsigned id){return Key{id+1,0x100+id};};
 // Establish the three healthy residents, then alternate failed sectors with resident hits.
 for(unsigned id:good_ids){const Key k=key(id);assert(load(image,false,&k));}
 const unsigned index_start=reads,open_start=calls,eviction_start=evictions;
 for(frame=0;frame<20;++frame)for(unsigned n=0;n<3;++n){const Key bad=key(bad_ids[n]),good=key(good_ids[n]);assert(!load(image,false,&bad));const unsigned before=calls;assert(load(image,false,&good));assert(calls==before);}
 const unsigned alternating_index=reads-index_start,alternating_opens=calls-open_start;
#if RE4DC_TEX_PAYLOAD_RETRY
 assert(alternating_opens==3);
#else
 assert(alternating_opens==60);
#endif
 // Every failed draw still calls find(), so alternating sectors retain index I/O.
 assert(alternating_index==60&&evictions==eviction_start);
 printf("INTERLEAVED actual_index_reads=%u index_bytes=%u payload_opens=%u evictions=%u healthy_resident_hits=60\n",alternating_index,2048*alternating_index,alternating_opens,evictions-eviction_start);
 // Also admit new healthy members interleaved across all three sectors.
 unsigned healthy_opens=0;
 for(unsigned id:{2U,130U,258U}){const Key k=key(id);const unsigned before=calls;assert(load(image,false,&k));healthy_opens+=calls-before;}
 assert(healthy_opens==3);printf("HEALTHY_FIRST_USE opens=%u\n",healthy_opens);
#if RE4DC_TEX_PAYLOAD_RETRY
 unsigned member=~0U,epoch=0,off=0,size=0;
 const Key old_key=key(5);
 assert(texpack::find(old_key,off,size,frame,&member,&epoch)==texpack::kFound);
 texpack::room_loaded();assert(texpack::payload_blocked(member,frame,epoch));
 texpack::payload_failed(member,frame,epoch);assert(!texpack_payload_retry::blocked(member,frame));
 // Reset exactly after find and before the new loader's gate: no package/eviction.
 after_find=[](){texpack::room_loaded();};const unsigned before_reset=calls;assert(!load(image,false,&old_key));assert(calls==before_reset);
 // A late failure after a reset during open cannot rearm a new room's member.
 const Key bad=key(0);during_open=[](){texpack::room_loaded();};assert(!load(image,false,&bad));assert(!texpack_payload_retry::blocked(0,frame));
 // A late success cannot clear a failure already published in the new room epoch.
 const Key good=key(6);during_open=[](){texpack::room_loaded();texpack::payload_failed(6,frame,texpack::payload_epoch);};assert(load(image,false,&good));assert(texpack_payload_retry::blocked(6,frame));
 assert(texpack::find(old_key,off,size,frame,&member,&epoch)==texpack::kFound);texpack::state=texpack::kUntried;
 unsigned new_epoch=0;assert(texpack::find(old_key,off,size,frame,&member,&new_epoch)==texpack::kFound&&new_epoch!=epoch);
 texpack::payload_failed(member,frame,new_epoch);texpack::payload_succeeded(member,epoch);assert(texpack::payload_blocked(member,frame,new_epoch));
 texpack::payload_epoch=~0U;texpack::room_loaded();assert(texpack::payload_epoch_exhausted);
 assert(texpack::find(old_key,off,size,frame,&member,&epoch)==texpack::kFound&&epoch==0);assert(texpack::payload_blocked(member,frame,epoch));
 printf("EPOCH_RESET_CONTROLS PASS after_find/during_open/republish/late_success/exhaustion\n");
#endif
 assert(locks==0&&nmissing==0);printf("INTERLEAVED_PROBE PASS\n");
}
