#include "include/movie_world_arena.h"
// PS2 prerecorded cinematics as presentation for source events (PS2-inspired
// profile). Generalised from the experiment/ps2-fmv-spike r120s00 adapter:
// same R4FMV003 transport (MPEG-1 WxH 29.97 + PCM16 stereo 32 kHz, one
// interleaved record per picture), same bounded reader, decoder and AICA
// stream; any route movie by id, and a native_ui override so a movie shows
// while the source holds its picture (System_flg 0x400).
// In-room budget: everything below comes from the current source heap and is
// returned at the terminal. At the route size 288x192 the player stages about
// 250 KB (two I/P frames 166 KB, video 32 KB, read 16 KB, PCM 16 KB, AICA
// separation 8 KB, callback 8 KB, strip 4.5 KB); r100's entry event has
// 311 KB free. The KOS heap is not used (native_movie_stream.c).
// The source event caller owns every gameplay effect and the skip semantics;
// this file never touches source state.
#include <kos.h>
#include <dc/sound/stream.h>
#include <dc/sound/sound.h>
#include <fcntl.h>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <malloc.h>
#include <dc/sq.h>
#include <dc/pvr.h>
#include "re4dc_platform.h"
#include "native_ui.h"
#include "native_io.h"
#include "native_movie.h"
#include "include/gc_asset_movie.h"
#include "include/native_cabin.h"
#include "../../room/room_storage.hpp"
#if RE4DC_MOVIE_DISC_QUIET
// MOVIE_DISC_QUIET: 1 while a route movie is open (it owns the GD drive); audio_aica.cpp's disc stream reader
// holds back any stream prefill meanwhile. Timing of sound reads only; game state never reads it.
extern "C" { volatile int re4dc_movie_disc_owner; }
#endif
#if RE4DC_ROUTE_MOVIES
#ifndef RE4DC_ROUTE_MOVIE_YUV
#define RE4DC_ROUTE_MOVIE_YUV 1      // full-range movies go through the PVR YUV converter
#endif
#ifndef RE4DC_ROUTE_MOVIE_TEXHASH
#define RE4DC_ROUTE_MOVIE_TEXHASH 0  // verification: FNV of the texture of pictures 0/1/30/300
#endif
namespace { void* plm_alloc(size_t n); }
// Two I/P reference frames, fixed buffers: no growth path is reachable.
#define PLM_MALLOC(n) plm_alloc(n)
#define PLM_REALLOC(p,n) nullptr
#define PLM_FREE(p) ((void)0)
#define PLM_NO_STDIO
#define PLM_VIDEO_TWO_FRAMES
#if RE4DC_MOVIE_HEAP_EVICT
#define PLM_VIDEO_SPLIT_FRAMES  // the frames in two 83 KB pieces (288x192), not one 166 KB piece
#endif
#define PLM_RE4DC_FAST        // bit-exact fast paths (third_party/PL_MPEG_PIN.md)
#define PL_MPEG_IMPLEMENTATION
#include "../third_party/pl_mpeg.h"
extern "C" int re4dc_movie_stream_initialized();
#if RE4DC_MOVIE_WORLD_ARENA
extern "C" int re4dc_movie_stream_idle();
#endif
extern "C" unsigned re4dc_movie_stream_active();
extern "C" unsigned re4dc_movie_stream_staged;
#if defined(RE4DC_LEON_HAND_PACK) && RE4DC_LEON_HAND_PACK
extern "C" void re4dc_leon_hands_yield();  // coarse_actor_leon_hands.inc
#endif
extern "C" void re4dc_pad_consume_movie_skip(unsigned);
// Fixture state reports are optional: the pad-script fixture defines this
// (uncommitted pad.cpp work); without it the movie reports nothing.
extern "C" void re4dc_fixture_state(const char* name,int a,int b) __attribute__((weak));
static void movie_state(int a,int b){if(re4dc_fixture_state)re4dc_fixture_state("movie",a,b);}
extern "C" int re4dc_ui_movie_open(unsigned width, unsigned height);
extern "C" int re4dc_ui_movie_present_now();
// main.cpp: vsyncs since the last presented game frame. postVSyncCallback -> haltExecCheck
// halts the game after 3600 (60 s) without one; a movie owns the frame and presents instead.
extern volatile int vsync_cnt;
extern "C" unsigned re4dc_pad_movie_buttons();
extern "C" unsigned long re4dc_vi_retrace_count(void);
extern "C" int re4dc_ui_movie_upload_begin();
extern "C" void re4dc_ui_movie_upload_rows(const void* uyvy, unsigned y, unsigned rows);
extern "C" void re4dc_ui_movie_upload_end();
extern "C" int re4dc_ui_movie_close();
extern "C" unsigned re4dc_ui_movie_presented();
extern "C" uint64_t re4dc_ui_movie_first_picture_us();
extern "C" int re4dc_ui_movie_last_presented();
extern "C" void* re4dc_ui_movie_texture();
#if RE4DC_CABIN_SOURCE
extern "C" void re4dc_ui_movie_background(int);
#endif
namespace {
// Hard caps: every write is checked against them, nothing grows.
// snd_stream_fill asks for half the 8 KiB ring per channel: 8 KiB interleaved.
// Ring: the AICA ring per channel, 512 ms of 32 kHz PCM16. The player is one thread: a GD read
// blocks audio polling, and a read that outlasts the fresh part of the ring (half of it after a
// poll) loses audio for good, which puts every later picture behind the vblank clock. Seeks
// after the game's own reads took up to 306 ms (r101s30 from the r101 fight); an 8 KiB ring
// (128 ms) lost 717 ms in its first 3 s and dropped 1321 of 1331 pictures. The poll hands out
// up to half the ring per channel (CallbackCap interleaved); AudioStart primes 320 ms before
// the clock starts; VideoCap holds the video of those records plus one more.
constexpr unsigned Ring=32768, VideoCap=65536, AudioCap=49152, AudioStart=40960, CallbackCap=Ring, ReadCap=16384;
constexpr unsigned Rows=8, MaxWidth=320, MaxHeight=240;
#if RE4DC_MOVIE_HEAP_EVICT
constexpr unsigned MaxAllocs=16;  // + the frames' planes as six pieces
#else
constexpr unsigned MaxAllocs=10;
#endif
#if !RE4DC_MOVIE_HEAP_EVICT
#undef RE4DC_MOVIE_STAGE_ORDER
#undef RE4DC_MOVIE_BALLAST_TEST
#endif
#ifndef RE4DC_MOVIE_STAGE_ORDER
#define RE4DC_MOVIE_STAGE_ORDER 0
#endif
#ifndef RE4DC_MOVIE_BALLAST_TEST
#define RE4DC_MOVIE_BALLAST_TEST 0   // test only: bytes of heap 4 held through r100 s30 (the margin probe)
#endif
#if RE4DC_MOVIE_STAGE_ORDER
// MOVIE_STAGE_ORDER: the movie's large pieces are staged up front, largest first (first fit decreasing), while
// heap 4 still has its largest holes; the player and the decoder then take them by size.
constexpr unsigned MaxReserve=12;
#endif
struct Movie {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::CheckedAsset asset{};unsigned asset_owner=0;
#endif
    unsigned id=0; char path[40]{};
    file_t file=-1; plm_buffer_t* input=nullptr; plm_video_t* decoder=nullptr;
    unsigned char *pcm=nullptr,*callback=nullptr,*readbuf=nullptr,*rows=nullptr;
    void* allocs[MaxAllocs]{}; unsigned nallocs=0, staged=0;
    unsigned transport_left=0,read_at=0,read_used=0;
    snd_stream_hnd_t stream=-1; bool owns_service=false,started=false,failed=false,texture=false;
    unsigned pcm_used=0,video_left=0,audio_left=0,frames=0,uploaded=0,underruns=0,silence_bytes=0;
    unsigned samples=0,last_real_sample=0,expected_frames=0,audio_bytes=0;
    unsigned long long entered=0,start=0,max_read=0,max_decode=0,max_convert=0,max_upload=0;
    unsigned long long sum_decode=0,sum_convert=0,sum_upload=0,duration_us=0;
    int heap_before=0,heap_active=0,terminal=0; unsigned vram_before=0,width=0,height=0;
    unsigned shown=0,dropped=0,late=0,cadence2=0,cadence_other=0,max_gap=0,last_submit=0,v0=0;
    unsigned long long sum_present=0,max_present=0,sum_idle=0,starve_since=0;
    unsigned starved=0;
#if RE4DC_MOVIE_STAGE_ORDER
    void* reserve[MaxReserve]{}; unsigned reserve_bytes[MaxReserve]{}; unsigned nreserve=0;
#endif
#if RE4DC_MOVIE_BALLAST_TEST
    void* ballast=nullptr;
#endif
    unsigned k=0,held=0,mask=0; bool armed=false,held_end=false; plm_frame_t* pending=nullptr;  // loop state (start/iterate)
    bool full=false,hw=false; void* tex=nullptr; unsigned yuv_timeouts=0;
#if RE4DC_ROUTE_MOVIE_DIAG
    const char* why=nullptr; unsigned reads=0,iter=0; unsigned long long read_us=0;
#endif
} m;
#if RE4DC_CABIN_SOURCE
// CABIN_MOVIE_STATE_BEGIN
struct CabinMovie {
    unsigned generation=0, readers=0, ui_generation=0, final_upload=0;
    unsigned video_records=0, video_bytes=0, audio_bytes=0, fast_passes=0;
    unsigned long long final_wait=0;
    plm_frame_t* final_frame=nullptr;
    void* codec_control[2]{};bool codec_taken[2]{};
    bool finishing=false, retiring=false, skip=false, checked=false, transport_retired=false;
    int terminal=RE4DC_MOVIE_RUNNING;
} cabin_movie;
unsigned cabin_movie_epoch=0;
struct CabinMovieRead {
    CabinMovieRead(){++cabin_movie.readers;}
    ~CabinMovieRead(){--cabin_movie.readers;}
};
int cabin_movie_finish(int status);
bool cabin_movie_content();
bool cabin_movie_identity();
// CABIN_MOVIE_STATE_END
#endif
#if RE4DC_MOVIE_WORLD_ARENA
static_assert(sizeof(plm_buffer_t)==52 && sizeof(plm_video_t)==716,"review movie arena decoder ABI");
unsigned movie_world_token=0,movie_scope=0,movie_epoch=1,movie_readers=0;
bool movie_full_call=false,movie_retiring=false,movie_finishing=false;
bool movie_world_id(unsigned id){
    return id==0x11f10 || id==0x11f11
#if RE4DC_MOVIE_WORLD_ARENA_S30
        || id==0x10030
#endif
        ;
}
struct MovieFinishScope {
    bool active;
    MovieFinishScope():active(movie_world_token!=0){if(active)movie_finishing=true;}
    ~MovieFinishScope(){if(active)movie_finishing=false;}
};
struct MovieReader { MovieReader(){++movie_readers;} ~MovieReader(){--movie_readers;} };
bool movie_world_current(){return !movie_world_token || re4dc_ps2_mesh_movie_valid(movie_world_token);}
void movie_stage_free(void* p){
    if(movie_world_token){
        if(!re4dc_ps2_mesh_movie_free(movie_world_token,p))re4dc_missing("movie arena invalid or duplicate free");
    }else re4dc_ui_stage_free(p);
}
#endif
#if RE4DC_ROUTE_MOVIE_DIAG
#define MOVIE_WHY(s) (m.why=(s))
#else
#define MOVIE_WHY(s) ((void)0)
#endif
#if RE4DC_MOVIE_HEAP_EVICT
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
extern "C" void re4dc_motion_movie_begin();
extern "C" unsigned re4dc_motion_movie_evict_one();
extern "C" void re4dc_motion_movie_finish(int);
#endif
extern "C" unsigned re4dc_motion_evict_one();   // native_motion.cpp
#if RE4DC_WEAPON_HEAP4
extern "C" int re4dc_weapon_heap4_movie_release();   // read.cpp
#endif
extern "C" unsigned re4dc_heap_largest_current(unsigned* free_bytes);   // sscrn_bridge.cpp (SS_PACK)
extern "C" unsigned re4dc_heap_largest_current(unsigned*) __attribute__((weak));
extern "C" void re4dc_heap4_free_map() __attribute__((weak));   // ui_bridge.cpp (diagnostic)
extern "C" unsigned re4dc_model_release_retained() __attribute__((weak));   // ui_bridge.cpp
#if defined(RE4DC_GANADO_VAR) && RE4DC_GANADO_VAR
// ACTOR_GANADO_PS2_STUMP (coarse_actor_owner_ganado.inc): the Ganado variant cell is lent after the model cache.
extern "C" unsigned re4dc_ganado_var_lend();
extern "C" void re4dc_ganado_var_return();
#endif
// ui_bridge.cpp owns the loan: 1 when this movie had it (bytes restored, model draws that asked during the loan).
extern "C" int re4dc_model_return_retained(unsigned* bytes,unsigned* requests) __attribute__((weak));
#if defined(RE4DC_MOVIE_LOAN_TEST) && RE4DC_MOVIE_LOAN_TEST
unsigned loan_test_id;   // test only: the movie that lent the cache at its first staging allocation (+1)
#endif
#endif
#if RE4DC_PS2_INTERIOR_CULL
extern "C" unsigned re4dc_ps2_interior_movie_release();   // native_static.cpp: the r100 cell block
#endif
#if RE4DC_FAR_SHELL
extern "C" unsigned re4dc_far_shell_movie_release();   // native_static.cpp far_shell.inc: the room's far shell
#endif
void* stage_alloc(size_t n){
#if RE4DC_MOVIE_WORLD_ARENA
    if(movie_world_token)return n<=0xffffffffu?re4dc_ps2_mesh_movie_alloc(movie_world_token,unsigned(n)):nullptr;
#endif
#if RE4DC_MOVIE_HEAP_EVICT && defined(RE4DC_MOVIE_HEAP_PREFLIGHT) && RE4DC_MOVIE_HEAP_PREFLIGHT
    // MOVIE_HEAP_PREFLIGHT (game30.mk): the loan and the key evictions below, before an allocation that cannot fit
    // (exact: mem_alloc asks OSAlloc for round32(n) + 0x20, which takes a free cell of that + 0x20 header), so no
    // required allocation fails first. Heap 4 ends as it did after the failed attempt and the same releases.
    if(re4dc_heap_largest_current){
        const unsigned want=((unsigned(n)+31U)&~31U)+0x40U;
        unsigned free_bytes=0,largest=re4dc_heap_largest_current(&free_bytes);
        if(largest<want){
            unsigned lent=0,evicted=0,freed=0;
            if(re4dc_model_release_retained){
                lent=re4dc_model_release_retained();
                if(lent)largest=re4dc_heap_largest_current(&free_bytes);
            }
#if defined(RE4DC_GANADO_VAR) && RE4DC_GANADO_VAR
            if(largest<want){
                const unsigned v=re4dc_ganado_var_lend();
                if(v){lent+=v;largest=re4dc_heap_largest_current(&free_bytes);}
            }
#endif
            while(largest<want){
                const unsigned f=
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
                    re4dc_motion_movie_evict_one();
#else
                    re4dc_motion_evict_one();
#endif
                if(!f)break;
                ++evicted;freed+=f;
                largest=re4dc_heap_largest_current(&free_bytes);
            }
            re4dc_log("route movie heap: preflight need=%u lent=%u evicted=%u motion keys (%u B) %s free=%u largest=%u\n",
                      (unsigned)n,lent,evicted,freed,largest>=want?"fits":"short",free_bytes,largest);
        }
    }
#endif
    void* p=re4dc_ui_stage_alloc((unsigned)n);
#if RE4DC_MOVIE_HEAP_EVICT
#if defined(RE4DC_MOVIE_LOAN_TEST) && RE4DC_MOVIE_LOAN_TEST
    // MOVIE_LOAN_TEST=1 (test only, game30.mk): at each movie's first staging allocation the model preparation
    // cache is lent although heap 4 had room (the stepped-movie ownership test); the allocation itself is kept, so
    // a movie still plays when there is no cache to lend.
    if(p && loan_test_id!=m.id+1 && re4dc_model_release_retained){
        loan_test_id=m.id+1;
        const unsigned lent=re4dc_model_release_retained();
        re4dc_log("route movie heap: test: %05x lends the model preparation cache (%u B; need=%u had room)\n",m.id,lent,
                  (unsigned)n);
    }
#endif
    // Heap 4 short or fragmented (r100 s30 after the ambush: 257,568 B free for 363 KB, the largest piece under
    // 83 KB): first the model preparation cache (rebuilt per frame; the movie owns the frame) is lent to the movie,
    // then unpinned motion keys go, least recently used first, until the piece fits. LRU keys alone did not always
    // make a contiguous piece: with the texture pack the route reached the cliff earlier and the second luma plane
    // failed with 197 KB free in holes of at most 40 KB (route-hm1).
    if(!p && re4dc_model_release_retained){
        const unsigned lent=re4dc_model_release_retained();
        if(lent){
            p=re4dc_ui_stage_alloc((unsigned)n);
            re4dc_log("route movie heap: need=%u model preparation cache lent (%u B) %s\n",(unsigned)n,lent,p?"ok":"short");
        }
    }
#if defined(RE4DC_GANADO_VAR) && RE4DC_GANADO_VAR
    if(!p){
        const unsigned v=re4dc_ganado_var_lend();
        if(v){
            p=re4dc_ui_stage_alloc((unsigned)n);
            re4dc_log("route movie heap: need=%u ganado variants lent (%u B) %s\n",(unsigned)n,v,p?"ok":"short");
        }
    }
#endif
    if(!p){
        unsigned evicted=0,freed=0;
        while(!p){
            const unsigned f=
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
                    re4dc_motion_movie_evict_one();
#else
                    re4dc_motion_evict_one();
#endif
            if(!f)break;
            ++evicted;freed+=f;
            p=re4dc_ui_stage_alloc((unsigned)n);
        }
        unsigned free_bytes=0,largest=0;
        if(re4dc_heap_largest_current)largest=re4dc_heap_largest_current(&free_bytes);
        re4dc_log("route movie heap: need=%u evicted=%u motion keys (%u B) %s free=%u largest=%u\n",(unsigned)n,
                  evicted,freed,p?"ok":"FAILED",free_bytes,largest);
#if RE4DC_WEAPON_HEAP4
        // WEAPON_HEAP4: a heap-4 weapon body is lent to the movie and loaded again after it (read.cpp).
        if(!p && re4dc_weapon_heap4_movie_release()){
            p=re4dc_ui_stage_alloc((unsigned)n);
            re4dc_log("route movie heap: need=%u heap-4 weapon body lent %s\n",(unsigned)n,p?"ok":"FAILED");
        }
#endif
        if(!p && re4dc_heap4_free_map)re4dc_heap4_free_map();
    }
#endif
    return p;
}
void* plm_alloc(size_t n){
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation && (n==sizeof(plm_buffer_t) || n==sizeof(plm_video_t))){
        const unsigned i=n==sizeof(plm_buffer_t)?0:1;
        if(!cabin_movie.codec_control[i] || cabin_movie.codec_taken[i]){
            re4dc_missing("cabin codec control allocation protocol");return nullptr;
        }
        cabin_movie.codec_taken[i]=true;return cabin_movie.codec_control[i];
    }
#endif
    if(m.nallocs==MaxAllocs)return nullptr;
#if RE4DC_MOVIE_STAGE_ORDER
    for(unsigned i=0;i<m.nreserve;++i)if(m.reserve[i]&&m.reserve_bytes[i]==n){
        void* p=m.reserve[i];m.reserve[i]=nullptr;
        m.allocs[m.nallocs++]=p;m.staged+=n;
        return p;
    }
#endif
    void* p=stage_alloc(n);
    if(p){m.allocs[m.nallocs++]=p;m.staged+=n;}
    return p;
}
#if RE4DC_MOVIE_STAGE_ORDER
// The pieces open() is about to stage, in the order it would ask (read buffer, PCM, callback, strip, video input,
// two frames' luma and chroma planes, the stream service's separation buffer), staged largest first. r100 s30 with
// the crash screen + PS2_WORLD_DYNAMIC + PS2_INTERIOR_ACTORS (r22f2-s30): asked in the old order, the PCM and callback
// pieces split the lent 131,168 B model-cache hole, and the second luma plane found 219,520 B free in holes of at
// most 47,808 B. Every piece is a staging piece the movie owned before; only the order of the requests changes.
bool reserve_largest_first(bool want_hw,bool service){
    unsigned sizes[MaxReserve],n=0;
    const unsigned luma=m.width*m.height,chroma=(m.width/2)*(m.height/2);
    sizes[n++]=VideoCap;sizes[n++]=luma;sizes[n++]=luma;sizes[n++]=AudioCap;sizes[n++]=CallbackCap;sizes[n++]=ReadCap+32;
    for(unsigned i=0;i<4;++i)sizes[n++]=chroma;
    if(!want_hw)sizes[n++]=Rows*m.width*2;
    if(service)sizes[n++]=Ring+32;
    for(unsigned i=1;i<n;++i)for(unsigned j=i;j&&sizes[j]>sizes[j-1];--j){unsigned t=sizes[j];sizes[j]=sizes[j-1];sizes[j-1]=t;}
    for(unsigned i=0;i<n;++i){
        void* p=stage_alloc(sizes[i]);
        if(!p){re4dc_log("route movie heap: order: piece %u (%u B) short\n",i,sizes[i]);return false;}
        m.reserve[m.nreserve]=p;m.reserve_bytes[m.nreserve]=sizes[i];++m.nreserve;
    }
    return true;
}
// The separation buffer piece goes back just before snd_stream_init_ex stages its own (first fit finds that hole).
void release_reserved(unsigned bytes){
    for(unsigned i=0;i<m.nreserve;++i)if(m.reserve[i]&&(!bytes||m.reserve_bytes[i]==bytes)){
        re4dc_ui_stage_free(m.reserve[i]);m.reserve[i]=nullptr;if(bytes)return;
    }
}
#endif
unsigned little(const unsigned char* p){return p[0]|p[1]<<8|p[2]<<16|p[3]<<24;}
#if defined(RE4DC_MOVIE_AUDIO_PRIME) && RE4DC_MOVIE_AUDIO_PRIME
bool feed();
#endif
void* audio(snd_stream_hnd_t,int requested,int* received){
    // The pinned snd_stream.c passes a byte count.
    unsigned bytes=(unsigned)requested;
    if(bytes>CallbackCap){
        if(!m.failed)re4dc_log("route movie audio request %u exceeds %u\n",bytes,CallbackCap);
        m.failed=true;*received=0;return nullptr;
    }
#if defined(RE4DC_MOVIE_AUDIO_PRIME) && RE4DC_MOVIE_AUDIO_PRIME
    // MOVIE_AUDIO_PRIME (lane fix18, #38): snd_stream_start prefills BOTH ring halves (two requests of CallbackCap =
    // 64 KiB interleaved) before the clock starts, but AudioCap (48 KiB) primes ~47 KB: the second prefill request
    // came up 18,556 B short in every movie (one underrun, ~145 ms of silence spliced into the ring; the Mendez s00c
    // clip's "underruns=1 silence_bytes=18556" at any heap). During the prefill only (not started, same thread, the
    // stream lock not held yet), top the PCM up from the file first. No new memory; feed stops at the video cap.
    if(!m.started)
        while(m.pcm_used<bytes&&m.audio_left&&!m.failed){
            const unsigned before=m.pcm_used;
            if(!feed()){m.failed=true;break;}
            if(m.pcm_used==before)break;  // video full: the rest stays silence, as before
        }
#endif
    unsigned take=bytes<m.pcm_used?bytes:m.pcm_used;
    std::memcpy(m.callback,m.pcm,take);std::memmove(m.pcm,m.pcm+take,m.pcm_used-take);m.pcm_used-=take;
    if(take<bytes){std::memset(m.callback+take,0,bytes-take);if(m.audio_left){++m.underruns;m.silence_bytes+=bytes-take;}}
    if(take)m.last_real_sample=m.samples+take/4;
    m.samples+=bytes/4;*received=requested;return m.callback;
}
#if defined(RE4DC_MOVIE_POLL_SETTLE) && RE4DC_MOVIE_POLL_SETTLE
// MOVIE_POLL_SETTLE (Makefile): right after snd_stream_start the AICA may not have restarted the stream's channel,
// so snd_stream_poll reads the previous voice's play offset (beyond the stream buffer) and returns -1. That is not
// a stream failure: for 200 ms after start it is a no-refill pass (the ring was primed before the start).
int poll_audio(){
    const int r=snd_stream_poll(m.stream);
    if(r==-1 && m.started && timer_us_gettime64()-m.start<200000ULL){
        static unsigned long long logged_start;
        if(logged_start!=m.start){logged_start=m.start;re4dc_log("route movie audio settle: id=%05x stale channel position after start\n",m.id);}
        return 0;
    }
    return r;
}
#else
int poll_audio(){return snd_stream_poll(m.stream);}
#endif
// Sequential transport through the shared ReaderGuard: 32 KiB aligned chunks,
// the header is sector padded so every full chunk stays aligned.
bool transport(void* destination,unsigned bytes){
    auto* out=(unsigned char*)destination;
    while(bytes){
        if(m.read_at==m.read_used){
            unsigned n=m.transport_left<ReadCap?m.transport_left:ReadCap;
            if(!n)return false;
            auto t=timer_us_gettime64();bool ok=true;
            {Re4dcIoScope owner;unsigned aligned=n&~31U;
             if(aligned)ok=re4dc::storage::read_aligned_chunk(m.file,m.readbuf,aligned);
             if(ok&&aligned<n)ok=re4dc::storage::read_exact(m.file,m.readbuf+aligned,n-aligned);}
            auto dt=timer_us_gettime64()-t;if(dt>m.max_read)m.max_read=dt;
#if RE4DC_ROUTE_MOVIE_DIAG
            ++m.reads;m.read_us+=dt;
#endif
            if(!ok){MOVIE_WHY("read");return false;}
            m.transport_left-=n;m.read_at=0;m.read_used=n;
        }
        unsigned n=m.read_used-m.read_at;if(n>bytes)n=bytes;
        std::memcpy(out,m.readbuf+m.read_at,n);out+=n;m.read_at+=n;bytes-=n;
    }
    return true;
}
bool record(){
    unsigned char h[8];if(!transport(h,8))return false;
    unsigned nv=little(h),na=little(h+4);
    if(nv>16384||na>8192||nv>m.video_left||na>m.audio_left||(!nv&&!na))return false;
    plm_buffer_discard_read_bytes(m.input);
    if(nv>VideoCap-m.input->length||na>AudioCap-m.pcm_used)return false;
    if(!transport(m.input->bytes+m.input->length,nv)||!transport(m.pcm+m.pcm_used,na))return false;
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation){
        if(nv)++cabin_movie.video_records;
        cabin_movie.video_bytes+=nv;cabin_movie.audio_bytes+=na;
    }
