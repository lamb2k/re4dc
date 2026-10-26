// DVD_READ_SAFE=1 (Phase 2 D4, default 0) and its test hook DVD_STUCK_TEST (default 0); built only with one of them.
//
// With the full test 7 data and the GC-bake r119 package, r119 after the boss logged "cdrom_stream_request: Previous
// DMA request is in progress" for every later disc stream request: 249 texture uploads failed and every tex.pak index
// re-read failed until the end of the run. The refusals never stop, so KOS's dma_in_progress flag (hardware/cdrom.c)
// is stuck, not briefly busy: once a stream command is running, the vblank handler leaves the flag alone (the command
// reports "streaming") and only a G1 DMA completion clears it. Which earlier request left it set depends on timing
// (the same configuration passes with the image a few hundred bytes larger).
//
// DVD_READ_SAFE=1 wraps cdrom_stream_start / cdrom_stream_request. A request KOS refuses (ERR_SYS) is retried for up
// to 10 ms (a genuine DMA would be done by then: fs_iso9660 serialises its reads and waits for each one); if it is
// still refused the flag is stale, so it is cleared the only public way, cdrom_abort_cmd(timeout, abort_dma=true),
// which aborts the stream command too (the G1 ATA semaphore is taken first: that abort path assumes it is held and
// signals it at the end). The stream is then started again where it stood (it is only restartable at a sector
// boundary of what was already handed out) and the request repeated. A request that succeeds the first time takes
// the old path, with one counter update.
//
// DVD_STUCK_TEST=<seconds> (test discs only, with DVD_STUCK_ADDR): sets the flag just before the first stream start after
// that much uptime: the stuck state on demand, with or without the fix.
//
// DISC_READ_FALLBACK=1 (issue #28, default 0): reads that a disc emulator does not complete. DreamShell's ISO loader
// (IDE-modded console) crashed test 10 at boot in Snd_str_blk_init: its log showed "cdrom_abort_cmd: Timeout exceeded,
// resetting." and then "DVD: Read Ok" for the sound stream table, whose contents were not the file. KOS ends a blocking
// DMA wait (cdrom_stream_request, cdrom_read_sectors_ex with dma) when the vblank handler sees the GD command no
// longer busy, and returns ERR_OK without checking that the transfer happened; when the emulated stream command
// fails, the buffer keeps its old bytes and fs_iso9660's stream stop then times out (the reset in the log). The fix:
// before each DMA read the last 32 bytes of the destination get a marker (written through the uncached P2 mirror: the
// read's dcache invalidate would drop a cached write); if the marker is still there after an "OK" read, or the read
// failed, or a stream stop timed out, the session latches to PIO: the read is done again by PIO sector reads
// (cdrom_read_sectors_ex dma=false, the stream stopped first), later stream starts are refused (fs_iso9660 then uses
// sector reads) and later sector reads use PIO. Normal discs never trip it: the cost is the marker (two 32-byte
// uncached accesses per DMA read).
//
// DISC_FAIL_TEST=1|2 (test discs only): every DMA stream request (1), and also every DMA sector read (2), is skipped
// and reported OK, as the emulator does: the failure on demand, with or without the fix.
//
// DISC_READ_VERIFY=1 (test 11 console faults, default 0): the console halted with disc-loaded data that was not the
// file (a model's texture pointer 0x99158863 in cModel::modelInit, OT links holding code or motion-key bytes), early
// and outside radio calls, never on Flycast (whose BIOS stream and sector DMAs land inside the syscall). KOS wakes a
// blocking DMA waiter from its vblank handler as soon as the BIOS says the GD command is no longer busy or streaming,
// without looking at the G1 DMA engine; a read handed back before its bytes land gives the caller the old memory and
// lets the late bytes overwrite whatever uses that memory next. With this knob a DMA read that KOS reports done waits
// until SB_GDST (G1 GD-DMA start/status, 0xA05F7418) is idle (2 s bound) and re-invalidates the destination's cache
// lines when it had to wait; fs_iso9660's one non-blocking request (32 bytes) is made blocking to get the same wait;
// DVD_READ_SAFE's stale-flag abort is held off while the engine is still running (2 s). Every late completion logs a
// "disc read verify:" line with counters.
//
// DISC_READ_FALLBACK=2 (issue #28 v2, default 0): the v1 disc (=1) gave a black screen with no text on the tester's
// DreamShell ISO loader, DMA on and off. v1 latched to PIO sector reads, which go through KOS cdrom_exec_cmd: a
// thd_poll with no timeout whose poll callback (BIOS exec_server + check_command) runs inside the scheduler with
// interrupts masked, so a loader that never completes a PIO read stops every thread, the 30 s crash watchdog included.
// v1 also checked its marker through the uncached mirror while a loader that copies by CPU leaves the data in dirty
// cache lines (a false "did not land"). DreamShell's stream path returns the raw 2352-byte track bytes (headers not
// stripped) of our track03.bin, so a stream never delivers the file there. v2:
// - no cdrom_stream at all: every stream start is refused, so fs_iso9660 reads by sector reads only;
// - every sector read is this file's own GD command (send_command, then exec_server / check_command polled from the
//   calling thread with interrupts on, never from the scheduler): DMA first, each wait bounded (drive lock 30 s, command
//   5 s + 8 ms per sector, GD-DMA engine idle 1 s, abort 1 s then BIOS reset + init, late landing 250 ms);
// - the marker check writes the marker line back first (dcache purge) and allows a late landing;
// - a read that fails, times out or does not land: the drive is re-initialised (bounded CD_CMD_INIT, cdrom_reinit is
//   wrapped too) and the DMA read retried once, then a PIO read; the method that worked is reported and kept (PIO is
//   latched); if all fail, a "DISC READ FAILED" screen stays up (redrawn every second) instead of a silent hang;
// - an on-screen boot log until the game's first picture (re4dc_disc_note, 5x7 font straight into the displayed frame
//   buffer, no BIOS font): drive init, first read, every fallback, the sound stream table check (snd.cpp), and a
//   status row naming the read in flight, so a call that never returns still leaves "now: ... lba=" on the screen.
// DISC_FAIL_TEST with =2 (test discs only): 2 = DMA reads report done without a transfer (PIO then works), 3 = as 2 and
// PIO never completes (all fail: the FAILED screen), 4 = the first DMA read never completes and its abort never
// finishes (BIOS reset, reinit, DMA retry), 5 = the first read spins with interrupts off (a BIOS call that never returns).
#include <kos.h>
#include <dc/cdrom.h>

#include "re4dc_platform.h"

#if defined(RE4DC_DISC_PIO_FALLBACK) && RE4DC_DISC_PIO_FALLBACK
#include <dc/asic.h>
#include "disc_pio_fallback.h"
#if !defined(RE4DC_DISC_READ_FALLBACK) || RE4DC_DISC_READ_FALLBACK < 2
#error DISC_PIO_FALLBACK requires DISC_READ_FALLBACK 2 or 3
#endif
#endif

#ifndef RE4DC_DVD_READ_SAFE
#define RE4DC_DVD_READ_SAFE 0
#endif
#ifndef RE4DC_DVD_STUCK_TEST
#define RE4DC_DVD_STUCK_TEST 0
#endif
#ifndef RE4DC_DISC_READ_FALLBACK
#define RE4DC_DISC_READ_FALLBACK 0
#endif
#ifndef RE4DC_DISC_FAIL_TEST
#define RE4DC_DISC_FAIL_TEST 0
#endif
#ifndef RE4DC_DISC_READ_VERIFY
#define RE4DC_DISC_READ_VERIFY 0
#endif
// DISC_READ_FALLBACK=3 (test 15, user decision 10-16 "option A"): the stream reads of =0 (the fast path, unchanged
// timing) with =1's checks (each DMA request's last 32 bytes marked and checked), and on the first stream or sector
// read that fails, times out or does not land, a session latch: from then on every read is =2's plain bounded sector
// read (v2::read: DMA, DMA after a bounded drive re-init, then PIO) and no stream is started again.
#define RE4DC_FB_V1 (RE4DC_DISC_READ_FALLBACK == 1 || RE4DC_DISC_READ_FALLBACK == 3)
#ifndef RE4DC_DISC_FAIL_AFTER_S
#define RE4DC_DISC_FAIL_AFTER_S 0
#endif

