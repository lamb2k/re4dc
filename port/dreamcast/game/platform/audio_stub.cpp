// Sound and movie interfaces, first stage: silent. The AX voice API hands out
// voice blocks and accepts every parameter; the 5 ms audio-frame callback the
// sound driver registers (snd_main.cpp cb_audio_frame) runs from the vblank
// interrupt at 60 Hz so the driver's state machines advance; ARAM requests
// complete at once without a copy (the 7 MB ARAM has no Dreamcast home yet,
// see R4_ASSET_RESIDENCY_PLAN.md); Sofdec/ADX report no movie.
#include <kos.h>
#include <string.h>

#include "re4dc_platform.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef signed long s32;
typedef unsigned long u32;
typedef float f32;

typedef void (*ARQCallback)(u32);
// AICA_AUDIO=1 (Makefile) replaces the AX / MIX / SYN / SEQ interfaces below
// with platform/audio_aica.cpp and routes ARAM sound uploads to it.
#if !RE4DC_AICA_AUDIO
typedef void (*AXCallback)(void);
struct AXVPB { u32 w[128]; };  // 0x200: larger than the SDK's voice block

static AXVPB g_voices[64];
static u8 g_voiceUsed[64];
static AXCallback g_axCallback;
// Stream player voices (acquired with cb_str_voice_drop): pb.state / pb.addr /
// pb.src are kept at the SDK offsets and the address advanced each audio frame
// (audio_strm.cpp), so a stream runs for its length and ends, silently.
static u8 g_strmVoice[64];
static f32 g_strmFrac[64];
static uint64_t g_strmLastUs, g_tickUs;
static const u32 kPb = 0x138, kPbState = kPb + 0x0E, kPbAddr = kPb + 0x6E, kPbSrc = kPb + 0xA6;
static inline u16* pb16(AXVPB* p, u32 ofs) { return (u16*) ((u8*) p + ofs); }
#endif
static u32 g_aramNext = 0x4000;

