#include "include/movie_world_arena.h"
#include "include/gc_asset_movie_stream.h"
#if RE4DC_MOVIE_WORLD_ARENA
void re4dc_missing(const char*);
#endif
// Private object from the unchanged pinned KOS source, never a shared SDK write.
// KOS BSD-like license/provenance remains in the included SDK source.
// -Os selects KOS's supported cache-purge implementation without16KiB scratch.
#if RE4DC_ROUTE_MOVIES
#include <stdlib.h>
#include <malloc.h>
#include <stdint.h>
// The stereo separation buffer (snd_stream_init_ex) is the service's only heap
// use. It is staged from the current source heap like the rest of the player,
// because the in-room KOS heap has under 4 KiB free; it is returned on
// snd_stream_shutdown. The filter path (malloc/free of filter_t) is unused.
void* re4dc_ui_stage_alloc(unsigned bytes);
void re4dc_ui_stage_free(void* data);
static void* movie_sep_raw;
static void* movie_sep;
unsigned re4dc_movie_stream_staged;
static void* re4dc_movie_sep_alloc(size_t alignment, size_t bytes) {
    if(movie_sep || alignment > 32) return NULL;
#if RE4DC_MOVIE_WORLD_ARENA
    if(re4dc_movie_world_active()){
        if(alignment!=32 || bytes!=32768)return NULL;
        movie_sep_raw=re4dc_movie_world_sep_alloc((unsigned)(bytes+32));
    }
    else
#endif
    movie_sep_raw = re4dc_ui_stage_alloc((unsigned)(bytes + 32));
    if(!movie_sep_raw) return NULL;
    re4dc_movie_stream_staged = (unsigned)(bytes + 32);
    movie_sep = (void*)(((uintptr_t)movie_sep_raw + 31) & ~(uintptr_t)31);
    return movie_sep;
}
static void re4dc_movie_sep_free(void* p) {
    if(p && p == movie_sep) {
#if RE4DC_MOVIE_WORLD_ARENA
        if(re4dc_movie_world_active()){
            if(!re4dc_movie_world_sep_free(movie_sep_raw)){re4dc_missing("movie arena invalid separation free");return;}
        }else
#endif
        re4dc_ui_stage_free(movie_sep_raw);
        movie_sep = movie_sep_raw = NULL;
        re4dc_movie_stream_staged = 0;
        return;
    }
#if RE4DC_MOVIE_WORLD_ARENA
    if(p && re4dc_movie_world_active()){re4dc_missing("movie arena unexpected stream free");return;}
#endif
    free(p);
}
#define aligned_alloc(a, n) re4dc_movie_sep_alloc((a), (n))
#define free(p) re4dc_movie_sep_free(p)
#if RE4DC_CABIN_SOURCE
#include <dc/spu.h>
#include <dc/sound/sound.h>
static int cabin_stream_dma(void*, uintptr_t, size_t, int, spu_dma_callback_t, void*);
static int cabin_stream_command(void*, uint32_t);
#define spu_dma_transfer cabin_stream_dma
#endif
#if RE4DC_GC_ASSET_GATE
#include <dc/sound/sound.h>
static int gcasset_movie_command(void*,uint32_t);
#define snd_sh4_to_aica gcasset_movie_command
#elif RE4DC_CABIN_SOURCE
#define snd_sh4_to_aica cabin_stream_command
#endif
#if RE4DC_CABIN_SOURCE || RE4DC_GC_ASSET_GATE
#define snd_stream_start cabin_sdk_stream_start
#define snd_stream_start_pcm8 cabin_sdk_stream_start_pcm8
#define snd_stream_start_adpcm cabin_sdk_stream_start_adpcm
#define snd_stream_stop cabin_sdk_stream_stop
#define snd_stream_destroy cabin_sdk_stream_destroy
#define snd_stream_shutdown cabin_sdk_stream_shutdown
#endif
#include "snd_stream.c"
#if RE4DC_CABIN_SOURCE || RE4DC_GC_ASSET_GATE
#undef spu_dma_transfer
#undef snd_sh4_to_aica
#undef snd_stream_start
#undef snd_stream_start_pcm8
#undef snd_stream_start_adpcm
#undef snd_stream_stop
#undef snd_stream_destroy
#undef snd_stream_shutdown
#endif