extern "C" int __real_cdrom_stream_start(int sector, int cnt, bool dma);
extern "C" int __real_cdrom_stream_request(void* buffer, size_t size, bool block);
extern "C" semaphore_t _g1_ata_sem;
#if RE4DC_DISC_READ_FALLBACK || RE4DC_DISC_FAIL_TEST || RE4DC_DISC_READ_VERIFY || RE4DC_DISC_READ_METER
extern "C" int __real_cdrom_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma);
#endif
#if RE4DC_DISC_READ_FALLBACK || RE4DC_DISC_FAIL_TEST || RE4DC_DISC_READ_VERIFY
extern "C" int __real_cdrom_stream_stop(bool abort_dma);
#endif
#if defined(RE4DC_DISC_DMA_WAIT_TIMEOUT) && RE4DC_DISC_DMA_WAIT_TIMEOUT
// DISC_DMA_WAIT_TIMEOUT=1 (issue #28): KOS's DMA wait gave up (kos-804b319-cdrom-dma-wait-timeout.patch); the caller below
// falls back to plain reads. Counters are KOS's.
extern "C" unsigned re4dc_cdrom_wait_timeouts, re4dc_cdrom_wait_max_us, re4dc_cdrom_wait_last_ms;
extern "C" unsigned re4dc_cdrom_wait_hw_busy, re4dc_cdrom_wait_abort_reset;
static void dma_wait_timeout_log(const char* what, uint32_t at, size_t bytes)
{
    re4dc_log("disc dma wait timeout: %s (%u bytes at %u) got no completion in %u ms; GD DMA stopped (engine was busy "
              "%u, drive reset %u); falling back to plain reads (timeouts %u)\n", what, (unsigned) bytes, (unsigned) at,
              re4dc_cdrom_wait_last_ms, re4dc_cdrom_wait_hw_busy, re4dc_cdrom_wait_abort_reset, re4dc_cdrom_wait_timeouts);
}
// The longest completed DMA wait so far, logged when it grows by a quarter (how far normal reads stay from the bound).
static unsigned s_wait_max_logged;
static void dma_wait_note(size_t bytes)
{
    const unsigned m = re4dc_cdrom_wait_max_us;
    if (m > s_wait_max_logged + s_wait_max_logged / 4 + 1000u) {
        s_wait_max_logged = m;
        re4dc_log("disc dma wait max: %u us (request %u bytes; bound 5000 ms + 8 ms a sector)\n", m, (unsigned) bytes);
    }
}
#endif

#if RE4DC_DISC_READ_METER
// DISC_READ_METER=1 (Makefile; T12 Phases disc, display / log only). Every drive call made through the wraps below
// (stream start, stream request, sector read) is "in flight" while it runs; requests and sector reads count as reads
// with their bytes. Time inside a call is the game's blocked time only when the game made it: the main thread (the one
// that closes the pace windows, pace.cpp) or a source task thread (os.cpp "re4-task": the frame waits for the task); other
// threads' reads count for the marker, reads and KB only (the last one's label is logged as other=).
// fs_iso9660's one non-blocking request (32 bytes) is followed by a poll outside the wrap: not in the blocked time.
#include <arch/irq.h>
#include <arch/timer.h>
#include <kos/thread.h>
#include <string.h>
namespace {
unsigned m_busy, m_seen;                       // drive calls in flight; one ran since the HUD last looked
unsigned m_reads, m_bytes;                     // this window
unsigned m_mbusy, m_mseen, m_mreads, m_mbytes; // the same for the music stream thread (kept apart)
kthread_t* m_music;
kthread_t* m_other;                            // the last thread other than the game / music thread that read
unsigned long long m_block_us, m_t0;           // game-thread time inside drive calls this window; window start
unsigned m_tot_reads;                          // since boot (room-entry deltas)
unsigned long long m_tot_bytes, m_tot_block;
kthread_t* m_game;
unsigned m_rate[3];                            // last window: reads/s, KB/s, blocked ms/s
bool m_room_pending;
const char* m_room_from = "";
unsigned long long m_room_t0, m_room_until, m_room_b0, m_room_k0;
unsigned m_room_r0, m_room_ms;
struct DiscMeterScope {
    unsigned long long t0;
    bool game, music;
    DiscMeterScope(size_t bytes, bool read)
    {
        music = m_music && thd_current == m_music;
        if (music) {
            const int o = irq_disable();
            ++m_mbusy;
            m_mseen = 1;
            if (read) {
                ++m_mreads;
                m_mbytes += (unsigned) bytes;
            }
            irq_restore(o);
            game = false;
            t0 = 0;
            return;
        }
        const int o = irq_disable();
        ++m_busy;
        m_seen = 1;
        if (read) {
            ++m_reads;
            m_bytes += (unsigned) bytes;
            ++m_tot_reads;
            m_tot_bytes += bytes;
        }
        irq_restore(o);
        // the game: the main thread and the source task threads (os.cpp "re4-task": a task's read stalls the frame)
        game = m_game && (thd_current == m_game || !strncmp(thd_current->label, "re4-task", 8));
        if (!game) m_other = thd_current;
        t0 = game ? timer_us_gettime64() : 0;
    }
    ~DiscMeterScope()
    {
        if (music) {
            const int o = irq_disable();
            --m_mbusy;
            m_mseen = 1;
            irq_restore(o);
            return;
        }
        const unsigned long long us = game ? timer_us_gettime64() - t0 : 0;
        const int o = irq_disable();
        m_block_us += us;
        m_tot_block += us;
        --m_busy;
        m_seen = 1;
        irq_restore(o);
    }
};
}  // namespace
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
extern "C" void re4dc_bench_disc(unsigned reads, unsigned long long block_us, unsigned long long dt_us);  // bench.cpp
#endif

#if defined(RE4DC_MOTION_STATS_LOG) && RE4DC_MOTION_STATS_LOG
#include "native_motion.h"
extern "C" int re4dc_static_heap_free();             // ui_bridge.cpp: heap 4 free bytes (-1 when inactive)
extern "C" void re4dc_motion_ws_window();             // native_motion.cpp: the MOTWS working-set lines
namespace {
// MOTION_STATS_LOG (Makefile): the native motion cache per DISCRD window.
void motion_stats_window(unsigned window_ms)
{
    static Re4dcMotionStats last;
    Re4dcMotionStats s;
    re4dc_motion_get_stats(&s);
    re4dc_log("MOTSTAT: window_ms=%u misses=%u evictions=%u kb=%u hits=%u resident=%u peak=%u hot=%u heap4=%d\n",
              window_ms, s.misses - last.misses, s.evictions - last.evictions, (unsigned) ((s.bytes_read - last.bytes_read) / 1024),
              s.hits - last.hits, s.resident_bytes, s.peak_cache_bytes, s.hot_bytes,
              s.metadata_bytes ? re4dc_static_heap_free() : -1);   // a room heap only while an archive is bound
    last = s;
    re4dc_motion_ws_window();
}
}  // namespace
#endif
// pace.cpp, each one-second window close (the game thread).
extern "C" void re4dc_disc_meter_window(void)
{
    const unsigned long long now = timer_us_gettime64();
    m_game = thd_current;
    const int o = irq_disable();
    const unsigned reads = m_reads, bytes = m_bytes, mreads = m_mreads, mbytes = m_mbytes;
    const unsigned long long block = m_block_us;
    m_reads = m_bytes = m_mreads = m_mbytes = 0;
    m_block_us = 0;
    irq_restore(o);
    if (m_t0) {
        const unsigned long long dt = now > m_t0 ? now - m_t0 : 1;
        m_rate[0] = (unsigned) ((reads * 1000000ULL + dt / 2) / dt);
        m_rate[1] = (unsigned) ((bytes * 1000000ULL / 1024 + dt / 2) / dt);
        m_rate[2] = (unsigned) ((block * 1000ULL + dt / 2) / dt);
        if (reads || block)
            re4dc_log("DISCRD: window_ms=%u reads=%u kb=%u block_ms=%u (per s: reads=%u kb=%u block_ms=%u) music reads=%u kb=%u other=%s\n",
                      (unsigned) (dt / 1000), reads, bytes / 1024, (unsigned) (block / 1000), m_rate[0], m_rate[1], m_rate[2],
                      mreads, mbytes / 1024, m_other ? m_other->label : "-");
        m_other = nullptr;
#if defined(RE4DC_MOTION_STATS_LOG) && RE4DC_MOTION_STATS_LOG
        motion_stats_window((unsigned) (dt / 1000));
#endif
#if defined(RE4DC_BENCHMARK) && RE4DC_BENCHMARK
        re4dc_bench_disc(reads, block, dt);   // bench.cpp (bench.mk BENCHMARK): the measured scene's disc reads
#endif
    }
    m_t0 = now;
}