extern "C" {

u32 re4dc_vi_retrace_count(void);
void re4dc_audio_pend_run(void);                           // audio_strm.cpp
#if RE4DC_AICA_AUDIO
void re4dc_audio_arq(u32 src, u32 dst, u32 len);
#else
void cb_str_voice_drop(void* voice);                        // snd_str3.cpp
int re4dc_strm_advance(u16* addr, f32 samples, f32* frac);  // audio_strm.cpp
void re4dc_strm_test_frame(void);                           // audio_strm.cpp (RE4DC_STRM_TEST)

// Once per game frame (pad.cpp PADRead): the driver's 5 ms audio frames that
// wall time owes (the GC AI interrupt rate, as audio_aica.cpp's thread runs
// them; at most 64 after a stall), each after the stream player's I/O
// completions; then the stream voices move on in real time.
void re4dc_audio_frame(void)
{
    uint64_t now = timer_us_gettime64();
    if (!g_strmLastUs) g_strmLastUs = g_tickUs = now - 5000;
    u32 ticks = (u32) ((now - g_tickUs) / 5000);
    if (ticks > 64) { ticks = 64; g_tickUs = now; }
    else g_tickUs += ticks * 5000ull;
    for (u32 t = 0; t < ticks; t++) {
        re4dc_audio_pend_run();
        if (g_axCallback) {
            g_axCallback();
        }
    }
    f32 dt = (f32) (now - g_strmLastUs) * 1e-6f;
    g_strmLastUs = now;
    for (int i = 0; i < 64; i++) {
        AXVPB* p = &g_voices[i];
        if (!g_voiceUsed[i] || !g_strmVoice[i] || !*pb16(p, kPbState)) continue;
        u16* src = pb16(p, kPbSrc);
        f32 ratio = (f32) (((u32) src[0] << 16) | src[1]) / 65536.0f;
        if (re4dc_strm_advance(pb16(p, kPbAddr), dt * ratio * 32000.0f, &g_strmFrac[i])) *pb16(p, kPbState) = 0;
    }
    re4dc_strm_test_frame();
}

void AIInit(u8* stack) { (void) stack; }
void AIReset(void) {}
void AXInitEx(u32 mode) { (void) mode; memset(g_voiceUsed, 0, sizeof(g_voiceUsed)); }
void AXQuit(void) {}
void AXSetMode(u32 mode) { (void) mode; }
void AXSetCompressor(u32 sw) { (void) sw; }
u32 AXGetDspCycles(void) { return 0; }
u32 AXGetMaxDspCycles(void) { return 0; }
AXCallback AXRegisterCallback(AXCallback cb) { AXCallback old = g_axCallback; g_axCallback = cb; return old; }
void AXRegisterAuxACallback(void (*cb)(void*, void*), void* ctx) { (void) cb; (void) ctx; }
void AXRegisterAuxBCallback(void (*cb)(void*, void*), void* ctx) { (void) cb; (void) ctx; }

AXVPB* AXAcquireVoice(u32 prio, void (*cb)(void*), u32 user)
{
    (void) prio; (void) user;
    for (int i = 0; i < 64; i++) {
        if (!g_voiceUsed[i]) {
            g_voiceUsed[i] = 1;
            g_strmVoice[i] = cb == cb_str_voice_drop;
            g_strmFrac[i] = 0;
            memset(&g_voices[i], 0, sizeof(AXVPB));
            g_voices[i].w[1] = (u32) i;  // the SDK keeps the index at +4
            return &g_voices[i];
        }
    }
    return 0;
}
void AXFreeVoice(AXVPB* p) { if (p) g_voiceUsed[p - g_voices] = 0; }
void AXSetVoiceState(AXVPB* p, u16 s) { if (g_strmVoice[p - g_voices]) *pb16(p, kPbState) = s; }
void AXSetVoiceType(AXVPB* p, u16 t) { (void) p; (void) t; }
void AXSetVoicePriority(AXVPB* p, u32 prio) { (void) p; (void) prio; }
void AXSetVoiceAddr(AXVPB* p, void* a) { if (g_strmVoice[p - g_voices]) memcpy(pb16(p, kPbAddr), a, 16); }
void AXSetVoiceAdpcm(AXVPB* p, void* a) { (void) p; (void) a; }
void AXSetVoiceAdpcmLoop(AXVPB* p, void* a) { (void) p; (void) a; }
void AXSetVoiceLoop(AXVPB* p, u16 l) { if (g_strmVoice[p - g_voices]) pb16(p, kPbAddr)[0] = l; }
void AXSetVoiceLoopAddr(AXVPB* p, u32 a)
{
    if (g_strmVoice[p - g_voices]) { pb16(p, kPbAddr)[2] = (u16) (a >> 16); pb16(p, kPbAddr)[3] = (u16) a; }
}
void AXSetVoiceEndAddr(AXVPB* p, u32 a)
{
    if (g_strmVoice[p - g_voices]) { pb16(p, kPbAddr)[4] = (u16) (a >> 16); pb16(p, kPbAddr)[5] = (u16) a; }
}
void AXSetVoiceSrc(AXVPB* p, void* s) { if (g_strmVoice[p - g_voices]) memcpy(pb16(p, kPbSrc), s, 4); }
void AXSetVoiceSrcType(AXVPB* p, u32 t) { (void) p; (void) t; }
void AXSetVoiceSrcRatio(AXVPB* p, f32 r) { (void) p; (void) r; }
void AXSetVoiceLpf(AXVPB* p, void* l) { (void) p; (void) l; }
void AXSetVoiceLpfCoefs(AXVPB* p, u16 a0, u16 b0) { (void) p; (void) a0; (void) b0; }

// AXFX effects: init/settings return success, callbacks do nothing.
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
void MIXInitChannel(AXVPB* p, u32 mode, int in, int auxA, int auxB, int pan, int span, int fader) { (void) p; (void) mode; (void) in; (void) auxA; (void) auxB; (void) pan; (void) span; (void) fader; }
void MIXReleaseChannel(AXVPB* p) { (void) p; }
void MIXSetInput(AXVPB* p, int dB) { (void) p; (void) dB; }
void MIXSetAuxA(AXVPB* p, int dB) { (void) p; (void) dB; }
void MIXSetAuxB(AXVPB* p, int dB) { (void) p; (void) dB; }
void MIXSetPan(AXVPB* p, int pan) { (void) p; (void) pan; }
void MIXSetSPan(AXVPB* p, int span) { (void) p; (void) span; }
void MIXSetSoundMode(u32 mode) { (void) mode; }
void MIXUpdateSettings(void) {}

void SYNInit(void) {}
void SYNQuit(void) {}
void SYNInitSynth(void* s, void* wt, u32 aram, u32 zero, u32 p1, u32 p2, u32 p3) { (void) s; (void) wt; (void) aram; (void) zero; (void) p1; (void) p2; (void) p3; }
void SYNQuitSynth(void* s) { (void) s; }
void SYNRunAudioFrame(void) {}
void SYNMidiInput(void* s, u8* in) { (void) s; (void) in; }
u32 SYNGetActiveNotes(void* s) { (void) s; return 0; }
void SYNSetMasterVolume(void* s, s32 dB) { (void) s; (void) dB; }
void SEQInit(void) {}
void SEQQuit(void) {}
void SEQRunAudioFrame(void) {}
// AICA RAM held by the audio backend (movie audio's free-AICA figure); none here.
unsigned re4dc_aica_used_bytes(void) { return 0; }
unsigned re4dc_aica_skipped_blocks(void) { return 0; }
#endif  // !RE4DC_AICA_AUDIO

// ARAM: addresses are handed out, requests complete without a transfer.
// The allocator is the SDK's (src/lib/ar.c): a stack of at most the
// ARInit entry count, popped by ARFree, over the GameCube's 16 MB. The game
// takes one block at SndInit for the sound region and addresses the rest
// (room/world data, sub screen) at fixed offsets, so the stack pointer is
// constant across rooms; re4dc_aram_state reports it for the room audit and
// any overrun halts instead of silently handing out overlapping addresses.
static const u32 kAramSize = 0x1000000;
static u32* g_aramBlockLength;
static u32 g_aramFreeBlocks;
static int g_aramInit;

u32 ARInit(u32* stack, u32 n)
{
    if (g_aramInit) {
        return 0x4000;
    }
    g_aramNext = 0x4000;
    g_aramFreeBlocks = n;
    g_aramBlockLength = stack;
    g_aramInit = 1;
    return g_aramNext;
}
u32 ARGetBaseAddress(void) { return 0x4000; }
u32 ARGetSize(void) { return kAramSize; }
u32 ARGetInternalSize(void) { return kAramSize; }
int ARCheckInit(void) { return g_aramInit; }
u32 ARAlloc(u32 len)
{
    int old = irq_disable();
    len = (len + 31) & ~31u;
    if (!g_aramInit || g_aramFreeBlocks == 0 || len > kAramSize - g_aramNext) {
        irq_restore(old);
        re4dc_log("ARAlloc(%lu): init=%d free_blocks=%lu sp=%08lx\n", len, g_aramInit, g_aramFreeBlocks, g_aramNext);
        re4dc_missing("ARAlloc out of ARAM or blocks");
        return 0;
    }
    u32 a = g_aramNext;
    g_aramNext += len;
    *g_aramBlockLength++ = len;
    g_aramFreeBlocks--;
    irq_restore(old);
    return a;
}
u32 ARFree(u32* length)
{
    int old = irq_disable();
    g_aramBlockLength--;
    if (length) {
        *length = *g_aramBlockLength;
    }
    g_aramNext -= *g_aramBlockLength;
    g_aramFreeBlocks++;
    u32 sp = g_aramNext;
    irq_restore(old);
    return sp;
}
void re4dc_aram_state(u32* stack_pointer, u32* free_blocks)
{
    *stack_pointer = g_aramNext;
    *free_blocks = g_aramFreeBlocks;
}
void ARQInit(void) {}
void ARQFlushQueue(void) {}
// ARQRequest (include/dolphin/ar.h): the SDK fills the request before the
// transfer and hands it back to the callback, which reads owner/length
// from it (dvd.cpp trans2aram_cb). There is no auxiliary RAM here: the
// transfer itself is not performed (the sound data path is stubbed).
struct ARQRequestView {
    ARQRequestView* next;
    u32 owner;
    u32 type;
    u32 priority;
    u32 source;
    u32 dest;
    u32 length;
    ARQCallback callback;
};

void ARQPostRequest(void* req, u32 owner, u32 type, u32 prio, u32 src, u32 dst, u32 len, ARQCallback cb)
{
    ARQRequestView* r = (ARQRequestView*) req;
    r->next = NULL;
    r->owner = owner;
    r->type = type;
    r->priority = prio;
    r->source = src;
    r->dest = dst;
    r->length = len;
    r->callback = cb;
#if RE4DC_AICA_AUDIO
    if (type == 0) {  // ARQ_TYPE_MRAM_TO_ARAM: sound blocks are converted into AICA RAM
        re4dc_audio_arq(src, dst, len);
    }
#endif
    if (cb) {
        cb((u32) req);
    }
}

// Sofdec / ADX
void ADXGC_SetupDvdFs(int a) { (void) a; }
void ADXM_ExecMain(void) {}
void ADXM_SetCbErr(void* f, void* o) { (void) f; (void) o; }
void ADXT_SetOutputMono(int m) { (void) m; }
void mwPlyInitSfdFx(void* prm) { (void) prm; }
int mwPlyCalcWorkCprmSfd(void* prm) { (void) prm; return 0x1000; }
void* mwPlyCreateSofdec(void* prm) { (void) prm; re4dc_log("mwPlyCreateSofdec: no movie playback yet\n"); return 0; }
void mwPlyGetHdrInf(void* buf, int size, void* info) { (void) buf; (void) size; memset(info, 0, 0x40); }
void mwPlyGetCurFrm(void* hn, void* frm) { (void) hn; memset(frm, 0, 0x40); }
void mwPlyRelCurFrm(void* hn) { (void) hn; }
int mwPlyGetNumSkipDec(void* hn) { (void) hn; return 0; }
int mwPlyGetNumSkipDisp(void* hn) { (void) hn; return 0; }
void mwPlyFxSetOutBufSize(void* hn, int w, int h) { (void) hn; (void) w; (void) h; }
void mwPlyFxSetOutBufPitchHeight(void* hn, int p, int h) { (void) hn; (void) p; (void) h; }
void mwPlyFxCnvFrmARGB8888(void* hn, void* frm, void* buf) { (void) hn; (void) frm; (void) buf; }
void mwPlyFxCnvFrmY84C44(void* hn, void* frm, void* y, void* uv) { (void) hn; (void) frm; (void) y; (void) uv; }

}  // extern "C"
