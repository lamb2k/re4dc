#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "include/fallback_audit29.h"
#endif
#line 1
// Disc stream plumbing shared by every audio build (audio_stub.cpp and
// audio_aica.cpp): the recovered stream player (src/game/snd_str*.cpp) must run
// through ready -> playing -> ended whether or not a stream can be heard, since
// scenario code waits on it (event.cpp SndStrPlayBlock spins until the stream is
// ready; SndStrStopBlock until it has stopped; r100/r101 Ope radio calls use both).
//
//  * I/O completion order. The player issues a DVD read or an ARAM DMA and only
//    then sets dvd_busy / dma_busy; the GC completes both later, from an
//    interrupt. The port's DVDReadAsyncPrio and ARQPostRequest complete inside
//    the call, so the flag set afterwards never clears and the player stalls at
//    its first block: the stream never becomes ready. Its completions are queued
//    here (Makefile: --wrap=DVDReadAsyncPrio --wrap=ARQPostRequest, matched on
//    the player's own callbacks) and delivered at the next audio frame, before
//    the driver runs, as the GC interrupt would. Its DVD reads are not performed:
//    the GC ADPCM data would only feed the GC ring, which no build plays (the
//    AICA backend plays bgm/aica_str.dat), and a synchronous 32 KB read every
//    0.26 s would sit on the audio frame.
//  * Stream voice position. The player follows its left voice's current ARAM
//    address block by block and detects the end from it. re4dc_strm_advance
//    moves an AXPBADDR the way the DSP would (4-bit ADPCM, 14 samples per 8-byte
//    frame), honouring the loop / end addresses the player reprograms, so the
//    stream plays for its real length and then ends.
#include <kos.h>
#include <string.h>

#include "re4dc_platform.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef signed long s32;
typedef unsigned long u32;
typedef float f32;

extern "C" {
void cb_dvd_read_end(s32 result, void* info);   // snd_str2.cpp
void cb_aram_dma_end(u32 task);                 // snd_str2.cpp
s32 __real_DVDReadAsyncPrio(void* fi, void* addr, s32 length, s32 offset, void (*cb)(s32, void*), s32 prio);
void __real_ARQPostRequest(void* req, u32 owner, u32 type, u32 prio, u32 src, u32 dst, u32 len, void (*cb)(u32));
u32 re4dc_strm_reads_skipped, re4dc_strm_dmas;
}

namespace {

struct Pend { void (*dvd)(s32, void*); void (*arq)(u32); void* obj; s32 res; };
Pend g_pend[8];
u32 g_pendN;
bool g_logged;

void pend_push(const Pend& p)
{
    int old = irq_disable();
    bool ok = g_pendN < 8;
    if (ok) g_pend[g_pendN++] = p;
    irq_restore(old);
    if (!ok) {   // cannot happen with 4 stream works (one read + one DMA each): complete now
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
        re4dc::fa29::hit(re4dc::fa29::SoundPendingFull);
#endif
#line 56
        if (p.dvd) p.dvd(p.res, p.obj);
        else p.arq((u32) p.obj);
    }
}

// GC sample index of nibble `nib` in the frame starting at nibble `frame`.
inline u32 nib_to_sample(u32 nib, u32 frame)
{
    u32 r = nib - frame;
    u32 in = r & 15;
    return (r >> 4) * 14 + (in >= 2 ? in - 2 : 0);
}

}  // namespace