// ui_bridge.cpp: 0 StageSet entry (re4dc_room_leave), 1 room enter (heap 4 rebuilt; the start for the first room),
// 2 the first gameMainLoop frame in the room (the load time ends).
extern "C" void re4dc_disc_meter_room(int what, unsigned room)
{
    const unsigned long long now = timer_us_gettime64();
    if (what == 0 || (what == 1 && !m_room_pending)) {
        const int o = irq_disable();
        m_room_r0 = m_tot_reads;
        m_room_k0 = m_tot_bytes;
        m_room_b0 = m_tot_block;
        irq_restore(o);
        m_room_t0 = now;
        m_room_pending = true;
        m_room_from = what == 0 ? "door" : "enter";
        return;
    }
    if (what != 2 || !m_room_pending) return;
    m_room_pending = false;
    m_room_ms = (unsigned) ((now - m_room_t0 + 500) / 1000);
    m_room_until = now + 5000000ULL;
    re4dc_log("DISCRD: room=%03x load_ms=%u from=%s reads=%u kb=%u block_ms=%u\n", room, m_room_ms, m_room_from,
              m_tot_reads - m_room_r0, (unsigned) ((m_tot_bytes - m_room_k0) / 1024),
              (unsigned) ((m_tot_block - m_room_b0) / 1000));
}

#if defined(RE4DC_DOOR_PROBE) && RE4DC_DOOR_PROBE
// door_probe.cpp (DOOR_PROBE=1, diagnostic): the game-read totals since boot, for the door window's phase marks.
extern "C" void re4dc_disc_meter_totals(unsigned* reads, unsigned long long* bytes, unsigned long long* block_us)
{
    const int o = irq_disable();
    *reads = m_tot_reads;
    *bytes = m_tot_bytes;
    *block_us = m_tot_block;
    irq_restore(o);
}
#endif

// audio_aica.cpp str_main: the calling thread is the music stream.
extern "C" void re4dc_disc_meter_music_thread(void) { m_music = thd_current; }

// native_ui.cpp: a room load is under way (the meter is drawn although the speed counter hides during room changes).
extern "C" int re4dc_disc_meter_loading(void) { return m_room_pending; }

// native_ui.cpp speed display: lit (game and loader reads) and music (the music stream) 2 = a read in flight now,
// 1 = one ran since the last call, 0 = none; the last window's rates (without the music stream); 1 + the room-entry
// load time for 5 s after the room's first frame. During a room load: the reads, KB and blocked ms so far and the
// elapsed load time (counting up).
extern "C" int re4dc_disc_meter_hud(unsigned* lit, unsigned* music, unsigned* rate, unsigned* load_ms)
{
    if (m_room_pending) {
        *lit = m_busy ? 2U : m_seen ? 1U : 0U;
        m_seen = 0;
        *music = m_mbusy ? 2U : m_mseen ? 1U : 0U;
        m_mseen = 0;
        rate[0] = m_tot_reads - m_room_r0;
        rate[1] = (unsigned) ((m_tot_bytes - m_room_k0) / 1024);
        rate[2] = (unsigned) ((m_tot_block - m_room_b0) / 1000);
        *load_ms = (unsigned) ((timer_us_gettime64() - m_room_t0) / 1000);
        return 1;
    }
    *lit = m_busy ? 2U : m_seen ? 1U : 0U;
    m_seen = 0;
    *music = m_mbusy ? 2U : m_mseen ? 1U : 0U;
    m_mseen = 0;
    rate[0] = m_rate[0];
    rate[1] = m_rate[1];
    rate[2] = m_rate[2];
    *load_ms = m_room_ms;
    return m_room_ms && timer_us_gettime64() < m_room_until;
}
#endif

namespace {
int s_sector, s_cnt;
bool s_dma;
size_t s_consumed;  // bytes requested from the current stream since its start
unsigned g_refused, g_recovered, g_failed;
#if RE4DC_DISC_READ_VERIFY
unsigned g_late, g_late_timeouts, g_late_max_us, g_held;
inline bool gd_dma_busy() { return (*(volatile uint32_t*) 0xA05F7418u & 1u) != 0; }
// A DMA read KOS reported done: wait for the G1 GD-DMA engine to finish moving its bytes. When it was still running,
// the destination's cache lines are invalidated again (nothing wrote them meanwhile: the reader was waiting) so the
// caller reads the landed bytes.
void dma_settle(const char* what, void* buf, size_t size)
{
    if (!gd_dma_busy()) return;
    const uint64_t t0 = timer_us_gettime64();
    bool timed_out = false;
    while (gd_dma_busy()) {
        if (timer_us_gettime64() - t0 > 2000000u) {
            timed_out = true;
            break;
        }
        thd_pass();
    }
    const unsigned us = (unsigned) (timer_us_gettime64() - t0);
    const uintptr_t a = (uintptr_t) buf;
    if ((a & 0xE0000000u) != 0xA0000000u && !(a & 31) && size >= 32) dcache_inval_range(a, size & ~(size_t) 31);
    ++g_late;
    if (timed_out) ++g_late_timeouts;
    if (us > g_late_max_us) g_late_max_us = us;
    re4dc_log("disc read verify: %s of %u bytes at %08x reported done while the GD DMA ran: %s after %u us "
              "(late %u timeouts %u max %u us)\n", what, (unsigned) size, (unsigned) a,
              timed_out ? "STILL RUNNING" : "landed", us, g_late, g_late_timeouts, g_late_max_us);
}
#endif
#if RE4DC_DVD_STUCK_TEST
// Compile-time: DVD_STUCK_ADDR (address of KOS dma_in_progress from a first build's symbols; the value does not change
// the code size, so a second build keeps the address) and DVD_STUCK_TEST (seconds of uptime). No file reads here: this
// runs inside fs_iso9660 with its handle mutex held.
bool g_done;
void stuck_test()
{
    if (!g_done && timer_ms_gettime64() >= 1000ULL * RE4DC_DVD_STUCK_TEST) {
        g_done = true;
        *(volatile bool*) (uintptr_t) RE4DC_DVD_STUCK_ADDR = true;
        re4dc_log("dvd stuck test: dma_in_progress set before a stream start\n");
    }
}
#endif
#if RE4DC_DISC_READ_FALLBACK == 3
}  // namespace
namespace v2 {
int read(void* buf, uint32_t lba, size_t cnt, bool dma);
}
namespace {
#endif
#if RE4DC_FB_V1
bool g_pio;  // session latch: DMA reads did not land, every read is PIO from now on
unsigned g_fb_dma, g_fb_reads;
alignas(32) uint8_t g_bounce[2048];

volatile uint32_t* mark_at(void* buf, size_t size)
{
    return (volatile uint32_t*) ((((uintptr_t) buf + size - 32) & 0x1FFFFFFFu) | 0xA0000000u);
}
uint32_t mark_word(volatile uint32_t* p, int i)
{
    return 0x5EAD0DC5u ^ (uint32_t) (uintptr_t) p ^ (uint32_t) i * 0x9E3779B9u;
}
// A DMA destination this can check: 32-byte aligned (the DMA requirement) and at least 32 bytes.
bool markable(void* buf, size_t size)
{
    return !((uintptr_t) buf & 31) && size >= 32;
}
void mark(void* buf, size_t size)
{
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i) p[i] = mark_word(p, i);
}
bool landed(void* buf, size_t size)
{
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i) {
        if (p[i] != mark_word(p, i)) return true;
    }
    return false;
}
void latch(const char* why)
{
    if (!g_pio) re4dc_log("disc read fallback: %s; reads use PIO sector reads from now on\n", why);
    g_pio = true;
}
// Bytes [pos, pos + size) of the run starting at `lba`, by PIO sector reads.
int pio_fill(uint8_t* dst, int lba, size_t pos, size_t size)
{
    while (size) {
        const int sec = lba + (int) (pos / 2048);
        const size_t off = pos % 2048;
        int rv;
        size_t k;
        if (!off && size >= 2048 && !((uintptr_t) dst & 1)) {
            k = size & ~(size_t) 2047;
#if RE4DC_DISC_READ_FALLBACK == 3
            rv = v2::read(dst, sec, k / 2048, true);
#else
            rv = __real_cdrom_read_sectors_ex(dst, sec, k / 2048, false);
#endif
        } else {
#if RE4DC_DISC_READ_FALLBACK == 3
            rv = v2::read(g_bounce, sec, 1, true);
#else
            rv = __real_cdrom_read_sectors_ex(g_bounce, sec, 1, false);
#endif
            k = 2048 - off < size ? 2048 - off : size;
            if (rv == ERR_OK) memcpy(dst, g_bounce + off, k);
        }
        if (rv != ERR_OK) return rv;
        dst += k;
        pos += k;
        size -= k;
    }
    return ERR_OK;
}
// A stream request that failed or did not land: stop the stream (fs_iso9660 then sees no transfer pending and ends
// its stream too) and fill the request from where the stream stood.
int stream_fallback(void* buffer, size_t size, const char* why)
{
    latch(why);
    ++g_fb_reads;
    __real_cdrom_stream_stop(false);
    const int rv = pio_fill((uint8_t*) buffer, s_sector, s_consumed, size);
    if (rv == ERR_OK) s_consumed += size;
    re4dc_log("disc read fallback: stream request (%u bytes at sector %d + %u) %s by PIO (fallbacks %u)\n",
              (unsigned) size, s_sector, (unsigned) (s_consumed - (rv == ERR_OK ? size : 0)),
              rv == ERR_OK ? "read" : "FAILED", g_fb_reads);
    return rv;
}
#endif
}