#undef free
#undef aligned_alloc
#if RE4DC_GC_ASSET_GATE
// GC_ASSET_MOVIE_STREAM_BEGIN
// These observers surround the unchanged SDK calls. No IO, hashing, logging,
// allocation, command modification or G2 ownership is introduced here.
typedef struct gcasset_movie_start {
    unsigned owner,asset,slot,serial,commands,accepted;
    int handle,active,failed,ch[2];uint32_t base[2],size;
    snd_stream_callback_t callback;
} gcasset_movie_start_t;
static gcasset_movie_start_t gcasset_movie_start;
static struct {int handle;unsigned owner,asset;} gcasset_movie_armed;
static void gcasset_movie_start_end(void);
void re4dc_gcasset_movie_stream_arm(int handle,unsigned owner,unsigned asset){
    gcasset_movie_armed.handle=handle;gcasset_movie_armed.owner=owner;gcasset_movie_armed.asset=asset;
}
void re4dc_gcasset_movie_stream_cancel(int handle){
    if(handle<0 || handle==gcasset_movie_armed.handle)gcasset_movie_armed.owner=0;
    if(gcasset_movie_start.active && (handle<0 || handle==gcasset_movie_start.handle))gcasset_movie_start.failed=1;
}
static void gcasset_movie_start_begin(int handle,uint32_t frequency,int stereo){
    if(gcasset_movie_start.active){gcasset_movie_start.failed=1;gcasset_movie_start_end();}
    memset(&gcasset_movie_start,0,sizeof gcasset_movie_start);
    gcasset_movie_start.handle=handle;gcasset_movie_start.active=1;
    if(handle<0 || handle>=SND_STREAM_MAX){gcasset_movie_start.failed=1;return;}
    const strchan_t* stream=&streams[handle];
    gcasset_movie_start.owner=gcasset_movie_armed.owner;gcasset_movie_start.asset=gcasset_movie_armed.asset;
    if(gcasset_movie_armed.handle!=handle || !gcasset_movie_start.owner || !stream->initted ||
       frequency!=32000 || !stereo || max_channels!=2 || stream->buffer_size!=32768 ||
       !stream->get_data || stream->req_data || stream->queueing || TAILQ_FIRST(&stream->filters))gcasset_movie_start.failed=1;
    gcasset_movie_start.size=stream->buffer_size;gcasset_movie_start.callback=stream->get_data;
    for(unsigned i=0;i<2;++i){gcasset_movie_start.ch[i]=stream->ch[i];gcasset_movie_start.base[i]=stream->spu_ram_sch[i];
        if(stream->ch[i]<0 || stream->ch[i]>=32 || stream->spu_ram_sch[i]<AICA_RAM_START ||
           stream->spu_ram_sch[i]>AICA_RAM_END-stream->buffer_size)gcasset_movie_start.failed=1;
    }
    if(stream->ch[0]==stream->ch[1] || stream->spu_ram_sch[1]!=stream->spu_ram_sch[0]+stream->buffer_size)gcasset_movie_start.failed=1;
}
static int gcasset_movie_command(void* packet,uint32_t bytes){
    gcasset_movie_start_t* use=&gcasset_movie_start;
    if(use->active){
        const aica_cmd_t* command=(const aica_cmd_t*)packet;const aica_channel_t* channel=packet?(const aica_channel_t*)command->cmd_data:NULL;
        const unsigned sequence=use->commands;
        if(!sequence)re4dc_gcasset_movie_audio_ticket(&use->slot,&use->serial);
        if(!packet || bytes!=AICA_CMDSTR_CHANNEL_SIZE || command->size!=bytes || command->cmd!=AICA_CMD_CHAN ||
           command->timestamp || sequence>=3 || !use->owner || use->owner!=gcasset_movie_armed.owner ||
           use->handle!=gcasset_movie_armed.handle || use->asset!=gcasset_movie_armed.asset ||
           use->ch[0]<0 || use->ch[0]>=32 || use->ch[1]<0 || use->ch[1]>=32)use->failed=1;
        else if(sequence<2){
            if(command->cmd_id!=(unsigned)use->ch[sequence] || channel->cmd!=(AICA_CH_CMD_START|AICA_CH_START_DELAY) ||
               channel->base!=use->base[sequence] || channel->type!=AICA_SM_16BIT || channel->length!=use->size/2 ||
               !channel->loop || channel->loopstart || channel->loopend!=use->size/2 || channel->freq!=32000)use->failed=1;
        }else if(command->cmd_id!=((1u<<use->ch[0])|(1u<<use->ch[1])) ||
                 channel->cmd!=(AICA_CH_CMD_START|AICA_CH_START_SYNC))use->failed=1;
        if(use->commands==~0u)use->failed=1;else ++use->commands;
    }
#if RE4DC_CABIN_SOURCE
    const int result=cabin_stream_command(packet,bytes);
#else
    const int result=snd_sh4_to_aica(packet,bytes);
#endif
    if(use->active){if(result)use->failed=1;else ++use->accepted;}
    return result;
}
static void gcasset_movie_start_end(void){
    gcasset_movie_start_t* use=&gcasset_movie_start;
    if(!use->active)return;
    if(use->commands){
        if(use->handle<0 || use->handle>=SND_STREAM_MAX)use->failed=1;
        else{const strchan_t* stream=&streams[use->handle];
            if(!stream->initted || stream->get_data!=use->callback || stream->req_data || stream->queueing ||
               TAILQ_FIRST(&stream->filters) || stream->channels!=2 || stream->type!=AICA_SM_16BIT || stream->bitsize!=16 ||
               stream->frequency!=32000 || stream->buffer_size!=use->size ||
               stream->ch[0]!=use->ch[0] || stream->ch[1]!=use->ch[1] ||
               stream->spu_ram_sch[0]!=use->base[0] || stream->spu_ram_sch[1]!=use->base[1])use->failed=1;
        }
        re4dc_gcasset_movie_audio_submit(use->slot,use->serial,
            !use->failed && use->commands==3 && use->accepted==3?use->asset:0);
    }
    use->active=0;
}
// GC_ASSET_MOVIE_STREAM_END
#endif
#if RE4DC_CABIN_SOURCE
// CABIN_STREAM_OBSERVER_BEGIN
// The included SDK owns transfer scheduling. Its semaphore is released by the
// final stereo callback, but ALSO on DMA submission failure; both are checked.
typedef struct cabin_stream_observer {
    unsigned generation, last_generation;
    int handle, active, starting, failed, acknowledged, armed;
    int ch[2]; uint32_t base[2], size;
    snd_stream_callback_t callback;
    unsigned commands, first_dma, second_dma, armed_dma;
    uint32_t pos[2], travelled[2];
    uint64_t started, sampled, progress[2], armed_at;
} cabin_stream_observer_t;
static cabin_stream_observer_t cabin_stream;

