// The engine's AICA sound layer (lane eng-snd1, integrator ruling H-025.1).
//
// Lifted from the old port's Dreamcast backend (t15/int port/dreamcast/game/platform/audio_aica.cpp, the release's
// AICA_AUDIO=1 AICA_LAYOUT_RECOVER=1 AICA_SPILL=1 AICA_TAIL_FIRST=1 form) and adapted to the engine:
//  - no old-port globals or hooks (the cabin, Leon-hand cache, GC-ASSET gate, fallback audit, movie and debug-log
//    hooks are gone; the boot log is the engine's);
//  - banks reach it from the engine's room loader (snd_svc.cpp aica_bank_place / _copy / _done) at room load, not
//    through the GameCube ARAM queue in the middle of a read; only converted ("AIC1") banks are placed, a bank in the
//    GameCube's own format is refused and stays silent (the old port's run-time re-encoding is not lifted: every bank
//    the engine's rooms use is converted on the disc tree);
//  - the room arena is emptied by the loader (aica_room_reset), not detected from a GameCube address;
//  - the per-step cost goes to the service (aica_step_hook) for its per-picture accounting.
// What it is (unchanged from the old port): the hosted Capcom driver (src/game/snd*.cpp) resolves SE numbers,
// positions, priorities, envelopes and the BGM MIDI sequences and drives Nintendo's AX voice / MIX / SYN interfaces.
// This file implements those interfaces on the AICA:
//  * Sample banks: copied into a fixed AICA layout, one slot per resident block (CORE, PL, WEP, BGM0/1, DOOR) and one
//    room arena (ROOM, FOOT, enemies) reset at each room load, all sized by the conversion tool's route budget, so
//    nothing fragments across rooms.
//  * AX voices (SEs) map to AICA channels programmed directly over G2 (32-bit writes, a FIFO wait every 8 writes). The
//    end of a one-shot voice is estimated from elapsed time and pitch (no register read back in play).
//  * SYN (the MIDI synth under the BGM sequencer) is a minimal GM voice layer on AICA channels.
//  * The driver's 5 ms audio frame runs on a 200 Hz KOS thread (the GameCube AI interrupt rate); then all register
//    writes are flushed under one G2 lock.
// Not covered (as in the old port): AUX reverb, LPF, LFO, DPL2. Disc streams: the stream player runs (snd_svc.cpp
// completes its I/O) and its voices advance silently; the AICA ring for bgm/aica_str.dat is not lifted yet.
#include <kos.h>
#include <dc/sound/sound.h>
#include <dc/sound/sfxmgr.h>
#include <dc/g2bus.h>
#include <dc/spu.h>
#include <math.h>
#include <string.h>
#include "aica.h"

// The main thread's lines go to the engine log, the audio thread's to a ring printed with the report (snd_svc.cpp).
extern "C" void aica_log(const char* fmt, ...);
#define snd_log aica_log

typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef signed short s16;
typedef signed long s32;
typedef unsigned long u32;
typedef unsigned long long u64;
typedef float f32;

// ---------------------------------------------------------------------------
// SDK structure mirrors (include/dolphin/ax.h). Only the fields the driver reads back (pb.state, pb.addr) must sit at
// the SDK offsets.
struct AXPBADDR { u16 loopFlag, format, loopAddressHi, loopAddressLo, endAddressHi, endAddressLo, currentAddressHi, currentAddressLo; };
struct AXPBSRC { u16 ratioHi, ratioLo, currentAddressFrac, last_samples[4]; };
struct MixState { s16 in, fader; u8 pan; u8 pad; };

// The driver sees an AXVPB; its SDK header (0x138 bytes before pb) is not read by the driver, so the layer keeps its
// own voice state there.
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
static_assert(sizeof(WTSAMPLE) == 16, "WTSAMPLE");
struct SndWtHdr { u32 x0, inst_ofs, rgn_ofs, art_ofs, sample_ofs, adpcm_ofs; };