#if RE4DC_DISC_READ_FALLBACK >= 2
// ---------------------------------------------------------------------------------------------------------------
// DISC_READ_FALLBACK=2: the on-screen boot log and the bounded sector reads (see the top of this file).
#include <dc/syscalls.h>
#include <dc/video.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
extern "C" unsigned re4dc_ui_frame();  // native_ui.cpp: pictures the game has shown (0 during the boot)

namespace dn {
// 5x7 glyphs (bench.cpp's table plus _ < > [ ] '), each font pixel 2x2 screen pixels in a 12x16 cell.
const uint8_t* glyph(char c)
{
    static const uint8_t kFont[][8] = {
        {' ', 0, 0, 0, 0, 0, 0, 0},
        {'0', 0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E}, {'1', 0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E},
        {'2', 0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F}, {'3', 0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E},
        {'4', 0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02}, {'5', 0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E},
        {'6', 0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E}, {'7', 0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08},
        {'8', 0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E}, {'9', 0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C},
        {'A', 0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11}, {'B', 0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E},
        {'C', 0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E}, {'D', 0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C},
        {'E', 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F}, {'F', 0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10},
        {'G', 0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F}, {'H', 0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11},
        {'I', 0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E}, {'J', 0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C},
        {'K', 0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11}, {'L', 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F},
        {'M', 0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11}, {'N', 0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11},
        {'O', 0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E}, {'P', 0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10},
        {'Q', 0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D}, {'R', 0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11},
        {'S', 0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E}, {'T', 0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04},
        {'U', 0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E}, {'V', 0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04},
        {'W', 0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A}, {'X', 0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11},
        {'Y', 0x11, 0x11, 0x11, 0x0A, 0x04, 0x04, 0x04}, {'Z', 0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F},
        {'.', 0, 0, 0, 0, 0, 0x0C, 0x0C}, {'-', 0, 0, 0, 0x1F, 0, 0, 0}, {':', 0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0},
        {'/', 0, 0x01, 0x02, 0x04, 0x08, 0x10, 0}, {'%', 0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03},
        {'(', 0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02}, {')', 0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08},
        {'=', 0, 0, 0x1F, 0, 0x1F, 0, 0}, {'+', 0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0},
        {'>', 0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08}, {'<', 0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02},
        {',', 0, 0, 0, 0, 0x0C, 0x04, 0x08}, {'#', 0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A},
        {'!', 0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04}, {'?', 0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04},
        {'*', 0, 0x15, 0x0E, 0x1F, 0x0E, 0x15, 0}, {'_', 0, 0, 0, 0, 0, 0, 0x1F},
        {'[', 0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E}, {']', 0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E},
        {'\'', 0x04, 0x04, 0x08, 0, 0, 0, 0},
    };
    if (c >= 'a' && c <= 'z') c = (char) (c - 32);
    for (const auto& g : kFont)
        if (g[0] == (uint8_t) c) return g + 1;
    return kFont[0] + 1;
}
// Inside a TV's overscan: 48 columns from x 32, 27 rows from y 24 (row 0-1 header, 2..24 log, 26 status).
constexpr int kX0 = 32, kY0 = 24, kCW = 12, kCH = 16, kCols = 48, kRows = 27, kLog0 = 2, kLogRows = 23, kStatus = 26;
const uint16_t kColor[5] = {0xFFFF, 0x07E0, 0xFFE0, 0xF800, 0x07FF};  // RGB565: info, good, warn, bad, header
char g_line[kLogRows][kCols + 1];
uint8_t g_lev[kLogRows];
int g_n;                      // lines logged (the newest kLogRows are shown)
char g_status[kCols + 1];
char g_head[2][kCols + 1];
volatile bool g_fatal;

struct Fb {
    volatile uint16_t* p;
    int w, h;
    bool c565;
};
// The frame buffer on screen now (FB_R_SOF1 / FB_R_CTRL), as the crash screen and bench.cpp find it.
bool fb_now(Fb& fb)
{
    const uint32_t ctrl = *(volatile uint32_t*) 0xA05F8044, sof1 = *(volatile uint32_t*) 0xA05F8050;
    const int depth = (ctrl >> 2) & 3;
    if (depth > 1) return false;  // 24 / 32 bpp: never used by this game
    fb.c565 = depth == 1;
    fb.w = vid_mode ? vid_mode->width : 640;
    fb.h = vid_mode ? vid_mode->height : 480;
    fb.p = (volatile uint16_t*) (0xA5000000u | (sof1 & 0x007FFFFFu));
    return fb.w >= 640 && fb.h >= 480;
}
uint16_t col(const Fb& fb, int level)
{
    const uint16_t c = kColor[level < 0 ? 0 : level > 4 ? 4 : level];
    return fb.c565 ? c : (uint16_t) (((c >> 1) & 0x7FE0) | (c & 0x1F));
}
void put_row(const Fb& fb, int row, const char* s, uint16_t fg)
{
    const int y0 = kY0 + row * kCH;
    int n = 0;
    for (; n < kCols; ++n) {
        const char ch = s && *s ? *s++ : ' ';
        const uint8_t* g = glyph(ch);
        const int x0 = kX0 + n * kCW;
        for (int y = 0; y < kCH; ++y) {
            volatile uint16_t* px = fb.p + (y0 + y) * fb.w + x0;
            const int fy = y / 2;
            const uint8_t bits = fy < 7 ? g[fy] : 0;
            for (int x = 0; x < kCW; ++x) {
                const int fx = x / 2;
                px[x] = fx < 5 && (bits & (0x10 >> fx)) ? fg : 0;
            }
        }
    }
}
#ifndef RE4DC_DISC_POLL_SPIN_MS
#define RE4DC_DISC_POLL_SPIN_MS 0
#endif
#ifndef RE4DC_DISC_LAND_SPIN_MS
#define RE4DC_DISC_LAND_SPIN_MS 0
#endif
#ifndef RE4DC_DISC_BOOT_LOG
#define RE4DC_DISC_BOOT_LOG 1
#endif
// DISC_BOOT_LOG=1 (the #28 test discs): on screen through the whole boot. =2 (DISC_COMPAT): only once a warning or an
// error was noted (then with every line so far), so a healthy boot shows nothing.
volatile bool g_trouble;
bool screen_on() { return g_fatal || (re4dc_ui_frame() == 0 && (RE4DC_DISC_BOOT_LOG == 1 || g_trouble)); }
void draw_all()
{
    Fb fb;
    if (!fb_now(fb)) return;
    if (g_fatal) {
        // Stopped: everything outside the text block is cleared on every redraw (the game's last picture, or the crash
        // screen's 30 s hang report drawn over this one); the block itself is rewritten pixel for pixel, so no flicker.
        const int x1 = kX0 + kCols * kCW, y1 = kY0 + kRows * kCH;
        for (int y = 0; y < fb.h; ++y)
            for (int x = 0; x < fb.w; ++x)
                if (y < kY0 || y >= y1 || x < kX0 || x >= x1) fb.p[y * fb.w + x] = 0;
    }
    put_row(fb, 0, g_head[0], col(fb, 4));
    put_row(fb, 1, g_head[1], col(fb, 4));
    const int first = g_n > kLogRows ? g_n - kLogRows : 0;
    for (int i = 0; i < kLogRows; ++i) {
        const int k = first + i;
        put_row(fb, kLog0 + i, k < g_n ? g_line[k % kLogRows] : "", col(fb, k < g_n ? g_lev[k % kLogRows] : 0));
    }
    put_row(fb, kStatus - 1, "", col(fb, 0));
    put_row(fb, kStatus, g_status, col(fb, 2));
}
void header()
{
    if (g_head[0][0]) return;
    snprintf(g_head[0], sizeof(g_head[0]), RE4DC_DISC_BOOT_LOG == 1 ? "RE4DC disc check v2 - issue 28 test 2"
                                                                     : "RE4DC disc log - a disc read had trouble");
    // The GD-ROM syscall vectors: a loader (DreamShell's ISO loader) points them at its own code.
    snprintf(g_head[1], sizeof(g_head[1]), "photo if it stops. gd vec %08lx %08lx",
             (unsigned long) *(volatile uint32_t*) 0x8C0000BCu, (unsigned long) *(volatile uint32_t*) 0x8C0000C0u);
    re4dc_log("DISCNOTE: %s | %s\n", g_head[0], g_head[1]);
    // For the harness's VRAM capture (capture_ui_vram.py reads the last "fb=" pair: KOS pointer = base + 2 * offset).
    const unsigned long fbo = *(volatile uint32_t*) 0xA05F8050 & 0x007FFFFFu;
    re4dc_log("DISCNOTE: boot screen fb=%08lx,%08lx\n", 0xA5000000ul + 2 * fbo, 0xA5000000ul + 2 * fbo);
}
}  // namespace dn

