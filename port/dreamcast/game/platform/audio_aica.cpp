// AICA audio backend (AICA_AUDIO=1; audio_stub.cpp keeps the silent version).
//
// The recovered Capcom sound driver (src/game/snd_*.cpp) already runs on the
// Dreamcast: it resolves SE numbers, positions, priorities, envelopes and the
// BGM MIDI sequences, and drives Nintendo's AX voice / MIX / SYN interfaces.
// This file implements those interfaces on the AICA instead of silencing them:
//
//  * Sample banks. A sound block's ARAM part reaches ARQPostRequest in 128 KB
//    pieces after its MRAM part (the SYN wavetable: sample offsets, lengths,
//    rates, DSP-ADPCM coefficients). Banks converted at build time
//    (tools/aica_banks.py: AicaBankHeader + AICA 4-bit ADPCM image in place of
//    the GC image) are copied straight into a fixed AICA layout: one slot per
//    resident block (CORE, PL, WEP, BGM0/1, DOOR) and one room arena (ROOM,
//    FOOT, enemies) reset at each room load, all sized by the tool's route
//    budget, so nothing fragments across room changes and continues. A bank
//    without the header is still decoded (GC DSP-ADPCM) and re-encoded here,
//    decimated to a rate cap that fits, into free AICA RAM outside the layout.
//  * AX voices (SEs) map to AICA channels programmed directly over G2 (32-bit
//    writes, a FIFO wait every 8 writes, no reads). End of a one-shot voice is
//    estimated from elapsed time and pitch, so no AICA register is read back.
//  * SYN (the MIDI synth under the BGM sequencer) is a minimal GM voice layer:
//    note on/off, program, volume/expression/pan, pitch bend and the region's
//    DLS envelope mapped onto the AICA hardware envelope.
//  * The driver's 5 ms audio frame runs on a 200 Hz KOS thread (the GameCube
//    AI interrupt rate), then all register writes are flushed under one G2 lock.
//  * Disc streams (snd_str, bio4bgm.sbb) converted at build time
//    (tools/aica_banks.py streams -> bgm/aica_str.dat, AICA ADPCM, intro then a
//    seamless loop body) play from a 2 x 12 KB per channel AICA ring in ADPCM
//    long-stream mode, refilled by a reader thread (DMA reads, no decoding on the
//    SH-4). The driver's own stream voices keep running silently and drive
//    start, stop and volume (audio_strm.cpp keeps them running in every build,
//    so scenario waits on a stream always complete). A stream missing from
//    aica_str.dat, or a build without AICA_STREAMS=1, is silent.
//
// Not covered yet: AUX reverb, LPF, LFO, DPL2.
#include <kos.h>
#include <dc/sound/sound.h>
#include <dc/sound/sfxmgr.h>
#include <dc/g2bus.h>
#include <dc/spu.h>
#include <math.h>
#include <string.h>

#include "re4dc_platform.h"

#ifndef RE4DC_AICA_VERIFY
#define RE4DC_AICA_VERIFY 0   // 1: log an FNV of every block as it sits in AICA RAM (debug)
#endif

typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef signed short s16;
typedef signed long s32;
typedef unsigned long u32;
typedef unsigned long long u64;
typedef float f32;

// ---------------------------------------------------------------------------
// SDK structure mirrors (include/dolphin/ax.h, syn.h). Only the fields the
// driver reads back (pb.state, pb.addr) must sit at the SDK offsets.
struct AXPBADDR { u16 loopFlag, format, loopAddressHi, loopAddressLo, endAddressHi, endAddressLo, currentAddressHi, currentAddressLo; };
struct AXPBSRC { u16 ratioHi, ratioLo, currentAddressFrac, last_samples[4]; };
struct MixState { s16 in, fader; u8 pan; u8 pad; };

struct Voice;
// The driver sees an AXVPB; its SDK header (0x138 bytes before pb) is unused by
// the driver, so the backend keeps its own voice state there.
struct VoiceState {
    u8 used, running, loop, dirty;   // dirty: 1 start, 2 vol/pan, 4 freq, 8 stop
    s8 ch;                           // AICA channel, -1 none
    s8 blk;                          // sound block of the sample, -1 unmapped
    u8 mapped, freed;
    u32 aica;                        // AICA byte address of the sample start
    u32 len;                         // AICA samples (after decimation)
    u32 loop_start;                  // AICA samples
    u32 gc_start_nib;                // GC nibble address of the first sample
    u32 gc_len;                      // GC samples to the end (or the loop end)
    u32 gc_loop;                     // GC sample index of the loop start
    u32 s0;                          // GC sample index the voice started at
    u32 rate;                        // source sample rate (Hz)
    u8 shift;                        // decimation 1 << shift
    u8 strm;                         // acquired by the stream player (snd_str3 cb_str_voice_drop)
    u8 pad2[2];
    f32 ratio;                       // AX src ratio (1.0 = 32 kHz output)
    f32 pos;                         // estimated GC sample position
    MixState mix;
    u32 play_cont;                   // AICA reg 0 without the key bits
    u16 sent_tl, sent_pan, sent_freq, pad3;
};
struct AXVPBView {
    VoiceState vs;                                   // 0x000 (the SDK header area)
    u8 pad_to_pb[0x138 - sizeof(VoiceState)];
    // AXPB
    u16 nextHi, nextLo, currHi, currLo, srcSelect, coefSelect, mixerCtrl;
    u16 state;                                       // 0x138 + 0x0E
    u16 type;                                        // 0x138 + 0x10
    u8 pad_mix[0x6E - 0x12];
    AXPBADDR addr;                                   // 0x138 + 0x6E
    u8 pad_tail[0x10];
};
static_assert(sizeof(VoiceState) <= 0x138, "voice state must fit the SDK header");
static_assert(__builtin_offsetof(AXVPBView, state) == 0x146, "pb.state offset");
static_assert(__builtin_offsetof(AXVPBView, addr) == 0x1A6, "pb.addr offset");

struct WTREGION { u8 unityNote; u8 keyGroup; s16 fineTune; s32 attn; u32 loopStart; u32 loopLength; u32 articulationIndex; u32 sampleIndex; };
struct WTART { s32 lfoFreq, lfoDelay, lfoAtten, lfoPitch, lfoMod2Atten, lfoMod2Pitch, eg1Attack, eg1Decay, eg1Sustain, eg1Release, eg1Vel2Attack, eg1Key2Decay, eg2Attack, eg2Decay, eg2Sustain, eg2Release, eg2Vel2Attack, eg2Key2Decay, eg2Pitch, pan; };
struct WTSAMPLE { u16 format; u16 sampleRate; u32 offset; u32 length; u16 adpcmIndex; u16 pad; };
struct WTADPCM { s16 a[8][2]; u16 gain, pred_scale, yn1, yn2, loop_pred_scale, loop_yn1, loop_yn2; };
static_assert(sizeof(WTSAMPLE) == 16, "WTSAMPLE");
static_assert(sizeof(WTADPCM) == 0x2E, "WTADPCM");
struct SndWtHdr { u32 x0, inst_ofs, rgn_ofs, art_ofs, sample_ofs, adpcm_ofs; };

// Driver globals (src/game/snd.cpp, snd_ram.cpp). Variables are not mangled.
struct SndMemView { u8 pad[0x14]; u8* blk_mram[14]; u32 blk_aram[14]; };
extern SndMemView SndMem;
extern u32 UseAramSize[14];

typedef void (*AXCallback)(void);

// Stream player (src/game/snd_str*.cpp): SND_STR_WORK (include/snd_drv.h,
// Snd_str_work[4], 0x14C bytes), only the fields read here, at their offsets.
struct Re4dcStrWorkView {
    u16 status;                  // 0x00  bit 0 open
    u8 pad0[0x0A];
    const u32* shd;              // 0x0C  SND_SHD: [0] flag (1 stereo), [7] .sbb offset
    u8 pad1[0x0C];
    u32 flag;                    // 0x1C  shd->flag
    u8 pad2[0xC8 - 0x20];
    void* voiceL;                // 0xC8
    void* voiceR;                // 0xCC
    u8 pad3[0x14C - 0xD0];
};
static_assert(sizeof(Re4dcStrWorkView) == 0x14C, "SND_STR_WORK size");
static_assert(__builtin_offsetof(Re4dcStrWorkView, flag) == 0x1C, "SND_STR_WORK flag");
static_assert(__builtin_offsetof(Re4dcStrWorkView, voiceL) == 0xC8, "SND_STR_WORK voiceL");
extern "C" {
extern Re4dcStrWorkView Snd_str_work[4];
const u32* Snd_get_shd_adrs(u16 blk_no, u16 req_no);   // SND_SHD*
void cb_str_voice_drop(void* voice);                   // the stream player's AX voice callback
// Stream player plumbing shared with the stub (audio_strm.cpp).
void re4dc_audio_pend_run(void);
int re4dc_strm_advance(u16* addr, f32 samples, f32* frac);
extern u32 re4dc_strm_reads_skipped, re4dc_strm_dmas;
}
#ifndef RE4DC_AICA_STREAMS
#define RE4DC_AICA_STREAMS 0   // Makefile AICA_STREAMS=1: play disc streams from bgm/aica_str.dat
#endif
u32 SndStrReq(int blk, int no, int req, int time, int vol, f32 pos);   // snd.cpp (C++ linkage)

