/* disc_safe.c: the engine's disc read safety (lane eng-load1, 2026-11-21). Lifted from the old port's
   game/platform/dvd_read_safe.cpp (origin/t15/int a5aca9cf9) with the knob set the Test 27.2 release shipped
   (DVD_READ_SAFE=1 DISC_READ_FALLBACK=3 DISC_NOTREADY_RETRY=1; tools/d367/test27.2/release-knobs*.txt), as one fixed
   path: no build switches, no disc meter, HUD, boot log screen or fixture hooks. core/play_files.c's wraps of the KOS
   drive calls (they count every request first) call it; it calls KOS's own (__real_). docs/engine/SERVICES.md "Disc
   read safety".

   What each part guards against, with the evidence it mattered on hardware (the old port's notes, kept short):
   1. A stale "DMA in progress" flag (DVD_READ_SAFE, Phase 2 D4): after the r119 boss with the test 7 data every later
      stream request was refused ("cdrom_stream_request: Previous DMA request is in progress"): 249 texture uploads and
      every later index read failed until the end of the run. KOS's dma_in_progress is cleared only by a G1 DMA
      completion. A refused request is retried for 10 ms; then the flag is stale: cdrom_abort_cmd(1000, true) under the
      G1 ATA semaphore clears it, the stream restarts where it stood (a sector boundary) and the request is repeated.
   2. Reads a disc emulator reports done without moving the bytes (DISC_READ_FALLBACK, issue #28): DreamShell's ISO
      loader crashed test 10 at boot with a sound table that was not the file ("Read Ok" after a drive reset). Before
      each DMA read the last 32 bytes of the destination get a marker through the uncached mirror; a read that reports
      OK with the marker still there, a failed read, or a stream stop that timed out latches the session: the read is
      done again by plain sector reads, later stream starts are refused (fs_iso9660 then reads by sectors) and later
      sector reads take the bounded path below. Normal discs never trip it (two 32-byte uncached accesses a read). The
      release shipped =3 (streams kept, the latch on the first fault: the owner's "option A", 10-16).
   3. A drive that answers "not ready" for a while (DISC_NOTREADY_RETRY, #66 bug 3): all three read ways failed within
      moments on GDEMU 930 s into play and nothing waited. The bounded read keeps trying for 30 s (drive re-init and the
      read again each round, 250 ms then 1 s apart) before it gives up; a read that still fails returns the error (the
      loader then refuses the room: "E1 load: read failed", the scene FAILED), never a hang. Console status of this
      part: "needs console check" (KNOWN_ISSUES.md:109 on the release line).
   Not lifted (stated in the hand-back): the release's own GD command loop for =2/=3's latched reads (v2::read: the BIOS
   command polled from the calling thread with interrupts on, every wait bounded). The engine's latched reads use KOS's
   cdrom_read_sectors_ex, whose command waits are bounded by the KOS disc fixes the engine links (engine/loader/
   kosfix.mk: the hang fixes and the stale DMA completion fix). The release's DISC_DMA_WAIT_TIMEOUT KOS patch is not in
   kosfix.mk either. Both are console questions for the deferred run.

   Control (boot file DISCFAIL, the DOOR scene): from the first room change on, the first DMA transfer (stream request
   or sector read) is reported done without being made, as the ISO loader did; the marker check must catch it, latch,
   and read the bytes again (E1 DISCSAFE not-landed 1, fallbacks 1, latched 1), and the room must still load. */
#include <kos.h>
#include <dc/cdrom.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

void e1_log(const char* fmt, ...);
int __real_cdrom_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma);
int __real_cdrom_stream_start(int sector, int cnt, bool dma);
int __real_cdrom_stream_request(void* buffer, size_t size, bool block);
extern semaphore_t _g1_ata_sem;

static int s_sector, s_cnt;
static bool s_dma;
static size_t s_consumed;   /* bytes requested from the current stream since its start */
static bool g_latched;      /* a DMA read did not land: plain bounded sector reads from now on */
static unsigned g_refused, g_recovered, g_failed, g_marked, g_not_landed, g_fallbacks, g_notready_waits, g_read_failed;
static int g_fail_armed;    /* DISCFAIL (control): the next DMA transfer is reported done without being made */
static uint8_t g_bounce[2048] __attribute__((aligned(32)));

