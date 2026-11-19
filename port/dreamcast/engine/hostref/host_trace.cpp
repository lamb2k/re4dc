// hostref (PC side): per-tick bookkeeping for the trace (stub calls: count, FNV of the names in call
// order, the distinct names; the generator's call count) and the run log. Also OSReport, which the game
// declares with its own va_list: defined here, with the PC's, so the format is expanded correctly.
#include "hostref.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned host_rnd_calls;
static unsigned g_calls, g_hash = 2166136261u;
static char g_names[160];
FILE* host_log_file;

extern "C" void host_log(const char* fmt, ...)
{
    FILE* f = host_log_file ? host_log_file : stderr;
    va_list ap;
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
    size_t n = strlen(fmt);
    if (!n || fmt[n - 1] != '\n') fputc('\n', f);
}

extern "C" void host_fatal(int code, const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "re4ref: ");
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
    if (host_log_file) fflush(host_log_file);
    exit(code);
}

extern "C" void OSReport(const char* fmt, ...)
{
    FILE* f = host_log_file ? host_log_file : stderr;
    va_list ap;
    va_start(ap, fmt);
    fprintf(f, "OSReport: ");
    vfprintf(f, fmt, ap);
    va_end(ap);
}

extern "C" void host_stub_hit(const char* name)
{
    ++g_calls;
    for (const char* c = name; *c; ++c) g_hash = (g_hash ^ (unsigned char) *c) * 16777619u;
    g_hash = (g_hash ^ 0x2Fu) * 16777619u;
    // the distinct names, as long as they fit
    size_t used = strlen(g_names);
    size_t n = strlen(name);
    for (const char* s = g_names; (s = strstr(s, name)); s += n)
        if ((s == g_names || s[-1] == '+') && (s[n] == 0 || s[n] == '+')) return;
    if (used + n + 2 < sizeof g_names) {
        if (used) g_names[used++] = '+';
        memcpy(g_names + used, name, n + 1);
    }
}

extern "C" void host_stub_tick_reset()
{
    g_calls = 0;
    g_hash = 2166136261u;
    g_names[0] = 0;
    host_rnd_calls = 0;
}

extern "C" uint32_t host_stub_calls() { return g_calls; }
extern "C" uint32_t host_stub_hash() { return g_hash; }
extern "C" const char* host_stub_names() { return g_names[0] ? g_names : "-"; }

// The old port's log (re4dc_platform.h), reached by a few original files with every knob off.
extern "C" void re4dc_log(const char* fmt, ...)
{
    FILE* f = host_log_file ? host_log_file : stderr;
    va_list ap;
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
}

// GX (GameCube graphics) state and vertex calls that only drawing code reaches (the weapon's laser
// sight and debug lines). C linkage, caller-cleaned arguments: an empty body is safe for every one.
#define HOST_GX_NOOP(name) extern "C" void name() {}
HOST_GX_NOOP(GXBegin)
HOST_GX_NOOP(GXClearVtxDesc)
HOST_GX_NOOP(GXLoadPosMtxImm)
HOST_GX_NOOP(GXSetBlendMode)
HOST_GX_NOOP(GXSetChanCtrl)
HOST_GX_NOOP(GXSetCullMode)
HOST_GX_NOOP(GXSetCurrentMtx)
HOST_GX_NOOP(GXSetNumChans)
HOST_GX_NOOP(GXSetNumTevStages)
HOST_GX_NOOP(GXSetNumTexGens)
HOST_GX_NOOP(GXSetTevOp)
HOST_GX_NOOP(GXSetTevOrder)
HOST_GX_NOOP(GXSetVtxAttrFmt)
HOST_GX_NOOP(GXSetVtxDesc)
HOST_GX_NOOP(GXSetZMode)