#endif
    m.input->length+=nv;m.input->has_ended=0;m.pcm_used+=na;m.video_left-=nv;m.audio_left-=na;
    if(!m.video_left)plm_buffer_signal_end(m.input);
    return true;
}
// Interleaved records carry one picture of PCM (<= 4276 bytes); only the
// audio-only tail records carry up to 8 KiB. The AICA asks for 8 KiB (64 ms)
// at a time, so the PCM ring is topped up before every poll, not once a step.
bool feed(){
    for(unsigned i=0;i<4&&(m.video_left||m.audio_left);++i){
        plm_buffer_discard_read_bytes(m.input);
        if(VideoCap-m.input->length<16384||AudioCap-m.pcm_used<(m.video_left?4352u:8192u))break;
        if(!record())return false;
    }
    return true;
}
void path_for(unsigned id,char* out,unsigned size){
    // Bit 24 (RE4DC_MOVIE_CANCEL_CLIP): the PS2 clip of the event's cancel cut, rRRRsEEc (r104s00c).
    snprintf(out,size,"/cd/dc/movie/r%03xs%02x%s.seq",(id>>8)&0xfff,id&0xff,(id&0x1000000)?"c":"");
}
bool header(file_t f,unsigned* video,unsigned* audio_bytes,unsigned* frames,unsigned* width=nullptr,unsigned* height=nullptr,bool* full=nullptr){
    unsigned char h[32];
    if(!re4dc::storage::read_exact(f,h,32))return false;
    const unsigned w=little(h+8),hh=little(h+12);
    // Macroblock sizes only (the PVR row load needs 32-byte rows); the 512x256
    // texture and the staging budget bound the rest.
    if(std::memcmp(h,"R4FMV003",8)||!w||!hh||(w&15)||(hh&15)||w>MaxWidth||hh>MaxHeight||little(h+28)>1)return false;
    if(width)*width=w;
    if(full)*full=little(h+28)&1;  // pre-expanded to full range by the converter
    if(height)*height=hh;
    *video=little(h+16);*audio_bytes=little(h+20);*frames=little(h+24);
    return *video>=4096 && *video<=16000000 && *audio_bytes>=16384 && *audio_bytes<=24000000 &&
           !(*audio_bytes&3) && *frames && *frames<=6000;
}
void memory(const char* phase){
    auto k=mallinfo();
    re4dc_log("route movie %s: id=%05x source_heap=%d staged=%u vram_free=%u aica_largest_any=%u kos_free=%u stream_init=%d stream_active=%u\n",
        phase,m.id,re4dc_ui_heap_free(),m.staged,(unsigned)pvr_mem_available(),(unsigned)snd_mem_available(),(unsigned)k.fordblks,
        re4dc_movie_stream_initialized(),re4dc_movie_stream_active());
}
int finish(int status){
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation)return cabin_movie_finish(status);
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    // snd_stream_destroy may yield while DMA owns the separator. Keep one
    // teardown owner across that yield and every subsequent cleanup step.
    if(movie_world_token && movie_finishing){re4dc_missing("movie arena recursive teardown");return RE4DC_MOVIE_ERROR;}
    MovieFinishScope finish_scope;