static void cabin_stream_invalidate(snd_stream_hnd_t hnd) {
    if(cabin_stream.active && (hnd < 0 || hnd == cabin_stream.handle)) {
        cabin_stream.failed = 1;
        cabin_stream.active = 0;
    }
}
void snd_stream_start(snd_stream_hnd_t hnd, uint32_t freq, int stereo) {
    cabin_stream_invalidate(hnd);
#if RE4DC_GC_ASSET_GATE
    gcasset_movie_start_begin(hnd,freq,stereo);
#endif
    cabin_sdk_stream_start(hnd, freq, stereo);
#if RE4DC_GC_ASSET_GATE
    gcasset_movie_start_end();
#endif
}
void snd_stream_start_pcm8(snd_stream_hnd_t hnd, uint32_t freq, int stereo) {
    cabin_stream_invalidate(hnd);
#if RE4DC_GC_ASSET_GATE
    gcasset_movie_start_begin(hnd,freq,stereo);
#endif
    cabin_sdk_stream_start_pcm8(hnd, freq, stereo);
#if RE4DC_GC_ASSET_GATE
    gcasset_movie_start_end();
#endif
}
void snd_stream_start_adpcm(snd_stream_hnd_t hnd, uint32_t freq, int stereo) {
    cabin_stream_invalidate(hnd);
#if RE4DC_GC_ASSET_GATE
    gcasset_movie_start_begin(hnd,freq,stereo);
#endif
    cabin_sdk_stream_start_adpcm(hnd, freq, stereo);
#if RE4DC_GC_ASSET_GATE
    gcasset_movie_start_end();
#endif
}
void snd_stream_stop(snd_stream_hnd_t hnd) {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset_movie_stream_cancel(hnd);
#endif
    cabin_stream_invalidate(hnd); cabin_sdk_stream_stop(hnd);
}
void snd_stream_destroy(snd_stream_hnd_t hnd) {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset_movie_stream_cancel(hnd);
#endif
    cabin_stream_invalidate(hnd); cabin_sdk_stream_destroy(hnd);
}
void snd_stream_shutdown(void) {
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset_movie_stream_cancel(-1);
#endif
    cabin_stream_invalidate(-1); cabin_sdk_stream_shutdown();
}