// A boot log line: the ring log always, the screen while the game has shown no picture yet (or after a fatal stop).
// level 0 info, 1 good, 2 warning, 3 bad. Lines longer than 48 characters are cut on screen.
extern "C" void re4dc_disc_note(int level, const char* fmt, ...)
{
    char b[96];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    dn::header();
    re4dc_log("DISCNOTE: %s\n", b);
    const int o = irq_disable();
    const int k = dn::g_n++ % dn::kLogRows;
    strncpy(dn::g_line[k], b, dn::kCols);
    dn::g_line[k][dn::kCols] = 0;
    dn::g_lev[k] = (uint8_t) level;
    if (level >= 2) dn::g_trouble = true;
    irq_restore(o);
    if (dn::screen_on()) dn::draw_all();
}

namespace v2 {
using dn::g_status;
uint64_t ms() { return timer_ms_gettime64(); }
void status(const char* fmt, ...)
{
    if (!dn::screen_on()) return;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(g_status, sizeof(g_status), fmt, ap);
    va_end(ap);
    dn::Fb fb;
    if (dn::fb_now(fb)) dn::put_row(fb, dn::kStatus, g_status, dn::col(fb, 2));
}
// The game cannot go on: the reason stays on screen (redrawn every second, over the game's picture or the crash
// screen's 30 s hang report) and this thread stops here.
[[noreturn]] void fatal(const char* fmt, ...)
{
    char b[96];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    dn::g_fatal = true;
    re4dc_disc_note(3, "%s", b);
    re4dc_disc_note(3, "DISC READ FAILED - the game cannot go on.");
    re4dc_disc_note(3, "Please photograph this screen for issue 28.");
    snprintf(g_status, sizeof(g_status), "stopped at %u ms", (unsigned) ms());
    for (;;) {
        dn::draw_all();
        thd_sleep(1000);
    }
}

unsigned g_reads, g_dma, g_pio, g_late, g_reinits;
bool g_use_pio;      // latched: PIO worked where DMA did not
bool g_first = true;
#if RE4DC_DISC_FAIL_TEST == 4 || RE4DC_DISC_FAIL_TEST == 5
bool g_test_once;    // the simulated failure happened (modes 4 and 5: the first read only)
#endif

// The G1 ATA lock (KOS cdrom.c's _g1_ata_sem), taken in 1 s slices: a note after 5 s, the stop screen after 30 s.
void lock(const char* what, uint32_t lba)
{
    const uint64_t t0 = ms();
    bool told = false;
    for (;;) {
        if (sem_wait_timed(&_g1_ata_sem, 1000) == 0) {
            if (told) re4dc_disc_note(1, "disc: drive free after %u ms", (unsigned) (ms() - t0));
            return;
        }
        const unsigned el = (unsigned) (ms() - t0);
        if (el >= 5000 && !told) {
            told = true;
            re4dc_disc_note(2, "disc: drive busy %u s (%s lba=%u)", el / 1000, what, (unsigned) lba);
        }
        if (el >= 30000) fatal("disc: drive lock stuck 30 s (%s)", what);
    }
}
void unlock() { sem_signal(&_g1_ata_sem); }

bool g_abort_hang_test;  // mode 4: this abort never finishes
// A command that ran out of time: abort it (1 s), else reset and re-initialise the BIOS drive driver. Lock held.
void abort_bounded(gdc_cmd_hnd_t h, const char* what, uint32_t lba)
{
    re4dc_disc_note(3, "disc: %s timeout lba=%u, abort", what, (unsigned) lba);
    status("now: abort %s lba=%u", what, (unsigned) lba);
    syscall_gdrom_abort_command(h);
    const uint64_t t0 = ms();
    bool done = false;
    while (ms() - t0 < 1000) {
        syscall_gdrom_exec_server();
        cd_cmd_chk_status_t st = {};
        const int r = syscall_gdrom_check_command(h, &st);
        if (!g_abort_hang_test && (r == CD_CMD_NOT_FOUND || r == CD_CMD_COMPLETED || r <= CD_CMD_FAILED)) {
            done = true;
            break;
        }
        thd_sleep(1);
    }
    if (!done) {
        re4dc_disc_note(3, "disc: abort timeout, drive reset");
        status("now: drive reset (bios)");
        syscall_gdrom_reset();
        syscall_gdrom_init();
        re4dc_disc_note(0, "disc: drive reset done");
    }
}

// One GD command to its end, polled from this thread with interrupts on. Lock held. busy_test: the command never
// completes (a test hook). Returns ERR_OK / ERR_NO_DISC / ERR_DISC_CHG / ERR_SYS / ERR_TIMEOUT.
int run(int cmd, void* params, unsigned timeout_ms, bool busy_test, const char* what, uint32_t lba)
{
    const uint64_t t0 = ms();
    gdc_cmd_hnd_t h = 0;
    for (;;) {
        h = syscall_gdrom_send_command((cd_cmd_code_t) cmd, params);
        syscall_gdrom_exec_server();
        if (h > 0 || ms() - t0 >= 200) break;
        thd_pass();
    }
    if (h <= 0) {
        re4dc_disc_note(3, "disc: %s not accepted lba=%u", what, (unsigned) lba);
        return ERR_SYS;
    }
    for (unsigned spins = 0;; ++spins) {
        syscall_gdrom_exec_server();
        cd_cmd_chk_status_t st = {};
        int r = syscall_gdrom_check_command(h, &st);
        if (busy_test && r != CD_CMD_BUSY) r = CD_CMD_PROCESSING;
        if (r <= CD_CMD_FAILED) {
            re4dc_log("DISCNOTE: %s lba=%u failed err1=%d err2=%d\n", what, (unsigned) lba, (int) st.err1, (int) st.err2);
            return st.err1 == 2 ? ERR_NO_DISC : st.err1 == 6 ? ERR_DISC_CHG : ERR_SYS;
        }
        if (r == CD_CMD_COMPLETED || r == CD_CMD_NOT_FOUND || r == CD_CMD_STREAMING) return ERR_OK;
        if (ms() - t0 > timeout_ms) {
            abort_bounded(h, what, lba);
            return ERR_TIMEOUT;
        }
        // DISC_POLL_SPIN_MS: keep yielding (thd_pass) for that long before sleeping; a KOS sleep lasts until the next
        // scheduler tick (THD_SCHED_HZ 100 = 10 ms), so a read that completes in 2 ms otherwise costs up to 10.
        if (spins < 64 || ms() - t0 < RE4DC_DISC_POLL_SPIN_MS) thd_pass();
        else thd_sleep(1);
    }
}

// Bounded drive initialisation (KOS cdrom_reinit: CD_CMD_INIT, then the 2048-byte data sector mode).
int reinit(const char* why)
{
    ++g_reinits;
    status("now: drive init (%s)", why);
    lock("init", 0);
    int rv = ERR_SYS;
    for (int i = 0; i < 3; ++i) {
        rv = run(CD_CMD_INIT, nullptr, 6000, false, "drive init", 0);
        if (rv != ERR_DISC_CHG) break;
    }
    if (rv == ERR_OK || rv == ERR_DISC_CHG) {
        cd_check_drive_status_t ds = {};
        syscall_gdrom_check_drive(&ds);
        cd_sec_mode_params_t p = {};
        p.rw = 0;
        p.sector_part = CDROM_READ_DATA_AREA;
        p.track_type = ds.disc_type == CD_CDROM_XA ? 2048 : 1024;
        p.sector_size = 2048;
        rv = syscall_gdrom_sector_mode(&p) < 0 ? ERR_SYS : ERR_OK;
    }
    unlock();
    status("now: drive init done (%d)", rv);
    return rv;
}

// The marker: the destination's last 32 bytes, written through the uncached mirror before the read.
volatile uint32_t* mark_at(void* buf, size_t size)
{
    return (volatile uint32_t*) ((((uintptr_t) buf + size - 32) & 0x1FFFFFFFu) | 0xA0000000u);
}
uint32_t mark_word(volatile uint32_t* p, int i) { return 0x5EAD0DC5u ^ (uint32_t) (uintptr_t) p ^ (uint32_t) i * 0x9E3779B9u; }
bool aligned32(void* buf, size_t size) { return !((uintptr_t) buf & 31) && size >= 32; }
bool cached(void* buf) { return ((uintptr_t) buf & 0xE0000000u) != 0xA0000000u; }
void mark(void* buf, size_t size)
{
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i) p[i] = mark_word(p, i);
}
bool marker_gone(void* buf, size_t size)
{
    // A loader that copies by CPU leaves the bytes in dirty cache lines: write the marker line back first.
    if (cached(buf)) dcache_purge_range((uintptr_t) buf + size - 32, 32);
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i)
        if (p[i] != mark_word(p, i)) return true;
    return false;
}
// After a read reported done: the bytes are there now, or within 250 ms (then the whole range is written back and
// dropped from the cache so the caller reads memory).
bool landed(void* buf, size_t size, const char* what, uint32_t lba)
{
    if (marker_gone(buf, size)) return true;
    const uint64_t t0 = ms();
    while (ms() - t0 < 250) {
        thd_sleep(5);
        if (marker_gone(buf, size)) {
            ++g_late;
            // line by line: dcache_purge_range of >= 39 KB would pull in KOS's 16 KB static purge-all buffer
#if defined(RE4DC_CACHE_COHERENT_DMA) && RE4DC_CACHE_COHERENT_DMA
            // the destination is 32-byte aligned and whole lines (aligned32): drop, never write back over the DMA
            if (cached(buf)) dcache_inval_range((uintptr_t) buf, size);
#else
            if (cached(buf))
                for (uintptr_t a = (uintptr_t) buf & ~(uintptr_t) 31; a < (uintptr_t) buf + size; a += 32)
                    arch_dcache_purge_line((void*) a);
#endif
            re4dc_disc_note(2, "disc: %s landed late (%u ms) lba=%u", what, (unsigned) (ms() - t0), (unsigned) lba);
            return true;
        }
    }
    return false;
}
unsigned timeout_for(size_t cnt) { return 5000u + 8u * (unsigned) cnt; }