#endif
    if(m.terminal)status=m.terminal;else m.terminal=status;
#if RE4DC_ROUTE_MOVIE_DIAG
    re4dc_log("route movie diag: id=%05x status=%d why=%s iter=%u reads=%u read_us=%llu" "\n",m.id,status,m.why?m.why:"-",m.iter,m.reads,m.read_us);
#endif
    const unsigned presented=m.texture?re4dc_ui_movie_presented():0;
    if(m.stream>=0){snd_stream_stop(m.stream);snd_stream_destroy(m.stream);m.stream=-1;}
    // Retire only a service this movie initialised, after its own stream is gone.
    if(m.owns_service&&re4dc_movie_stream_active()==0){snd_stream_shutdown();m.owns_service=false;}
    if(m.file>=0){Re4dcIoScope owner;fs_close(m.file);m.file=-1;}
    // The texture is freed once the last scene that samples it has rendered.
#if RE4DC_MOVIE_WORLD_ARENA
    if(movie_world_token){
        if(movie_retiring){
            // Called before a heap transition. Never wait for another source
            // thread's open scene/GPU; a refusal halts before the heap mutates.
            if(m.texture && re4dc_ui_movie_try_close())m.texture=false;
        }else for(unsigned tries=0;m.texture && tries<=100;++tries){
            if(re4dc_ui_movie_close()){m.texture=false;break;}
            thd_sleep(1);
        }
        for(unsigned i=0;i<m.nallocs;++i)movie_stage_free(m.allocs[i]);
        m.nallocs=0;
        if(m.texture){
            // Keep token and texture ownership live. Never republish the world
            // or claim texture retirement from a void/failed fence result.
            re4dc_missing("movie arena texture retirement fence failed");return RE4DC_MOVIE_ERROR;
        }
        if(re4dc_movie_stream_initialized() || re4dc_movie_stream_active()){
            re4dc_missing("movie arena stream still owns staging");return RE4DC_MOVIE_ERROR;
        }
        const int result=re4dc_ps2_mesh_movie_return(movie_world_token,movie_retiring);
        if(result<0){re4dc_missing("movie arena world restore failed after bounded reread");return RE4DC_MOVIE_ERROR;}
        movie_world_token=0;++movie_epoch;
    }else