static int cabin_stream_dma(void *from, uintptr_t dest, size_t length,
                            int block, spu_dma_callback_t callback, void *data) {
    const int owned = cabin_stream.active && data == &streams[cabin_stream.handle];
    const int second = callback == dma_done;
    if(owned && (block || (callback != dma_chain && callback != dma_done) ||
       !length || length > cabin_stream.size / 2 ||
       dest < cabin_stream.base[second] ||
       dest + length > cabin_stream.base[second] + cabin_stream.size))
        cabin_stream.failed = 1;
    const int result = spu_dma_transfer(from, dest, length, block, callback, data);
    if(owned) {
        // EINPROGRESS is retried only by the SDK's FIRST-channel transfer loop.
        if(result < 0 && (second || errno != EINPROGRESS))cabin_stream.failed = 1;
        if(result == 0) {
            unsigned *count = second ? &cabin_stream.second_dma : &cabin_stream.first_dma;
            if(*count == ~0u)cabin_stream.failed = 1; else ++*count;
        }
    }
    return result;
}

static int cabin_stream_command(void *packet, uint32_t size) {
    if(cabin_stream.active) {
        aica_cmd_t *command = packet;
        aica_channel_t *channel = (aica_channel_t *)command->cmd_data;
        const unsigned sequence = cabin_stream.commands;
        if(!cabin_stream.starting || sequence >= 3 ||
           size != AICA_CMDSTR_CHANNEL_SIZE || command->size != size ||
           command->cmd != AICA_CMD_CHAN || command->timestamp != 0)
            cabin_stream.failed = 1;
        else if(sequence < 2) {
            if(command->cmd_id != (unsigned)cabin_stream.ch[sequence] ||
               channel->cmd != (AICA_CH_CMD_START | AICA_CH_START_DELAY) ||
               channel->base != cabin_stream.base[sequence] ||
               channel->type != AICA_SM_16BIT || channel->length != cabin_stream.size / 2 ||
               channel->loop != 1 || channel->loopstart != 0 ||
               channel->loopend != cabin_stream.size / 2 || channel->freq != 32000)
                cabin_stream.failed = 1;
        }
        else if(command->cmd_id != ((1u << cabin_stream.ch[0]) | (1u << cabin_stream.ch[1])) ||
                channel->cmd != (AICA_CH_CMD_START | AICA_CH_START_SYNC))
            cabin_stream.failed = 1;
        if(sequence == ~0u)cabin_stream.failed = 1; else ++cabin_stream.commands;
    }
    const int result = snd_sh4_to_aica(packet, size);
    if(cabin_stream.active && result != 0)cabin_stream.failed = 1;
    return result;
}