// ---------------------------------------------------------------------------
// AICA access. Registers from the SH-4: 0xA0700000 + ch * 0x80. Only 32-bit
// writes; a FIFO wait before every 8th write (Sega: bursts of at most 8).
namespace {

const uintptr_t kAicaChan = 0xA0700000u;
const u32 kReserveBytes = 64 * 1024;   // AICA RAM kept free for streams / movie

struct RegWriter {
    u32 n = 0;
    void w(u32 ch, u32 reg, u32 v) {
        if ((n++ & 7) == 0) g2_fifo_wait();
        g2_write_32_raw(kAicaChan + ch * 0x80 + reg, v);
    }
};

// AICA pitch register: freq = 44100 * 2^oct * (1 + fns / 1024).
u16 aica_freq_reg(u32 hz)
{
    if (hz < 173) hz = 173;
    if (hz > 180000) hz = 180000;
    u32 base = 5644800;
    int oct = 7;
    while (hz < base && oct > -8) { base >>= 1; --oct; }
    u32 fns = (hz << 10) / base;
    return (u16) (((oct & 0xF) << 11) | ((fns - 1024) & 1023));
}

// AICA hardware envelope tables (ms, effective rate = 2 * R, key rate scaling off).
const f32 kArMs[32] = { 100000, 8100, 6000, 4000, 3000, 2000, 1500, 1000, 760, 500, 380, 250, 190, 130,
                        95, 63, 47, 31, 24, 15, 12, 7.9f, 6.0f, 3.8f, 3.0f, 2.0f, 1.6f, 1.1f, 0.85f, 0.53f, 0.40f, 0 };
const f32 kDrMs[32] = { 100000, 118200, 88600, 59100, 44300, 29600, 22200, 14800, 11100, 7400, 5500, 3700, 2800, 1800,
                        1400, 920, 690, 460, 340, 230, 170, 110, 85, 57, 43, 28, 22, 14, 11, 7.1f, 5.4f, 3.6f };
u32 rate_for_ms(const f32* t, f32 ms)
{
    u32 best = 31;
    f32 bd = 1e30f;
    for (u32 r = 1; r < 32; r++) {
        f32 d = fabsf(t[r] - ms);
        if (d < bd) { bd = d; best = r; }
    }
    return best;
}

// AX / DLS attenuation (0.1 dB, <= 0) to AICA TL (0.375 dB steps).
u16 tl_from_db10(s32 db10)
{
    if (db10 >= 0) return 0;
    s32 tl = (-db10 * 8 + 15) / 30;
    return (u16) (tl > 255 ? 255 : tl);
}
// 0..127 pan (64 centre) to the AICA DIPAN field.
u16 dipan(u32 pan)
{
    u32 x = pan * 2;
    if (x == 128) return 0;
    if (x < 128) return 0x10 | ((127 - x) >> 3);
    return (x - 128) >> 3;
}

// ---------------------------------------------------------------------------
// Converted sample banks.
struct MapEnt { u32 gc_nib; u32 len; u32 aica; };  // aica: addr | shift << 24 | ok << 31
struct Blk {
    u32 gc_base, gc_size;        // GC ARAM bytes
    u32 aica, aica_size;         // AICA allocation
    u16 first, count;            // map entries (sample index order)
    u16 rate_cap;
    u8 valid, slotted;          // slotted: lives in the fixed layout (never freed)
    const WTSAMPLE* smp;
    const WTADPCM* adpcm;
};
const int kMapMax = 640;
MapEnt g_map[kMapMax];
u32 g_mapUsed;
Blk g_blk[14];

// Build-time converted bank (tools/aica_banks.py) at the start of the ARAM part.
const u32 kBankMagic = 0x31434941;   // "AIC1"
struct AicaBankHeader {
    u32 magic;
    u16 version, cap_hz;
    u32 total;            // AICA image bytes (follow the header)
    u32 nsamples;
    u32 fnv;              // FNV-1a of the wavetable sample table
    u32 gc_size;          // GC ARAM part size
    u32 slot;             // layout slot of this block (8 = room arena)
    u32 pad;
    u32 slot_bytes[9];    // the route layout, by block index (8 = room arena)
    u32 pad2[7];
};
static_assert(sizeof(AicaBankHeader) == 96, "AicaBankHeader");
struct Slot { u32 base, size; };
Slot g_slot[9];
u32 g_arenaNext;
bool g_layout, g_layoutWarned;
inline u32 slot_of(int t) { return (t == 5 || t == 6 || t >= 8) ? 8 : (u32) t; }

// Disc stream ring in AICA RAM: per channel two halves of 12 KB of 4-bit ADPCM
// (24576 samples, 0.77 s at 32 kHz); allocated once after the layout, never freed.
// tools/aica_banks.py budgets it as STREAM_RING.
const u32 kStrHalfBytes = 12 * 1024;
const u32 kStrHalfSamples = kStrHalfBytes * 2;
const u32 kStrChBytes = 2 * kStrHalfBytes;
const u32 kStrRingBytes = 2 * kStrChBytes;
u32 g_strRing;
const u32 kAicaPoolBytes = 1900544;          // KOS snd_mem pool (AICA RAM above the driver)
const u32 kMovieReserveBytes = 64 * 1024;    // left free for snd_stream (movie audio)

// Conversion (or copy) of the block currently being uploaded.
struct Conv {
    int blk = -1;
    u8 prebuilt;
    u32 img_total;
    u32 next_dst;
    u16 order[512];              // sample indices by offset
    u16 n, cur;                  // samples, cursor into order[]
    // state of the sample at the cursor
    s32 h1, h2;                  // DSP history
    s32 pred, step;              // AICA encoder
    s32 acc; u32 acc_n;          // decimation accumulator
    u32 in_done;                 // GC samples decoded
    u32 out_bytes;               // bytes written to AICA for this sample
    u8 nib_have, nib;            // pending low nibble
    u8 stage[1024 + 32] __attribute__((aligned(32)));
    u32 stage_len;
} g_conv;

// Sound-block ARAM policy: preferred rate cap per block kind (Hz), lowered
// until the block fits. 0 CORE, 1 PL, 2 WEP, 3/4 BGM, 5 FOOT, 6 ROOM, 7 DOOR, 8.. EM.
u16 pref_cap(int t)
{
    switch (t) {
    case 3: case 4: return 32000;          // BGM instruments
    case 0: case 2: case 7: return 22050;  // core, weapon, door
    case 6: return 16000;                  // room
    default: return 11025;                 // player, foot, enemies
    }
}
bool room_arena(int t) { return t == 5 || t == 6 || t >= 8; }

// Bytes a sample needs at a rate cap; its decimation shift.
u32 sample_shift(const WTSAMPLE& s, u32 cap)
{
    u32 sh = 0;
    while (sh < 3 && ((u32) (s.sampleRate >> sh) > cap + cap / 64 || (s.length >> sh) > 65534)) ++sh;
    return sh;
}
u32 sample_bytes(const WTSAMPLE& s, u32 sh)
{
    u32 n = (s.length + (1u << sh) - 1) >> sh;
    return ((n + 7) / 8) * 4;
}

// ---------------------------------------------------------------------------
// Statistics (read out with the RAM log; also exported for the capture tools).
struct Stats {
    u32 frames, ticks, drv_us, flush_us, max_drv_us, max_flush_us;
    u32 conv_us, conv_bytes_in, conv_bytes_out, conv_samples;
    u32 se_starts, se_unmapped, se_stops, note_on, note_off, note_steal;
    u32 keyons, regwrites, aica_free, blocks, blocks_skipped;
    u32 blocks_prebuilt, blocks_runtime, copy_bytes;
    u32 active_voices, active_notes, peak_voices, peak_notes;
    u32 str_starts, str_underruns, str_read_bytes, str_reads, str_io_us, str_io_max_us, str_load_us;
};

}  // namespace

extern "C" {
Stats re4dc_audio_stats;
int re4dc_audio_max_ticks = 64;    // driver 5 ms frames run at once after a stall (catch-up cap)
#ifndef RE4DC_AUDIO_SOLO
#define RE4DC_AUDIO_SOLO 0
#endif
int re4dc_audio_solo = RE4DC_AUDIO_SOLO;   // evidence knob: 1 = music only, 2 = SFX only
}