#endif
    {
        for(unsigned tries=0;m.texture&&!re4dc_ui_movie_close()&&tries<100;++tries)thd_sleep(1);
        m.texture=false;
        for(unsigned i=0;i<m.nallocs;++i)re4dc_ui_stage_free(m.allocs[i]);
    }
#if RE4DC_MOVIE_STAGE_ORDER
    release_reserved(0);   // pieces nobody took (a failed open)
#endif
#if RE4DC_MOVIE_BALLAST_TEST
    if(m.ballast){re4dc_ui_stage_free(m.ballast);m.ballast=nullptr;}
#endif
#if RE4DC_MOVIE_HEAP_EVICT
#if defined(RE4DC_GANADO_VAR) && RE4DC_GANADO_VAR
    re4dc_ganado_var_return();   // the variant cell is read again at the next plan that selects a variant
#endif
    // After the staging is freed: ui_bridge ends the loan and allocates the cache again (the next draw attaches it).
    {unsigned bytes=0,requests=0;
     if(re4dc_model_return_retained && re4dc_model_return_retained(&bytes,&requests)){
         if(bytes)re4dc_log("route movie heap: model preparation cache back (%u B), %u model draws asked during the loan\n",
                            bytes,requests);
         else re4dc_log("route movie heap: model preparation cache back FAILED (0 B), %u model draws asked during the loan; "
                        "the next model draw retries\n",requests);
     }}
#endif
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
    // Queue only. Route restoration runs after weapon/world loans and source
    // end callbacks, before the next normal source gameplay frame.
#if RE4DC_MOVIE_WORLD_ARENA
    re4dc_motion_movie_finish(movie_retiring?1:0);
#else
    re4dc_motion_movie_finish(0);
#endif
#endif
    const unsigned long long wall=timer_us_gettime64()-(m.start?m.start:m.entered);
    const unsigned d=m.frames?m.frames:1;
    re4dc_log("route movie terminal=%d id=%05x frames=%u/%u uploaded=%u presented=%u wall_us=%llu media_us=%llu underruns=%u silence_bytes=%u heap_before=%d heap_active=%d staged=%u\n",
        status,m.id,m.frames,m.expected_frames,m.uploaded,presented,wall,m.duration_us,m.underruns,m.silence_bytes,m.heap_before,m.heap_active,m.staged);
    re4dc_log("route movie cost id=%05x decode_avg_us=%llu decode_max_us=%llu convert_avg_us=%llu convert_max_us=%llu upload_avg_us=%llu upload_max_us=%llu present_avg_us=%llu present_max_us=%llu read_max_us=%llu idle_us=%llu\n",
        m.id,m.sum_decode/d,m.max_decode,m.sum_convert/(m.uploaded?m.uploaded:1),m.max_convert,
        m.sum_upload/(m.uploaded?m.uploaded:1),m.max_upload,m.sum_present/(m.shown?m.shown:1),m.max_present,m.max_read,m.sum_idle);
    re4dc_log("route movie cadence id=%05x shown=%u dropped=%u late=%u two_field=%u other=%u max_gap_fields=%u (29.97 fps = one picture per 2 fields)\n",
        m.id,m.shown,m.dropped,m.late,m.cadence2,m.cadence_other,m.max_gap);
    memory("retired");
    movie_state(4,status);
    m=Movie{};
#if RE4DC_MOVIE_DISC_QUIET
    re4dc_movie_disc_owner=0;
#endif
    return status;
}
bool open(unsigned id){
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
#if RE4DC_CABIN_SOURCE
    if(!cabin_movie.generation)
#endif
    re4dc_motion_movie_begin();
#endif
#if RE4DC_PS2_INTERIOR_CULL
    // PS2_INTERIOR_CULL: no world is drawn during a route movie, so it borrows the r100 cell block (read again by
    // route_movie_bridge.cpp after the movie); taken before heap_before so the movie sees the knob-off heap.
    re4dc_ps2_interior_movie_release();
#endif
#if RE4DC_FAR_SHELL
    // FAR_SHELL: the far shell (View distance Short) is lent the same way, read again at the first world draw after
    // the movie (route_movie_bridge.cpp re4dc_far_shell_movie_restore); before heap_before.
    re4dc_far_shell_movie_release();
#endif
#if defined(RE4DC_GANADO_VAR_MOVIE_LEND) && RE4DC_GANADO_VAR_MOVIE_LEND
    // ACTOR_GANADO_PS2_GRIP (compose-test24 10-24): armed Ganados keep the variant cell (22.6 KB grip hands) resident
    // in r100, where the knob-off game read it only for a lost head; every route movie borrows it before heap_before
    // (re4dc_ganado_var_return at retire; read again at the next variant plan).
    if(const unsigned v=re4dc_ganado_var_lend())re4dc_log("GANADOVAR lent to a movie (%u B)\n",v);
#endif
#if RE4DC_MOVIE_BALLAST_TEST
    if(id==0x10030){m.ballast=re4dc_ui_stage_alloc(RE4DC_MOVIE_BALLAST_TEST);
        re4dc_log("route movie heap: test ballast %u B %s\n",(unsigned)RE4DC_MOVIE_BALLAST_TEST,m.ballast?"held":"FAILED");}
#endif
    m.id=id;m.entered=timer_us_gettime64();m.heap_before=re4dc_ui_heap_free();m.vram_before=pvr_mem_available();
#if RE4DC_MOVIE_DISC_QUIET
    re4dc_movie_disc_owner=1;  // audio_aica.cpp: no disc stream prefill while the movie reads
#endif
    path_for(id,m.path,sizeof(m.path));
    movie_state(0,(int)(id&0xffff));
    {Re4dcIoScope owner;m.file=fs_open(m.path,O_RDONLY);}
    if(m.file<0)return false;
    {Re4dcIoScope owner;if(!header(m.file,&m.video_left,&m.audio_left,&m.expected_frames,&m.width,&m.height,&m.full))return false;}
    m.audio_bytes=m.audio_left;
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation && (m.expected_frames!=(id==0x11c00?2296u:id==0x11c10?761u:526u) ||
       m.width!=288 || m.height!=192 || !m.full))return false;
#endif
    auto size=fs_total(m.file);if(size<2048||size>40000000)return false;
#if RE4DC_GC_ASSET_GATE
    // One extra immutable container read in diagnostic builds. Hash after the
    // original size/header checks, outside audio/G2 and native file-call locks.
    m.asset={};
    if(re4dc_gcasset::ensure_disc_catalog()){
        re4dc_gcasset::Digest digest{};bool captured=false;
        {
            Re4dcIoScope owner;const file_t file=fs_open(m.path,O_RDONLY);
            // gc-catalog24b: the same whole-container SHA256 through the shared 16 KiB
            // storage reads (room_storage read_chunks), not 512-byte reads: ~32x fewer
            // disc requests before playback (h2 r100s30 hit the 30 s frame watchdog).
            re4dc_gcasset::DigestStream stream;re4dc_gcasset::digest_begin(stream);
            captured=file>=0 && fs_total(file)==size &&
                re4dc::storage::read_chunks(file,std::size_t(size),[](const std::uint8_t* p,std::size_t n,void* ctx){
                    re4dc_gcasset::digest_update(*static_cast<re4dc_gcasset::DigestStream*>(ctx),p,unsigned(n));return true;
                },&stream);
            if(captured)digest=re4dc_gcasset::digest_finish(stream);
            if(file>=0)fs_close(file);
        }
        if(captured){char id[16];snprintf(id,sizeof id,"%05x",m.id);m.asset=re4dc_gcasset::bind_checked("movie",id,digest);}
        else re4dc_gcasset::unresolved(re4dc_gcasset::Movie,"movie-container-read");
    }
#endif
    m.transport_left=size-2048;
    {Re4dcIoScope owner;if(fs_seek(m.file,2048,SEEK_SET)!=2048)return false;}
    const unsigned long long video_us=(unsigned long long)m.expected_frames*1001000ULL/30,audio_us=(unsigned long long)m.audio_bytes*1000000ULL/128000;
    m.duration_us=video_us>audio_us?video_us:audio_us;
#if RE4DC_MOVIE_WORLD_ARENA
    if(movie_full_call && movie_scope==id && movie_world_id(id)){
        if(movie_world_token || m.width!=288 || m.height!=192 || !m.full || !RE4DC_ROUTE_MOVIE_YUV ||
           !re4dc_movie_stream_idle() || m.expected_frames!=(id==0x11f10?265u:id==0x11f11?321u:340u))return false;
        movie_world_token=re4dc_ps2_mesh_movie_borrow(id);
        if(!movie_world_token)return false; // eligible arena attempt has NO heap fallback
    }
#endif
#if RE4DC_MOVIE_STAGE_ORDER
#if RE4DC_MOVIE_WORLD_ARENA
    if(!movie_world_token)
#endif
    if(!reserve_largest_first(RE4DC_ROUTE_MOVIE_YUV&&m.full,!re4dc_movie_stream_initialized()))return false;
#endif
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation){
        // The pinned codec dereferences its control allocations immediately.
        // Admit both through the same source allocator before its constructors.
        const unsigned sizes[2]={sizeof(plm_buffer_t),sizeof(plm_video_t)};
        for(unsigned i=0;i<2;++i){
            if(m.nallocs==MaxAllocs)return false;
            void* control=stage_alloc(sizes[i]);if(!control)return false;
            cabin_movie.codec_control[i]=control;
            m.allocs[m.nallocs++]=control;m.staged+=sizes[i];
        }
    }