static int cabin_stream_identity(void) {
    if(!cabin_stream.active || cabin_stream.failed || cabin_stream.handle < 0 ||
       cabin_stream.handle >= SND_STREAM_MAX)return 0;
    const strchan_t *stream = &streams[cabin_stream.handle];
    return stream->initted && stream->get_data == cabin_stream.callback && !stream->req_data &&
        !TAILQ_FIRST(&stream->filters) && stream->channels == 2 &&
        stream->type == AICA_SM_16BIT && stream->bitsize == 16 &&
        stream->frequency == 32000 && !stream->queueing &&
        stream->buffer_size == cabin_stream.size &&
        stream->ch[0] == cabin_stream.ch[0] && stream->ch[1] == cabin_stream.ch[1] &&
        stream->spu_ram_sch[0] == cabin_stream.base[0] && stream->spu_ram_sch[1] == cabin_stream.base[1];
}

// The pinned allocator marks a slot initted even if sample RAM or either
// channel allocation fails. Validate before START and unwind only this new
// slot's exact reservations; SDK destroy would STOP an invalid channel.
int re4dc_movie_stream_cabin_alloc(void *(*callback)(int, int, int *), unsigned bytes) {
    if(!callback || bytes != 32768 || max_channels != 2 || cabin_stream.active)return SND_STREAM_INVALID;
    const snd_stream_hnd_t hnd = snd_stream_alloc(callback, bytes);
    if(hnd == SND_STREAM_INVALID)return hnd;
    strchan_t *stream = &streams[hnd];
    if(stream->spu_ram_sch[0] >= AICA_RAM_START &&
       stream->spu_ram_sch[0] <= AICA_RAM_END - 2 * bytes &&
       stream->spu_ram_sch[1] == stream->spu_ram_sch[0] + bytes &&
       stream->ch[0] >= 0 && stream->ch[0] < 32 &&
       stream->ch[1] >= 0 && stream->ch[1] < 32 && stream->ch[0] != stream->ch[1])return hnd;
    // Nothing has played or issued DMA/ARM commands for this slot. Preserve
    // pre-existing streams, queued commands and every unrelated channel.
    if(stream->ch[0] >= 0 && stream->ch[0] < 64)snd_sfx_chn_free(stream->ch[0]);
    if(stream->ch[1] >= 0 && stream->ch[1] < 64 && stream->ch[1] != stream->ch[0])
        snd_sfx_chn_free(stream->ch[1]);
    if(stream->spu_ram_sch[0])snd_mem_free(stream->spu_ram_sch[0]);
    memset(stream, 0, sizeof(*stream));
    return SND_STREAM_INVALID;
}

int re4dc_movie_stream_cabin_start(int hnd, unsigned generation) {
    if(!generation || generation <= cabin_stream.last_generation || cabin_stream.active ||
       hnd < 0 || hnd >= SND_STREAM_MAX || !streams[hnd].initted ||
       streams[hnd].ch[0] < 0 || streams[hnd].ch[0] >= 32 ||
       streams[hnd].ch[1] < 0 || streams[hnd].ch[1] >= 32 ||
       streams[hnd].ch[0] == streams[hnd].ch[1] || streams[hnd].buffer_size != 32768 ||
       !streams[hnd].get_data || streams[hnd].req_data || streams[hnd].queueing ||
       TAILQ_FIRST(&streams[hnd].filters) || max_channels != 2)return 0;
    // A previous generation's callbacks cannot be re-labelled during reuse.
    if(sem_trywait(&stream_sem) < 0)return 0;
    sem_signal(&stream_sem);
    memset(&cabin_stream, 0, sizeof(cabin_stream));
    cabin_stream.generation = cabin_stream.last_generation = generation;
    cabin_stream.handle = hnd; cabin_stream.active = cabin_stream.starting = 1;
    cabin_stream.callback = streams[hnd].get_data; cabin_stream.size = streams[hnd].buffer_size;
    for(unsigned i = 0; i < 2; ++i) {
        cabin_stream.ch[i] = streams[hnd].ch[i];
        cabin_stream.base[i] = streams[hnd].spu_ram_sch[i];
        if(cabin_stream.base[i] < AICA_RAM_START || cabin_stream.base[i] > AICA_RAM_END - cabin_stream.size)
            cabin_stream.failed = 1;
    }
    if(cabin_stream.base[1] != cabin_stream.base[0] + cabin_stream.size)cabin_stream.failed = 1;
    cabin_stream.started = timer_us_gettime64();
    if(!cabin_stream.failed){
#if RE4DC_GC_ASSET_GATE
        gcasset_movie_start_begin(hnd,32000,1);
#endif
        cabin_sdk_stream_start(hnd, 32000, 1);
#if RE4DC_GC_ASSET_GATE
        gcasset_movie_start_end();
#endif
    }
    cabin_stream.starting = 0;
    if(cabin_stream.commands != 3 || !cabin_stream_identity())cabin_stream.failed = 1;
    return !cabin_stream.failed;
}

