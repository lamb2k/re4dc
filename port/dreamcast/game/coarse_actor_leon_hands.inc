#ifndef RE4DC_LEON_HAND_RETAIN
#define RE4DC_LEON_HAND_RETAIN 0
#endif
// LEON_HAND_PACK=1 (crowd.mk; needs LEON_HAND_POSES=1, PS2_LEON=1, ACTOR_PL08=1; render only). Included by
// coarse_actor_owner_leon.inc. Leon's hands (roles 5 right / 6 left) for every pose come from the outfit's hand package
// (dc/native/pl00/leon_hands_pl00.re4hp, tools/d367/ps2leon/hands_pack.py), not from the image: the standard hands'
// arrays are left out of ps2leon_runtime.h (hands_pack.py derive), and leon4k::chunks[5] / [6] point at two fixed draw
// slots that hold the pose drawn now.
//   - Directory: read once from the package (rows: GC runtime key -> blob; blobs; sources: weapon archive -> blob).
#if RE4DC_LEON_HAND_RETAIN
//   - Cache: 4 cells in AICA RAM (two per side, with demand priority over fallback hints), filled
#else
//   - Cache: 4 cells in AICA RAM (per side: the home pose, prefetched at room load, and the last other pose), filled
#endif
//     from the disc and copied to the draw slot over G2 when the game swaps a hand info. A real-time swap between the
//     home hand and the equipped weapon's hand (grabs, the boat, the knife) is a copy, not a disc read.
//   - Prefetch (synchronous, at load points): room load (the standard hands, then the home / alternating poses:
//     FLAG_STANDARD, FLAG_HOME right, FLAG_ALT left) and weapon equip (ReadWepData: the weapon's own hand BINs, else
//     the side's alternating pose).
//   - Anything else (a real-time pose not in a cell) is read by a worker thread: the hand drawn before stays in the
//     slot until the read lands, so a pose change never stalls the frame. The worker reads through the persistent
//     package handle into a heap buffer that is deliberately not 32-byte aligned (KOS iso9660 then reads through its
//     sector cache, not a CD stream: the audio stream reader's rule, platform/audio_aica.cpp); the buffer and the
//     worker's stack are one transient allocation (re4dc_motion_alloc), freed when the read lands.
//   - The movie audio stream needs the whole 64 KiB AICA movie reserve: the cells are freed at movie open (and before
//     any runtime sound bank conversion; a read in flight is waited for) and refilled by the worker after the movie.
// A slot change resets the role's immutable proof (IDs 6 / 7) and is part of the skin key, so the FTRV palette program
// and the chunk proof are rebuilt from the new bytes before use.
#include <kos/fs.h>
#include <fcntl.h>
#include <dc/spu.h>
#include <dc/sound/sound.h>
#include <arch/timer.h>
#include <kos/thread.h>
#include <kos/mutex.h>
extern "C" void* re4dc_motion_alloc(unsigned);
extern "C" void re4dc_motion_free(void*);
#ifndef RE4DC_DVD_BUFF_BYTES
#define RE4DC_DVD_BUFF_BYTES 0x20000   // DVD_BUFF_KB (Makefile): the staging area size
#endif
extern "C" unsigned char re4dc_dvd_buff[RE4DC_DVD_BUFF_BYTES];
#pragma GCC push_options
#pragma GCC optimize("Os")  // cold loader code: size, not speed (image bytes are heap 4)
namespace leon_hand_pack {
constexpr unsigned kMagic=0x3150484Cu,kVersion=1,kRows=24,kBlobs=24,kSources=48;  // hands_pack.py CAPS
constexpr unsigned kSlotBytes[2]={6144,6400};   // hands_pack.py SLOT_CAP (right, left)
constexpr unsigned kCellBytes=2*(6144+6400);    // AICA: per side a home cell and an other cell
struct Row { unsigned char role,blob; unsigned short positions,normals,palette; unsigned hash; };
struct Blob { unsigned char role,flags; unsigned short pc,nc,pal,tri,size[5],stream,offset32; };
struct Src { unsigned char wep,arc; unsigned short blob; };
static_assert(sizeof(Row)==12 && sizeof(Blob)==24 && sizeof(Src)==4,"hand package directory layout");
Row rows[kRows];Blob blobs[kBlobs];Src srcs[kSources];
unsigned nrows,nblobs,nsrcs,file_bytes;
int dir_state;  // 0 not read, 1 ready, 2 failed (logged once)
alignas(32) unsigned char slot5[kSlotBytes[0]];
alignas(32) unsigned char slot6[kSlotBytes[1]];
unsigned char* const slot[2]={slot5,slot6};
int slot_blob[2]={-1,-1};
unsigned aica;               // the cells' base (0: not allocated)
int cell_blob[4]={-1,-1,-1,-1};   // 0 right home, 1 right other, 2 left home, 3 left other
int refill[4]={-1,-1,-1,-1};      // what the cells held when they were freed
#if RE4DC_LEON_HAND_RETAIN
unsigned cell_used[4],use_clock;   // demand LRU per side; zero means prefetched but not drawn
#else
unsigned cell_used[4],use_clock;   // LRU per side: the least recently drawn cell of the side is replaced
#endif
unsigned reads,read_bytes,copies,hits,misses,yields,refills,alloc_fails,hit_max_us,async_reads,async_fails,async_max_us,pick_max_us;
inline unsigned r32(unsigned x){return (x+31u)&~31u;}
unsigned blob_bytes(const Blob& b){unsigned n=0;for(unsigned i=0;i<5;++i)n+=r32(b.size[i]);return n;}
unsigned cell_offset(unsigned c){return (c>>1)*2u*kSlotBytes[0]+(c&1u)*kSlotBytes[c>>1];}
const char* package(){return "/cd/dc/native/pl00/leon_hands_pl00.re4hp";}  // pl00 and pl08 hands are byte-identical

file_t job_file=FILEHND_INVALID;  // the worker's handle: opened with the directory (a load point; an open costs ~20 ms)
bool read_at(unsigned offset,void* to,unsigned bytes) {
    file_t f=fs_open(package(),O_RDONLY);
    if(f==FILEHND_INVALID)return false;
    const bool ok=fs_seek(f,offset,SEEK_SET)==off_t(offset) && fs_read(f,to,bytes)==ssize_t(bytes);
    fs_close(f);
    ++reads;read_bytes+=bytes;
    return ok;
}
#include "platform/include/gc_asset_hand_source.inc"
#include "platform/include/gc_asset_hand_runtime.inc"
// The package's directory (hands_pack.py checks every field it writes; here: the layout, the bounds the reads and
// slots rely on, and the standard hands as blobs 0 (right) and 1 (left)).
bool directory() {
    if(dir_state)return dir_state==1;
    dir_state=2;
    unsigned char* b=re4dc_dvd_buff+RE4DC_DVD_BUFF_BYTES/2;  // DVD_BUFF2: used only inside synchronous DVD swaps (src/game/dvd.cpp)
    unsigned h[8]{};
    unsigned bad=1;
    if(read_at(0,h,32) && h[0]==kMagic && (h[1]&0xffffu)==kVersion && h[3]==kSlotBytes[0] && h[4]==kSlotBytes[1]) {
        nrows=h[1]>>16;nblobs=h[2]&0xffffu;nsrcs=h[2]>>16;file_bytes=h[6];
        const unsigned dir=h[5],ro=32,bo=ro+nrows*12,so=bo+nblobs*24;
        bad=2;
        if(nrows<=kRows && nblobs>=2 && nblobs<=kBlobs && nsrcs<=kSources && dir<=RE4DC_DVD_BUFF_BYTES/2 && so+nsrcs*4<=dir && read_at(0,b,dir)) {
            std::memcpy(rows,b+ro,nrows*12);std::memcpy(blobs,b+bo,nblobs*24);std::memcpy(srcs,b+so,nsrcs*4);
            bad=(blobs[0].role!=5 || blobs[1].role!=6 || !(blobs[0].flags&blobs[1].flags&1))?3:0;
            for(unsigned i=0;i<nblobs;++i){const Blob& x=blobs[i];
                if((x.role-5u)>1u || blob_bytes(x)>kSlotBytes[x.role-5] || x.offset32*32u+blob_bytes(x)>file_bytes)bad=4;}
        }
    }
    re4dc_log("LHPACK dir rows=%u blobs=%u src=%u file=%u why=%u\n",nrows,nblobs,nsrcs,file_bytes,bad);
    if(bad)return false;
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_directory_candidate(h);
#endif
    job_file=fs_open(package(),O_RDONLY);
    dir_state=1;
    return true;
}
// The cells live in AICA RAM between the sound layout and the movie reserve; never while a movie streams.
bool cells() {
    if(aica)return true;
    aica=snd_mem_malloc(kCellBytes);
    if(!aica){if(alloc_fails++<4)re4dc_log("LHPACK no cells\n");return false;}
    return true;
}
int cell_of(int b){for(unsigned c=0;c<4;++c)if(cell_blob[c]==b)return int(c);return -1;}
// The side's cell for a new blob: an empty one, else the least recently drawn (the home poses are only prefetched first).
#if RE4DC_LEON_HAND_RETAIN
unsigned cell_for(int b){const int found=cell_of(b);if(found>=0)return unsigned(found);
    const unsigned c=(blobs[b].role-5u)*2u;
#else
unsigned cell_for(int b){const unsigned c=(blobs[b].role-5u)*2u;
#endif
    if(cell_blob[c]<0)return c;if(cell_blob[c+1]<0)return c+1;return cell_used[c]<=cell_used[c+1]?c:c+1;}
#if RE4DC_LEON_HAND_RETAIN
bool hint_room(int b){const unsigned c=(blobs[b].role-5u)*2u;
    return cell_of(b)>=0 || cell_blob[c]<0 || cell_blob[c+1]<0 || !cell_used[c] || !cell_used[c+1];}
enum CacheUse { Hint, Prefetch, Demand };
// A fallback hint cannot evict two demanded poses. Reuse an existing cell;
// only source demand refreshes LRU, while exact loadpoint prefetch may replace.
void cache(int b,const unsigned char* from,CacheUse use=Prefetch) {
    if((use==Hint && !hint_room(b)) || !cells())return;
    const unsigned c=cell_for(b);const bool same=cell_blob[c]==b;
#else
// Put blob b in its cell from `from` (main RAM holding its bytes).
void cache(int b,const unsigned char* from) {
    if(!cells())return;
    const unsigned c=cell_for(b);
#endif
#if RE4DC_GC_ASSET_GATE
    const auto gcasset_copy=gcasset_hand_cell_begin(c,b,from);
#endif
    spu_memload(aica+cell_offset(c),from,blob_bytes(blobs[b]));
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_cell_end(c,b,gcasset_copy);
#endif
#if RE4DC_LEON_HAND_RETAIN
    cell_blob[c]=b;if(use==Demand)cell_used[c]=++use_clock;else if(!same)cell_used[c]=0;
#else
    cell_blob[c]=b;cell_used[c]=++use_clock;
#endif
}
#if RE4DC_LEON_HAND_RETAIN
// Fallback ALT is a hint. An unchanged current CPU slot is already authoritative
// package data, so loadpoints need not read that blob back from the disc.
void prefetch(int b,bool hint=false) {
    if(b<0 || unsigned(b)>=nblobs || cell_of(b)>=0 || (hint && !hint_room(b)) || !cells())return;
    const unsigned side=blobs[b].role-5u;const auto use=hint?Hint:Prefetch;
    if(slot_blob[side]==b){cache(b,slot[side],use);return;}
#else
// Prefetch blob b into its cell (bounce through DVD_BUFF2; the draw slots are not touched).
void prefetch(int b) {
    if(b<0 || unsigned(b)>=nblobs || cell_of(b)>=0 || !cells())return;
#endif
    unsigned char* t=re4dc_dvd_buff+RE4DC_DVD_BUFF_BYTES/2;
    static_assert(kSlotBytes[0]<=RE4DC_DVD_BUFF_BYTES/2 && kSlotBytes[1]<=RE4DC_DVD_BUFF_BYTES/2,"LHPACK blob bounce exceeds DVD_BUFF2");
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_scratch={};const auto gcasset_read=gcasset_hand_read_begin(b);
#endif
    if(!read_at(unsigned(blobs[b].offset32)*32u,t,blob_bytes(blobs[b])))return;
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_scratch=gcasset_hand_read_end(gcasset_read,b,true);
#endif
#if RE4DC_LEON_HAND_RETAIN
    cache(b,t,use);
#else
    cache(b,t);
#endif
}
// Room load: per side the standard hand, then its home (right) / alternating (left) pose; the second prefetch of a
// side goes to its other cell, so both stay cached.
void prefetch_home() {
    if(!directory())return;
    for(unsigned i=0;i<nblobs;++i)if(blobs[i].flags&1)prefetch(int(i));
    for(unsigned i=0;i<nblobs;++i)if((blobs[i].flags&4) || (blobs[i].role==5 && (blobs[i].flags&2)))prefetch(int(i));
}
// The worker: one read at a time, from the queue (a draw's missing pose, or a cell to refill after a movie).
constexpr unsigned kJobStack=6144,kJobBytes=kJobStack+4+6400+32;
kthread_t* job_thd;
unsigned char* job_mem;
volatile int job_state;   // 0 idle, 1 reading, 2 landed, 3 failed
int job_blob=-1;
volatile unsigned job_us;
int job_queue[8];unsigned job_n;
int want[2]={-1,-1};
// The cache and the worker are shared with the movie / sound bank yield (audio thread): the draw only try-locks
// (busy: it keeps drawing the slots), the load points and the yield wait.
mutex_t lh_mutex=MUTEX_INITIALIZER;      // per side: the pose the game asks for while the slot still draws the one before
unsigned char* job_data(){return job_mem+kJobStack+4;}
void* job_main(void*) {
    const Blob& x=blobs[job_blob];const unsigned off=unsigned(x.offset32)*32u,n=blob_bytes(x);
    const unsigned t0=unsigned(timer_us_gettime64());
    const bool ok=fs_seek(job_file,off,SEEK_SET)==off_t(off) && fs_read(job_file,job_data(),n)==ssize_t(n);
    job_us=unsigned(timer_us_gettime64())-t0;
    job_state=ok?2:3;
    return nullptr;
}
void job_enqueue(int b) {
    if(b<0 || unsigned(b)>=nblobs || b==job_blob)return;
    for(unsigned i=0;i<job_n;++i)if(job_queue[i]==b)return;
    if(job_n<8)job_queue[job_n++]=b;
}
bool job_start(int b) {
    if(job_file==FILEHND_INVALID)return false;
    job_mem=static_cast<unsigned char*>(re4dc_motion_alloc(kJobBytes));
    if(!job_mem)return false;
    job_blob=b;job_state=1;
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_job_begin(b,job_mem,job_data());
#endif
    kthread_attr_t a{};
    a.stack_ptr=job_mem;a.stack_size=kJobStack;a.prio=PRIO_DEFAULT;a.label="leon-hands";
    job_thd=thd_create_ex(&a,job_main,nullptr);
    if(!job_thd){
#if RE4DC_GC_ASSET_GATE
        gcasset_hand_job={};
#endif
        re4dc_motion_free(job_mem);job_mem=nullptr;job_blob=-1;job_state=0;return false;}
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_job.thread=job_thd;
#endif
    return true;
}
void set_slot(unsigned side,int b);
#if RE4DC_LEON_HAND_RETAIN
bool load(unsigned side,int b);
#endif
// Main thread, each Leon draw: take a landed read (into its cell, and into the slot when that side still wants it),
// then start the next queued one.
void job_poll() {
    if(job_state==1)return;
    if(job_thd) {
#if RE4DC_GC_ASSET_GATE
        auto* const gcasset_joined=job_thd;
#endif
        thd_join(job_thd,nullptr);job_thd=nullptr;
        const int b=job_blob;
#if RE4DC_GC_ASSET_GATE
        gcasset_hand_job_end(gcasset_joined,job_mem,job_data(),b,job_state==2);
#endif
        if(job_state==2) {
            const Blob& x=blobs[b];const unsigned side=x.role-5u;
            ++reads;++async_reads;read_bytes+=blob_bytes(x);if(job_us>async_max_us)async_max_us=job_us;
#if RE4DC_LEON_HAND_RETAIN
            const bool demanded=want[side]==b;
            cache(b,job_data(),demanded?Demand:Hint);
            if(demanded){
#if RE4DC_GC_ASSET_GATE
                const auto gcasset_copy=gcasset_hand_slot_begin(side,b,gcasset_hand_origin(job_data(),b));
#endif
                std::memcpy(slot[side],job_data(),blob_bytes(x));
#if RE4DC_GC_ASSET_GATE
                gcasset_hand_slot_end(side,b,gcasset_copy);
#endif
                set_slot(side,b);want[side]=-1;}
#else
            cache(b,job_data());
            if(want[side]==b){
#if RE4DC_GC_ASSET_GATE
                const auto gcasset_copy=gcasset_hand_slot_begin(side,b,gcasset_hand_origin(job_data(),b));
#endif
                std::memcpy(slot[side],job_data(),blob_bytes(x));
#if RE4DC_GC_ASSET_GATE
                gcasset_hand_slot_end(side,b,gcasset_copy);
#endif
                set_slot(side,b);want[side]=-1;}
#endif
            if(async_reads<=64)re4dc_log("LHPACK landed blob=%u role=%u read_us=%u\n",unsigned(b),5u+side,unsigned(job_us));
        } else ++async_fails;
#if RE4DC_GC_ASSET_GATE
        gcasset_hand_job={};
#endif
        re4dc_motion_free(job_mem);job_mem=nullptr;job_blob=-1;job_state=0;
    }
    while(job_n) {
        const int b=job_queue[0];
        for(unsigned i=1;i<job_n;++i)job_queue[i-1]=job_queue[i];
        --job_n;
        const unsigned side=blobs[b].role-5u;
#if RE4DC_LEON_HAND_RETAIN
        // An equip/loadpoint may satisfy an already queued pose. Consume its
        // cached/current-slot bytes before starting an unnecessary worker read.
        if(cell_of(b)>=0){if(want[side]==b)load(side,b);continue;}
        if(slot_blob[side]==b){if(want[side]==b)load(side,b);else cache(b,slot[side],Hint);continue;}
        if(want[side]!=b && !hint_room(b))continue;
#else
        if(cell_of(b)>=0 && want[side]!=b)continue;
#endif
        if(!cells() && want[side]!=b)continue;
        if(!job_start(b)){++async_fails;if(want[side]==b)job_enqueue(b);}
        break;
    }
}
// After a movie: the cells it took back, through the worker.
void refill_now() {
    if(refill[0]<0 && refill[1]<0 && refill[2]<0 && refill[3]<0)return;
    if(!cells())return;
    ++refills;
    for(unsigned c=0;c<4;++c){job_enqueue(refill[c]);refill[c]=-1;}
}
void reset_role_ids(unsigned role);   // coarse_actor_owner_leon.inc, after coarse_actor_geometry_once.inc
// Point leon4k::chunks[5 + side] at the slot, which now holds blob b.
void set_slot(unsigned side,int b) {
    const Blob& x=blobs[b];
    unsigned char* p=slot[side];const unsigned char* a[5];
    for(unsigned i=0;i<5;++i){a[i]=p;p+=r32(x.size[i]);}
    leon4k::chunks[5+side]=leon4k::Chunk{5+side,x.pc,x.nc,x.pal,x.tri,x.stream,a[0],a[1],a[2],a[3],
        reinterpret_cast<const leon4k::Weight*>(a[4])};
    slot_blob[side]=b;
    reset_role_ids(5+side);
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_slot_publish(side,b);
#endif
}
// Load point only (room load: an empty slot): read blob b into the slot now.
bool load_now(unsigned side,int b) {
    const Blob& x=blobs[b];
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_slot_revoke(side);const auto gcasset_read=gcasset_hand_read_begin(b);
#endif
    if(!read_at(unsigned(x.offset32)*32u,slot[side],blob_bytes(x)))return false;
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_copy[side]=gcasset_hand_read_end(gcasset_read,b,true);
#endif
#if RE4DC_LEON_HAND_RETAIN
    cache(b,slot[side],Demand);set_slot(side,b);
#else
    cache(b,slot[side]);set_slot(side,b);
#endif
    return true;
}
// Draw: make slot `side` hold blob b when it is cached (a G2 copy); else ask the worker for it and keep drawing the
// slot's pose. false: the slot is empty (the plan declines).
bool load(unsigned side,int b) {
#if RE4DC_LEON_HAND_RETAIN
    if(slot_blob[side]==b){
        want[side]=-1;const int c=cell_of(b);
        if(c>=0)cell_used[c]=++use_clock;else if(aica)cache(b,slot[side],Demand);
        return true;
    }
#else
    if(slot_blob[side]==b){want[side]=-1;return true;}
#endif
    const Blob& x=blobs[b];
    const int c=cell_of(b);
    if(c>=0) {
        const unsigned t0=unsigned(timer_us_gettime64());
#if RE4DC_GC_ASSET_GATE
        const auto gcasset_copy=gcasset_hand_slot_begin(side,b,gcasset_hand_cell_origin(unsigned(c),b));
#endif
        spu_memread(slot[side],aica+cell_offset(unsigned(c)),blob_bytes(x));++copies;++hits;cell_used[c]=++use_clock;
#if RE4DC_GC_ASSET_GATE
        gcasset_hand_slot_end(side,b,gcasset_copy);
#endif
        const unsigned us=unsigned(timer_us_gettime64())-t0;if(us>hit_max_us)hit_max_us=us;
        set_slot(side,b);want[side]=-1;
        return true;
    }
    if(want[side]!=b) {
        ++misses;want[side]=b;job_enqueue(b);
        // The hitch check reads these: a pose not in the cache (the slot keeps drawing slot_blob until it lands).
        if(misses<=64)re4dc_log("LHPACK miss blob=%u role=%u drawing=%d cells=%d/%d/%d/%d\n",unsigned(b),5u+side,
            slot_blob[side],cell_blob[0],cell_blob[1],cell_blob[2],cell_blob[3]);
    }
    return slot_blob[side]>=0;
}
// The blob that draws role 5 / 6 for this hand info: its GC key's row, else the standard hand.
int blob_for(unsigned role,const cModelInfo* info) {
    if(info && info->pData && info->pData->vtxOrig) {
        const ModelData* d=info->pData;
        const unsigned pal=d->weight_ext_num>255?d->weight_ext_num:d->weight_palette_num;
        const unsigned h=fingerprint(d->vtxOrig);
        for(unsigned k=0;k<nrows;++k) {
            const Row& r=rows[k];
            if(r.role==role && r.positions==d->nVtx && r.normals==d->nNrm && r.palette==pal && r.hash==h && r.blob<nblobs &&
               blobs[r.blob].role==role)return r.blob;
        }
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
        static unsigned seen[16],nseen;bool known=false;
        for(unsigned k=0;k<nseen;++k)known|=seen[k]==(h^role);
        if(!known && nseen<16){seen[nseen++]=h^role;
            re4dc_log("LEONHAND standard role=%u key=%u/%u/%u/%u (no PS2 pose hand)\n",role,unsigned(d->nVtx),unsigned(d->nNrm),pal,h);}
#endif
    }
    return int(role-5);   // the standard hand (blob 0 right, 1 left)
}
inline unsigned std_pal(unsigned role){return blobs[role-5].pal;}  // the standard hands are blobs 0 / 1
}
#if RE4DC_GC_ASSET_GATE
extern "C" unsigned re4dc_gcasset_hand_derive_begin(const void* target,unsigned bytes){return leon_hand_pack::gcasset_hand_derive_begin(target,bytes);}
extern "C" void re4dc_gcasset_hand_derive_end(unsigned ticket,bool complete){leon_hand_pack::gcasset_hand_derive_end(ticket,complete);}
#endif
namespace {
unsigned leon_hand_asset(unsigned){return 0;}  // unused: the slots keep IDs 6 / 7
struct LeonHandPick { const leon4k::Chunk* chunk;re4dc_source::ChunkInput input;unsigned asset;int pose; };
// Role 5 / 6 for this hand info, loaded into its slot (nullptr: no package / read failure: the plan declines).
__attribute__((noinline)) LeonHandPick leon_hand_pick(unsigned role,const cModelInfo* info,const leon4k::Chunk&,const re4dc_source::ChunkInput&) {
    using namespace leon_hand_pack;
    if(!directory())return {nullptr,{},0,-1};
    if(mutex_trylock(&lh_mutex)==0) {
        const unsigned t0=unsigned(timer_us_gettime64());
        refill_now();job_poll();
        const bool ok=load(role-5,blob_for(role,info));
        const unsigned us=unsigned(timer_us_gettime64())-t0;if(us>pick_max_us)pick_max_us=us;  // the draw's own cost
        mutex_unlock(&lh_mutex);
        if(!ok)return {nullptr,{},0,-1};
    }
    if(slot_blob[role-5]<0)return {nullptr,{},0,-1};
    const int b=slot_blob[role-5];
    const auto& c=leon4k::chunks[role];const Blob& x=blobs[b];
    return {&c,re4dc_source::ChunkInput{{c.positions,x.size[0]},{c.normals,x.size[1]},{c.uv,x.size[2]},{c.stream,x.size[3]},
        {reinterpret_cast<const unsigned char*>(c.weights),x.size[4]},c.position_count,c.normal_count,c.palette_count,c.triangles,119u},
        role+1u,b};
}
inline unsigned leon_r32(unsigned x){return (x+31u)&~31u;}
const leon4k::Chunk* leon_cur[8]={&leon4k::chunks[0],&leon4k::chunks[1],&leon4k::chunks[2],&leon4k::chunks[3],
    &leon4k::chunks[4],&leon4k::chunks[5],&leon4k::chunks[6],&leon4k::chunks[7]};
unsigned leon_cur_key;
inline unsigned leon_hand_key(unsigned costume,int right,int left) {
    return costume|unsigned(right+1)<<8|unsigned(left+1)<<16;
}
}
// Room load (ui_bridge.cpp, with the pl08 package): the home poses into their cells.
extern "C" void re4dc_leon_hands_room_enter() {
    using namespace leon_hand_pack;
    mutex_lock(&lh_mutex);
    prefetch_home();refill_now();
    for(unsigned side=0;side<2;++side)if(slot_blob[side]<0 && directory())load_now(side,int(side));
    re4dc_log("LHPACK room reads=%u bytes=%u hits=%u misses=%u async=%u/%u/%u pick=%u yields=%u copy=%u cells=%d/%d/%d/%d\n",
        reads,read_bytes,hits,misses,async_reads,async_fails,async_max_us,pick_max_us,yields,hit_max_us,
        cell_blob[0],cell_blob[1],cell_blob[2],cell_blob[3]);
    mutex_unlock(&lh_mutex);
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_directory_pump();
#endif
}
// Weapon equip (read.cpp ReadWepData, after the weapon archive read): the weapon's own hand BINs into the other cells.
extern "C" void re4dc_leon_hands_weapon(const char* name) {
    using namespace leon_hand_pack;
    if(!name || !directory())return;
    const char* w=name;
    while(*w && !(w[0]=='w' && w[1]=='e' && w[2]=='p'))++w;
    if(!*w || unsigned(w[3]-'0')>9u || unsigned(w[4]-'0')>9u)return;
    const unsigned no=unsigned(w[3]-'0')*10u+unsigned(w[4]-'0');
    bool done[2]={};
    mutex_lock(&lh_mutex);
    for(unsigned i=0;i<nsrcs;++i) {
        const Blob& x=blobs[srcs[i].blob];
        if(srcs[i].wep!=no || done[x.role-5] || (x.flags&2))continue;
        done[x.role-5]=true;prefetch(srcs[i].blob);
    }
#if RE4DC_LEON_HAND_RETAIN
    for(unsigned i=0;i<nblobs;++i)if((blobs[i].flags&4) && !done[blobs[i].role-5])prefetch(int(i),true);
#else
    for(unsigned i=0;i<nblobs;++i)if((blobs[i].flags&4) && !done[blobs[i].role-5])prefetch(int(i));
#endif
    mutex_unlock(&lh_mutex);
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_directory_pump();
#endif
}
// Movie open (native_movie.cpp) and a runtime sound bank conversion (audio_aica.cpp): give the AICA cells back.
extern "C" void re4dc_leon_hands_yield() {
    using namespace leon_hand_pack;
    mutex_lock(&lh_mutex);
#if RE4DC_GC_ASSET_GATE
    gcasset_hand_job={};gcasset_hand_scratch={};
    for(auto& cell:gcasset_hand_cell)cell={};gcasset_hand_aica=0;
#endif
    if(job_thd){thd_join(job_thd,nullptr);job_thd=nullptr;re4dc_motion_free(job_mem);job_mem=nullptr;job_blob=-1;job_state=0;}
    job_n=0;want[0]=want[1]=-1;
    if(!aica){mutex_unlock(&lh_mutex);return;}
    snd_mem_free(aica);aica=0;++yields;
    for(unsigned c=0;c<4;++c){refill[c]=cell_blob[c];cell_blob[c]=-1;}
    mutex_unlock(&lh_mutex);
}
#pragma GCC pop_options