#endif
    unsigned char* rb=(unsigned char*)plm_alloc(ReadCap+32);
    m.readbuf=rb?(unsigned char*)(((uintptr_t)rb+31)&~(uintptr_t)31):nullptr;
    m.pcm=(unsigned char*)plm_alloc(AudioCap);m.callback=(unsigned char*)plm_alloc(CallbackCap);
    const bool want_hw=RE4DC_ROUTE_MOVIE_YUV&&m.full;
    if(!want_hw)m.rows=(unsigned char*)plm_alloc(Rows*m.width*2);
    if(!m.readbuf||!m.pcm||!m.callback||(!want_hw&&!m.rows))return false;
    m.input=plm_buffer_create_with_capacity(VideoCap);if(!m.input||!m.input->bytes||!record())return false;
    auto* seq=m.input->bytes;
    if(m.input->length<8||std::memcmp(seq,"\0\0\1\xb3",4)||unsigned((seq[4]<<4)|(seq[5]>>4))!=m.width||unsigned(((seq[5]&15)<<8)|seq[6])!=m.height||(seq[7]&15)!=4)return false;
    m.decoder=plm_video_create_with_buffer(m.input,1);
    if(!m.decoder||plm_video_get_width(m.decoder)!=(int)m.width||plm_video_get_height(m.decoder)!=(int)m.height)return false;
    plm_video_set_no_delay(m.decoder,1); // I/P-only: the newest picture is the output
    if(!re4dc_ui_movie_open(m.width,m.height))return false;
    m.texture=true;
    m.tex=re4dc_ui_movie_texture();
#if RE4DC_GC_ASSET_GATE
    m.asset_owner=re4dc_gcasset_movie_bind(m.tex,m.width,m.height,m.asset.value);
#endif
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation)cabin_movie.ui_generation=re4dc_ui_movie_cabin_generation();
#endif
    m.hw=want_hw&&m.tex;
    if(want_hw&&!m.hw)return false;
    m.owns_service=!re4dc_movie_stream_initialized();
#if RE4DC_MOVIE_HEAP_EVICT
    // The service's separation buffer (Ring + 32 B, native_movie_stream.c) is staged without eviction: make
    // room for a piece that size first and hand it back, so the service's first-fit allocation finds one.
#if RE4DC_MOVIE_WORLD_ARENA
    if(!movie_world_token){
#endif
#if RE4DC_MOVIE_STAGE_ORDER
    release_reserved(m.owns_service?Ring+32:~0u);
#else
    if(m.owns_service)if(void* room=stage_alloc(Ring+32))re4dc_ui_stage_free(room);
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    }
#endif
#endif
#if defined(RE4DC_LEON_HAND_PACK) && RE4DC_LEON_HAND_PACK
    re4dc_leon_hands_yield();  // the stream takes the whole AICA movie reserve: Leon's hand cache refills after the movie
#endif
    if(snd_stream_init_ex(2,Ring)<0)return false;
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation)m.stream=re4dc_movie_stream_cabin_alloc(audio,Ring);
    else
#endif
    m.stream=snd_stream_alloc(audio,Ring);
    if(m.stream<0)return false;
    m.staged+=re4dc_movie_stream_staged;
    m.heap_active=re4dc_ui_heap_free();
    memory("active");
    re4dc_log("route movie start: id=%05x path=%s size=%ux%u frames=%u media_us=%llu staged=%u heap=%d->%d range=%s path=%s\n",
        id,m.path,m.width,m.height,m.expected_frames,m.duration_us,m.staged,m.heap_before,m.heap_active,
        m.full?"full":"studio",m.hw?"pvr-yuv-converter":"software-uyvy");
    return true;
}
// PVR samples packed UYVY: expand studio range with two small tables, 8 rows
// at a time into a small staging strip uploaded by the existing frame owner.
void convert_upload(plm_frame_t* f){
    static unsigned char yfull[256],cfull[256];static int initialized=-1;
    if(initialized!=(int)m.full){for(int i=0;i<256;++i){int y=m.full?i:(i-16)*255/219,c=m.full?i:(i-128)*255/224+128;
        yfull[i]=y<0?0:y>255?255:y;cfull[i]=c<0?0:c>255?255:c;}initialized=(int)m.full;}
    auto t=timer_us_gettime64();
    unsigned long long convert_us=0;
    const unsigned pairs=m.width/2;
    for(unsigned y0=0;y0<m.height;y0+=Rows){
        auto c0=timer_us_gettime64();
        auto* out=(unsigned*)m.rows;
        for(unsigned r=0;r<Rows;++r){
            const unsigned y=y0+r;
            const auto* yy=f->y.data+y*f->y.width;
            const auto* u=f->cb.data+(y/2)*f->cb.width;
            const auto* v=f->cr.data+(y/2)*f->cr.width;
            for(unsigned x=0;x<pairs;++x)out[r*pairs+x]=cfull[u[x]]|yfull[yy[x*2]]<<8|cfull[v[x]]<<16|yfull[yy[x*2+1]]<<24;
        }
        convert_us+=timer_us_gettime64()-c0;
        re4dc_ui_movie_upload_rows(m.rows,y0,Rows);
    }
    re4dc_ui_movie_upload_end();
    const auto total=timer_us_gettime64()-t, upload=total>convert_us?total-convert_us:0;
    m.sum_convert+=convert_us;if(convert_us>m.max_convert)m.max_convert=convert_us;
    m.sum_upload+=upload;if(upload>m.max_upload)m.max_upload=upload;
    ++m.uploaded;
}
}
namespace {
// Full-range movie through the TA YUV converter: the decoded YUV420 planes go
// out as 16x16 macroblocks (U 8x8, V 8x8, Y 4x 8x8), 4 rows of 8 bytes per
// 32-byte store-queue burst, and the PVR writes the 512-wide YUV422 texture
// itself. The texture row is 32 macroblocks wide, so each macroblock row ends
// with zero dummies (never sampled: the quad's UVs stop at width/512).
// Per picture: word copies only (no per-pixel CPU work, no separate upload).
void sq_rows4(uint32_t* o,const unsigned char* s,unsigned stride){
    for(unsigned r=0;r<4;++r){const auto* w=(const uint32_t*)(s+r*stride);o[r*2]=w[0];o[r*2+1]=w[1];}
    sq_flush(o);
}
bool yuv_upload(plm_frame_t* f){
    if(((uintptr_t)f->y.data|(uintptr_t)f->cb.data|(uintptr_t)f->cr.data|f->y.width|f->cb.width)&3){
        re4dc_log("route movie yuv converter: planes not word aligned\n");return false;}
    auto t=timer_us_gettime64();
    const unsigned mbw=m.width>>4,mbh=m.height>>4,tw=512>>4,total=tw*mbh;
    const unsigned yw=f->y.width,cw=f->cb.width;
    PVR_SET(PVR_YUV_ADDR,((uintptr_t)m.tex)&0xffffff);
    PVR_SET(PVR_YUV_CFG,((mbh-1)<<8)|(tw-1));  // bit 24 clear: YUV420 macroblocks
    (void)PVR_GET(PVR_YUV_CFG);
    uint32_t* d=sq_lock((void*)PVR_TA_YUV_CONV);
    unsigned q=0;
    for(unsigned my=0;my<mbh;++my){
        const unsigned char* yr=f->y.data+my*16*yw;
        const unsigned char* ur=f->cb.data+my*8*cw;
        const unsigned char* vr=f->cr.data+my*8*cw;
        for(unsigned mx=0;mx<mbw;++mx){
            const unsigned char* u=ur+mx*8;const unsigned char* v=vr+mx*8;const unsigned char* y=yr+mx*16;
            sq_rows4(d+(q<<3),u,cw);q^=1;sq_rows4(d+(q<<3),u+4*cw,cw);q^=1;
            sq_rows4(d+(q<<3),v,cw);q^=1;sq_rows4(d+(q<<3),v+4*cw,cw);q^=1;
            for(unsigned b=0;b<4;++b){const unsigned char* yb=y+(b>>1)*8*yw+(b&1)*8;
                sq_rows4(d+(q<<3),yb,yw);q^=1;sq_rows4(d+(q<<3),yb+4*yw,yw);q^=1;}
        }
        for(unsigned k=0;k<(tw-mbw)*12;++k){uint32_t* o=d+(q<<3);q^=1;
            o[0]=o[1]=o[2]=o[3]=o[4]=o[5]=o[6]=o[7]=0;sq_flush(o);}
    }
    sq_unlock();
    auto c=timer_us_gettime64();
    // The quad must not be submitted before the converter has written the texture.
    unsigned done=0;
    while((done=PVR_GET(PVR_YUV_STAT))<total&&timer_us_gettime64()-c<8000){}
    if(done<total&&m.yuv_timeouts++<4)re4dc_log("route movie yuv converter: %u/%u macroblocks after 8 ms\n",done,total);
    re4dc_ui_movie_upload_end();
    const auto e=timer_us_gettime64(),convert=c-t,wait=e-c;
    m.sum_convert+=convert;if(convert>m.max_convert)m.max_convert=convert;
    m.sum_upload+=wait;if(wait>m.max_upload)m.max_upload=wait;
    ++m.uploaded;
    return true;
}
#if RE4DC_ROUTE_MOVIE_TEXHASH
// FNV-1a over the width*2 active bytes of each texture row (UYVY), read back
// from VRAM with 32-bit loads; compared on the host with the expected texture.
void texhash(unsigned k){
    if(k!=0&&k!=1&&k!=30&&k!=300)return;
    const auto* t=(const volatile uint32_t*)m.tex;unsigned h=2166136261u;
    for(unsigned y=0;y<m.height;++y)for(unsigned x=0;x<m.width/2;++x){uint32_t w=t[y*256+x];
        for(unsigned b=0;b<4;++b){h^=(w>>(b*8))&255;h*=16777619u;}}
    re4dc_log("route movie texhash id=%05x picture=%u path=%s fnv=%08x\n",m.id,k,m.hw?"pvr-yuv-converter":"software-uyvy",h);
}
#endif
}
extern "C" int re4dc_movie_available(unsigned id){
    char path[40];path_for(id,path,sizeof(path));
    Re4dcIoScope owner;file_t f=fs_open(path,O_RDONLY);if(f<0)return 0;
    unsigned v,a,n;bool ok=header(f,&v,&a,&n);fs_close(f);return ok;
}
namespace {
plm_frame_t* decode_next(){
    if(!m.video_left)plm_buffer_signal_end(m.input);
    auto t=timer_us_gettime64();plm_frame_t* f=plm_video_decode(m.decoder);
    auto dt=timer_us_gettime64()-t;
    if(f){m.sum_decode+=dt;if(dt>m.max_decode)m.max_decode=dt;++m.frames;
#if RE4DC_CABIN_SOURCE
        if(cabin_movie.generation && m.frames==m.expected_frames)cabin_movie.final_frame=f;
#endif
    }
    return f;
}
// Upload picture `index` and submit it one field before its flip vblank.
bool show(plm_frame_t* f,unsigned index,unsigned now,RouteMoviePictureTick tick,bool present){
    if(!re4dc_ui_movie_upload_begin())return false;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset_movie_begin_upload(m.asset_owner,m.tex);
#endif
    if(!m.hw)convert_upload(f);else if(!yuv_upload(f))return false;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset_movie_uploaded(m.asset_owner,m.tex,m.width,m.height,m.asset.value);
#endif
#if RE4DC_ROUTE_MOVIE_TEXHASH
    if(m.tex)texhash(index);
#endif
    if(present){  // stepped pictures are drawn by the caller's frame (re4dc_ui_movie_background)
        auto t=timer_us_gettime64();
        if(!re4dc_ui_movie_present_now())return false;
        auto dt=timer_us_gettime64()-t;m.sum_present+=dt;if(dt>m.max_present)m.max_present=dt;
    }
    if(m.shown){const unsigned gap=now-m.last_submit;if(gap==2)++m.cadence2;else ++m.cadence_other;if(gap>m.max_gap)m.max_gap=gap;}
    m.last_submit=now;++m.shown;
    // A presented picture is a presented frame for the source hang detector: without this, a
    // movie over 60 s (r120 s00, 66.5 s) halts at main.cpp(548), whose store to 0x11111111
    // then lands in the TA FIFO area and wedges the YUV converter. Timing only: vsync_cnt
    // paces the frame loop and the interrupt task resume, never game state.
    vsync_cnt=0;
    if(m.shown==1){movie_state(1,(int)(m.id&0xffff));
        re4dc_log("route movie first picture: id=%05x latency_us=%llu\n",m.id,timer_us_gettime64()-m.entered);}
#if RE4DC_MOVIE_WORLD_ARENA
    const unsigned epoch=movie_epoch;
#endif
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation && index+1==m.expected_frames)
        cabin_movie.final_upload=re4dc_ui_movie_cabin_upload();
#endif
    if(tick)tick(index);
#if RE4DC_MOVIE_WORLD_ARENA
    if(epoch!=movie_epoch || !movie_world_current())return false;
#endif
    return true;
}
}
extern "C" unsigned re4dc_movie_picture(){return m.shown?m.shown-1:0;}
// Movie-owned presentation: the caller's game frame is not run while the
// picture plays (the world is hidden; the caller is a source task that simply
// does not sleep). Picture k flips at vblank v0 + 2k: 29.97 fps on NTSC,
// every picture held exactly two fields. Decode of k+1 overlaps the display
// of k; a picture two fields late is dropped (never shown late) so audio and
// picture stay on one clock.
namespace {
// Opens the movie and primes audio + picture 0; the picture clock starts here.
int start(unsigned id,unsigned mask){
    if(!open(id)){
        const bool missing=m.file<0;
        int st=finish(RE4DC_MOVIE_ERROR);
        if(missing){re4dc_log("route movie id=%05x: no media, source presentation applies\n",id);return RE4DC_MOVIE_UNHANDLED;}
        return st;
    }
    m.mask=mask;m.held=re4dc_pad_movie_buttons();
    m.armed=!(m.held&mask);
    // Prime: PCM for the AICA ring and picture 0, before the clock starts.
    while(m.pcm_used<AudioStart&&m.audio_left)if(!feed()||m.failed)return finish(RE4DC_MOVIE_ERROR);
    m.pending=decode_next();
    if(!m.pending||!feed())return finish(RE4DC_MOVIE_ERROR);
    m.start=timer_us_gettime64();
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset_movie_stream_arm(m.stream,m.asset_owner,m.asset.value);
#endif
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation){
        if(!re4dc_movie_stream_cabin_start(m.stream,cabin_movie.generation))return finish(RE4DC_MOVIE_ERROR);
    }else
#endif
    snd_stream_start(m.stream,32000,1);
    m.started=true;
    m.v0=re4dc_vi_retrace_count()+1;
    m.k=0;
    return RE4DC_MOVIE_RUNNING;
}
// One pass of the player: skip key, feed, audio poll, the due picture, the next decode.
// Movie-owned (stepped=false): presents the picture as its own scene and waits (bounded) for
// the next field. Stepped (re4dc_movie_step, the caller's game frames run): uploads only, the
// frame draws the picture behind its UI (re4dc_ui_movie_background); no skip key (the source
// event's cancel cut is not cancellable); the end holds the last picture until re4dc_movie_end.
int iterate(RouteMoviePictureTick tick,bool stepped){
    if(!stepped){
        const unsigned b=re4dc_pad_movie_buttons(),pressed=b&~m.held;m.held=b;
        if(!(b&m.mask))m.armed=true;
        if(m.armed&&(pressed&m.mask)){
            re4dc_pad_consume_movie_skip(pressed&m.mask);
            re4dc_log("route movie skip: id=%05x mask=%x picture=%u elapsed_us=%llu\n",m.id,pressed&m.mask,m.k,timer_us_gettime64()-m.entered);
            return finish(RE4DC_MOVIE_SKIP);
        }
    }
#if RE4DC_ROUTE_MOVIE_DIAG
    const unsigned long long d0=timer_us_gettime64();const unsigned r0=m.reads;const unsigned long long ru0=m.read_us;
#endif
    if(!feed()){MOVIE_WHY(m.why?m.why:"feed");return finish(RE4DC_MOVIE_ERROR);}
#if RE4DC_CABIN_SOURCE
    int cabin_audio=2;
    if(cabin_movie.generation){
        cabin_audio=re4dc_movie_stream_cabin_progress(m.stream,cabin_movie.generation,!m.audio_left&&!m.pcm_used);
        if(cabin_audio<0)return finish(RE4DC_MOVIE_ERROR);
    }
    if(cabin_audio)
#endif
    if(poll_audio()<0){MOVIE_WHY("poll_audio");return finish(RE4DC_MOVIE_ERROR);}
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation && cabin_audio){
        cabin_audio=re4dc_movie_stream_cabin_progress(m.stream,cabin_movie.generation,!m.audio_left&&!m.pcm_used);
        if(cabin_audio<0)return finish(RE4DC_MOVIE_ERROR);
    }