// One coherent G2 snapshot excludes all SH4 command producers (IRQ is masked
// by g2_lock_scoped). ARM publishes tail only AFTER executing each command.
// The generation's observed three-command START sequence plus an empty valid
// queue proves this START was consumed. Read-only: never writes ARM status.
static int cabin_stream_snapshot(uint32_t position[2]) {
    g2_lock_scoped();
    g2_fifo_wait();
    const uintptr_t queue = SPU_RAM_UNCACHED_BASE + AICA_MEM_CMD_QUEUE;
#define CABIN_Q(field) g2_read_32_raw(queue + offsetof(aica_queue_t, field))
    const uint32_t head = CABIN_Q(head), tail = CABIN_Q(tail);
    if(CABIN_Q(valid) != 1 || CABIN_Q(data) != AICA_MEM_CMD_QUEUE + sizeof(aica_queue_t) ||
       CABIN_Q(size) != AICA_MEM_RESP_QUEUE - AICA_MEM_CMD_QUEUE - sizeof(aica_queue_t) ||
       head >= AICA_MEM_RESP_QUEUE - AICA_MEM_CMD_QUEUE - sizeof(aica_queue_t) ||
       tail >= AICA_MEM_RESP_QUEUE - AICA_MEM_CMD_QUEUE - sizeof(aica_queue_t) ||
       (head & 3) || (tail & 3))return -1;
    if(CABIN_Q(process_ok) != 1 || head != tail || CABIN_Q(head) != head)return 0;
#undef CABIN_Q
    for(unsigned i = 0; i < 2; ++i) {
        const uintptr_t address = SPU_RAM_UNCACHED_BASE + AICA_CHANNEL(cabin_stream.ch[i]);
#define CABIN_CH(field) g2_read_32_raw(address + offsetof(aica_channel_t, field))
        if(CABIN_CH(base) != cabin_stream.base[i] || CABIN_CH(type) != AICA_SM_16BIT ||
           CABIN_CH(length) != cabin_stream.size / 2 || CABIN_CH(loop) != 1 ||
           CABIN_CH(loopstart) != 0 || CABIN_CH(loopend) != cabin_stream.size / 2 ||
           CABIN_CH(freq) != 32000 ||
           !(g2_read_32_raw(MEM_AREA_P2_BASE + 0x00700000 + 0x80 * cabin_stream.ch[i]) & AICA_CHANNEL_KEYONB))return -1;
        position[i] = CABIN_CH(pos);
        if(position[i] >= cabin_stream.size / 2)return -1;
#undef CABIN_CH
    }
    return 1;
}

