// The engine's AICA sound layer (lane eng-snd1, H-025.1): the interface the sound service (snd_svc.cpp) uses. The layer
// itself (aica.cpp) implements, on the Dreamcast's sound chip, the GameCube audio interfaces the hosted sound driver
// calls (AX voices, MIX, SYN, the AXFX / AXART / AI / SEQ entry points).
#ifndef ENG_SND_AICA_H
#define ENG_SND_AICA_H
#include <stdint.h>

// A converted bank (tools/aica_banks.py on the old port: "AIC1" header, then the AICA 4-bit ADPCM image) at the start
// of a sound block's ARAM part. 96 bytes.
struct AicaBankHeader {
    uint32_t magic;
    uint16_t version, cap_hz;
    uint32_t total;            // AICA image bytes (they follow the header)
    uint32_t nsamples;
    uint32_t fnv;              // FNV-1a of the wavetable's sample table
    uint32_t gc_size;          // GameCube ARAM part size
    uint32_t slot;             // layout slot of this block (8 = room arena)
    uint32_t pad;              // bit 0: tail-first (the BGM0 slot's unused tail)
    uint32_t slot_bytes[9];    // the route layout, by block index (8 = room arena)
    uint32_t pad2[7];
};
static_assert(sizeof(AicaBankHeader) == 96, "AicaBankHeader");
enum { AICA_BANK_MAGIC = 0x31434941u };   // "AIC1"

// Counters (read by the service for its report line and the AICA output check).
struct AicaStats {
    uint32_t frames, ticks, drv_us, flush_us, max_drv_us, max_flush_us;
    uint32_t se_starts, se_unmapped, note_on, note_off, note_steal, keyons, regwrites;
    uint32_t active_voices, active_notes, peak_voices, peak_notes;
    uint32_t blocks, blocks_skipped, copy_bytes, aica_used;
    uint32_t str_starts, str_underruns, str_read_bytes, str_reads;
};
extern AicaStats aica_stats;

// Boot: KOS's sound driver and AICA RAM allocator (snd_init). Before any bank.
void aica_init(void);
// A new room: the room arena (FOOT, ROOM, enemy blocks) is emptied before its banks are placed.
void aica_room_reset(void);
// Places sound block t's converted bank described by `h` (its MRAM part must already be at SndMem.blk_mram[t] and
// UseAramSize[t] set); false when refused (logged, the block stays silent). Then the image is copied in pieces
// (aica_bank_copy: image byte offset, bytes) and closed (aica_bank_done).
bool aica_bank_place(int t, uint32_t gc_dst, const AicaBankHeader& h);
void aica_bank_copy(uint32_t img_ofs, const void* src, uint32_t len);
void aica_bank_done(void);
// The 5 ms audio frame on its own thread (KOS thread, priority 3, above the game's main thread). Started once the
// driver has registered its callback (AXRegisterCallback) and aica_start has been called.
void aica_start(void);
// One audio step's cost and the step's voices (the service's per-picture accounting): called by the audio thread.
extern void (*aica_step_hook)(uint32_t us, uint32_t voices, uint32_t notes);
// Lab arm SNDMUTE (control of the output check): every channel keyed on at total attenuation (no output).
extern int aica_mute_all;
// Lab arm SNDSLOW (control of the cost ceiling): busy-wait this many microseconds inside every audio step.
extern uint32_t aica_slow_us;
// The output check: the AICA's own channel monitor, read back for every channel the layer owns (key on, envelope
// level, current sample address). Fills the counts; returns the number of channels keyed on and sounding.
struct AicaProbe { uint32_t keyed, sounding, moving, checked; };
void aica_probe(AicaProbe& p);
// Channels the layer owns now.
int aica_channels_used(void);
#endif