#endif
    if(m.failed){MOVIE_WHY("audio_failed");return finish(RE4DC_MOVIE_ERROR);}
    const unsigned now=re4dc_vi_retrace_count(),due=m.v0+2*m.k;
#if RE4DC_ROUTE_MOVIE_DIAG
    {const unsigned long long fu=timer_us_gettime64()-d0;++m.iter;
     if(m.iter<=24||fu>50000)re4dc_log("route movie diag: iter=%u k=%u now=%u due=%u frames=%u pending=%d feed_us=%llu reads=%u read_us=%llu pcm=%u" "\n",
         m.iter,m.k,now,due,m.frames,m.pending?1:0,fu,m.reads-r0,m.read_us-ru0,m.pcm_used);}
#endif
    if(m.pending&&now+1>=due){
        if(now>=due+2&&m.frames<m.expected_frames){++m.dropped;m.pending=nullptr;++m.k;}
        else{
            if(now>due)++m.late;
            if(!show(m.pending,m.k,now,tick,!stepped)){MOVIE_WHY("show");return finish(RE4DC_MOVIE_ERROR);}
            m.pending=nullptr;++m.k;
        }
    }
    if(!m.pending&&m.frames<m.expected_frames&&!m.starve_since){
#if RE4DC_ROUTE_MOVIE_DIAG
        const unsigned long long c0=timer_us_gettime64();
#endif
        m.pending=decode_next();
#if RE4DC_ROUTE_MOVIE_DIAG
        if(m.iter<=24||timer_us_gettime64()-c0>50000)re4dc_log("route movie diag: decode k=%u us=%llu ok=%d" "\n",m.k,timer_us_gettime64()-c0,m.pending?1:0);
#endif
        if(m.pending){m.starve_since=0;return RE4DC_MOVIE_RUNNING;}
        // The input ran dry. A slow read (a GD seek after the game's own reads, ~190 ms)
        // starts the picture clock late; the loop catches up by dropping pictures, which
        // uses video faster than the audio-paced feed refills it (one record per picture).
        // plm_video_decode returns NULL until the next picture is complete: wait for the
        // next record. Ended input or 2 s without a picture is still an error.
        if(!m.video_left){MOVIE_WHY("decode");return finish(RE4DC_MOVIE_ERROR);}
        const unsigned long long t=timer_us_gettime64();
        if(!m.starve_since){m.starve_since=t;++m.starved;}
        else if(t-m.starve_since>2000000ULL){MOVIE_WHY("starved");return finish(RE4DC_MOVIE_ERROR);}
        return RE4DC_MOVIE_RUNNING;
    }
#if RE4DC_CABIN_SOURCE
    const bool audio_complete=cabin_movie.generation?cabin_audio==1:m.samples>=m.last_real_sample+4096;
    if(!m.pending&&!m.audio_left&&!m.pcm_used&&audio_complete&&now>=m.v0+2*m.k)
#else
    if(!m.pending&&!m.audio_left&&!m.pcm_used&&m.samples>=m.last_real_sample+4096&&now>=m.v0+2*m.k)
#endif
    {
#if RE4DC_CABIN_SOURCE
        if(cabin_movie.generation){
            if(!cabin_movie_content())return cabin_movie_finish(RE4DC_MOVIE_ERROR);
            if(!cabin_movie.final_upload)cabin_movie.final_upload=re4dc_ui_movie_cabin_upload();
            if(!cabin_movie.final_upload || !cabin_movie_identity() ||
               re4dc_ui_movie_cabin_upload()!=cabin_movie.final_upload)
                return cabin_movie_finish(RE4DC_MOVIE_ERROR);
            if(re4dc_ui_movie_cabin_shown()!=cabin_movie.final_upload){
                const auto now_us=timer_us_gettime64();
                if(!cabin_movie.final_wait)cabin_movie.final_wait=now_us;
                if(now_us-cabin_movie.final_wait>10000000ULL)return finish(RE4DC_MOVIE_ERROR);
                return RE4DC_MOVIE_RUNNING;
            }
        }
#endif
        if(stepped){m.held_end=true;return RE4DC_MOVIE_EOF;}  // last picture held until re4dc_movie_end
        return finish(RE4DC_MOVIE_EOF);
    }
    if(timer_us_gettime64()-m.start>m.duration_us+10000000ULL){MOVIE_WHY("stalled");return finish(RE4DC_MOVIE_ERROR);} // stalled media
#if RE4DC_MOVIE_DISC_QUIET
    // A stepped movie that ran dry retries its decode at every pass (the movie-owned loop does it below). Without
    // this a starved stepped movie never decodes again: r10b s20 froze at picture 520 and its QTE ended it (terminal 4).
    if(stepped&&m.starve_since&&!m.pending&&m.frames<m.expected_frames){
        m.pending=decode_next();
        if(m.pending)m.starve_since=0;
        else if(timer_us_gettime64()-m.starve_since>2000000ULL){MOVIE_WHY("starved");return finish(RE4DC_MOVIE_ERROR);}
    }