#if RE4DC_DISC_FAIL_TEST == 5
[[noreturn]] void hang_test()
{
    re4dc_log("DISCNOTE: (log only) DISC_FAIL_TEST=5: interrupts off, spinning like a BIOS call that never returns\n");
    irq_disable();
    for (;;) {
    }
}
#endif

int read_dma(void* buf, uint32_t lba, size_t cnt, const char* what)
{
    const size_t size = cnt * 2048;
    if (!aligned32(buf, size)) return ERR_SYS;
    mark(buf, size);
    if (cached(buf)) dcache_inval_range((uintptr_t) buf, size);
    cd_read_params_t p = {};
    p.start_sec = lba;
    p.num_sec = cnt;
    p.buffer = (void*) ((uintptr_t) buf & 0x1FFFFFFFu);
    p.is_test = 0;
    status("now: %s lba=%u n=%u", what, (unsigned) lba, (unsigned) cnt);
    bool busy_test = false;
#if RE4DC_DISC_FAIL_TEST == 4
    if (!g_test_once) busy_test = g_abort_hang_test = true;
#endif
#if RE4DC_DISC_FAIL_TEST == 5
    if (!g_test_once) hang_test();
#endif
    lock(what, lba);
#if RE4DC_DISC_FAIL_TEST == 2 || RE4DC_DISC_FAIL_TEST == 3
    int rv = ERR_OK;  // reported done, nothing moved (the loader's failure on demand)
    (void) busy_test;
    (void) p;
#else
    int rv = run(CD_CMD_DMAREAD, &p, timeout_for(cnt), busy_test, what, lba);
#endif
    unlock();
#if RE4DC_DISC_FAIL_TEST == 4
    if (busy_test) {
        g_test_once = true;
        g_abort_hang_test = false;
    }
#endif
    if (rv != ERR_OK) return rv;
    // The G1 GD-DMA engine may still be moving bytes after the BIOS says done (1 s bound).
    const uint64_t t0 = ms();
    // DISC_LAND_SPIN_MS (Makefile): yield (thd_pass) for up to that long before sleeping. A KOS sleep lasts until the
    // next 10 ms scheduler tick, so on a unit that reports COMPLETED before its DMA lands (GDEMU) every read cost >= 10 ms.
    // With it the bound grows with the read (1 s + 8 ms a sector, the command's own timeout): a 600-sector read on a
    // ~600 KiB/s clone needs about 2 s, and the fixed 1 s bound declared it lost and re-initialised the drive mid-DMA.
#if RE4DC_DISC_LAND_SPIN_MS
    const uint64_t land_bound = timeout_for(cnt) - 4000u;
#else
    const uint64_t land_bound = 1000;
#endif
    while ((*(volatile uint32_t*) 0xA05F7418u & 1u) && ms() - t0 < land_bound) {
        if (RE4DC_DISC_LAND_SPIN_MS && ms() - t0 < RE4DC_DISC_LAND_SPIN_MS) thd_pass();
        else thd_sleep(1);
    }
    if (!landed(buf, size, what, lba)) {
        re4dc_disc_note(3, "disc: %s lba=%u n=%u did not land", what, (unsigned) lba, (unsigned) cnt);
        return ERR_SYS;
    }
#if defined(RE4DC_CACHE_COHERENT_DMA) && RE4DC_CACHE_COHERENT_DMA
    if (cached(buf)) dcache_inval_range((uintptr_t) buf, size);  // lines refetched while the DMA ran
#endif
    return ERR_OK;
}

int read_pio(void* buf, uint32_t lba, size_t cnt)
{
    const size_t size = cnt * 2048;
    if ((uintptr_t) buf & 1) return ERR_SYS;
    const bool check = aligned32(buf, size);
    if (check) mark(buf, size);
    cd_read_params_t p = {};
    p.start_sec = lba;
    p.num_sec = cnt;
    p.buffer = buf;
    p.is_test = 0;
    status("now: pio read lba=%u n=%u", (unsigned) lba, (unsigned) cnt);
    lock("pio read", lba);
    const int rv = run(CD_CMD_PIOREAD, &p, timeout_for(cnt), RE4DC_DISC_FAIL_TEST == 3, "pio read", lba);
    unlock();
    if (rv != ERR_OK) return rv;
    if (check && !landed(buf, size, "pio read", lba)) {
        re4dc_disc_note(3, "disc: pio read lba=%u n=%u did not land", (unsigned) lba, (unsigned) cnt);
        return ERR_SYS;
    }
    return ERR_OK;
}