namespace {

Stats& S = re4dc_audio_stats;
bool g_init;
AXCallback g_axCallback;
AXVPBView g_vpb[64] __attribute__((aligned(32)));
u64 g_lastTickUs, g_lastFrameUs, g_threadStartUs;
u32 g_logStarts;
u32 g_aicaUsed;   // bytes of AICA RAM held by the layout and runtime-converted blocks
int g_chUsed;     // AICA channels held by the backend (at most kMaxChannels)
const int kMaxChannels = 60;   // of 64: 4 stay free for snd_stream (movies)

// ---------------------------------------------------------------------------
void aica_init()
{
    if (g_init) return;
    snd_init();
    g_init = true;
    S.aica_free = snd_mem_available();
#if RE4DC_POISON_RAM
    if (const u32 a = snd_mem_malloc(S.aica_free & ~31u)) {
        spu_memset(a, 0x01010101u * (u32) RE4DC_POISON_RAM, (int) (S.aica_free & ~31u));
        snd_mem_free(a);
        re4dc_log("aica: POISON_RAM %02x sound RAM %u bytes\n", (unsigned) RE4DC_POISON_RAM, (unsigned) (S.aica_free & ~31u));
    }
#endif
    re4dc_log("aica: backend up, largest free %u bytes\n", (unsigned) S.aica_free);
}

void blk_cut(int t);

void blk_free(int t)
{
    Blk& b = g_blk[t];
    if (b.aica) blk_cut(t);
    if (b.aica && !b.slotted) { snd_mem_free(b.aica); g_aicaUsed -= (b.aica_size + 31) & ~31u; }
    // compact the map pool
    if (b.count) {
        u32 end = b.first + b.count;
        memmove(&g_map[b.first], &g_map[end], (g_mapUsed - end) * sizeof(MapEnt));
        g_mapUsed -= b.count;
        for (int i = 0; i < 14; i++)
            if (g_blk[i].count && g_blk[i].first >= end) g_blk[i].first -= b.count;
    }
    memset(&b, 0, sizeof(b));
}

// The block's wavetable (MRAM part): sample and coefficient tables.
bool blk_wavetable(int t, const WTSAMPLE*& smp, const WTADPCM*& adpcm, u32& n)
{
    u8* m = SndMem.blk_mram[t];
    if (!m) return false;
    if (t != 3 && t != 4) m += *(u32*) m;
    const u32* iss = (const u32*) m;
    const u8* dls = m + iss[1];
    const SndWtHdr* h = (const SndWtHdr*) dls;
    if (h->adpcm_ofs <= h->sample_ofs) return false;
    n = (h->adpcm_ofs - h->sample_ofs) / sizeof(WTSAMPLE);
    if (n == 0 || n > 512) { re4dc_log("aica: blk %d has %u samples, skipped\n", t, (unsigned) n); return false; }
    smp = (const WTSAMPLE*) (dls + h->sample_ofs);
    adpcm = (const WTADPCM*) (dls + h->adpcm_ofs);
    return true;
}

// A room load (ROOM block at its fixed GC address) empties the room arena.
void blk_prepare(int t, u32 dst)
{
    if (room_arena(t) && dst == 0x1F4100) {
        for (int i = 0; i < 14; i++) if (room_arena(i)) blk_free(i);
        g_arenaNext = 0;
    }
    blk_free(t);
}

// Map entries: sample i at `base` + the bytes of samples 0..i-1 at rate cap `cap`.
void blk_map(Blk& b, u32 n, u32 cap)
{
    b.first = (u16) g_mapUsed;
    b.count = (u16) n;
    u32 a = b.aica;
    for (u32 i = 0; i < n; i++) {
        u32 sh = sample_shift(b.smp[i], cap);
        MapEnt& e = g_map[g_mapUsed++];
        e.gc_nib = b.smp[i].offset;
        e.len = b.smp[i].length;
        e.aica = a | (sh << 24);
        a += sample_bytes(b.smp[i], sh);
    }
}

u32 fnv1a(const u8* p, u32 n)
{
    u32 h = 0x811C9DC5u;
    while (n--) h = (h ^ *p++) * 0x01000193u;
    return h;
}

// First converted bank: reserve the whole route layout, in slot order.
bool layout_init(const AicaBankHeader& h)
{
    if (g_layout) {
        for (int i = 0; i < 9; i++)
            if (h.slot_bytes[i] != g_slot[i].size && !g_layoutWarned) {
                g_layoutWarned = true;
                re4dc_log("aica: bank layout differs from the first bank's (slot %d %u vs %u): keeping the first\n",
                          i, (unsigned) h.slot_bytes[i], (unsigned) g_slot[i].size);
            }
        return true;
    }
    // The movie reserve (snd_stream, cutscene audio) is never given to the layout:
    // tools/aica_banks.py sizes it so, and a bank built for another budget is refused.
    u32 want = kStrRingBytes;
    for (int i = 0; i < 9; i++) want += (h.slot_bytes[i] + 31) & ~31u;
    if (g_aicaUsed + want > kAicaPoolBytes - kMovieReserveBytes) {
        re4dc_log("aica: layout %u + ring %u bytes would leave less than the %u byte movie reserve, banks silent\n",
                  (unsigned) (want - kStrRingBytes), (unsigned) kStrRingBytes, (unsigned) kMovieReserveBytes);
        return false;
    }
    for (int i = 0; i < 9; i++) {
        if (!h.slot_bytes[i]) continue;
        u32 a = snd_mem_malloc(h.slot_bytes[i]);
        if (!a) {
            re4dc_log("aica: layout slot %d (%u bytes) does not fit, %u bytes in use\n", i,
                      (unsigned) h.slot_bytes[i], (unsigned) g_aicaUsed);
            for (int k = 0; k < i; k++) if (g_slot[k].base) snd_mem_free(g_slot[k].base);
            memset(g_slot, 0, sizeof(g_slot));
            return false;
        }
        g_slot[i].base = a;
        g_slot[i].size = h.slot_bytes[i];
        g_aicaUsed += (h.slot_bytes[i] + 31) & ~31u;
    }
    g_layout = true;
    if (!g_strRing && (g_strRing = snd_mem_malloc(kStrRingBytes)) != 0) g_aicaUsed += kStrRingBytes;
    re4dc_log("aica: layout core=%06x+%u pl=%06x+%u wep=%06x+%u bgm0=%06x+%u bgm1=%06x+%u door=%06x+%u arena=%06x+%u "
              "str=%06x+%u, %u bytes, %u free (movie reserve %u)\n",
              (unsigned) g_slot[0].base, (unsigned) g_slot[0].size, (unsigned) g_slot[1].base, (unsigned) g_slot[1].size,
              (unsigned) g_slot[2].base, (unsigned) g_slot[2].size, (unsigned) g_slot[3].base, (unsigned) g_slot[3].size,
              (unsigned) g_slot[4].base, (unsigned) g_slot[4].size, (unsigned) g_slot[7].base, (unsigned) g_slot[7].size,
              (unsigned) g_slot[8].base, (unsigned) g_slot[8].size, (unsigned) g_strRing,
              (unsigned) (g_strRing ? kStrRingBytes : 0), (unsigned) g_aicaUsed,
              (unsigned) (kAicaPoolBytes - g_aicaUsed), (unsigned) kMovieReserveBytes);
    return true;
}

// A build-time converted bank: validate it against the wavetable, place it.
bool blk_begin_prebuilt(int t, u32 dst, const AicaBankHeader& h)
{
    const WTSAMPLE* smp;
    const WTADPCM* adpcm;
    u32 n;
    if (!blk_wavetable(t, smp, adpcm, n)) return false;
    u32 total = 0;
    for (u32 i = 0; i < n; i++) total += sample_bytes(smp[i], sample_shift(smp[i], h.cap_hz));
    const char* bad = h.version != 1 ? "version" : h.nsamples != n ? "sample count"
                    : fnv1a((const u8*) smp, n * sizeof(WTSAMPLE)) != h.fnv ? "wavetable hash"
                    : ((h.gc_size + 31) & ~31u) != UseAramSize[t] ? "part size"
                    : total != h.total ? "image size" : h.slot != slot_of(t) ? "slot" : nullptr;
    if (bad) {
        re4dc_log("aica: blk %d converted bank rejected (%s), block silent\n", t, bad);
        ++S.blocks_skipped;
        return false;
    }
    if (!layout_init(h)) { ++S.blocks_skipped; return false; }
    blk_prepare(t, dst);
    if (g_mapUsed + n > kMapMax) { re4dc_log("aica: map pool full\n"); return false; }
    Slot& sl = g_slot[h.slot];
    u32 base;
    if (h.slot == 8) {
        u32 need = (total + 31) & ~31u;
        if (g_arenaNext + need > sl.size) {
            re4dc_log("aica: blk %d (%u bytes) does not fit the room arena (%u of %u used), block silent\n", t,
                      (unsigned) total, (unsigned) g_arenaNext, (unsigned) sl.size);
            ++S.blocks_skipped;
            return false;
        }
        base = sl.base + g_arenaNext;
        g_arenaNext += need;
    } else {
        if (total > sl.size) {
            re4dc_log("aica: blk %d (%u bytes) larger than its slot (%u), block silent\n", t, (unsigned) total, (unsigned) sl.size);
            ++S.blocks_skipped;
            return false;
        }
        base = sl.base;
    }
    Blk& b = g_blk[t];
    b.smp = smp;
    b.adpcm = adpcm;
    b.gc_base = dst;
    b.gc_size = UseAramSize[t];
    b.aica = base;
    b.aica_size = total;
    b.slotted = 1;
    b.rate_cap = h.cap_hz;
    blk_map(b, n, h.cap_hz);
    b.valid = 1;
    ++S.blocks;
    ++S.blocks_prebuilt;
    Conv& c = g_conv;
    c.blk = t;
    c.prebuilt = 1;
    c.img_total = total;
    re4dc_log("aica: blk %d gc=%06x+%u -> aica=%06x %u bytes, %u samples, %u Hz (prebuilt, slot %u)\n", t, (unsigned) dst,
              (unsigned) b.gc_size, (unsigned) base, (unsigned) total, (unsigned) n, (unsigned) h.cap_hz, (unsigned) h.slot);
    return true;
}

// Parses the block's wavetable (MRAM part) and reserves its AICA copy (runtime conversion).
bool blk_begin(int t, u32 dst)
{
    const WTSAMPLE* smp;
    const WTADPCM* adpcm;
    u32 n;
    if (!blk_wavetable(t, smp, adpcm, n)) return false;
    blk_prepare(t, dst);
    if (g_mapUsed + n > kMapMax) { re4dc_log("aica: map pool full\n"); return false; }

    Blk& b = g_blk[t];
    b.smp = smp;
    b.adpcm = adpcm;
    b.gc_base = dst;
    b.gc_size = UseAramSize[t];

    // KOS snd_mem_available() reports the largest block whether or not it is
    // in use, so fit is probed with a real allocation that keeps kReserveBytes
    // free (other AICA users: streams, movie audio), stepping the rate cap down.
    static const u16 caps[] = { 32000, 22050, 16000, 11025, 8000 };
    u32 total = 0, cap = 0;
    for (u32 c = 0; c < 5 && !b.aica; c++) {
        if (caps[c] > pref_cap(t)) continue;
        total = 0;
        for (u32 i = 0; i < n; i++) total += sample_bytes(b.smp[i], sample_shift(b.smp[i], caps[c]));
        cap = caps[c];
        u32 probe = snd_mem_malloc(total + kReserveBytes);
        if (!probe) continue;
        snd_mem_free(probe);
        b.aica = snd_mem_malloc(total);
    }
    if (!b.aica) {
        re4dc_log("aica: blk %d (%u GC bytes) does not fit: needs %u at %u Hz, %u AICA bytes in use\n", t,
                  (unsigned) b.gc_size, (unsigned) total, (unsigned) cap, (unsigned) g_aicaUsed);
        ++S.blocks_skipped;
        memset(&b, 0, sizeof(b));
        return false;
    }
    b.aica_size = total;
    g_aicaUsed += (total + 31) & ~31u;
    b.rate_cap = (u16) cap;
    blk_map(b, n, cap);
    b.valid = 1;
    ++S.blocks;
    ++S.blocks_runtime;

    // conversion order: by offset (the ARAM image is written in order)
    Conv& c = g_conv;
    c.blk = t;
    c.prebuilt = 0;
    c.n = (u16) n;
    c.cur = 0;
    for (u32 i = 0; i < n; i++) {
        u32 j = i;
        while (j > 0 && b.smp[c.order[j - 1]].offset > b.smp[i].offset) { c.order[j] = c.order[j - 1]; --j; }
        c.order[j] = (u16) i;
    }
    c.in_done = 0;
    c.out_bytes = 0;
    c.stage_len = 0;
    c.nib_have = 0;
    re4dc_log("aica: blk %d gc=%06x+%u -> aica=%06x %u bytes, %u samples, cap %u Hz (runtime conversion)\n", t, (unsigned) dst,
              (unsigned) b.gc_size, (unsigned) b.aica, (unsigned) total, (unsigned) n, (unsigned) cap);
    return true;
}

// Yamaha (AICA) 4-bit ADPCM encoder; identical recurrence to the decoder.
inline u32 enc_nibble(s32 x, s32& pred, s32& step)
{
    static const u16 kScale[8] = { 230, 230, 230, 230, 307, 409, 512, 614 };
    s32 d = x - pred;
    u32 neg = d < 0;
    u32 t = (u32) (neg ? -d : d) << 2;
    u32 q;
    u32 s = (u32) step;
    if (t >= s << 3) q = 7;
    else {
        q = 0;
        if (t >= s << 2) { q = 4; t -= s << 2; }
        if (t >= s << 1) { q += 2; t -= s << 1; }
        if (t >= s) q += 1;
    }
    s32 delta = (s32) ((s * (2 * q + 1)) >> 3);
    pred += neg ? -delta : delta;
    if (pred > 32767) pred = 32767;
    if (pred < -32768) pred = -32768;
    step = (step * kScale[q]) >> 8;
    if (step < 127) step = 127;
    if (step > 24576) step = 24576;
    return q | (neg << 3);
}

void stage_flush(const Blk& b, const MapEnt& e, bool final)
{
    Conv& c = g_conv;
    if (final && c.nib_have) { c.stage[c.stage_len++] = c.nib; c.nib_have = 0; }
    u32 n = final ? (c.stage_len + 3) & ~3u : c.stage_len & ~3u;
    if (n) {
        for (u32 i = c.stage_len; i < n; i++) c.stage[i] = 0;
        u32 dst = (e.aica & 0xFFFFFF) + c.out_bytes;
        if (c.out_bytes + n <= sample_bytes(b.smp[&e - &g_map[b.first]], e.aica >> 24 & 3))
            spu_memload(dst, c.stage, n);
        c.out_bytes += n;
        u32 rest = c.stage_len > n ? c.stage_len - n : 0;
        memmove(c.stage, c.stage + n, rest);
        c.stage_len = rest;
        S.conv_bytes_out += n;
    }
}

void emit(s32 x)
{
    Conv& c = g_conv;
    u32 q = enc_nibble(x, c.pred, c.step);
    if (!c.nib_have) { c.nib = (u8) q; c.nib_have = 1; }
    else { c.stage[c.stage_len++] = (u8) (c.nib | (q << 4)); c.nib_have = 0; }
}

// Converts the frames of the open samples that lie in GC block bytes [lo, hi).
void conv_chunk(const u8* src, u32 lo, u32 hi)
{
    Conv& c = g_conv;
    const Blk& b = g_blk[c.blk];
    while (c.cur < c.n) {
        u32 si = c.order[c.cur];
        const WTSAMPLE& s = b.smp[si];
        const MapEnt& e = g_map[b.first + si];
        u32 sb = s.offset / 2;
        u32 frames = (s.length + 13) / 14;
        u32 se = sb + frames * 8;
        if (sb >= hi) return;
        if (c.in_done == 0 && c.out_bytes == 0 && c.stage_len == 0 && !c.nib_have) {
            const WTADPCM& a = b.adpcm[s.adpcmIndex];
            c.h1 = (s16) a.yn1;
            c.h2 = (s16) a.yn2;
            c.pred = 0;
            c.step = 127;
            c.acc = 0;
            c.acc_n = 0;
        }
        u32 sh = e.aica >> 24 & 3;
        const WTADPCM& a = b.adpcm[s.adpcmIndex];
        u32 f0 = sb + ((c.in_done / 14) * 8);
        for (u32 f = f0; f < se && f + 8 <= hi; f += 8) {
            if (f < lo) continue;
            const u8* p = src + (f - lo);
            u32 ps = p[0];
            s32 scale = 1 << (ps & 0xF);
            u32 idx = (ps >> 4) & 7;
            s32 c1 = a.a[idx][0], c2 = a.a[idx][1];
            for (u32 k = 0; k < 14 && c.in_done < s.length; k++) {
                u32 byte = p[1 + (k >> 1)];
                s32 nib = (k & 1) ? (byte & 0xF) : (byte >> 4);
                if (nib >= 8) nib -= 16;
                s32 v = (((nib * scale) << 11) + 1024 + c1 * c.h1 + c2 * c.h2) >> 11;
                if (v > 32767) v = 32767;
                if (v < -32768) v = -32768;
                c.h2 = c.h1;
                c.h1 = v;
                ++c.in_done;
                c.acc += v;
                if (++c.acc_n == (1u << sh)) { emit(c.acc >> sh); c.acc = 0; c.acc_n = 0; }
            }
            ++S.conv_samples;
            if (c.stage_len >= 1024) stage_flush(b, e, false);
        }
        if (c.in_done >= s.length || se <= hi) {
            if (c.acc_n) emit(c.acc / (s32) c.acc_n);
            stage_flush(b, e, true);
            ++c.cur;
            c.in_done = 0; c.out_bytes = 0; c.stage_len = 0; c.nib_have = 0; c.acc = 0; c.acc_n = 0;
            continue;
        }
        stage_flush(b, e, false);
        return;   // sample continues in the next piece
    }
}

// Finds the block and map entry of a GC nibble address (the sample's first
// sample, i.e. frame header + 2).
bool map_lookup(u32 nib, int& t, const MapEnt*& ent)
{
    for (int i = 0; i < 14; i++) {
        const Blk& b = g_blk[i];
        if (!b.valid) continue;
        if (nib < b.gc_base * 2 || nib >= (b.gc_base + b.gc_size) * 2) continue;
        u32 rel = nib - b.gc_base * 2;
        for (u32 k = 0; k < b.count; k++) {
            const MapEnt& e = g_map[b.first + k];
            u32 end = e.gc_nib + (e.len + 13) / 14 * 16;
            if (rel >= e.gc_nib && rel < end) { t = i; ent = &e; return true; }
        }
        return false;
    }
    return false;
}
// GC sample index of nibble `nib` inside a sample starting at nibble `start` (frame header).
inline u32 nib_to_sample(u32 nib, u32 start)
{
    u32 r = nib - start;
    u32 in = r & 15;
    return (r >> 4) * 14 + (in >= 2 ? in - 2 : 0);
}

// ---------------------------------------------------------------------------
// AICA channel programming (inside one G2 lock).
void ch_keyoff(RegWriter& w, s8 ch, u32 play_cont)
{
    w.w(ch, 0x00, (play_cont & ~0x4000u) | 0x8000u);
}
// pcms 2: ADPCM (the loop restores the decoder state saved at LSA); 3: ADPCM long
// stream (the state runs on across the loop: a ring buffer).
void ch_start(RegWriter& w, s8 ch, u32 aica, u32 len, u32 loop, u32 lsa, u16 freq, u16 tl, u16 pan,
              u32 env_ar, u32 env_d1r, u32 env_dl, u32 env_rr, u32& play_cont, u32 pcms = 2)
{
    if (len > 65535) len = 65535;
    if (len < 1) len = 1;
    if (lsa >= len) lsa = 0;
    play_cont = (pcms << 7) | ((aica >> 16) & 0x7F) | (loop ? 0x200u : 0);
    ch_keyoff(w, ch, play_cont);
    w.w(ch, 0x04, aica & 0xFFFF);
    w.w(ch, 0x08, loop ? lsa : 0);
    w.w(ch, 0x0C, len);
    w.w(ch, 0x10, (env_d1r << 6) | env_ar);            // D2R 0
    w.w(ch, 0x14, (0xFu << 10) | (env_dl << 5) | env_rr);
    w.w(ch, 0x18, freq);
    w.w(ch, 0x1C, 0);                                   // LFO off
    w.w(ch, 0x20, 0);                                   // no DSP send
    w.w(ch, 0x24, (0xFu << 8) | pan);
    w.w(ch, 0x28, ((u32) tl << 8) | 0x24);              // LPOFF, Q 4
    w.w(ch, 0x00, play_cont | 0xC000u);                 // key on
    ++S.keyons;
}

s8 chn_alloc()
{
    if (g_chUsed >= kMaxChannels) return -1;
    int ch = snd_sfx_chn_alloc();
    if (ch >= 0) ++g_chUsed;
    return (s8) ch;
}
void chn_free(s8 ch)
{
    if (ch < 0) return;
    snd_sfx_chn_free(ch);
    --g_chUsed;
}

// ---------------------------------------------------------------------------
// SYN: minimal GM synth on AICA channels. Levels are cached per channel and
// per note so a flush only recomputes what a MIDI event or a fade changed.
struct Note {
    void* synth;
    u8 used, ch_midi, key, released;
    s8 ch;                     // AICA channel
    u8 dirty;                  // 1 start, 8 key off
    u8 loop, ar, d1r, dl, rr, pad;
    u32 born_ms, rel_ms, life_ms;
    u32 aica, len, lsa;
    s32 lvl10;                 // region attenuation + velocity (0.1 dB)
    f32 base_hz;               // sample rate * 2^(note cents) / decimation
    u32 play_cont;
    u16 sent_tl, sent_freq;
    u16 seen_gen;
};
const int kNotes = 48;
Note g_notes[kNotes];
u32 g_nowMs;

struct SynCh {
    u8 prog, vol, exp, pan, rpn_lsb, rpn_msb, bend_range, pad;
    s16 bend;
    s16 db10;                  // CC7 + CC11 (0.1 dB)
    f32 bend_mul;              // 2^(bend cents / 1200)
};
struct Synth {
    u32 magic;
    const u8* wt;
    u32 aram;
    int blk;
    s32 master10;
    u16 gen;                   // bumped on master / channel changes
    u16 ninst;
    SynCh ch[16];
};
const u32 kSynMagic = 0x53594E41;  // "SYNA"

s32 db_curve(u32 v)  // GM 40 log10(v / 127) in 0.1 dB
{
    if (v == 0) return -960;
    return (s32) (400.0f * log10f((f32) v / 127.0f));
}
void ch_update(Synth* s, SynCh& c)
{
    c.db10 = (s16) (db_curve(c.vol) + db_curve(c.exp));
    c.bend_mul = exp2f((f32) c.bend / 8192.0f * (f32) c.bend_range / 12.0f);
    ++s->gen;
}

int synth_block(const Synth* s)
{
    for (int i = 0; i < 14; i++)
        if (g_blk[i].valid && g_blk[i].gc_base == s->aram) return i;
    return -1;
}

u16 note_tl(const Note& n, const Synth* s)
{
    if (re4dc_audio_solo == 2) return 255;
    return tl_from_db10(s->master10 + n.lvl10 + s->ch[n.ch_midi].db10);
}
u16 note_freq(const Note& n, const Synth* s)
{
    return aica_freq_reg((u32) (n.base_hz * s->ch[n.ch_midi].bend_mul));
}

// DLS timecents (x 65536) to milliseconds.
f32 tc_ms(s32 tc)
{
    if (tc == (s32) 0x80000000) return 0;
    return 1000.0f * exp2f((f32) tc / (1200.0f * 65536.0f));
}

void note_on(Synth* s, u32 chm, u32 key, u32 vel)
{
    const u8* wt = s->wt;
    const SndWtHdr* h = (const SndWtHdr*) wt;
    const SynCh& c = s->ch[chm];
    // SYN wavetable header: [0] percussive instrument, [1] melodic instruments
    const u16* inst;
    if (chm == 9) inst = (const u16*) (wt + h->x0);
    else {
        if (c.prog >= s->ninst) return;
        inst = (const u16*) (wt + h->inst_ofs) + c.prog * 128;
    }
    u16 ri = inst[key & 127];
    if (ri == 0xFFFF) return;
    const WTREGION& r = ((const WTREGION*) (wt + h->rgn_ofs))[ri];
    const WTART& art = ((const WTART*) (wt + h->art_ofs))[r.articulationIndex];
    int t = s->blk >= 0 ? s->blk : synth_block(s);
    if (t < 0) {
        ++S.se_unmapped;
#if defined(RE4DC_AICA_WEP_LOG) && RE4DC_AICA_WEP_LOG
        re4dc_log("aica: t=%u wep-log note UNMAPPED key=%u (silent)\n", (unsigned) g_nowMs, (unsigned) key);
#endif
        return;
    }
    s->blk = t;
#if defined(RE4DC_AICA_WEP_LOG) && RE4DC_AICA_WEP_LOG
    if (t == 2)
        re4dc_log("aica: t=%u wep-log note blk=2 key=%u sample=%u cap=%u Hz\n", (unsigned) g_nowMs, (unsigned) key,
                  (unsigned) r.sampleIndex, (unsigned) g_blk[t].rate_cap);
#endif
    const Blk& b = g_blk[t];
    if (r.sampleIndex >= b.count) return;
    const MapEnt& e = g_map[b.first + r.sampleIndex];
    const WTSAMPLE& smp = b.smp[r.sampleIndex];
    u32 sh = e.aica >> 24 & 3;

    // a free note slot; else steal the oldest released one; else the oldest
    int pick = -1;
    for (int i = 0; i < kNotes; i++) if (!g_notes[i].used) { pick = i; break; }
    if (pick < 0) {
        u32 oldest = 0xFFFFFFFF;
        for (int pass = 0; pass < 2 && pick < 0; pass++)
            for (int i = 0; i < kNotes; i++)
                if ((pass || g_notes[i].released) && g_notes[i].born_ms < oldest) { oldest = g_notes[i].born_ms; pick = i; }
        ++S.note_steal;
    }
    Note& n = g_notes[pick];
    s8 keep = n.used ? n.ch : -1;
    memset(&n, 0, sizeof(n));
    n.ch = keep >= 0 ? keep : chn_alloc();
    if (n.ch < 0) { ++S.note_steal; return; }
    n.used = 1;
    n.synth = s;
    n.ch_midi = (u8) chm;
    n.key = (u8) key;
    n.born_ms = g_nowMs;
    n.aica = e.aica & 0xFFFFFF;
    n.len = (smp.length + (1u << sh) - 1) >> sh;
    n.loop = r.loopLength != 0;
    n.lsa = r.loopStart >> sh;
    if (n.loop) n.len = (r.loopStart + r.loopLength) >> sh;
    n.lvl10 = r.attn / 65536 + db_curve(vel);
    f32 cents = (f32) ((s32) key - (s32) r.unityNote) * 100.0f + r.fineTune;
    n.base_hz = (f32) smp.sampleRate * exp2f(cents / 1200.0f) / (f32) (1u << sh);
    n.life_ms = n.loop ? 0xFFFFFFFF : (u32) ((f32) n.len * 1000.0f / (n.base_hz * c.bend_mul + 1.0f)) + 50;
    // envelope: eg1Sustain is an attenuation (0.1 dB x 65536), times are timecents
    n.ar = (u8) rate_for_ms(kArMs, tc_ms(art.eg1Attack));
    f32 sus_db = (f32) art.eg1Sustain / 655360.0f;
    if (sus_db > 0) sus_db = 0;
    u32 dl = (u32) (-sus_db / 3.0f);
    n.dl = (u8) (dl > 31 ? 31 : dl);
    n.d1r = (u8) (n.dl == 0 ? 0 : rate_for_ms(kDrMs, tc_ms(art.eg1Decay)));
    n.rr = (u8) rate_for_ms(kDrMs, tc_ms(art.eg1Release));
    if (n.rr < 8) n.rr = 8;
    n.dirty = 1;
    ++S.note_on;
    if (S.note_on <= 80)
        re4dc_log("aica: t=%u note ch=%u prog=%u key=%u vel=%u db=%d hz=%u ar=%u dl=%u d1r=%u rr=%u loop=%u aica_ch=%d\n",
                  (unsigned) g_nowMs, (unsigned) chm, (unsigned) c.prog, (unsigned) key, (unsigned) vel,
                  (int) (s->master10 + n.lvl10 + c.db10) / 10, (unsigned) n.base_hz, n.ar, n.dl, n.d1r, n.rr,
                  (unsigned) n.loop, n.ch);
}

void note_release(Note& n)
{
    n.released = 1;
    n.rel_ms = g_nowMs;
    n.dirty |= 8;
}

void note_off(Synth* s, u32 chm, u32 key)
{
    for (int i = 0; i < kNotes; i++) {
        Note& n = g_notes[i];
        if (n.used && !n.released && n.synth == s && n.ch_midi == chm && n.key == key) {
            note_release(n);
            ++S.note_off;
        }
    }
}

void synth_all_off(Synth* s, bool hard)
{
    for (int i = 0; i < kNotes; i++) {
        Note& n = g_notes[i];
        if (n.used && n.synth == s) {
            if (!n.released) note_release(n);
            if (hard) n.synth = nullptr;
        }
    }
}

Synth* as_synth(void* p)
{
    Synth* s = (Synth*) p;
    return s->magic == kSynMagic ? s : nullptr;
}

// A block is being replaced (room change, BGM reload, continue): voices and
// notes still sounding from its AICA copy are keyed off now, before the new
// data is written there, and reported ended to the driver.
void blk_cut(int t)
{
    g2_lock_scoped();
    RegWriter w;
    u32 cut = 0;
    for (int i = 0; i < 64; i++) {
        AXVPBView& p = g_vpb[i];
        VoiceState& v = p.vs;
        if (!v.used || v.ch < 0 || !v.mapped || v.blk != t) continue;
        ch_keyoff(w, v.ch, v.play_cont);
        v.running = 0;
        v.mapped = 0;
        v.dirty = 8;          // flush frees the channel
        p.state = 0;
        ++cut;
    }
    for (int i = 0; i < kNotes; i++) {
        Note& n = g_notes[i];
        Synth* s = n.used && n.synth ? as_synth(n.synth) : nullptr;
        if (!s || s->blk != t) continue;
        ch_keyoff(w, n.ch, n.play_cont);
        n.released = 1;
        n.rel_ms = g_nowMs - 1000;   // reclaimed at the next flush
        n.dirty = 0;
        ++cut;
    }
    S.regwrites += w.n;
    if (cut) re4dc_log("aica: blk %d replaced, %u sounding voices cut\n", t, (unsigned) cut);
}

// ---------------------------------------------------------------------------
// Disc streams. The stream player acquires its AX voices with cb_str_voice_drop
// (marked strm = 1); the reader thread matches an open stream work to an
// aica_str.dat entry (claim: strm = 2) and prefills the ring; the flush keys the
// ring channels on when the driver starts voice L, follows the voices' MIX level
// and keys off when the driver stops (fresh prefill) or frees them (closed).
// One ring: while a stream plays, another one stays silent.
struct StrEnt { u32 sbb_ofs, rate, flags, nch, a_samples, b_samples, a_ofs, b_ofs; };  // flags: 1 loops | blk << 8 | no << 16
const u32 kStrMagic = 0x31534941;   // "AIS1"
#ifndef RE4DC_STR_ENT_MAX
#define RE4DC_STR_ENT_MAX 16
#endif
// ROUTE_CH21 discs carry 17 streams (r118 added 0:23; aica_banks.py --streams ch21 + 0:23): 16 refused the whole file
// ("header invalid", every disc stream silent). The 2 KB header holds up to 63 entries.
const int kStrEntMax = RE4DC_STR_ENT_MAX;
StrEnt g_strEnt[kStrEntMax];
u32 g_strEntN;

enum { kStrIdle, kStrPrep, kStrReady, kStrPlaying };
struct Stream {
    volatile u8 state;           // kStr*; prep: the reader fills the ring from the start
    volatile u8 want;            // the driver's voice L is running
    volatile u8 dead;            // the driver freed the voices
    volatile u8 mute;            // a one-shot stream played out
    u8 nch, ended;
    s8 ch[2];
    volatile u32 gen;            // bumped on every (re)start; the reader drops older fills
    int slot;                    // Snd_str_work index
    const StrEnt* e;
    AXVPBView* v[2];
    u32 region, pos;             // reader cursor: 0 intro / 1 loop body, bytes per channel
    u32 filled, end_half;        // ring halves written; half holding a one-shot's end
    u64 t0, rate_q10;            // key-on time (us); AICA play rate (Hz x 1024)
    u32 play_cont[2];
    u16 sent_tl[2];
};
Stream g_str;   // channels / voices are set at the claim (state idle until then)

inline u32 str_key(const StrEnt& e) { return e.flags >> 8; }   // blk | no << 8

u16 str_tl(int c)
{
    if (re4dc_audio_solo == 2 || g_str.mute) return 255;
    const MixState& m = g_str.v[c]->vs.mix;
    return tl_from_db10(m.in + m.fader);
}

void str_keyoff(RegWriter& w)
{
    for (int c = 0; c < 2; c++) {
        if (g_str.ch[c] < 0) continue;
        ch_keyoff(w, g_str.ch[c], g_str.play_cont[c]);
        chn_free(g_str.ch[c]);
        g_str.ch[c] = -1;
    }
}

void str_flush(RegWriter& w)
{
    Stream& s = g_str;
    if (s.state == kStrIdle) return;
    u32 key = str_key(*s.e);
    if (s.dead) {
        str_keyoff(w);
        s.state = kStrIdle;
        s.dead = 0;
        s.want = 0;
        re4dc_log("aica: t=%u stream %u:%u closed\n", (unsigned) g_nowMs, (unsigned) (key & 255), (unsigned) (key >> 8));
        return;
    }
    if (s.state == kStrPlaying && !s.want) {
        str_keyoff(w);
        s.gen = s.gen + 1;
        s.state = kStrPrep;
        re4dc_log("aica: t=%u stream %u:%u stopped\n", (unsigned) g_nowMs, (unsigned) (key & 255), (unsigned) (key >> 8));
        return;
    }
    if (s.state == kStrReady && s.want) {
        for (int c = 0; c < s.nch; c++) {
            if (s.ch[c] < 0) s.ch[c] = chn_alloc();
            if (s.ch[c] < 0) { str_keyoff(w); return; }   // no channel now: retry at the next flush
        }
        u16 freq = aica_freq_reg(s.e->rate);
        int oct = (freq >> 11) & 15;
        if (oct & 8) oct -= 16;
        u64 r = 44100ull * (1024 + (freq & 1023));
        s.rate_q10 = oct >= 0 ? r << oct : r >> -oct;
        for (int c = 0; c < s.nch; c++) {
            u16 pan = s.nch == 1 ? dipan(s.v[0]->vs.mix.pan) : dipan(c ? 127 : 0);
            s.sent_tl[c] = str_tl(c);
            ch_start(w, s.ch[c], g_strRing + c * kStrChBytes, 2 * kStrHalfSamples, 1, 0, freq, s.sent_tl[c], pan,
                     31, 0, 0, 28, s.play_cont[c], 3);
        }
        s.t0 = timer_us_gettime64();
        s.state = kStrPlaying;
        ++S.str_starts;
        re4dc_log("aica: t=%u stream %u:%u start ch=%d/%d tl=%u rate=%u.%03u Hz\n", (unsigned) g_nowMs, (unsigned) (key & 255),
                  (unsigned) (key >> 8), s.ch[0], s.nch > 1 ? s.ch[1] : -1, (unsigned) s.sent_tl[0],
                  (unsigned) (s.rate_q10 >> 10), (unsigned) ((s.rate_q10 & 1023) * 1000 >> 10));
        return;
    }
    if (s.state == kStrPlaying) {
        for (int c = 0; c < s.nch; c++) {
            u16 tl = str_tl(c);
            if (tl != s.sent_tl[c]) { w.w(s.ch[c], 0x28, ((u32) tl << 8) | 0x24); s.sent_tl[c] = tl; }
        }
    }
}

// ---------------------------------------------------------------------------
void flush()
{
    g2_lock_scoped();
    RegWriter w;
    // AX voices
    for (int i = 0; i < 64; i++) {
        VoiceState& v = g_vpb[i].vs;
        if (!v.used || v.ch < 0) continue;
        if (v.dirty & 8) {
            ch_keyoff(w, v.ch, v.play_cont);
            chn_free(v.ch);
            v.ch = -1;
            v.dirty = 0;
            if (v.freed) v.used = 0;
            continue;
        }
        if (!v.dirty) continue;
        u16 tl = re4dc_audio_solo == 1 ? 255 : tl_from_db10(v.mix.in + v.mix.fader);
        u16 pan = dipan(v.mix.pan);
        u16 freq = (v.dirty & 5) ? aica_freq_reg((u32) (v.ratio * 32000.0f) >> v.shift) : v.sent_freq;
        if (v.dirty & 1) {
            ch_start(w, v.ch, v.aica, v.len, v.loop, v.loop_start, freq, tl, pan, 31, 0, 0, 31, v.play_cont);
            v.sent_tl = tl; v.sent_pan = pan; v.sent_freq = freq;
        } else {
            if (tl != v.sent_tl) { w.w(v.ch, 0x28, ((u32) tl << 8) | 0x24); v.sent_tl = tl; }
            if (pan != v.sent_pan) { w.w(v.ch, 0x24, (0xFu << 8) | pan); v.sent_pan = pan; }
            if (freq != v.sent_freq) { w.w(v.ch, 0x18, freq); v.sent_freq = freq; }
        }
        v.dirty = 0;
    }
    // SYN notes
    for (int i = 0; i < kNotes; i++) {
        Note& n = g_notes[i];
        if (!n.used) continue;
        Synth* s = n.synth ? as_synth(n.synth) : nullptr;
        if ((n.dirty & 1) && s) {
            n.sent_tl = note_tl(n, s);
            n.sent_freq = note_freq(n, s);
            n.seen_gen = s->gen;
            ch_start(w, n.ch, n.aica, n.len, n.loop, n.lsa, n.sent_freq, n.sent_tl,
                     dipan(n.ch_midi == 9 ? 64 : s->ch[n.ch_midi].pan), n.ar, n.d1r, n.dl, n.rr, n.play_cont);
            n.dirty &= ~1;
            if (n.released) n.dirty |= 8;   // released before it sounded
        }
        if (n.dirty & 1) { n.used = 0; chn_free(n.ch); continue; }  // synth gone before start
        if (n.dirty & 8) { ch_keyoff(w, n.ch, n.play_cont); n.dirty &= ~8; }
        if (s && !n.released && n.seen_gen != s->gen) {
            n.seen_gen = s->gen;
            u16 tl = note_tl(n, s);
            if (tl != n.sent_tl) { w.w(n.ch, 0x28, ((u32) tl << 8) | 0x24); n.sent_tl = tl; }
            u16 f = note_freq(n, s);
            if (f != n.sent_freq) { w.w(n.ch, 0x18, f); n.sent_freq = f; }
        }
        // reclaim: released notes after ~0.6 s of release, one-shots after their length
        bool done = n.released ? g_nowMs - n.rel_ms > 600 : g_nowMs - n.born_ms > n.life_ms;
        if (done || !s) {
            if (!n.released) ch_keyoff(w, n.ch, n.play_cont);
            chn_free(n.ch);
            n.used = 0;
        }
    }
    str_flush(w);
    S.regwrites += w.n;
}

}  // namespace