#endif
    if(stepped)return RE4DC_MOVIE_RUNNING;
    auto t=timer_us_gettime64();
    while(re4dc_vi_retrace_count()==now&&timer_us_gettime64()-t<2000){} // ahead: wait (bounded) for the next field
    m.sum_idle+=timer_us_gettime64()-t;
    if(m.starve_since&&!m.pending&&m.frames<m.expected_frames){
        m.pending=decode_next();
        if(m.pending)m.starve_since=0;
        else if(timer_us_gettime64()-m.starve_since>2000000ULL){MOVIE_WHY("starved");return finish(RE4DC_MOVIE_ERROR);}
    }
    return RE4DC_MOVIE_RUNNING;
}
}
#if RE4DC_CABIN_SOURCE
namespace {
// CABIN_MOVIE_FUNCTIONS_BEGIN
bool cabin_movie_identity(){
    return cabin_movie.ui_generation && m.texture && m.tex==re4dc_ui_movie_texture() &&
           cabin_movie.ui_generation==re4dc_ui_movie_cabin_generation();
}
// Validate BEFORE asking the decoder to search for another picture: that search
// could otherwise consume arbitrary trailing compressed data and hide a defect.
bool cabin_movie_content(){
    if(cabin_movie.checked)return true;
    if(m.frames!=m.expected_frames || m.video_left || m.audio_left ||
       m.transport_left || m.read_at!=m.read_used ||
       cabin_movie.video_records!=m.expected_frames ||
       cabin_movie.audio_bytes!=m.audio_bytes || !m.input || !m.decoder)return false;
    if(m.input->bit_index>m.input->length*8u)return false;
    const size_t residual=m.input->length*8u-m.input->bit_index;
    if(residual>7u || (residual &&
       (m.input->bytes[m.input->length-1]&((1u<<residual)-1u))))return false;
    if(plm_video_decode(m.decoder)!=nullptr ||
       m.input->bit_index!=m.input->length*8u)return false;
    cabin_movie.checked=true;
    return true;
}
// Only CPU/audio transport is retired here. The matching texture generation is
// held independently until its last scene is fenced by the existing UI owner.
int cabin_movie_finish(int status){
    if(cabin_movie.finishing)return RE4DC_MOVIE_ERROR;
    cabin_movie.finishing=true;
    if(cabin_movie.terminal==RE4DC_MOVIE_RUNNING)cabin_movie.terminal=status;
    if(!cabin_movie.transport_retired){
        if(m.stream>=0){snd_stream_stop(m.stream);snd_stream_destroy(m.stream);m.stream=-1;}
        m.started=false;
        if(m.owns_service){
            if(re4dc_movie_stream_active()){
                cabin_movie.terminal=RE4DC_MOVIE_ERROR;
                cabin_movie.finishing=false;return RE4DC_MOVIE_ERROR;
            }
            snd_stream_shutdown();m.owns_service=false;
        }
        if(m.file>=0){Re4dcIoScope owner;fs_close(m.file);m.file=-1;}
        for(unsigned i=0;i<m.nallocs;++i)re4dc_ui_stage_free(m.allocs[i]);
        m.nallocs=0;m.input=nullptr;m.decoder=nullptr;m.pending=nullptr;
        m.pcm=m.callback=m.readbuf=m.rows=nullptr;m.pcm_used=0;cabin_movie.final_frame=nullptr;
        cabin_movie.codec_control[0]=cabin_movie.codec_control[1]=nullptr;
#if RE4DC_MOVIE_STAGE_ORDER
        release_reserved(0);
#endif
#if RE4DC_MOVIE_HEAP_EVICT
        {unsigned bytes=0,requests=0;
         if(re4dc_model_return_retained)re4dc_model_return_retained(&bytes,&requests);}
#endif
#if RE4DC_MOVIE_DISC_QUIET
        re4dc_movie_disc_owner=0;
#endif
        cabin_movie.transport_retired=true;
    }
    m.terminal=cabin_movie.terminal;
    cabin_movie.finishing=false;
    return cabin_movie.terminal;
}
int cabin_movie_fast_final(){
    // Called only after the source's accepted RunEvtCancel hook. No pad reads.
    if(m.started){snd_stream_stop(m.stream);m.started=false;}
    for(unsigned i=0;i<16 && !cabin_movie.checked;++i){
        if(++cabin_movie.fast_passes>12000)return cabin_movie_finish(RE4DC_MOVIE_ERROR);
        m.pcm_used=0;
        if(!feed())return cabin_movie_finish(RE4DC_MOVIE_ERROR);
        if(m.frames<m.expected_frames){
            auto* frame=decode_next();
            if(frame)m.pending=frame;
            else if(!m.video_left)return cabin_movie_finish(RE4DC_MOVIE_ERROR);
        }
        if(m.frames==m.expected_frames && !m.video_left && !m.audio_left){
            if(!cabin_movie.final_frame || !cabin_movie_content())return cabin_movie_finish(RE4DC_MOVIE_ERROR);
            if(!cabin_movie.final_upload && !show(cabin_movie.final_frame,m.expected_frames-1,re4dc_vi_retrace_count(),nullptr,false))
                return cabin_movie_finish(RE4DC_MOVIE_ERROR);
            m.pending=nullptr;m.k=m.expected_frames;
            cabin_movie.final_upload=re4dc_ui_movie_cabin_upload();
        }
    }
    if(cabin_movie.checked){
        const auto now_us=timer_us_gettime64();
        if(!cabin_movie.final_wait)cabin_movie.final_wait=now_us;
        if(now_us-cabin_movie.final_wait>10000000ULL)return cabin_movie_finish(RE4DC_MOVIE_ERROR);
    }
    if(cabin_movie.checked && cabin_movie.final_upload && cabin_movie_identity() &&
       re4dc_ui_movie_cabin_upload()==cabin_movie.final_upload &&
       re4dc_ui_movie_cabin_shown()==cabin_movie.final_upload)
        return cabin_movie_finish(RE4DC_MOVIE_SKIP);
    return RE4DC_MOVIE_RUNNING;
}
// CABIN_MOVIE_FUNCTIONS_END
}
// CABIN_MOVIE_API_BEGIN
bool cabin_movie_header(unsigned id,unsigned video,unsigned audio,unsigned frames,unsigned width,unsigned height,bool full,unsigned size){
    const unsigned wanted_frames=id==0x11c00?2296:id==0x11c10?761:id==0x11c20?526:0;
    const unsigned wanted_video=id==0x11c00?6271092:id==0x11c10?2120385:1446405;
    const unsigned wanted_audio=id==0x11c00?9809152:id==0x11c10?3456088:2244352;
    const unsigned wanted_size=id==0x11c00?16100668:id==0x11c10?5584817:3697013;
    return wanted_frames && frames==wanted_frames && video==wanted_video && audio==wanted_audio &&
           width==288 && height==192 && full && size==wanted_size;
}
extern "C" int re4dc_movie_cabin_available(unsigned id){
    char path[40];path_for(id,path,sizeof(path));Re4dcIoScope owner;
    file_t file=fs_open(path,O_RDONLY);if(file<0)return 0;
    unsigned v=0,a=0,n=0,w=0,h=0;bool full=false;
    bool ok=header(file,&v,&a,&n,&w,&h,&full) && cabin_movie_header(id,v,a,n,w,h,full,fs_total(file));
    fs_close(file);return ok;
}
extern "C" unsigned re4dc_movie_cabin_open(unsigned id){
    if((id!=0x11c00 && id!=0x11c10 && id!=0x11c20) || cabin_movie.generation ||
       m.entered || cabin_movie_epoch==~0u)return 0;
#if RE4DC_MOVIE_WORLD_ARENA
    if(movie_world_token || movie_full_call)return 0;
#endif
    cabin_movie=CabinMovie{};cabin_movie.generation=++cabin_movie_epoch;
    int result;
    {CabinMovieRead reader;
     if(!re4dc_movie_cabin_available(id))result=cabin_movie_finish(RE4DC_MOVIE_ERROR);
     else result=start(id,0);}
    if(result==RE4DC_MOVIE_RUNNING){
        cabin_movie.ui_generation=re4dc_ui_movie_cabin_generation();
        if(!cabin_movie_identity())cabin_movie_finish(RE4DC_MOVIE_ERROR);
        else re4dc_ui_movie_background(1);
    }
    return cabin_movie.generation;
}
extern "C" int re4dc_movie_cabin_skip(unsigned generation){
    if(!generation || generation!=cabin_movie.generation || cabin_movie.finishing ||
       cabin_movie.retiring || cabin_movie.terminal!=RE4DC_MOVIE_RUNNING)return 0;
    cabin_movie.skip=true;return 1;
}
extern "C" int re4dc_movie_cabin_step(unsigned generation){
    if(!generation || generation!=cabin_movie.generation || cabin_movie.finishing ||
       cabin_movie.retiring || cabin_movie.readers)return RE4DC_MOVIE_ERROR;
    if(m.texture && !cabin_movie_identity()){
        cabin_movie.terminal=RE4DC_MOVIE_ERROR;
        return cabin_movie_finish(RE4DC_MOVIE_ERROR);
    }
    if(cabin_movie.terminal!=RE4DC_MOVIE_RUNNING)return cabin_movie.terminal;
    CabinMovieRead reader;
    if(!cabin_movie_identity())return cabin_movie_finish(RE4DC_MOVIE_ERROR);
    if(cabin_movie.skip)return cabin_movie_fast_final();
    int status=RE4DC_MOVIE_RUNNING;
    for(unsigned i=0;i<4 && status==RE4DC_MOVIE_RUNNING;++i){
        const unsigned k=m.k;
        status=iterate(nullptr,true);
        if(status==RE4DC_MOVIE_RUNNING && m.k==k && m.pending)break;
    }
    if(status==RE4DC_MOVIE_EOF)return cabin_movie_finish(RE4DC_MOVIE_EOF);
    return status;
}
extern "C" int re4dc_movie_cabin_abort(unsigned generation){
    if(!generation || generation!=cabin_movie.generation || cabin_movie.readers ||
       cabin_movie.finishing || cabin_movie.retiring)return RE4DC_MOVIE_ERROR;
    cabin_movie.terminal=RE4DC_MOVIE_ERROR;
    return cabin_movie_finish(RE4DC_MOVIE_ERROR);
}
extern "C" int re4dc_movie_cabin_status(unsigned generation){
#if RE4DC_CABIN_HANDOFF_DIAG
    static unsigned queries=0;
    if(++queries<=3 || queries%120==0)
        re4dc_log("CABIN_MOVIE_STATUS n=%u gen=%u want=%u terminal=%d decoded=%u/%u k=%u video=%u audio=%u pcm=%u pending=%u retired=%u final_upload=%u shown=%u\n",
            queries,cabin_movie.generation,generation,cabin_movie.terminal,m.frames,m.expected_frames,m.k,
            m.video_left,m.audio_left,m.pcm_used,unsigned(m.pending!=nullptr),unsigned(cabin_movie.transport_retired),
            cabin_movie.final_upload,re4dc_ui_movie_cabin_shown());
#endif
    return generation && generation==cabin_movie.generation?cabin_movie.terminal:RE4DC_MOVIE_CANCEL;
}
extern "C" int re4dc_movie_cabin_close(unsigned generation){
    // Refuse stale/reentrant ownership before touching any pointer. try_close is
    // nonblocking and checks the UI generation in the same protected operation.
    if(!generation || generation!=cabin_movie.generation)return 0;
    if(cabin_movie.readers || cabin_movie.finishing || cabin_movie.retiring)return 0;
    cabin_movie.retiring=true;
    if(m.texture){
        if(!cabin_movie_identity() || !re4dc_ui_movie_cabin_try_close(cabin_movie.ui_generation)){
            cabin_movie.retiring=false;return 0;
        }
        m.texture=false;m.tex=nullptr;
    }
    const int result=cabin_movie_finish(RE4DC_MOVIE_CANCEL);
    if(!cabin_movie.transport_retired){cabin_movie.retiring=false;return 0;}
    re4dc_log("cabin movie retired: generation=%u id=%05x terminal=%d final_upload=%u\n",
               generation,m.id,result,cabin_movie.final_upload);
    m=Movie{};cabin_movie=CabinMovie{};
    return 1;
}
#if RE4DC_CABIN_COMPLETE_HANDOFF
static int cabin_movie_complete_qualified(unsigned generation){
    if(!generation || generation!=cabin_movie.generation || cabin_movie.readers ||
       cabin_movie.finishing || !cabin_movie.transport_retired ||
       (cabin_movie.terminal!=RE4DC_MOVIE_EOF && cabin_movie.terminal!=RE4DC_MOVIE_SKIP) ||
       !cabin_movie.checked || !cabin_movie.final_upload || !cabin_movie_identity() ||
       re4dc_ui_movie_cabin_upload()!=cabin_movie.final_upload ||
       re4dc_ui_movie_cabin_shown()!=cabin_movie.final_upload ||
       !re4dc_cabin_complete_current(generation,m.id))return 0;
    return 1;
}
extern "C" int re4dc_movie_cabin_complete_current(unsigned generation){
    return cabin_movie.retiring && cabin_movie_complete_qualified(generation);
}
extern "C" int re4dc_movie_cabin_complete(unsigned generation){
    // Normal source completion may fence the frame opened before TaskScheduler.
    // Heap-change/cancel retirement continues to use the nonblocking close API.
    if(cabin_movie.retiring || !cabin_movie_complete_qualified(generation))return 0;
    cabin_movie.retiring=true;
    if(!re4dc_ui_movie_cabin_complete(cabin_movie.ui_generation,m.tex,cabin_movie.final_upload,generation)){
        cabin_movie.retiring=false;return 0;
    }
    // Transport was already retired by qualified EOF/SKIP. No further decoder,
    // source heap or audio work may yield after the protected UI release.
    re4dc_log("cabin movie completed: generation=%u id=%05x terminal=%d final_upload=%u\n",
        generation,m.id,cabin_movie.terminal,cabin_movie.final_upload);
    m=Movie{};cabin_movie=CabinMovie{};return 1;
}
#endif
// CABIN_MOVIE_API_END
#endif
// Movie-owned presentation: the caller's game frame is not run while the
// picture plays (the world is hidden; the caller is a source task that simply
// does not sleep). Picture k flips at vblank v0 + 2k: 29.97 fps on NTSC,
// every picture held exactly two fields. Decode of k+1 overlaps the display
// of k; a picture two fields late is dropped (never shown late) so audio and
// picture stay on one clock.
extern "C" int re4dc_movie_play(unsigned id,unsigned mask,RouteMoviePictureTick tick){
#if RE4DC_MOVIE_WORLD_ARENA
    if(m.entered || movie_world_token || movie_full_call)return RE4DC_MOVIE_ERROR;
    movie_full_call=true;
    const int result=re4dc_movie_play_until(id,mask,tick,~0u);
    movie_full_call=false;return result;
#else
    return re4dc_movie_play_until(id,mask,tick,~0u);
#endif
}
// As re4dc_movie_play up to picture `stop_at` (not shown): RE4DC_MOVIE_RUNNING leaves the
// movie open, its sound playing, for re4dc_movie_step / re4dc_movie_end (route lane: r104s00's
// QTE cut runs as game frames over the rest of the movie, the PS2 pattern).
extern "C" int re4dc_movie_play_until(unsigned id,unsigned mask,RouteMoviePictureTick tick,unsigned stop_at){
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation)return RE4DC_MOVIE_ERROR;
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(m.entered || movie_world_token)return RE4DC_MOVIE_ERROR;
    int st;
    {MovieReader reader;st=start(id,mask);}
    const unsigned epoch=movie_epoch;