// Every sector read fs_iso9660 makes. Order: the method in use (DMA, or PIO once latched), then DMA after a drive
// re-init (at most 6 re-inits a session), then PIO. The first method that works is reported; PIO is then kept.
int read(void* buf, uint32_t lba, size_t cnt, bool dma)
{
    ++g_reads;
    if (g_first) {
        g_first = false;
        re4dc_disc_note(0, "disc: first read lba=%u n=%u (dma, no streams)", (unsigned) lba, (unsigned) cnt);
    }
    const bool can_dma = dma && aligned32(buf, cnt * 2048);
    int rv = (g_use_pio || !can_dma) ? read_pio(buf, lba, cnt) : read_dma(buf, lba, cnt, "dma read");
    if (rv == ERR_OK) {
        if (g_use_pio || !can_dma) ++g_pio;
        else ++g_dma;
        if (g_reads == 1) re4dc_disc_note(1, "disc: first read ok (%s)", g_use_pio || !can_dma ? "pio" : "dma");
        status("reads %u: dma %u pio %u late %u", g_reads, g_dma, g_pio, g_late);
        return rv;
    }
    re4dc_disc_note(3, "disc: %s read failed (%d) lba=%u", g_use_pio || !can_dma ? "pio" : "dma", rv, (unsigned) lba);
    if (can_dma && g_reinits < 6) {
        const int ri = reinit("dma retry");
        re4dc_disc_note(ri == ERR_OK ? 1 : 3, "disc: drive reinit %s (%d)", ri == ERR_OK ? "ok" : "FAILED", ri);
        rv = read_dma(buf, lba, cnt, "dma retry");
        if (rv == ERR_OK) {
            ++g_dma;
            g_use_pio = false;
            re4dc_disc_note(1, "disc: dma after reinit ok lba=%u - dma kept", (unsigned) lba);
            status("reads %u: dma %u pio %u late %u", g_reads, g_dma, g_pio, g_late);
            return rv;
        }
        re4dc_disc_note(3, "disc: dma after reinit failed (%d) lba=%u", rv, (unsigned) lba);
    }
    if (can_dma && !g_use_pio) {
        rv = read_pio(buf, lba, cnt);
        if (rv == ERR_OK) {
            ++g_pio;
            g_use_pio = true;
            re4dc_disc_note(1, "disc: pio read ok lba=%u - pio from now on", (unsigned) lba);
            status("reads %u: dma %u pio %u late %u", g_reads, g_dma, g_pio, g_late);
            return rv;
        }
        re4dc_disc_note(3, "disc: pio read failed (%d) lba=%u", rv, (unsigned) lba);
    }
    fatal("disc: lba=%u n=%u: all 3 ways failed", (unsigned) lba, (unsigned) cnt);
}

int stream_refused()
{
    static bool told;
    if (!told) {
        told = true;
        re4dc_log("DISCNOTE: (log only) stream start refused: v2 reads by sector reads only\n");
    }
    return ERR_SYS;
}
#if defined(RE4DC_DISC_PIO_FALLBACK) && RE4DC_DISC_PIO_FALLBACK
#include "disc_pio_native.inc"
#endif
}  // namespace v2

#if defined(RE4DC_DISC_PIO_FALLBACK) && RE4DC_DISC_PIO_FALLBACK
extern "C" void re4dc_iso_retry_invalidate(void);  // knob-gated KOS ISO patch
extern "C" void re4dc_disc_pio_validation_begin(void) { v2::pio_validation_begin(); }
extern "C" void re4dc_disc_pio_validation_reject(void) {
    v2::pio_validation_reject();
    // Never acquire ISO while G1 is held: normal reads lock ISO then G1.
    // Drop only cached data tags, not handles, directory state or ownership.
    re4dc_iso_retry_invalidate();
}
extern "C" void re4dc_disc_pio_validation_end(void) { v2::pio_validation_end(); }
#endif

// fs_iso9660's init_percd (first /cd access and after a disc change): the bounded drive init.
extern "C" int __wrap_cdrom_reinit(void)
{
    re4dc_disc_note(0, "disc: drive init");
    const int rv = v2::reinit("boot");
    re4dc_disc_note(rv == ERR_OK ? 1 : 3, "disc: drive init %s (%d) at %u ms", rv == ERR_OK ? "ok" : "FAILED", rv,
                    (unsigned) v2::ms());
    return rv;
}
#endif

#if RE4DC_DISC_READ_FALLBACK || RE4DC_DISC_FAIL_TEST || RE4DC_DISC_READ_VERIFY || RE4DC_DISC_READ_METER
extern "C" int __wrap_cdrom_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma)
{
#if RE4DC_DISC_READ_METER
    DiscMeterScope meter(cnt * 2048, true);
#endif
#if defined(RE4DC_DISC_READ_LOG) && RE4DC_DISC_READ_LOG
    re4dc_log("DRL: S sec=%u n=%u thr=%s\n", (unsigned) sector, (unsigned) cnt, thd_current ? thd_current->label : "-");
#endif
#if defined(RE4DC_DISC_PIO_FALLBACK) && RE4DC_DISC_PIO_FALLBACK
    return v2::pio_read(buffer, sector, cnt, dma);
#endif
#if RE4DC_DISC_READ_FALLBACK == 2
    return v2::read(buffer, sector, cnt, dma);
#endif
#if RE4DC_DISC_READ_FALLBACK == 3
    if (g_pio) return v2::read(buffer, sector, cnt, dma);  // latched: plain bounded reads for the rest of the session
#endif
#if RE4DC_FB_V1
    if (!dma || g_pio || !markable(buffer, cnt * 2048)) return __real_cdrom_read_sectors_ex(buffer, sector, cnt, dma && !g_pio);
    mark(buffer, cnt * 2048);
#else
    if (!dma) return __real_cdrom_read_sectors_ex(buffer, sector, cnt, dma);
#endif
#if RE4DC_DISC_FAIL_TEST >= 2 && RE4DC_DISC_READ_FALLBACK == 3
    // mode 3: "done" without the transfer only from DISC_FAIL_AFTER_S seconds of uptime (a failure in mid game)
    int rv = timer_ms_gettime64() >= 1000ULL * RE4DC_DISC_FAIL_AFTER_S ? ERR_OK : __real_cdrom_read_sectors_ex(buffer, sector, cnt, true);
#elif RE4DC_DISC_FAIL_TEST >= 2
    int rv = ERR_OK;  // skipped: the emulator's "done" without the transfer
#else
    int rv = __real_cdrom_read_sectors_ex(buffer, sector, cnt, true);
#endif
#if defined(RE4DC_DISC_DMA_WAIT_TIMEOUT) && RE4DC_DISC_DMA_WAIT_TIMEOUT
    if (rv == ERR_TIMEOUT) dma_wait_timeout_log("a DMA sector read", sector, cnt * 2048);
    dma_wait_note(cnt * 2048);
#endif
#if RE4DC_DISC_READ_VERIFY
    if (rv == ERR_OK) dma_settle("a sector read", buffer, cnt * 2048);
#endif
#if RE4DC_FB_V1
    if (rv != ERR_OK || !landed(buffer, cnt * 2048)) {
        latch(rv == ERR_OK ? "a DMA sector read reported OK but did not land" : "a DMA sector read failed");
        ++g_fb_dma;
#if RE4DC_DISC_READ_FALLBACK == 3
        rv = v2::read(buffer, sector, cnt, true);
#else
        rv = __real_cdrom_read_sectors_ex(buffer, sector, cnt, false);
#endif
        re4dc_log("disc read fallback: %u sectors at %u read again by PIO: %s (fallbacks %u)\n", (unsigned) cnt,
                  (unsigned) sector, rv == ERR_OK ? "ok" : "FAILED", g_fb_dma);
    }
#endif
    return rv;
}
#endif

#if RE4DC_DISC_READ_FALLBACK || RE4DC_DISC_FAIL_TEST || RE4DC_DISC_READ_VERIFY
extern "C" int __wrap_cdrom_stream_stop(bool abort_dma)
{
#if defined(RE4DC_DISC_PIO_FALLBACK) && RE4DC_DISC_PIO_FALLBACK
    (void) abort_dma;
    return ERR_NO_ACTIVE;  // every stream start was refused; no owner to stop
#endif
    const int rv = __real_cdrom_stream_stop(abort_dma);
#if RE4DC_FB_V1
    if (rv == ERR_TIMEOUT) latch("a stream stop timed out (the drive was reset)");
#endif
    return rv;
}
#endif