// Driver globals (src/game/snd.cpp): the blocks' MRAM parts and ARAM part sizes. Variables are not mangled.
struct SndMemView { u8 pad[0x14]; u8* blk_mram[14]; u32 blk_aram[14]; };
extern SndMemView SndMem;
extern u32 UseAramSize[14];

typedef void (*AXCallback)(void);
extern "C" void cb_str_voice_drop(void* voice);   // the stream player's AX voice callback (snd_str3.cpp)
extern "C" int snd_strm_advance(u16* addr, f32 samples, f32* frac);   // snd_svc.cpp: a stream voice's position
extern "C" void snd_pend_run(void);                                   // snd_svc.cpp: the stream player's I/O completions

AicaStats aica_stats;
void (*aica_step_hook)(uint32_t us, uint32_t voices, uint32_t notes);
int aica_mute_all;
uint32_t aica_slow_us;

namespace {

AicaStats& S = aica_stats;
const uintptr_t kAicaChan = 0xA0700000u;
const u32 kAicaPoolBytes = 1900544;          // KOS snd_mem pool (AICA RAM above KOS's ARM driver)
const u32 kReserveBytes = 64 * 1024;         // AICA RAM kept free (movie audio, the stream ring when it is lifted)
const int kMaxChannels = 60;                 // of 64: 4 stay free for KOS snd_stream (movies)

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
    if (aica_mute_all) return 255;
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
struct MapEnt { u32 gc_nib; u32 len; u32 aica; };  // aica: addr | shift << 24
struct Blk {
    u32 gc_base, gc_size;        // GC ARAM bytes
    u32 aica, aica_size;         // AICA placement
    u16 first, count;            // map entries (sample index order)
    u16 rate_cap;
    u8 valid, slotted;           // slotted: lives in the fixed layout (never freed to KOS)
    const WTSAMPLE* smp;
};
const int kMapMax = 640;
MapEnt g_map[kMapMax];
u32 g_mapUsed;
Blk g_blk[14];

struct Slot { u32 base, size; };
Slot g_slot[9];
u32 g_arenaNext;
int g_spillBlk = -1;   // a room-arena block placed in the BGM0 slot's tail, or -1
bool g_layout, g_layoutWarned;
inline u32 slot_of(int t) { return (t == 5 || t == 6 || t >= 8) ? 8 : (u32) t; }
inline bool room_arena(int t) { return t == 5 || t == 6 || t >= 8; }

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

bool g_init;
AXCallback g_axCallback;
// The 64 voice blocks, packed: the driver reads only pb.state and pb.addr of a voice (snd_iss2 / snd_iss4 / snd_str1 /
// snd_str2) and the layer keeps its VoiceState in the SDK header area, so the blocks overlap with a 112-byte stride:
// per block, bytes 0-79 VoiceState, 86-101 pb.addr, 102-103 pb.state (offsets 0x1A6 and 0x146 modulo 112), nothing
// else is touched (no block is ever cleared whole). 7.6 KB instead of the SDK's 64 x 454 B (29 KB).
const u32 kVpbStride = 112;
static_assert(sizeof(VoiceState) <= 80, "VoiceState: bytes 0-79 of the stride");
static_assert(__builtin_offsetof(AXVPBView, addr) % kVpbStride == 86 && sizeof(AXPBADDR) == 16, "pb.addr: bytes 86-101");
static_assert(__builtin_offsetof(AXVPBView, state) % kVpbStride == 102, "pb.state: bytes 102-103");
u8 g_vpbmem[63 * kVpbStride + sizeof(AXVPBView)] __attribute__((aligned(32)));
inline AXVPBView& vpb(int i) { return *(AXVPBView*) (g_vpbmem + i * kVpbStride); }
u64 g_lastTickUs, g_lastFrameUs;
u32 g_logStarts;
u32 g_aicaUsed;   // bytes of AICA RAM held by the layout
int g_chUsed;     // AICA channels held by the layer
u8 g_chOwned[64]; // the layer's channels (the output check reads only these)
mutex_t g_lock = MUTEX_INITIALIZER;   // banks (main thread at load) vs the audio step

void blk_cut(int t);

void blk_free(int t)
{
    Blk& b = g_blk[t];
    if (b.aica) blk_cut(t);
    if (b.count) {   // compact the map pool
        u32 end = b.first + b.count;
        memmove(&g_map[b.first], &g_map[end], (g_mapUsed - end) * sizeof(MapEnt));
        g_mapUsed -= b.count;
        for (int i = 0; i < 14; i++)
            if (g_blk[i].count && g_blk[i].first >= end) g_blk[i].first -= b.count;
    }
    memset(&b, 0, sizeof(b));
}

// The block's wavetable (MRAM part): its sample table.
bool blk_wavetable(int t, const WTSAMPLE*& smp, u32& n)
{
    u8* m = SndMem.blk_mram[t];
    if (!m) return false;
    if (t != 3 && t != 4) m += *(u32*) m;
    const u32* iss = (const u32*) m;
    const u8* dls = m + iss[1];
    const SndWtHdr* h = (const SndWtHdr*) dls;
    if (h->adpcm_ofs <= h->sample_ofs) return false;
    n = (h->adpcm_ofs - h->sample_ofs) / sizeof(WTSAMPLE);
    if (n == 0 || n > 512) { snd_log("aica: blk %d has %u samples, skipped\n", t, (unsigned) n); return false; }
    smp = (const WTSAMPLE*) (dls + h->sample_ofs);
    return true;
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

// First converted bank: reserve the whole route layout, in slot order. Published only once every slot is owned.
bool layout_init(const AicaBankHeader& h)
{
    if (g_layout) {
        for (int i = 0; i < 9; i++)
            if (h.slot_bytes[i] != g_slot[i].size && !g_layoutWarned) {
                g_layoutWarned = true;
                snd_log("aica: bank layout differs from the first bank's (slot %d %u vs %u): keeping the first\n",
                        i, (unsigned) h.slot_bytes[i], (unsigned) g_slot[i].size);
            }
        return true;
    }
    u32 want = 0;
    for (int i = 0; i < 9; i++) want += (h.slot_bytes[i] + 31) & ~31u;
    if (g_aicaUsed + want > kAicaPoolBytes - kReserveBytes) {
        snd_log("aica: layout %u bytes would leave less than the %u byte reserve, banks silent\n", (unsigned) want,
                (unsigned) kReserveBytes);
        return false;
    }
    Slot pending[9] = {};
    u32 owned = 0;
    for (int i = 0; i < 9; i++) {
        if (!h.slot_bytes[i]) continue;
        u32 a = snd_mem_malloc(h.slot_bytes[i]);
        if (!a) {
            snd_log("aica: layout slot %d (%u bytes) does not fit, %u bytes in use\n", i, (unsigned) h.slot_bytes[i],
                    (unsigned) g_aicaUsed);
            for (int k = 0; k < i; k++) if (pending[k].base) snd_mem_free(pending[k].base);
            g_aicaUsed -= owned;
            return false;
        }
        pending[i].base = a;
        pending[i].size = h.slot_bytes[i];
        owned += (h.slot_bytes[i] + 31) & ~31u;
        g_aicaUsed += (h.slot_bytes[i] + 31) & ~31u;
    }
    memcpy(g_slot, pending, sizeof(g_slot));
    g_layout = true;
    snd_log("aica: layout core=%06x+%u pl=%06x+%u wep=%06x+%u bgm0=%06x+%u bgm1=%06x+%u door=%06x+%u arena=%06x+%u, "
            "%u bytes, %u free\n",
            (unsigned) g_slot[0].base, (unsigned) g_slot[0].size, (unsigned) g_slot[1].base, (unsigned) g_slot[1].size,
            (unsigned) g_slot[2].base, (unsigned) g_slot[2].size, (unsigned) g_slot[3].base, (unsigned) g_slot[3].size,
            (unsigned) g_slot[4].base, (unsigned) g_slot[4].size, (unsigned) g_slot[7].base, (unsigned) g_slot[7].size,
            (unsigned) g_slot[8].base, (unsigned) g_slot[8].size, (unsigned) g_aicaUsed,
            (unsigned) (kAicaPoolBytes - g_aicaUsed));
    S.aica_used = g_aicaUsed;
    return true;
}

struct Copy { int blk; u32 total; } g_copy = { -1, 0 };

// ---------------------------------------------------------------------------
// GC nibble address -> block and map entry (the sample's first sample: frame header + 2).
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
// pcms 2: ADPCM (the loop restores the decoder state saved at LSA).
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
    if (ch >= 0) { ++g_chUsed; g_chOwned[ch] = 1; }
    return (s8) ch;
}
void chn_free(s8 ch)
{
    if (ch < 0) return;
    g_chOwned[(int) ch] = 0;
    snd_sfx_chn_free(ch);
    --g_chUsed;
}

// ---------------------------------------------------------------------------
// SYN: minimal GM synth on AICA channels. Levels are cached per channel and per note so a flush only recomputes what
// a MIDI event or a fade changed.
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

u16 note_tl(const Note& n, const Synth* s) { return tl_from_db10(s->master10 + n.lvl10 + s->ch[n.ch_midi].db10); }
u16 note_freq(const Note& n, const Synth* s) { return aica_freq_reg((u32) (n.base_hz * s->ch[n.ch_midi].bend_mul)); }

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
    if (t < 0) { ++S.se_unmapped; return; }
    s->blk = t;
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

// A block is being replaced (room change, BGM reload): voices and notes still sounding from its AICA copy are keyed
// off now, before the new data is written there, and reported ended to the driver.
void blk_cut(int t)
{
    g2_lock_scoped();
    RegWriter w;
    u32 cut = 0;
    for (int i = 0; i < 64; i++) {
        AXVPBView& p = vpb(i);
        VoiceState& v = p.vs;
        if (!v.used || v.ch < 0 || !v.mapped || v.blk != t) continue;
        ch_keyoff(w, v.ch, v.play_cont);
        v.running = 0;
        v.mapped = 0;
        v.dirty = 8;          // the flush frees the channel
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
    if (cut) snd_log("aica: blk %d replaced, %u sounding voices cut\n", t, (unsigned) cut);
}

// ---------------------------------------------------------------------------
void flush()
{
    g2_lock_scoped();
    RegWriter w;
    // AX voices
    for (int i = 0; i < 64; i++) {
        VoiceState& v = vpb(i).vs;
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
        u16 tl = tl_from_db10(v.mix.in + v.mix.fader);
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
    S.regwrites += w.n;
}

// ---------------------------------------------------------------------------
// The driver's audio frame. On the GameCube it is the 5 ms AI DMA interrupt; here a KOS thread (priority 3, above the
// game's main thread at the default 10) wakes every 5 ms, runs the frames that wall time owes (normally one, at most
// 64 after a stall), advances the one-shot end estimate and flushes register writes. The hosted driver's calls from
// game code are guarded with OSDisableInterrupts (snd_svc.cpp: irq_disable), so the thread cannot run inside them,
// exactly as the interrupt could not.
u8 g_thread_stack[12 * 1024] __attribute__((aligned(8)));
const u32 kCatchUp = 2;   // driver frames a step at most
kthread_t* g_thread;
int g_started;

void audio_step()
{
    u64 now = timer_us_gettime64();
    g_nowMs = (u32) (now / 1000);
    if (!g_lastTickUs) { g_lastTickUs = now - 5000; g_lastFrameUs = now; }
    u32 ticks = (u32) ((now - g_lastTickUs) / 5000);
    if (ticks == 0) return;
    // Frames owed after the thread was held up are paid back at most kCatchUp a step (the debt carries to the next
    // steps, so the music keeps its tempo and no single picture takes the whole debt); a debt over 64 frames (320 ms)
    // is dropped, as the old port did.
    if (ticks > 64) { g_lastTickUs = now - 5000ull * kCatchUp; ticks = kCatchUp; ++S.debt_drops; }
    if (ticks > kCatchUp) ticks = kCatchUp;
    if (ticks > S.max_ticks) S.max_ticks = ticks;
    // banks being placed by the main thread (a room load, a BGM read): this step's frames wait for the next step
    if (mutex_trylock(&g_lock)) return;
    g_lastTickUs += ticks * 5000ull;
    for (u32 i = 0; i < ticks; i++) {
        snd_pend_run();
        g_axCallback();
    }
    u64 t1 = timer_us_gettime64();
    f32 dt = (f32) (now - g_lastFrameUs) * 1e-6f;
    g_lastFrameUs = now;
    u32 active = 0;
    for (int i = 0; i < 64; i++) {
        AXVPBView& p = vpb(i);
        VoiceState& v = p.vs;
        if (!v.used || !v.running) continue;
        ++active;
        if (v.strm) {   // silent: position only
            if (snd_strm_advance(&p.addr.loopFlag, dt * v.ratio * 32000.0f, &v.pos)) { p.state = 0; v.running = 0; }
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
    const u64 tv = timer_us_gettime64();
    flush();
    mutex_unlock(&g_lock);
    if (aica_slow_us) {   // SNDSLOW (control): a known delay inside the step, so the cost must read it
        const u64 until = timer_us_gettime64() + aica_slow_us;
        while (timer_us_gettime64() < until) {}
    }
    u64 t2 = timer_us_gettime64();
    ++S.frames;
    S.ticks += ticks;
    u32 d = (u32) (t1 - now), f = (u32) (t2 - t1);
    S.drv_us += d; S.flush_us += f;
    if (d > S.max_drv_us) S.max_drv_us = d;
    if (f > S.max_flush_us) S.max_flush_us = f;
    if ((u32) (t2 - now) > S.long_us) {   // the longest step and its parts (diagnosis)
        S.long_us = (u32) (t2 - now);
        S.long_drv = d;
        S.long_vox = (u32) (tv - t1);
        S.long_flush = (u32) (t2 - tv);
        S.long_frames = ticks;
    }
    S.active_voices = active; S.active_notes = notes;
    if (active > S.peak_voices) S.peak_voices = active;
    if (notes > S.peak_notes) S.peak_notes = notes;
    if (aica_step_hook) aica_step_hook((uint32_t) (t2 - now), active, notes);
}

void probe_step();
void* audio_main(void*)
{
    for (;;) {
        thd_sleep(5);
        if (!g_axCallback || !g_started) continue;
        const u64 a = timer_us_gettime64();
        // The step runs with interrupts off. KOS's scheduler, at its 10 ms tick, hands the CPU to another ready thread
        // whatever the priorities (thread.c thd_schedule picks from the run queue before the running thread is put back),
        // so a tick that fell inside a step gave the main thread a whole timeslice in the middle of it (10 to 20 ms
        // steps, one to several a scene). With interrupts off the step is atomic, as the GameCube's audio interrupt was:
        // the tick is taken when the step ends, and the main thread gets the CPU then, as it would anyway. The vblank
        // interrupt (the field count the pacer waits on) waits at most one step; the report gives the longest step.
        const int irq = irq_disable();
        audio_step();
        irq_restore(irq);
        probe_step();   // the output check: a few register reads, outside the step's cost (aica_step_hook)
        aica_busy_us = aica_busy_us + (uint32_t) (timer_us_gettime64() - a);
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
    a.label = "eng-sound";
    a.create_detached = true;
    g_thread = thd_create_ex(&a, audio_main, nullptr);
    // (Priority alone does not keep a step whole, priority 0 made it worse: audio_main runs the step with interrupts off.)
    snd_log("aica: audio thread tid=%d prio=3 period=5ms\n", g_thread ? (int) g_thread->tid : -1);
}

}  // namespace

// ---------------------------------------------------------------------------
// The service's interface (aica.h).
void aica_init(void)
{
    if (g_init) return;
    snd_init();
    g_init = true;
    snd_log("aica: up, KOS sound RAM largest free %u bytes\n", (unsigned) snd_mem_available());
}

void aica_room_reset(void)
{
    mutex_lock(&g_lock);
    for (int i = 0; i < 14; i++) if (room_arena(i)) blk_free(i);
    g_arenaNext = 0;
    mutex_unlock(&g_lock);
}

bool aica_bank_place(int t, uint32_t dst, const AicaBankHeader& h)
{
    const WTSAMPLE* smp;
    u32 n;
    mutex_lock(&g_lock);
    g_copy.blk = -1;
    bool ok = false;
    do {
        if (h.magic != AICA_BANK_MAGIC) {
            snd_log("aica: blk %d is not a converted bank, block silent\n", t);
            ++S.blocks_skipped;
            break;
        }
        if (!blk_wavetable(t, smp, n)) { ++S.blocks_skipped; break; }
        u32 total = 0;
        for (u32 i = 0; i < n; i++) total += sample_bytes(smp[i], sample_shift(smp[i], h.cap_hz));
        const char* bad = h.version != 1 ? "version" : h.nsamples != n ? "sample count"
                        : fnv1a((const u8*) smp, n * sizeof(WTSAMPLE)) != h.fnv ? "wavetable hash"
                        : ((h.gc_size + 31) & ~31u) != UseAramSize[t] ? "part size"
                        : total != h.total ? "image size" : h.slot != slot_of(t) ? "slot" : nullptr;
        if (bad) {
            snd_log("aica: blk %d converted bank rejected (%s), block silent\n", t, bad);
            ++S.blocks_skipped;
            break;
        }
        if (!layout_init(h)) { ++S.blocks_skipped; break; }
        if (t == g_spillBlk) g_spillBlk = -1;
        blk_free(t);
        if (g_mapUsed + n > kMapMax) { snd_log("aica: map pool full\n"); ++S.blocks_skipped; break; }
        Slot& sl = g_slot[h.slot];
        u32 base = 0;
        bool placed = false;
        // A BGM0 bank about to overwrite a room-arena bank spilled into its slot's tail silences that bank first.
        if (h.slot == 3 && g_spillBlk >= 0 && g_blk[g_spillBlk].valid
            && g_slot[3].base + ((total + 31) & ~31u) > g_blk[g_spillBlk].aica) {
            snd_log("aica: BGM0 bank %u bytes overlaps blk %d spilled at %06x, blk %d silent\n", (unsigned) total,
                    g_spillBlk, (unsigned) g_blk[g_spillBlk].aica, g_spillBlk);
            blk_free(g_spillBlk);
            g_spillBlk = -1;
        }
        if (h.slot == 8) {
            u32 need = (total + 31) & ~31u;
            // a bank marked tail-first (header pad bit 0, aica_banks.py fit --tail-blk) goes to the BGM0 slot's unused
            // tail even while the arena has room, so the room's later banks still fit the arena
            if ((h.pad & 1) && (g_spillBlk < 0 || !g_blk[g_spillBlk].valid) && need <= g_slot[3].size) {
                const u32 used = g_blk[3].valid ? g_blk[3].aica - g_slot[3].base + ((g_blk[3].aica_size + 31) & ~31u) : 0;
                if (used + need <= g_slot[3].size) {
                    base = g_slot[3].base + g_slot[3].size - need;
                    g_spillBlk = t;
                    placed = true;
                    snd_log("aica: blk %d (%u bytes) tail-first to the BGM0 slot tail at %06x\n", t, (unsigned) total,
                            (unsigned) base);
                }
            }
            // arena full: the unused tail of the BGM0 slot, one spilled bank at a time
            if (!placed && g_arenaNext + need > sl.size && (g_spillBlk < 0 || !g_blk[g_spillBlk].valid) && g_blk[3].valid
                && g_blk[3].aica == g_slot[3].base) {
                const u32 used = (g_blk[3].aica_size + 31) & ~31u;
                if (used + need <= g_slot[3].size) {
                    base = g_slot[3].base + used;
                    g_spillBlk = t;
                    placed = true;
                    snd_log("aica: blk %d (%u bytes) spills to the BGM0 slot tail at %06x\n", t, (unsigned) total,
                            (unsigned) base);
                }
            }
            if (!placed) {
                if (g_arenaNext + need > sl.size) {
                    snd_log("aica: blk %d (%u bytes) does not fit the room arena (%u of %u used), block silent\n", t,
                            (unsigned) total, (unsigned) g_arenaNext, (unsigned) sl.size);
                    ++S.blocks_skipped;
                    break;
                }
                base = sl.base + g_arenaNext;
                g_arenaNext += need;
            }
        } else {
            if (total > sl.size) {
                snd_log("aica: blk %d (%u bytes) larger than its slot (%u), block silent\n", t, (unsigned) total,
                        (unsigned) sl.size);
                ++S.blocks_skipped;
                break;
            }
            base = sl.base;
        }
        Blk& b = g_blk[t];
        b.smp = smp;
        b.gc_base = dst;
        b.gc_size = UseAramSize[t];
        b.aica = base;
        b.aica_size = total;
        b.slotted = 1;
        b.rate_cap = h.cap_hz;
        blk_map(b, n, h.cap_hz);
        b.valid = 1;
        ++S.blocks;
        g_copy.blk = t;
        g_copy.total = total;
        snd_log("aica: blk %d gc=%06x+%u -> aica=%06x %u bytes, %u samples, %u Hz (slot %u)\n", t, (unsigned) dst,
                (unsigned) b.gc_size, (unsigned) base, (unsigned) total, (unsigned) n, (unsigned) h.cap_hz,
                (unsigned) h.slot);
        ok = true;
    } while (0);
    mutex_unlock(&g_lock);
    return ok;
}

void aica_bank_copy(uint32_t img_ofs, const void* src, uint32_t len)
{
    if (g_copy.blk < 0 || img_ofs >= g_copy.total) return;
    if (len > g_copy.total - img_ofs) len = g_copy.total - img_ofs;
    spu_memload(g_blk[g_copy.blk].aica + img_ofs, (void*) src, (len + 3) & ~3u);
    S.copy_bytes += len;
}

void aica_bank_done(void) { g_copy.blk = -1; }

void aica_start(void)
{
    g_started = 1;
    if (g_axCallback && g_init) start_thread();
}

int aica_channels_used(void) { return g_chUsed; }

// The output check (lane eng-snd1): the AICA's channel monitor, read back, one channel a step. A step reads the
// channel the previous step selected: reg 0 (KYONB, bit 14: keyed on), reg 0x28 (TL, bits 15-8: attenuation, 255
// total), the monitor 0x2810 (EG, bits 12-0: the envelope's attenuation, 0x1FFF silent) and 0x2814 (CA: the current
// sample address, compared with the same channel's previous sample); then it selects the next channel the layer owns
// (0x280C MSLC, bits 13-8).
AicaProbe aica_probe_counts;
volatile uint32_t aica_busy_us;
namespace {
int g_probeCh = -1;
u16 g_lastCa[64];
u8 g_lastKey[64];
void probe_step()
{
    AicaProbe& p = aica_probe_counts;
    if (g_probeCh >= 0) {
        const int ch = g_probeCh;
        const u32 r0 = g2_read_32(kAicaChan + ch * 0x80);
        ++p.samples;
        if (r0 & 0x4000) {
            ++p.keyed;
            const u32 tl = (g2_read_32(kAicaChan + ch * 0x80 + 0x28) >> 8) & 0xFF;
            const u32 eg = g2_read_32(0xA0702810) & 0x1FFF;
            const u16 ca = (u16) (g2_read_32(0xA0702814) & 0xFFFF);
            if (eg < 0x1F00 && tl < 255) ++p.audible;
            if (g_lastKey[ch] && ca != g_lastCa[ch]) ++p.moving;
            g_lastCa[ch] = ca;
            g_lastKey[ch] = 1;
        } else {
            g_lastKey[ch] = 0;
        }
    }
    int next = -1;
    for (int k = 1; k <= 64; k++) {
        const int ch = (g_probeCh + k) & 63;
        if (g_chOwned[ch]) { next = ch; break; }
    }
    g_probeCh = next;
    if (next >= 0) g2_write_32(0xA070280C, (u32) next << 8);
}
}  // namespace

// ---------------------------------------------------------------------------
// The GameCube audio interfaces the hosted driver calls (include/dolphin/ax.h, mix.h, syn.h, seq.h, axfx.h, ai.h).
extern "C" {

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
    if (cb && g_init && g_started) start_thread();
    return old;
}
void AXRegisterAuxACallback(void (*cb)(void*, void*), void* ctx) { (void) cb; (void) ctx; }
void AXRegisterAuxBCallback(void (*cb)(void*, void*), void* ctx) { (void) cb; (void) ctx; }

void* AXAcquireVoice(u32 prio, void (*cb)(void*), u32 user)
{
    (void) prio; (void) user;
    for (int i = 0; i < 64; i++) {
        AXVPBView& p = vpb(i);
        if (!p.vs.used) {
            memset(&p.vs, 0, sizeof(p.vs));   // the block's own bytes only (the blocks overlap)
            memset(&p.addr, 0, sizeof(p.addr));
            p.state = 0;
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
    p->vs.strm = 0;
    if (p->vs.ch >= 0) {   // released through the next flush; the slot is reused afterwards
        p->vs.dirty |= 8;
        p->vs.running = 0;
        p->state = 0;
        p->vs.freed = 1;
        return;
    }
    p->vs.used = 0;
}

void AXSetVoiceAddr(void* vp, void* a) { memcpy(&((AXVPBView*) vp)->addr, a, sizeof(AXPBADDR)); }
void AXSetVoiceState(void* vp, u16 st)
{
    AXVPBView* p = (AXVPBView*) vp;
    VoiceState& v = p->vs;
    p->state = st;
    if (v.strm) {   // stream player voices: silent, their address advanced by snd_strm_advance
        if (st && !v.running) v.pos = 0;
        v.running = st != 0;
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
        return;
    }
    const Blk& b = g_blk[t];
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
    if (v.ch < 0) v.ch = chn_alloc();
    if (v.ch < 0) { v.running = 0; p->state = 0; return; }
    v.dirty = 1;
    ++S.se_starts;
    if (g_logStarts < 8) {
        ++g_logStarts;
        snd_log("aica: t=%u se start blk=%d aica=%06x len=%u loop=%u/%u ratio=%d/1000 shift=%u ch=%d in=%d pan=%u\n",
                (unsigned) g_nowMs, t, (unsigned) v.aica, (unsigned) v.len, (unsigned) v.loop, (unsigned) v.loop_start,
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
        s->ch[i].bend_mul = 1.0f;
        s->ch[i].db10 = (s16) db_curve(100);
    }
    const SndWtHdr* h = (const SndWtHdr*) wt;
    s->ninst = (u16) ((h->rgn_ofs - h->inst_ofs) / 256);
    s->blk = synth_block(s);
    snd_log("aica: synth %p wt=%p aram=%06x blk=%d\n", sp, wt, (unsigned) aram, s->blk);
}
void SYNQuitSynth(void* sp)
{
    Synth* s = as_synth(sp);
    if (!s) return;
    synth_all_off(s, true);
    s->magic = 0;
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
        default: break;   // reverb / chorus sends (AUX A/B on the GameCube): not rendered
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