#else
    int st=start(id,mask);
#endif
    while(st==RE4DC_MOVIE_RUNNING){
#if RE4DC_MOVIE_WORLD_ARENA
        if(epoch!=movie_epoch)return RE4DC_MOVIE_CANCEL;
        if(!movie_world_current()){re4dc_missing("movie arena stale iteration");return RE4DC_MOVIE_ERROR;}
#endif
        if(m.k>=stop_at){
            re4dc_log("route movie handoff: id=%05x picture=%u (game frames continue it)\n",m.id,m.k);
            return RE4DC_MOVIE_RUNNING;
        }
#if RE4DC_MOVIE_WORLD_ARENA
        {MovieReader reader;st=iterate(tick,false);}
#else
        st=iterate(tick,false);
#endif
    }
    return st;
}
// Opens a movie for re4dc_movie_step only (no movie-owned pictures): r104s00c, the QTE cut
// the source plays after a skip.
extern "C" int re4dc_movie_play_stepped(unsigned id){
    return re4dc_movie_play_until(id,0,nullptr,0);
}
// Once per game frame of the caller: feeds the open movie and uploads its due picture.
// RUNNING while pictures remain, EOF once the last one is up (held), else the terminal.
extern "C" int re4dc_movie_step(RouteMoviePictureTick tick){
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation)return RE4DC_MOVIE_ERROR;
#endif
    if(!m.entered)return m.terminal?m.terminal:RE4DC_MOVIE_ERROR;
    if(m.held_end)return RE4DC_MOVIE_EOF;
    int st=RE4DC_MOVIE_RUNNING;
    // Up to four passes: the due picture (dropping late ones) and the next decode.
    for(unsigned i=0;i<4&&st==RE4DC_MOVIE_RUNNING;++i){
        const unsigned k=m.k;
        st=iterate(tick,true);
        if(st==RE4DC_MOVIE_RUNNING&&m.k==k&&m.pending)break;  // nothing due yet
    }
    return st;
}
// Retires an open (handed-off or stepped) movie.
extern "C" int re4dc_movie_end(void){
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation)return RE4DC_MOVIE_ERROR;
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(movie_world_token && movie_readers){re4dc_missing("movie arena end while reader active");return RE4DC_MOVIE_ERROR;}
#endif
    if(!m.entered)return m.terminal?m.terminal:RE4DC_MOVIE_ERROR;
    return finish(m.held_end?RE4DC_MOVIE_EOF:RE4DC_MOVIE_CANCEL);
}
extern "C" int re4dc_movie_cancel(){
#if RE4DC_CABIN_SOURCE
    if(cabin_movie.generation)return RE4DC_MOVIE_ERROR;
#endif
#if RE4DC_MOVIE_WORLD_ARENA
    if(movie_world_token && movie_readers){re4dc_missing("movie arena cancel while reader active");return RE4DC_MOVIE_ERROR;}
#endif
    return m.entered?finish(RE4DC_MOVIE_CANCEL):RE4DC_MOVIE_CANCEL;
}
#if RE4DC_MOVIE_WORLD_ARENA
extern "C" void re4dc_movie_world_scope(unsigned id){movie_scope=movie_world_id(id)?id:0;}
extern "C" int re4dc_movie_world_active(){return movie_world_token!=0;}
extern "C" void* re4dc_movie_world_sep_alloc(unsigned bytes){
    return movie_world_token?re4dc_ps2_mesh_movie_alloc(movie_world_token,bytes):nullptr;
}
extern "C" int re4dc_movie_world_sep_free(void* p){
    return movie_world_token && re4dc_ps2_mesh_movie_free(movie_world_token,p);
}
extern "C" int re4dc_movie_world_before_room_retire(){
    // A source cut callback/I/O-yield can request retirement with live pointers
    // still on the stack. Refuse BEFORE room owners or heap 4 are touched.
    if(movie_finishing || movie_retiring || (movie_readers && (movie_scope || movie_world_token)))return 0;
    if(!movie_world_token)return 1;
    if(!movie_world_current())return 0;
    movie_retiring=true;
    const int status=finish(RE4DC_MOVIE_CANCEL);
    movie_retiring=false;movie_scope=0;
    return status==RE4DC_MOVIE_CANCEL && !movie_world_token;
}
#endif
#if defined(RE4DC_LAKE_RIPPLES) && RE4DC_LAKE_RIPPLES
// LAKE_RIPPLES (native_lake.cpp): 1 while a movie is open (its decoder needs the CPU; the lake layers wait).
extern "C" int re4dc_movie_open_now(){return m.entered && !m.terminal;}
#endif
#else
extern "C" int re4dc_movie_available(unsigned){return 0;}
extern "C" unsigned re4dc_movie_picture(){return 0;}
extern "C" int re4dc_movie_play(unsigned,unsigned,RouteMoviePictureTick){return RE4DC_MOVIE_UNHANDLED;}
extern "C" int re4dc_movie_cancel(){return RE4DC_MOVIE_CANCEL;}
extern "C" int re4dc_movie_play_until(unsigned,unsigned,RouteMoviePictureTick,unsigned){return RE4DC_MOVIE_UNHANDLED;}
extern "C" int re4dc_movie_play_stepped(unsigned){return RE4DC_MOVIE_UNHANDLED;}
extern "C" int re4dc_movie_step(RouteMoviePictureTick){return RE4DC_MOVIE_ERROR;}
extern "C" int re4dc_movie_end(void){return RE4DC_MOVIE_ERROR;}
#endif