#if defined(RE4DC_DISC_GD_ATOMIC) && RE4DC_DISC_GD_ATOMIC
// DISC_GD_ATOMIC=1 (Makefile): each GD-ROM BIOS syscall runs with interrupts masked, so KOS's vblank / G1 DMA handlers
// (which call exec_server and check_command from interrupt context) never enter the BIOS while a thread is inside it.
#include <dc/syscalls.h>
#define RE4DC_GD_WRAP(ret, name, params, args)                                  \
    extern "C" ret __real_syscall_gdrom_##name params;                          \
    extern "C" ret __wrap_syscall_gdrom_##name params                           \
    {                                                                           \
        const irq_mask_t o = irq_disable();                                     \
        const ret r = __real_syscall_gdrom_##name args;                         \
        irq_restore(o);                                                         \
        return r;                                                               \
    }
#define RE4DC_GD_WRAP_VOID(name, params, args)                                  \
    extern "C" void __real_syscall_gdrom_##name params;                         \
    extern "C" void __wrap_syscall_gdrom_##name params                          \
    {                                                                           \
        const irq_mask_t o = irq_disable();                                     \
        __real_syscall_gdrom_##name args;                                       \
        irq_restore(o);                                                         \
    }
RE4DC_GD_WRAP(int, check_drive, (cd_check_drive_status_t* st), (st))
RE4DC_GD_WRAP(gdc_cmd_hnd_t, send_command, (cd_cmd_code_t cmd, void* params), (cmd, params))
RE4DC_GD_WRAP(cd_cmd_chk_t, check_command, (gdc_cmd_hnd_t h, cd_cmd_chk_status_t* st), (h, st))
RE4DC_GD_WRAP_VOID(exec_server, (void), ())
RE4DC_GD_WRAP(int, abort_command, (gdc_cmd_hnd_t h), (h))
RE4DC_GD_WRAP_VOID(dma_callback, (uintptr_t cb, void* param), (cb, param))
RE4DC_GD_WRAP(int, dma_transfer, (gdc_cmd_hnd_t h, const cd_transfer_params_t* p), (h, p))
RE4DC_GD_WRAP(int, dma_check, (gdc_cmd_hnd_t h, size_t* size), (h, size))
RE4DC_GD_WRAP_VOID(pio_callback, (uintptr_t cb, void* param), (cb, param))
RE4DC_GD_WRAP(int, pio_transfer, (gdc_cmd_hnd_t h, const cd_transfer_params_t* p), (h, p))
RE4DC_GD_WRAP(int, pio_check, (gdc_cmd_hnd_t h, size_t* size), (h, size))
#endif

extern "C" int __wrap_cdrom_stream_start(int sector, int cnt, bool dma)
{
#if RE4DC_DISC_READ_METER
    DiscMeterScope meter(0, false);
#endif
#if defined(RE4DC_DISC_READ_LOG) && RE4DC_DISC_READ_LOG
    re4dc_log("DRL: T sec=%d n=%d thr=%s\n", sector, cnt, thd_current ? thd_current->label : "-");
#endif
#if defined(RE4DC_DISC_PIO_FALLBACK) && RE4DC_DISC_PIO_FALLBACK
    // ISO falls back to sector reads. No stream DMA callback/wait is installed.
    (void) sector; (void) cnt; (void) dma;
    return ERR_SYS;
#endif
#if RE4DC_DVD_STUCK_TEST
    stuck_test();
#endif
#if RE4DC_FB_V1
    if (g_pio) return ERR_SYS;  // fs_iso9660 falls back to sector reads
#endif
#if RE4DC_DISC_READ_FALLBACK == 2
    (void) sector;
    (void) cnt;
    (void) dma;
    return v2::stream_refused();  // no streams at all: fs_iso9660 reads by sector reads (v2::read)
#endif
    s_sector = sector;
    s_cnt = cnt;
    s_dma = dma;
    s_consumed = 0;
    return __real_cdrom_stream_start(sector, cnt, dma);
}

extern "C" int __wrap_cdrom_stream_request(void* buffer, size_t size, bool block)
{
#if RE4DC_DISC_READ_METER
    DiscMeterScope meter(size, true);
#endif
#if defined(RE4DC_DISC_PIO_FALLBACK) && RE4DC_DISC_PIO_FALLBACK
    // A caller ignoring the refused stream start must not enter an untimed wait.
    (void) buffer; (void) size; (void) block;
    return ERR_SYS;
#endif
#if RE4DC_FB_V1
    // fs_iso9660's one non-blocking request (32 bytes) polls for completion right after: blocking here is the same.
    const bool check = s_dma && markable(buffer, size);
    if (check) {
        block = true;
        mark(buffer, size);
    }
#endif
#if RE4DC_DISC_READ_VERIFY
    if (s_dma) block = true;  // fs_iso9660's 32-byte request polls for completion right after: the same, with the wait
#endif
#if RE4DC_DISC_FAIL_TEST && RE4DC_DISC_READ_FALLBACK == 3
    int rv = (s_dma && timer_ms_gettime64() >= 1000ULL * RE4DC_DISC_FAIL_AFTER_S) ? ERR_OK
                                                                                : __real_cdrom_stream_request(buffer, size, block);
#elif RE4DC_DISC_FAIL_TEST
    int rv = s_dma ? ERR_OK : __real_cdrom_stream_request(buffer, size, block);  // skipped: "done" without the transfer
#else
    int rv = __real_cdrom_stream_request(buffer, size, block);
#endif
#if defined(RE4DC_DISC_DMA_WAIT_TIMEOUT) && RE4DC_DISC_DMA_WAIT_TIMEOUT
    if (rv == ERR_TIMEOUT) dma_wait_timeout_log("a DMA stream request", (uint32_t) s_sector, size);
    dma_wait_note(size);
#endif
#if RE4DC_DISC_READ_VERIFY
    if (rv == ERR_OK && s_dma) dma_settle("a stream request", buffer, size);
#endif
    if (rv == ERR_OK) {
#if RE4DC_FB_V1
        if (check && !landed(buffer, size)) return stream_fallback(buffer, size, "a DMA stream request reported OK but did not land");
#endif
        s_consumed += size;
        return rv;
    }
#if RE4DC_DVD_READ_SAFE
#if RE4DC_FB_V1
    if (rv != ERR_SYS) return stream_fallback(buffer, size, "a stream request failed");
#else
    if (rv != ERR_SYS) return rv;
#endif
    ++g_refused;
    for (int i = 0; i < 5 && rv == ERR_SYS; ++i) {
        thd_sleep(2);
        rv = __real_cdrom_stream_request(buffer, size, block);
    }
#if RE4DC_DISC_READ_VERIFY
    // The flag is only stale when no GD DMA is moving: never abort a live transfer (a GD seek alone is 100+ ms).
    if (rv == ERR_SYS && gd_dma_busy()) {
        ++g_held;
        const uint64_t t0 = timer_us_gettime64();
        while (rv == ERR_SYS && gd_dma_busy() && timer_us_gettime64() - t0 < 2000000u) {
            thd_sleep(2);
            rv = __real_cdrom_stream_request(buffer, size, block);
        }
        re4dc_log("disc read verify: refused stream request held %u us for a running GD DMA: %s (held %u)\n",
                  (unsigned) (timer_us_gettime64() - t0), rv == ERR_OK ? "accepted" : "still refused", g_held);
    }
    if (rv == ERR_OK && s_dma) dma_settle("a held stream request", buffer, size);
#endif
    bool restarted = false;
    if (rv == ERR_SYS && sem_wait_timed(&_g1_ata_sem, 1000) == 0) {
        if (cdrom_abort_cmd(1000, true) == ERR_NO_ACTIVE) sem_signal(&_g1_ata_sem);  // took no ownership
        const size_t done_sectors = s_consumed / 2048;
        if (!(s_consumed % 2048) && (int) done_sectors < s_cnt &&
            __real_cdrom_stream_start(s_sector + (int) done_sectors, s_cnt - (int) done_sectors, s_dma) == ERR_OK) {
            s_sector += (int) done_sectors;
            s_cnt -= (int) done_sectors;
            s_consumed = 0;
            restarted = true;
            rv = __real_cdrom_stream_request(buffer, size, block);
        }
    }
    if (rv == ERR_OK) {
        s_consumed += size;
        ++g_recovered;
    } else {
        ++g_failed;
    }
    re4dc_log("dvd read safe: stream request refused, %s%s (%u bytes; refused %u recovered %u failed %u)\n",
              rv == ERR_OK ? "recovered" : "FAILED", restarted ? " after a stream restart" : "", (unsigned) size,
              g_refused, g_recovered, g_failed);
#endif
#if RE4DC_FB_V1
    if (rv != ERR_OK) rv = stream_fallback(buffer, size, "a stream request failed");
#endif
    return rv;
}