void disc_safe_fail_arm(void) { g_fail_armed = 1; }

static volatile uint32_t* mark_at(void* buf, size_t size)
{
    return (volatile uint32_t*)((((uintptr_t)buf + size - 32) & 0x1FFFFFFFu) | 0xA0000000u);
}
static uint32_t mark_word(volatile uint32_t* p, int i) { return 0x5EAD0DC5u ^ (uint32_t)(uintptr_t)p ^ (uint32_t)i * 0x9E3779B9u; }
static bool markable(void* buf, size_t size) { return !((uintptr_t)buf & 31) && size >= 32; }   /* the DMA's own rule */
static void mark(void* buf, size_t size)
{
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i) p[i] = mark_word(p, i);
    g_marked++;
}
static bool landed(void* buf, size_t size)
{
    volatile uint32_t* p = mark_at(buf, size);
    for (int i = 0; i < 8; ++i)
        if (p[i] != mark_word(p, i)) return true;
    return false;
}
static void latch(const char* why)
{
    if (!g_latched) e1_log("E1 DISCSAFE latched: %s; sector reads from now on\n", why);
    g_latched = true;
}

/* The bounded read: DMA, DMA after a drive re-init, PIO; then the not-ready wait (30 s); then the error. */
static int bounded_read(void* buf, uint32_t lba, size_t cnt)
{
    const bool can_dma = markable(buf, cnt * 2048);
    int rv = can_dma ? __real_cdrom_read_sectors_ex(buf, lba, cnt, true) : ERR_SYS;
    if (rv == ERR_OK) return rv;
    if (can_dma && cdrom_reinit() == ERR_OK) {
        rv = __real_cdrom_read_sectors_ex(buf, lba, cnt, true);
        if (rv == ERR_OK) return rv;
    }
    rv = __real_cdrom_read_sectors_ex(buf, lba, cnt, false);
    if (rv == ERR_OK) return rv;
    const uint64_t t0 = timer_ms_gettime64();
    unsigned round = 0;
    g_notready_waits++;
    e1_log("E1 DISCSAFE not ready: waiting for the drive at lba %lu (rv %d)\n", (unsigned long)lba, rv);
    while (rv != ERR_OK && timer_ms_gettime64() - t0 < 30000) {
        ++round;
        thd_sleep(round < 4 ? 250 : 1000);
        if (cdrom_reinit() != ERR_OK) continue;
        rv = __real_cdrom_read_sectors_ex(buf, lba, cnt, can_dma);
    }
    if (rv != ERR_OK) {
        g_read_failed++;
        e1_log("E1 DISCSAFE READ FAILED lba %lu n %lu after %lu ms (rv %d)\n", (unsigned long)lba, (unsigned long)cnt,
               (unsigned long)(timer_ms_gettime64() - t0), rv);
    }
    return rv;
}
/* Bytes [pos, pos + size) of the stream that started at `lba`, by bounded sector reads. */
static int sector_fill(uint8_t* dst, int lba, size_t pos, size_t size)
{
    while (size) {
        const int sec = lba + (int)(pos / 2048);
        const size_t off = pos % 2048;
        int rv;
        size_t k;
        if (!off && size >= 2048 && !((uintptr_t)dst & 31)) {
            k = size & ~(size_t)2047;
            rv = bounded_read(dst, (uint32_t)sec, k / 2048);
        } else {
            rv = bounded_read(g_bounce, (uint32_t)sec, 1);
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
static int stream_fallback(void* buffer, size_t size, const char* why)
{
    latch(why);
    g_fallbacks++;
    cdrom_stream_stop(false);
    const int rv = sector_fill((uint8_t*)buffer, s_sector, s_consumed, size);
    if (rv == ERR_OK) s_consumed += size;
    e1_log("E1 DISCSAFE stream request (%lu bytes at sector %d + %lu) %s by sector reads\n", (unsigned long)size, s_sector,
           (unsigned long)(s_consumed - (rv == ERR_OK ? size : 0)), rv == ERR_OK ? "read" : "FAILED");
    return rv;
}

int disc_safe_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma)
{
    if (g_latched) return bounded_read(buffer, sector, cnt);
    if (!dma || !markable(buffer, cnt * 2048)) return __real_cdrom_read_sectors_ex(buffer, sector, cnt, dma);
    mark(buffer, cnt * 2048);
    int rv;
    if (g_fail_armed) { g_fail_armed = 0; rv = ERR_OK; }   /* DISCFAIL: "done" without the transfer */
    else rv = __real_cdrom_read_sectors_ex(buffer, sector, cnt, true);
    if (rv != ERR_OK || !landed(buffer, cnt * 2048)) {
        if (rv == ERR_OK) g_not_landed++;
        latch(rv == ERR_OK ? "a DMA sector read reported done but did not land" : "a DMA sector read failed");
        g_fallbacks++;
        rv = bounded_read(buffer, sector, cnt);
        e1_log("E1 DISCSAFE %lu sectors at %lu read again: %s\n", (unsigned long)cnt, (unsigned long)sector,
               rv == ERR_OK ? "ok" : "FAILED");
    }
    return rv;
}

int disc_safe_stream_start(int sector, int cnt, bool dma)
{
    if (g_latched) return ERR_SYS;   /* fs_iso9660 falls back to sector reads */
    s_sector = sector;
    s_cnt = cnt;
    s_dma = dma;
    s_consumed = 0;
    return __real_cdrom_stream_start(sector, cnt, dma);
}

int disc_safe_stream_request(void* buffer, size_t size, bool block)
{
    /* fs_iso9660's one non-blocking request (32 bytes) polls for completion right after: blocking here is the same */
    const bool check = s_dma && markable(buffer, size);
    if (check) {
        block = true;
        mark(buffer, size);
    }
    int rv;
    if (g_fail_armed && check) { g_fail_armed = 0; rv = ERR_OK; }   /* DISCFAIL: "done" without the transfer */
    else rv = __real_cdrom_stream_request(buffer, size, block);
    if (rv == ERR_OK) {
        if (check && !landed(buffer, size)) {
            g_not_landed++;
            return stream_fallback(buffer, size, "a DMA stream request reported done but did not land");
        }
        s_consumed += size;
        return rv;
    }
    if (rv != ERR_SYS) return stream_fallback(buffer, size, "a stream request failed");
    /* refused: the DMA flag is busy or stale */
    ++g_refused;
    for (int i = 0; i < 5 && rv == ERR_SYS; ++i) {
        thd_sleep(2);
        rv = __real_cdrom_stream_request(buffer, size, block);
    }
    bool restarted = false;
    if (rv == ERR_SYS && sem_wait_timed(&_g1_ata_sem, 1000) == 0) {
        if (cdrom_abort_cmd(1000, true) == ERR_NO_ACTIVE) sem_signal(&_g1_ata_sem);   /* took no ownership */
        const size_t done_sectors = s_consumed / 2048;
        if (!(s_consumed % 2048) && (int)done_sectors < s_cnt &&
            __real_cdrom_stream_start(s_sector + (int)done_sectors, s_cnt - (int)done_sectors, s_dma) == ERR_OK) {
            s_sector += (int)done_sectors;
            s_cnt -= (int)done_sectors;
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
    e1_log("E1 DISCSAFE stream request refused, %s%s (%lu bytes; refused %u recovered %u failed %u)\n",
           rv == ERR_OK ? "recovered" : "FAILED", restarted ? " after a stream restart" : "", (unsigned long)size, g_refused,
           g_recovered, g_failed);
    if (rv != ERR_OK) rv = stream_fallback(buffer, size, "a stream request failed");
    return rv;
}

void disc_safe_report(void)
{
    e1_log("E1 DISCSAFE refused %u recovered %u failed %u marked %u not-landed %u fallbacks %u latched %u notready-waits %u "
           "read-failed %u\n", g_refused, g_recovered, g_failed, g_marked, g_not_landed, g_fallbacks, g_latched ? 1u : 0u,
           g_notready_waits, g_read_failed);
}