extern "C" {

s32 __wrap_DVDReadAsyncPrio(void* fi, void* addr, s32 length, s32 offset, void (*cb)(s32, void*), s32 prio)
{
    if (cb != cb_dvd_read_end) return __real_DVDReadAsyncPrio(fi, addr, length, offset, cb, prio);
    u8* f = (u8*) fi;
    *(s32*) (f + 0x0C) = 1;   // DVDFileInfo cb.state: DVD_STATE_BUSY until the completion
    *(u32*) (f + 0x20) = 0;   // cb.transferredSize
    ++re4dc_strm_reads_skipped;
    if (!g_logged) {
        g_logged = true;
        re4dc_log("audio: disc stream player running; its GC data reads are skipped and complete at the next "
                  "audio frame (streams are heard only from bgm/aica_str.dat with AICA_AUDIO=1 AICA_STREAMS=1)\n");
    }
    pend_push(Pend{ cb, nullptr, fi, length });
    return 1;
}

void __wrap_ARQPostRequest(void* req, u32 owner, u32 type, u32 prio, u32 src, u32 dst, u32 len, void (*cb)(u32))
{
    if (cb != cb_aram_dma_end) { __real_ARQPostRequest(req, owner, type, prio, src, dst, len, cb); return; }
    __real_ARQPostRequest(req, owner, type, prio, src, dst, len, nullptr);
    ++re4dc_strm_dmas;
    pend_push(Pend{ nullptr, cb, req, 0 });
}

// Start of every audio frame, before the driver: the stream player's completions.
void re4dc_audio_pend_run(void)
{
    Pend run[8];
    int old = irq_disable();
    u32 n = g_pendN;
    memcpy(run, g_pend, n * sizeof(Pend));
    g_pendN = 0;
    irq_restore(old);
    for (u32 i = 0; i < n; i++) {
        if (run[i].dvd) {
            u8* fi = (u8*) run[i].obj;
            *(s32*) (fi + 0x0C) = 0;             // DVD_STATE_END
            *(u32*) (fi + 0x20) = (u32) run[i].res;
            run[i].dvd(run[i].res, run[i].obj);
        } else {
            run[i].arq((u32) run[i].obj);
        }
    }
}

// Moves a stream voice's AXPBADDR (u16 loopFlag, format, loop Hi/Lo, end Hi/Lo,
// current Hi/Lo) on by `samples` (fraction kept in *frac). 1 = it ran past its
// end address without a loop: the voice has stopped.
int re4dc_strm_advance(u16* a, f32 samples, f32* frac)
{
    *frac += samples;
    u32 n = (u32) *frac;
    if (!n) return 0;
    *frac -= (f32) n;
    u32 nib = ((u32) a[6] << 16) | a[7];
    u32 end = ((u32) a[4] << 16) | a[5];
    u32 lp = ((u32) a[2] << 16) | a[3];
    int stopped = 0;
    for (int guard = 0; n && guard < 16; guard++) {
        u32 r = nib & 15;
        if (r < 2) { nib = (nib & ~15u) + 2; r = 2; }   // frame header nibbles hold no sample
        u32 frame = nib & ~15u;
        if (end < nib) {
            if (a[0]) { nib = lp; continue; }
            stopped = 1;
            break;
        }
        u32 to_end = nib_to_sample(end, frame) + 1 - (r - 2);   // samples up to and including end
        u32 k = n < to_end ? n : to_end;
        u32 s = (r - 2) + k;
        nib = frame + (s / 14) * 16 + 2 + s % 14;
        n -= k;
        if (k == to_end) {
            if (a[0]) nib = lp;
            else { stopped = 1; break; }
        }
    }
    a[6] = (u16) (nib >> 16);
    a[7] = (u16) nib;
    return stopped;
}

}  // extern "C"

// ---------------------------------------------------------------------------
// Evidence knob (default off): -DRE4DC_STRM_TEST=0x<blk><no> (e.g. 0x103 = the
// r101 Ope radio stream 1:3, 0x002 = r100 BGM stream 0:2) runs the scenario's own
// sequence on that stream 5 s after the first room's sound banks are in: the
// SndStrPlayBlock request and wait for ready, play, then either its natural end
// or, after 75 s, the SndStrStopBlock stop and wait. Every step is logged with
// its time, so a capture shows the waits return.
#ifndef RE4DC_STRM_TEST
#define RE4DC_STRM_TEST 0
#endif
#if RE4DC_STRM_TEST
u32 SndStrReq(int blk, int no, int req, int time, int vol, f32 pos);   // snd.cpp (C++ linkage)
int SndStrReq(u32 id, int req, int time, int vol);
int SndStrStatusCk(u32 id, u32 status);
extern "C" u32 UseAramSize[14];
#endif

extern "C" void re4dc_strm_test_frame(void)
{
#if RE4DC_STRM_TEST
    static u32 phase, id, t_arm, t_step;
    const int blk = (RE4DC_STRM_TEST >> 8) & 15, no = RE4DC_STRM_TEST & 255;
    u32 now = (u32) (timer_us_gettime64() / 1000);
    switch (phase) {
    case 0:   // a game room's FOOT bank is in: the room is up
        if (UseAramSize[5]) { t_arm = now; phase = 1; }
        break;
    case 1:
        if (now - t_arm < 5000) break;
        id = SndStrReq(blk, no, 1, 0, 0, 0.0f);   // SndStrPlayBlock
        t_step = now;
        re4dc_log("strm test: SndStrReq(%d, %d, ready) id=%u\n", blk, no, (unsigned) id);
        phase = id ? 2 : 9;
        break;
    case 2:
        if (SndStrStatusCk(id, 2) != 1) {
            if (now - t_step > 10000) { re4dc_log("strm test: NOT READY after 10 s (the scenario would hang)\n"); phase = 9; }
            break;
        }
        re4dc_log("strm test: ready after %u ms, play\n", (unsigned) (now - t_step));
        SndStrReq(id, 2, 0, 0);
        t_step = now;
        phase = 3;
        break;
    case 3:
        if (!SndStrStatusCk(id, 0x10) && !SndStrStatusCk(id, 1)) {
            re4dc_log("strm test: ended by itself after %u ms\n", (unsigned) (now - t_step));
            phase = 9;
        } else if (now - t_step > 75000) {
            re4dc_log("strm test: still playing after 75 s (loops), stop\n");
            SndStrReq(id, 8, 0, 0);                // SndStrStopBlock
            t_step = now;
            phase = 4;
        }
        break;
    case 4:
        if (SndStrStatusCk(id, 0x10) != 0) {
            if (now - t_step > 10000) { re4dc_log("strm test: NOT STOPPED after 10 s (the scenario would hang)\n"); phase = 9; }
            break;
        }
        re4dc_log("strm test: stopped after %u ms\n", (unsigned) (now - t_step));
        phase = 9;
        break;
    default:
        break;
    }
#endif
}