// ---------------------------------------------------------------------------
// The driver's audio frame. On the GameCube it is the 5 ms AI DMA interrupt;
// here a KOS thread (priority 3, above every game thread) wakes every 5 ms,
// runs the frames that wall time owes (normally one), advances the one-shot end
// estimate and flushes register writes. Game code guards its driver calls with
// OSDisableInterrupts (irq_disable), so the thread cannot run inside them,
// exactly as the interrupt could not. Music timing is therefore independent
// of the game's frame rate and of load hitches.
namespace {

mutex_t g_lock = MUTEX_INITIALIZER;   // blocks (map) vs the audio step
u8 g_thread_stack[12 * 1024] __attribute__((aligned(8)));
kthread_t* g_thread;

// A stream player voice ran out (re4dc_strm_advance): the driver sees it stopped.
void strm_stop(AXVPBView& p)
{
    p.state = 0;
    p.vs.running = 0;
    if (p.vs.strm == 2 && &p == g_str.v[0]) g_str.want = 0;
}

void audio_step()
{
    u64 now = timer_us_gettime64();
    g_nowMs = (u32) (now / 1000);
    if (!g_lastTickUs) { g_lastTickUs = now - 5000; g_lastFrameUs = now; }
    u32 ticks = (u32) ((now - g_lastTickUs) / 5000);
    if (ticks == 0) return;
    if ((int) ticks > re4dc_audio_max_ticks) { ticks = re4dc_audio_max_ticks; g_lastTickUs = now; }
    else g_lastTickUs += ticks * 5000ull;
    mutex_lock(&g_lock);
    re4dc_audio_pend_run();
    for (u32 i = 0; i < ticks; i++) g_axCallback();
    u64 t1 = timer_us_gettime64();

    f32 dt = (f32) (now - g_lastFrameUs) * 1e-6f;
    g_lastFrameUs = now;
    u32 active = 0;
    for (int i = 0; i < 64; i++) {
        AXVPBView& p = g_vpb[i];
        VoiceState& v = p.vs;
        if (!v.used || !v.running) continue;
        ++active;
        if (v.strm) {   // silent: position only (the AICA ring plays the stream)
            if (re4dc_strm_advance(&p.addr.loopFlag, dt * v.ratio * 32000.0f, &v.pos)) strm_stop(p);
            continue;
        }
        v.pos += dt * v.ratio * 32000.0f;
        if (!v.loop && v.pos >= (f32) v.gc_len) {
            p.state = 0;
            v.running = 0;
            if (v.ch >= 0) v.dirty |= 8;
        }
        u32 sp = (u32) v.pos;
        if (v.loop && v.gc_len > v.gc_loop && sp >= v.gc_len) sp = v.gc_loop + (sp - v.gc_loop) % (v.gc_len - v.gc_loop);
        if (!v.mapped) continue;
        sp += v.s0;
        u32 nib = v.gc_start_nib + (sp / 14) * 16 + 2 + sp % 14;
        p.addr.currentAddressHi = (u16) (nib >> 16);
        p.addr.currentAddressLo = (u16) nib;
    }
    u32 notes = 0;
    for (int i = 0; i < kNotes; i++) notes += g_notes[i].used;
    flush();
    mutex_unlock(&g_lock);
    u64 t2 = timer_us_gettime64();

    ++S.frames;
    S.ticks += ticks;
    u32 d = (u32) (t1 - now), f = (u32) (t2 - t1);
    S.drv_us += d; S.flush_us += f;
    if (d > S.max_drv_us) S.max_drv_us = d;
    if (f > S.max_flush_us) S.max_flush_us = f;
    S.active_voices = active; S.active_notes = notes;
    if (active > S.peak_voices) S.peak_voices = active;
    if (notes > S.peak_notes) S.peak_notes = notes;
    if ((S.frames % 2000) == 0) {   // every ~10 s
        S.aica_free = g_aicaUsed;
        u64 wall = now - g_threadStartUs;
        // two lines: the log truncates long lines
        re4dc_log("aica: str wall=%ums starts=%u state=%u under=%u reads=%u %uKB io=%uus max %uus g2=%uus gc_skip=%u/%u\n",
                  (unsigned) (wall / 1000), (unsigned) S.str_starts, (unsigned) g_str.state, (unsigned) S.str_underruns,
                  (unsigned) S.str_reads, (unsigned) (S.str_read_bytes >> 10), (unsigned) S.str_io_us,
                  (unsigned) S.str_io_max_us, (unsigned) S.str_load_us, (unsigned) re4dc_strm_reads_skipped,
                  (unsigned) re4dc_strm_dmas);
        re4dc_log("aica: steps=%u ticks=%u wall=%ums drv=%uus flush=%uus total (%u+%u us per 33ms) max %u/%u\n",
                  (unsigned) S.frames, (unsigned) S.ticks, (unsigned) (wall / 1000), (unsigned) S.drv_us, (unsigned) S.flush_us,
                  (unsigned) ((u64) S.drv_us * 33333 / (wall ? wall : 1)), (unsigned) ((u64) S.flush_us * 33333 / (wall ? wall : 1)),
                  (unsigned) S.max_drv_us, (unsigned) S.max_flush_us);
        re4dc_log("aica: se=%u unm=%u notes on=%u off=%u steal=%u keyon=%u regw=%u act=%u/%u peak=%u/%u used=%u conv=%uus blocks pre/rt=%u/%u copy=%u ch=%u\n",
                  (unsigned) S.se_starts, (unsigned) S.se_unmapped,
                  (unsigned) S.note_on, (unsigned) S.note_off, (unsigned) S.note_steal, (unsigned) S.keyons, (unsigned) S.regwrites,
                  (unsigned) active, (unsigned) notes, (unsigned) S.peak_voices, (unsigned) S.peak_notes, (unsigned) S.aica_free,
                  (unsigned) S.conv_us, (unsigned) S.blocks_prebuilt, (unsigned) S.blocks_runtime,
                  (unsigned) S.copy_bytes, (unsigned) g_chUsed);
    }
}

void* audio_main(void*)
{
    for (;;) {
        thd_sleep(5);
        if (g_axCallback) audio_step();
    }
    return nullptr;
}

// ---------------------------------------------------------------------------
// Stream reader: a KOS thread (priority 4, above the game) that sleeps 10 ms at a
// time. It claims streams, prefills the ring and, while one plays, rewrites each
// ring half once the play position (time x the AICA rate) has left it: one
// 12 KB-per-channel refill per 0.77 s at 32 kHz; the CPU cost is the G2 copy.
// The read buffer is deliberately NOT 32-byte aligned: KOS iso9660 turns a
// sector-aligned read into a 32-byte aligned buffer into a CD stream over the
// rest of the file (cdrom_stream_start), and a stream kept open by this thread
// while game threads open and read other files made every later fs_open fail
// (b1 capture). Unaligned, KOS reads through its sector cache instead.
u8 g_strStack[6 * 1024] __attribute__((aligned(8), unused));   // unused without AICA_STREAMS
u8 g_strCacheRaw[8 * 1024 + 32] __attribute__((aligned(32)));
u8* const g_strCache = g_strCacheRaw + 4;   // 4-byte aligned for the G2 32-bit copy
const u32 kStrCacheBytes = 8 * 1024;
u32 g_strCacheOfs = 0xFFFFFFFFu, g_strCacheLen;
file_t g_strFile = -1;
const u32* g_strMissShd;

bool str_index_load()
{
    g_strFile = fs_open("/cd/bgm/aica_str.dat", O_RDONLY);
    if (g_strFile < 0) { re4dc_log("aica: no bgm/aica_str.dat, disc streams stay silent\n"); return false; }
    const u32* h = (const u32*) g_strCache;
    if (fs_read(g_strFile, g_strCache, 2048) != 2048 || h[0] != kStrMagic || h[1] > (u32) kStrEntMax) {
        re4dc_log("aica: bgm/aica_str.dat header invalid, disc streams stay silent\n");
        fs_close(g_strFile);
        g_strFile = -1;
        return false;
    }
    g_strEntN = h[1];
    memcpy(g_strEnt, h + 4, g_strEntN * sizeof(StrEnt));
    for (u32 i = 0; i < g_strEntN; i++) {
        const StrEnt& e = g_strEnt[i];
        re4dc_log("aica: stream %u:%u sbb=%06x %u Hz ch=%u intro=%u loop=%u samples\n", (unsigned) (e.flags >> 8 & 255),
                  (unsigned) (e.flags >> 16), (unsigned) e.sbb_ofs, (unsigned) e.rate, (unsigned) e.nch,
                  (unsigned) e.a_samples, (unsigned) e.b_samples);
    }
    return true;
}

AXVPBView* vpb_of(void* p)
{
    uintptr_t a = (uintptr_t) p, b = (uintptr_t) g_vpb;
    if (a < b || a >= b + sizeof(g_vpb) || (a - b) % sizeof(AXVPBView)) return nullptr;
    return (AXVPBView*) p;
}

// An open stream work whose voices are the stream player's, matched to an entry.
void str_scan()
{
    if (g_str.state != kStrIdle || !g_strRing) return;
    for (int i = 0; i < 4; i++) {
        const Re4dcStrWorkView& w = Snd_str_work[i];
        if (!(w.status & 1) || !w.shd) continue;
        u32 nch = (w.flag & 1) ? 2 : 1;
        AXVPBView* vl = vpb_of(w.voiceL);
        AXVPBView* vr = nch == 2 ? vpb_of(w.voiceR) : vl;
        if (!vl || !vr || vl->vs.strm != 1 || vr->vs.strm != 1) continue;
        const StrEnt* e = nullptr;
        for (u32 k = 0; k < g_strEntN && !e; k++) {
            const StrEnt& c = g_strEnt[k];
            if (c.sbb_ofs == w.shd[7] && c.nch == nch && Snd_get_shd_adrs((u16) (c.flags >> 8 & 255), (u16) (c.flags >> 16)) == w.shd)
                e = &c;
        }
        if (!e) {
            if (g_strMissShd != w.shd) {
                g_strMissShd = w.shd;
                re4dc_log("aica: stream sbb=%06x not in aica_str.dat, silent\n", (unsigned) w.shd[7]);
            }
            continue;
        }
        mutex_lock(&g_lock);   // the driver frees voices inside the audio step
        if (Snd_str_work[i].voiceL == (void*) vl && vl->vs.strm == 1 && vr->vs.strm == 1) {
            Stream& s = g_str;
            s.slot = i;
            s.e = e;
            s.nch = (u8) nch;
            s.v[0] = vl;
            s.v[1] = vr;
            s.ch[0] = s.ch[1] = -1;
            s.dead = 0;
            s.want = vl->state != 0;
            vl->vs.strm = vr->vs.strm = 2;
            s.gen = s.gen + 1;
            s.state = kStrPrep;
        }
        mutex_unlock(&g_lock);
        return;
    }
}

// Make the 2 KB-per-channel group at file offset `fofs` resident (reads up to 8 KB, not past `fend`).
bool str_cache(u32 fofs, u32 fend)
{
    u32 grp = g_str.nch * 2048u;
    if (fofs >= g_strCacheOfs && fofs + grp <= g_strCacheOfs + g_strCacheLen) return true;
    u32 len = fend - fofs;
    if (len > kStrCacheBytes) len = kStrCacheBytes / grp * grp;
    u64 t0 = timer_us_gettime64();
    bool ok = fs_seek(g_strFile, fofs, SEEK_SET) == (off_t) fofs && fs_read(g_strFile, g_strCache, len) == (ssize_t) len;
    u32 us = (u32) (timer_us_gettime64() - t0);
    S.str_io_us += us;
    if (us > S.str_io_max_us) S.str_io_max_us = us;
    ++S.str_reads;
    S.str_read_bytes += len;
    if (!ok) {
        g_strCacheOfs = 0xFFFFFFFFu;
        g_strCacheLen = 0;
        re4dc_log("aica: aica_str.dat read failed at %u (+%u)\n", (unsigned) fofs, (unsigned) len);
        return false;
    }
    g_strCacheOfs = fofs;
    g_strCacheLen = len;
    return true;
}

// Ring half `h` (both channels) from the reader cursor: intro, then the loop body again and again.
void str_fill(u32 h, u32 gen)
{
    Stream& s = g_str;
    const StrEnt& e = *s.e;
    u32 dst = h * kStrHalfBytes, need = kStrHalfBytes;
    u64 t0 = timer_us_gettime64();
    u32 io0 = S.str_io_us;
    while (need && s.gen == gen) {
        if (s.ended) {   // one-shot played out: alternating +/- steps hold the level (muted once reached)
            for (u32 c = 0; c < s.nch; c++) spu_memset(g_strRing + c * kStrChBytes + dst, 0x80808080u, need);
            break;
        }
        u32 rbytes = (s.region ? e.b_samples : e.a_samples) / 2;
        if (s.pos >= rbytes) {
            if ((e.flags & 1) && e.b_samples) { s.region = 1; s.pos = 0; continue; }
            s.ended = 1;
            s.end_half = s.filled;
            continue;
        }
        u32 grp = s.nch * 2048u;
        u32 base = s.region ? e.b_ofs : e.a_ofs;
        u32 fend = base + (rbytes + 2047) / 2048 * grp;
        u32 blk = s.pos / 2048, in = s.pos % 2048;
        u32 k = 2048 - in;
        if (k > need) k = need;
        if (k > rbytes - s.pos) k = rbytes - s.pos;
        u32 fofs = base + blk * grp;
        if (!str_cache(fofs, fend)) { s.ended = 1; s.end_half = s.filled; continue; }
        const u8* src = g_strCache + (fofs - g_strCacheOfs) + in;
        for (u32 c = 0; c < s.nch; c++) spu_memload(g_strRing + c * kStrChBytes + dst, (void*) (src + c * 2048), k);
        s.pos += k;
        dst += k;
        need -= k;
    }
    S.str_load_us += (u32) (timer_us_gettime64() - t0) - (S.str_io_us - io0);
}

__attribute__((unused)) void* str_main(void*)
{
    if (!str_index_load()) return nullptr;
    for (;;) {
        thd_sleep(10);
        Stream& s = g_str;
        if (s.state == kStrIdle) str_scan();
        u32 gen = s.gen;
        if (s.state == kStrPrep) {
            s.region = s.pos = 0;
            s.ended = 0;
            s.mute = 0;
            s.end_half = 0xFFFFFFFFu;
            s.filled = 0;
            str_fill(0, gen);
            s.filled = 1;
            str_fill(1, gen);
            mutex_lock(&g_lock);
            if (s.gen == gen && s.state == kStrPrep) {
                s.filled = 2;
                s.state = kStrReady;
                u32 key = str_key(*s.e);
                re4dc_log("aica: t=%u stream %u:%u ready (slot %d, %s)\n", (unsigned) g_nowMs, (unsigned) (key & 255),
                          (unsigned) (key >> 8), s.slot, s.want ? "voice running" : "waiting for play");
            }
            mutex_unlock(&g_lock);
        } else if (s.state == kStrPlaying) {
            u64 el = timer_us_gettime64() - s.t0;
            u32 consumed = (u32) (el * s.rate_q10 / (1024ull * 1000000ull) / kStrHalfSamples);
            if (s.filled < consumed + 1) {
                if (S.str_underruns < 16)
                    re4dc_log("aica: t=%u stream underrun: half %u playing, %u written\n", (unsigned) g_nowMs,
                              (unsigned) consumed, (unsigned) s.filled);
                ++S.str_underruns;
                s.filled = consumed + 1;
            }
            while (s.filled < consumed + 2 && s.gen == gen && s.state == kStrPlaying) {
                str_fill(s.filled & 1, gen);
                ++s.filled;
            }
            if (s.ended && consumed > s.end_half) s.mute = 1;
        }
    }
    return nullptr;
}

void start_thread()
{
    if (g_thread) return;
    kthread_attr_t a{};
    a.stack_size = sizeof(g_thread_stack);
    a.stack_ptr = g_thread_stack;
    a.prio = 3;
    a.label = "re4dc-audio";
    a.create_detached = true;
    g_threadStartUs = timer_us_gettime64();
    g_thread = thd_create_ex(&a, audio_main, nullptr);
    re4dc_log("aica: audio thread tid=%d prio=3 period=5ms\n", g_thread ? (int) g_thread->tid : -1);
#if RE4DC_AICA_STREAMS
    kthread_attr_t r{};
    r.stack_size = sizeof(g_strStack);
    r.stack_ptr = g_strStack;
    r.prio = 4;
    r.label = "re4dc-aica-str";
    r.create_detached = true;
    kthread_t* st = thd_create_ex(&r, str_main, nullptr);
    re4dc_log("aica: stream reader tid=%d prio=4\n", st ? (int) st->tid : -1);
#else
    re4dc_log("aica: disc streams silent (built without AICA_STREAMS=1)\n");
#endif
}

}  // namespace

