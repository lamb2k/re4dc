// platform/play_read_log.cpp: DISC_READ_LOG=2 (lane coldread27 2026-11-02; diagnostic, log only, default 0 = file not
// built; needs DISC_READ_METER=1, not with DOOR_PROBE / IO_PROBE, which wrap the same fs entry points).
// Names the files behind the DISCRD window lines: fs_open keeps each handle's path tail, fs_read adds the read's bytes
// and wall time to that file's row for the current window, and at each DISCRD window close (dvd_read_safe.cpp)
// one "DRF:" line per file read in the window (the 8 largest by blocked time), tagged with the window's phase
// (play / load / movie) and the first reading thread's label. The PLAY-DISC-READ gate (tools/d367/rr/play_disc_read.py)
// lists the phase=play rows; motion keys show as dc/mot/<key>.fcv.
#include <kos.h>
#include <string.h>
#include "re4dc_platform.h"

extern "C" file_t __real_fs_open(const char* fn, int mode);
extern "C" ssize_t __real_fs_read(file_t hnd, void* buffer, size_t cnt);

namespace {
constexpr unsigned kHandles = 32, kFiles = 24, kTail = 31;
struct Handle { file_t fd; bool used; char path[kTail + 1]; };
struct Row { char path[kTail + 1]; char thr[12]; unsigned n, bytes; unsigned long long us; };
Handle handles[kHandles];
Row rows[kFiles];
unsigned nrows, dropped;

Row* row_for(const char* path)
{
    for (unsigned i = 0; i < nrows; ++i) if (!strcmp(rows[i].path, path)) return &rows[i];
    if (nrows == kFiles) { ++dropped; return nullptr; }
    Row* r = &rows[nrows++];
    memset(r, 0, sizeof(*r));
    strcpy(r->path, path);
    strncpy(r->thr, thd_current && thd_current->label ? thd_current->label : "-", sizeof(r->thr) - 1);
    return r;
}
}  // namespace

extern "C" file_t __wrap_fs_open(const char* fn, int mode)
{
    const file_t fd = __real_fs_open(fn, mode);
    if (fd < 0 || !fn) return fd;
    const size_t len = strlen(fn);
    const int o = irq_disable();
    Handle* slot = nullptr;
    for (auto& h : handles) if (h.used && h.fd == fd) { slot = &h; break; }
    if (!slot) for (auto& h : handles) if (!h.used) { slot = &h; break; }
    if (!slot) slot = &handles[(unsigned) fd % kHandles];
    slot->fd = fd;
    slot->used = true;
    strncpy(slot->path, len > kTail ? fn + len - kTail : fn, kTail);
    slot->path[kTail] = 0;
    irq_restore(o);
    return fd;
}

extern "C" ssize_t __wrap_fs_read(file_t hnd, void* buffer, size_t cnt)
{
    const unsigned long long t0 = timer_us_gettime64();
    const ssize_t r = __real_fs_read(hnd, buffer, cnt);
    const unsigned long long us = timer_us_gettime64() - t0;
    const int o = irq_disable();
    for (auto& h : handles) {
        if (!h.used || h.fd != hnd) continue;
        if (Row* w = row_for(h.path)) { ++w->n; w->us += us; w->bytes += r > 0 ? (unsigned) r : 0u; }
        break;
    }
    irq_restore(o);
    return r;
}

// dvd_read_safe.cpp re4dc_disc_meter_window, after the DISCRD window line (the game thread).
extern "C" void re4dc_play_read_window(const char* phase)
{
    Row copy[kFiles];
    const int o = irq_disable();
    const unsigned n = nrows, d = dropped;
    memcpy(copy, rows, sizeof(Row) * n);
    nrows = dropped = 0;
    irq_restore(o);
    for (unsigned k = 0; k < 8 && k < n; ++k) {
        unsigned best = k;
        for (unsigned i = k + 1; i < n; ++i) if (copy[i].us > copy[best].us) best = i;
        const Row t = copy[k]; copy[k] = copy[best]; copy[best] = t;
        re4dc_log("DRF: phase=%s file=%s reads=%u kb=%u ms=%u thr=%s\n", phase, copy[k].path, copy[k].n,
                  (copy[k].bytes + 1023) / 1024, (unsigned) (copy[k].us / 1000), copy[k].thr);
    }
    if (n > 8 || d) re4dc_log("DRF: phase=%s more_files=%u dropped=%u\n", phase, n > 8 ? n - 8 : 0, d);
}