// -1 error; 0 awaiting START/DMA; 1 drained; 2 live, ready to poll. A full ring
// AFTER the last real PCM write is conservative for even a short primed clip.
int re4dc_movie_stream_cabin_progress(int hnd, unsigned generation, int final_pcm) {
    if(!generation || generation != cabin_stream.generation || hnd != cabin_stream.handle ||
       !cabin_stream_identity() || cabin_stream.commands != 3)return -1;
    const uint64_t now = timer_us_gettime64();
    if(now < cabin_stream.started || (!cabin_stream.acknowledged && now - cabin_stream.started > 10000000ULL))
        goto invalid;
    if(sem_trywait(&stream_sem) < 0)return 0;
    // The untouched SDK releases this semaphore only after both chained DMAs
    // complete, or on an error captured by cabin_stream_dma above.
    uint32_t position[2];
    const int snapshot = cabin_stream_snapshot(position);
    const int transfers = !cabin_stream.failed && cabin_stream.first_dma &&
        cabin_stream.first_dma == cabin_stream.second_dma;
    sem_signal(&stream_sem);
    if(snapshot < 0 || !transfers)goto invalid;
    if(!snapshot)return 0;
    if(!cabin_stream.acknowledged) {
        cabin_stream.acknowledged = 1; cabin_stream.sampled = now;
        for(unsigned i = 0; i < 2; ++i) {
            cabin_stream.pos[i] = position[i]; cabin_stream.progress[i] = now;
        }
    }
    else {
        const uint64_t elapsed = now - cabin_stream.sampled;
        // At or beyond one ring, zero progress and a complete wrap alias.
        if(now < cabin_stream.sampled || elapsed >= 512000ULL)goto invalid;
        for(unsigned i = 0; i < 2; ++i) {
            const uint32_t delta = (position[i] + 16384u - cabin_stream.pos[i]) % 16384u;
            if(delta > elapsed * 32000ULL / 1000000ULL + 352u)goto invalid;
            if(delta)cabin_stream.progress[i] = now;
            else if(now - cabin_stream.progress[i] > 200000ULL)goto invalid;
            if(cabin_stream.armed)cabin_stream.travelled[i] += delta;
            cabin_stream.pos[i] = position[i];
        }
        cabin_stream.sampled = now;
    }
    if(final_pcm && !cabin_stream.armed) {
        cabin_stream.armed = 1; cabin_stream.armed_at = now;
        cabin_stream.armed_dma = cabin_stream.first_dma;
    }
    if(cabin_stream.armed) {
        if(!final_pcm || cabin_stream.travelled[0] > (now - cabin_stream.armed_at) * 32000ULL / 1000000ULL + 352u ||
           cabin_stream.travelled[1] > (now - cabin_stream.armed_at) * 32000ULL / 1000000ULL + 352u)goto invalid;
        if(cabin_stream.travelled[0] >= 16384 && cabin_stream.travelled[1] >= 16384)return 1;
    }
    return 2;
invalid:
    cabin_stream.failed = 1;
    return -1;
}
// CABIN_STREAM_OBSERVER_END
#elif RE4DC_GC_ASSET_GATE
void snd_stream_start(snd_stream_hnd_t hnd,uint32_t freq,int stereo){
    gcasset_movie_start_begin(hnd,freq,stereo);cabin_sdk_stream_start(hnd,freq,stereo);gcasset_movie_start_end();
}
void snd_stream_start_pcm8(snd_stream_hnd_t hnd,uint32_t freq,int stereo){
    gcasset_movie_start_begin(hnd,freq,stereo);cabin_sdk_stream_start_pcm8(hnd,freq,stereo);gcasset_movie_start_end();
}
void snd_stream_start_adpcm(snd_stream_hnd_t hnd,uint32_t freq,int stereo){
    gcasset_movie_start_begin(hnd,freq,stereo);cabin_sdk_stream_start_adpcm(hnd,freq,stereo);gcasset_movie_start_end();
}
void snd_stream_stop(snd_stream_hnd_t hnd){re4dc_gcasset_movie_stream_cancel(hnd);cabin_sdk_stream_stop(hnd);}
void snd_stream_destroy(snd_stream_hnd_t hnd){re4dc_gcasset_movie_stream_cancel(hnd);cabin_sdk_stream_destroy(hnd);}
void snd_stream_shutdown(void){re4dc_gcasset_movie_stream_cancel(-1);cabin_sdk_stream_shutdown();}
#endif

#if RE4DC_MOVIE_WORLD_ARENA
int re4dc_movie_stream_idle(void) {
    if(max_channels || movie_sep || movie_sep_raw || sep_buffer[0] || sep_buffer[1])return 0;
    for(unsigned i=0;i<SND_STREAM_MAX;++i)if(streams[i].initted || TAILQ_FIRST(&streams[i].filters))return 0;
    return 1;
}
#endif
int re4dc_movie_stream_initialized(void) { return max_channels != 0; }
unsigned re4dc_movie_stream_active(void) {
    unsigned n=0;
    for(unsigned i=0;i<SND_STREAM_MAX;++i) if(streams[i].initted) ++n;
    return n;
}
#endif