extern "C" {

// AICA RAM held by the backend (layout + runtime-converted blocks). Movie audio
// computes free AICA RAM as 1900544 - this - its own stream buffers (KOS
// snd_mem_available() reports the largest block, in use or not).
unsigned re4dc_aica_used_bytes(void) { return g_aicaUsed; }

#ifndef RE4DC_AICA_STR_TEST
#define RE4DC_AICA_STR_TEST 0   // evidence only: stream number of block 0 to request in every room
#endif

// Game-frame hook (pad.cpp PADRead): only a fallback when the thread is missing.
// With RE4DC_AICA_STR_TEST=n it also issues the request a floor attribute makes
// (snd.cpp SndStrReq(blk, no, 0x80000003, ...)) 5 s after each room bank load and
// the stop request 75 s later, so an idle capture exercises start, loop and stop.
void re4dc_strm_test_frame(void);   // audio_strm.cpp (RE4DC_STRM_TEST)
void re4dc_audio_frame(void)
{
    if (!g_thread && g_axCallback) audio_step();
    re4dc_strm_test_frame();
#if RE4DC_AICA_STR_TEST
    static u32 room_ms, blocks_seen, phase;
    u32 now = (u32) (timer_us_gettime64() / 1000);
    if (g_blk[5].valid && S.blocks != blocks_seen) { blocks_seen = S.blocks; room_ms = now; phase = 0; }   // FOOT: a game room
    if (!room_ms) return;
    if (phase == 0 && now - room_ms > 5000) {
        phase = 1;
        u32 id = SndStrReq(0, RE4DC_AICA_STR_TEST, (int) 0x80000003, 0, 0, 0.0f);
        re4dc_log("aica: t=%u test: SndStrReq(0, %d, play) id=%u\n", (unsigned) g_nowMs, RE4DC_AICA_STR_TEST, (unsigned) id);
    } else if (phase == 1 && now - room_ms > 80000) {
        phase = 2;
        SndStrReq(0, RE4DC_AICA_STR_TEST, 8, 0, 0, 0.0f);
        re4dc_log("aica: t=%u test: SndStrReq(0, %d, stop)\n", (unsigned) g_nowMs, RE4DC_AICA_STR_TEST);
    }
#endif
}


// ARQ hook (audio_stub.cpp ARQPostRequest): a piece of a sound block's ARAM part.
void re4dc_audio_arq(u32 src, u32 dst, u32 len)
{
    if (!g_init || !len) return;
    u64 t0 = timer_us_gettime64();
    Conv& c = g_conv;
    if (!(c.blk >= 0 && dst == c.next_dst)) {
        c.blk = -1;
        for (int t = 0; t < 14; t++) {
            if (UseAramSize[t] && SndMem.blk_aram[t] == dst) {
                const AicaBankHeader* h = (const AicaBankHeader*) src;
                bool pre = len >= sizeof(AicaBankHeader) && h->magic == kBankMagic;
                mutex_lock(&g_lock);
                bool ok = pre ? blk_begin_prebuilt(t, dst, *h) : blk_begin(t, dst);
                mutex_unlock(&g_lock);
                if (!ok) return;
                break;
            }
        }
        if (c.blk < 0) return;
    }
    const Blk& b = g_blk[c.blk];
    u32 lo = dst - b.gc_base;
    if (c.prebuilt) {
        // image bytes are part bytes [96, 96 + total): copy the overlap
        u32 a0 = lo > sizeof(AicaBankHeader) ? lo : (u32) sizeof(AicaBankHeader);
        u32 a1 = lo + len < sizeof(AicaBankHeader) + c.img_total ? lo + len : (u32) sizeof(AicaBankHeader) + c.img_total;
        if (a1 > a0) {
            spu_memload(b.aica + (a0 - sizeof(AicaBankHeader)), (void*) (src + (a0 - lo)), (a1 - a0 + 3) & ~3u);
            S.copy_bytes += a1 - a0;
        }
    } else {
        conv_chunk((const u8*) src, lo, lo + len);
        S.conv_bytes_in += len;
    }
    c.next_dst = dst + len;
    if (c.next_dst >= b.gc_base + b.gc_size) {
        if (c.prebuilt) re4dc_log("aica: blk %d copied, %u bytes\n", c.blk, (unsigned) c.img_total);
        else re4dc_log("aica: blk %d converted, %u/%u samples\n", c.blk, (unsigned) c.cur, (unsigned) c.n);
#if RE4DC_AICA_VERIFY
        {   // debug: hash of what AICA RAM now holds (compare with tools/aica_banks.py "fnv")
            static u8 rb[1024] __attribute__((aligned(32)));
            u32 h = 0x811C9DC5u;
            for (u32 o = 0; o < b.aica_size; o += sizeof(rb)) {
                u32 k = b.aica_size - o < sizeof(rb) ? b.aica_size - o : (u32) sizeof(rb);
                spu_memread(rb, b.aica + o, (k + 3) & ~3u);
                for (u32 i = 0; i < k; i++) h = (h ^ rb[i]) * 0x01000193u;
            }
            re4dc_log("aica: blk %d image fnv %08x (%u bytes, %u Hz)\n", c.blk, (unsigned) h, (unsigned) b.aica_size,
                      (unsigned) b.rate_cap);
        }
#endif
        c.blk = -1;
    }
    S.conv_us += (u32) (timer_us_gettime64() - t0);
}

void AIInit(u8* stack) { (void) stack; }
void AIReset(void) {}
void AXInitEx(u32 mode) { (void) mode; aica_init(); }
void AXQuit(void) {}
void AXSetMode(u32 mode) { (void) mode; }
void AXSetCompressor(u32 sw) { (void) sw; }
u32 AXGetDspCycles(void) { return 0; }
u32 AXGetMaxDspCycles(void) { return 0; }
AXCallback AXRegisterCallback(AXCallback cb)
{
    AXCallback old = g_axCallback;
    g_axCallback = cb;
    if (cb && g_init) start_thread();
    return old;
}
void AXRegisterAuxACallback(void (*cb)(void*, void*), void* ctx) { (void) cb; (void) ctx; }
void AXRegisterAuxBCallback(void (*cb)(void*, void*), void* ctx) { (void) cb; (void) ctx; }

void* AXAcquireVoice(u32 prio, void (*cb)(void*), u32 user)
{
    (void) prio; (void) user;
    for (int i = 0; i < 64; i++) {
        AXVPBView& p = g_vpb[i];
        if (!p.vs.used) {
            memset(&p, 0, sizeof(p));
            p.vs.used = 1;
            p.vs.ch = -1;
            p.vs.blk = -1;
            p.vs.strm = cb == cb_str_voice_drop;
            return &p;
        }
    }
    return 0;
}
void AXFreeVoice(void* vp)
{
    AXVPBView* p = (AXVPBView*) vp;
    if (!p) return;
    if (p->vs.strm == 2 && (p == g_str.v[0] || p == g_str.v[1])) g_str.dead = 1;   // closed at the next flush
    p->vs.strm = 0;
    if (p->vs.ch >= 0) {
        // released through the next flush; the slot is reused afterwards
        p->vs.dirty |= 8;
        p->vs.running = 0;
        p->state = 0;
        p->vs.freed = 1;
        return;
    }
    p->vs.used = 0;
}

void AXSetVoiceAddr(void* vp, void* a)
{
    AXVPBView* p = (AXVPBView*) vp;
    memcpy(&p->addr, a, sizeof(AXPBADDR));
}
void AXSetVoiceState(void* vp, u16 st)
{
    AXVPBView* p = (AXVPBView*) vp;
    VoiceState& v = p->vs;
    p->state = st;
    // Stream player voices: silent, their address advanced by strm_advance; a claimed
    // voice L starts / stops the AICA ring.
    if (v.strm) {
        if (st && !v.running) v.pos = 0;
        v.running = st != 0;
        if (v.strm == 2 && p == g_str.v[0]) g_str.want = st != 0;
        return;
    }
    if (st == 0) {
        if (v.ch >= 0) v.dirty |= 8;
        v.running = 0;
        return;
    }
    if (v.running) return;
    // start: resolve the sample from the GC addresses
    u32 cur = ((u32) p->addr.currentAddressHi << 16) | p->addr.currentAddressLo;
    u32 end = ((u32) p->addr.endAddressHi << 16) | p->addr.endAddressLo;
    u32 lp = ((u32) p->addr.loopAddressHi << 16) | p->addr.loopAddressLo;
    int t;
    const MapEnt* e;
    v.running = 1;
    v.pos = 0;
    if (!map_lookup(cur, t, e)) {
        v.mapped = 0;
        v.gc_len = 0xFFFFFFFF;
        v.loop = p->addr.loopFlag;
        if (!v.loop) v.gc_len = end > cur ? nib_to_sample(end, cur - 2) : 0;
        ++S.se_unmapped;
#if defined(RE4DC_AICA_WEP_LOG) && RE4DC_AICA_WEP_LOG
        re4dc_log("aica: t=%u wep-log se start UNMAPPED gc_nib=%07x (silent)\n", (unsigned) g_nowMs, (unsigned) cur);
#endif
        return;
    }
    const Blk& b = g_blk[t];
#if defined(RE4DC_AICA_WEP_LOG) && RE4DC_AICA_WEP_LOG
    if (t == 2)
        re4dc_log("aica: t=%u wep-log se start blk=2 sample=%d cap=%u Hz gc_bytes=%u\n", (unsigned) g_nowMs,
                  (int) (e - &g_map[b.first]), (unsigned) b.rate_cap, (unsigned) b.gc_size);
#endif
    u32 start = b.gc_base * 2 + e->gc_nib;
    v.blk = (s8) t;
    v.mapped = 1;
    v.gc_start_nib = start;
    v.shift = e->aica >> 24 & 3;
    v.aica = e->aica & 0xFFFFFF;
    u32 s0 = nib_to_sample(cur, start);
    v.loop = p->addr.loopFlag != 0;
    u32 ls = v.loop ? nib_to_sample(lp, start) : 0;
    if (v.loop && s0 > ls) s0 = ls;        // resumed inside the loop: restart at the loop
    s0 &= ~((1u << (v.shift + 1)) - 1);    // whole AICA byte
    v.s0 = s0;
    v.aica += (s0 >> v.shift) / 2;
    u32 se = nib_to_sample(end, start);
    v.gc_len = se > s0 ? se - s0 : 1;
    v.gc_loop = v.loop ? ls - s0 : 0;
    v.len = v.gc_len >> v.shift;
    v.loop_start = v.gc_loop >> v.shift;
    v.rate = 0;
    if (v.ch < 0) v.ch = chn_alloc();
    if (v.ch < 0) { v.running = 0; p->state = 0; return; }
    v.dirty = 1;
    ++S.se_starts;
    if (g_logStarts < 40) {
        ++g_logStarts;
        re4dc_log("aica: t=%u se start blk=%d aica=%06x len=%u loop=%u/%u ratio=%d/1000 shift=%u ch=%d in=%d pan=%u\n", (unsigned) g_nowMs, t,
                  (unsigned) v.aica, (unsigned) v.len, (unsigned) v.loop, (unsigned) v.loop_start,
                  (int) (v.ratio * 1000), (unsigned) v.shift, v.ch, (int) v.mix.in, (unsigned) v.mix.pan);
    }
}
void AXSetVoiceType(void* p, u16 t) { (void) p; (void) t; }
void AXSetVoicePriority(void* p, u32 prio) { (void) p; (void) prio; }
void AXSetVoiceAdpcm(void* p, void* a) { (void) p; (void) a; }       // converted with the bank's coefficients
void AXSetVoiceAdpcmLoop(void* p, void* a) { (void) p; (void) a; }
void AXSetVoiceLoop(void* vp, u16 l) { ((AXVPBView*) vp)->addr.loopFlag = l; }
void AXSetVoiceLoopAddr(void* vp, u32 a) { AXVPBView* p = (AXVPBView*) vp; p->addr.loopAddressHi = (u16) (a >> 16); p->addr.loopAddressLo = (u16) a; }
void AXSetVoiceEndAddr(void* vp, u32 a) { AXVPBView* p = (AXVPBView*) vp; p->addr.endAddressHi = (u16) (a >> 16); p->addr.endAddressLo = (u16) a; }
void AXSetVoiceSrc(void* vp, void* s)
{
    AXVPBView* p = (AXVPBView*) vp;
    const AXPBSRC* src = (const AXPBSRC*) s;
    p->vs.ratio = (f32) (((u32) src->ratioHi << 16) | src->ratioLo) / 65536.0f;
    p->vs.dirty |= 4;
}
void AXSetVoiceSrcType(void* p, u32 t) { (void) p; (void) t; }
void AXSetVoiceSrcRatio(void* vp, f32 r) { AXVPBView* p = (AXVPBView*) vp; p->vs.ratio = r; p->vs.dirty |= 4; }
void AXSetVoiceLpf(void* p, void* l) { (void) p; (void) l; }
void AXSetVoiceLpfCoefs(void* p, u16 a0, u16 b0) { (void) p; (void) a0; (void) b0; }

void AXFXSetHooks(void* (*a)(u32), void (*f)(void*)) { (void) a; (void) f; }
int AXFXReverbHiInit(void* r) { (void) r; return 1; }
int AXFXReverbHiSettings(void* r) { (void) r; return 1; }
int AXFXReverbHiShutdown(void* r) { (void) r; return 1; }
void AXFXReverbHiCallback(void* b, void* r) { (void) b; (void) r; }
int AXFXReverbHiInitDpl2(void* r) { (void) r; return 1; }
int AXFXReverbHiSettingsDpl2(void* r) { (void) r; return 1; }
int AXFXReverbHiShutdownDpl2(void* r) { (void) r; return 1; }
void AXFXReverbHiCallbackDpl2(void* b, void* r) { (void) b; (void) r; }
int AXFXReverbStdInit(void* r) { (void) r; return 1; }
int AXFXReverbStdSettings(void* r) { (void) r; return 1; }
int AXFXReverbStdShutdown(void* r) { (void) r; return 1; }
void AXFXReverbStdCallback(void* b, void* r) { (void) b; (void) r; }
int AXFXDelayInit(void* d) { (void) d; return 1; }
int AXFXDelaySettings(void* d) { (void) d; return 1; }
int AXFXDelayShutdown(void* d) { (void) d; return 1; }
void AXFXDelayCallback(void* b, void* d) { (void) b; (void) d; }
int AXFXChorusInit(void* c) { (void) c; return 1; }
int AXFXChorusSettings(void* c) { (void) c; return 1; }
int AXFXChorusShutdown(void* c) { (void) c; return 1; }
void AXFXChorusCallback(void* b, void* c) { (void) b; (void) c; }

void AXARTInit(void) {}
void AXARTQuit(void) {}
void AXARTServiceSounds(void) {}

void MIXInit(void) {}
void MIXQuit(void) {}
void MIXInitChannel(void* vp, u32 mode, int in, int auxA, int auxB, int pan, int span, int fader)
{
    (void) mode; (void) auxA; (void) auxB; (void) span;
    AXVPBView* p = (AXVPBView*) vp;
    p->vs.mix.in = (s16) in;
    p->vs.mix.fader = (s16) fader;
    p->vs.mix.pan = (u8) (pan & 127);
    p->vs.dirty |= 2;
}
void MIXReleaseChannel(void* p) { (void) p; }
void MIXSetInput(void* vp, int dB) { AXVPBView* p = (AXVPBView*) vp; p->vs.mix.in = (s16) dB; p->vs.dirty |= 2; }
void MIXSetAuxA(void* p, int dB) { (void) p; (void) dB; }
void MIXSetAuxB(void* p, int dB) { (void) p; (void) dB; }
void MIXSetPan(void* vp, int pan) { AXVPBView* p = (AXVPBView*) vp; p->vs.mix.pan = (u8) (pan & 127); p->vs.dirty |= 2; }
void MIXSetSPan(void* p, int span) { (void) p; (void) span; }
void MIXSetSoundMode(u32 mode) { (void) mode; }
void MIXUpdateSettings(void) {}

void SYNInit(void) {}
void SYNQuit(void) {}
void SYNInitSynth(void* sp, void* wt, u32 aram, u32 zero, u32 p1, u32 p2, u32 p3)
{
    (void) zero; (void) p1; (void) p2; (void) p3;
    Synth* s = (Synth*) sp;
    memset(s, 0, sizeof(*s));
    s->magic = kSynMagic;
    s->wt = (const u8*) wt;
    s->aram = aram;
    s->blk = -1;
    for (int i = 0; i < 16; i++) {
        s->ch[i].vol = 100;
        s->ch[i].exp = 127;
        s->ch[i].pan = 64;
        s->ch[i].bend_range = 2;
        s->ch[i].rpn_lsb = s->ch[i].rpn_msb = 127;
    }
    for (int i = 0; i < 16; i++) { s->ch[i].bend_mul = 1.0f; s->ch[i].db10 = (s16) db_curve(100); }
    const SndWtHdr* h = (const SndWtHdr*) wt;
    s->ninst = (u16) ((h->rgn_ofs - h->inst_ofs) / 256);
    s->blk = synth_block(s);
    re4dc_log("aica: synth %p wt=%p aram=%06x blk=%d\n", sp, wt, (unsigned) aram, s->blk);
}
void SYNQuitSynth(void* sp)
{
    Synth* s = as_synth(sp);
    if (!s) return;
    synth_all_off(s, true);
    s->magic = 0;
    re4dc_log("aica: t=%u synth %p quit (sequence closed, BGM slot can go idle)\n", (unsigned) g_nowMs, sp);
}
void SYNRunAudioFrame(void) {}
void SYNMidiInput(void* sp, u8* in)
{
    Synth* s = as_synth(sp);
    if (!s) return;
    u32 st = in[0] & 0xF0, ch = in[0] & 15, d1 = in[1] & 127, d2 = in[2] & 127;
    SynCh& c = s->ch[ch];
    switch (st) {
    case 0x90:
        if (d2) { note_on(s, ch, d1, d2); break; }
        [[fallthrough]];  // velocity 0 = note off
    case 0x80: note_off(s, ch, d1); break;
    case 0xC0: c.prog = (u8) d1; break;
    case 0xE0: c.bend = (s16) (((d2 << 7) | d1) - 8192); ch_update(s, c); break;
    case 0xB0:
        switch (d1) {
        case 7: c.vol = (u8) d2; ch_update(s, c); break;
        case 10: c.pan = (u8) d2; break;
        case 11: c.exp = (u8) d2; ch_update(s, c); break;
        case 100: c.rpn_lsb = (u8) d2; break;
        case 101: c.rpn_msb = (u8) d2; break;
        case 6: if (c.rpn_lsb == 0 && c.rpn_msb == 0) { c.bend_range = (u8) d2; ch_update(s, c); } break;
        case 120: case 123: synth_all_off(s, false); break;
        case 91: case 93: {   // reverb / chorus sends (AUX A/B on the GC): not rendered yet
            static u32 logged;
            if (logged < 32) {
                ++logged;
                re4dc_log("aica: t=%u synth cc%u ch=%u val=%u (aux send, not rendered)\n", (unsigned) g_nowMs,
                          (unsigned) d1, (unsigned) ch, (unsigned) d2);
            }
            break;
        }
        default: break;
        }
        break;
    default: break;
    }
}
u32 SYNGetActiveNotes(void* sp)
{
    u32 n = 0;
    for (int i = 0; i < kNotes; i++) if (g_notes[i].used && g_notes[i].synth == sp && !g_notes[i].released) ++n;
    return n;
}
void SYNSetMasterVolume(void* sp, s32 dB)
{
    Synth* s = as_synth(sp);
    if (s && s->master10 != dB) { s->master10 = dB; ++s->gen; }
}
void SEQInit(void) {}
void SEQQuit(void) {}
void SEQRunAudioFrame(void) {}

}  // extern "C"
