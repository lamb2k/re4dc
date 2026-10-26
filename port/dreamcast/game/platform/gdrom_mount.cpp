// GD-ROM high-density mount for /cd (D367 W10, GDEMU image).
//
// The pinned KOS (804b319) fs_iso9660 mounts /cd from the LOW-density table
// of contents: init_percd() calls cdrom_read_toc(&toc, false) and uses the
// last data track listed there. On a GD-ROM (a GDI on GDEMU or in Flycast)
// that is track 1, a placeholder in the single-density area. The game's file
// system is track 3 at LBA 45000 in the high-density area, so every
// fs_open("/cd/...") would fail even though the disc boots.
//
// The game link wraps cdrom_read_toc (-Wl,--wrap=cdrom_read_toc, game/Makefile
// GAME_LDFLAGS). When the drive reports a GD-ROM, a low-density request gets
// the high-density TOC instead, so fs_iso9660 finds track 3. fs_iso9660 is the
// only caller in KOS and in the game. A CD-R image (game.cue; disc type is not
// CD_GDROM) takes the original path unchanged, so one ELF boots both images.
// The KOS tree is not modified.
#include <kos.h>
#include <dc/cdrom.h>

#include "re4dc_platform.h"

extern "C" int __real_cdrom_read_toc(cd_toc_t* toc, bool high_density);

#if defined(RE4DC_DISC_COMPAT) && RE4DC_DISC_COMPAT
// DISC_COMPAT (test 14, lane discread): KOS mounts the LAST data track (cdrom_locate_data_track). GD MENU Card Manager's
// "Shrink GDI" splits the HD area into track 3 (IP.BIN + the ISO9660 tree) and track 4 (file data at the same LBAs), so
// KOS found no file system and every /cd open failed (#17). The last data track is kept when it holds a primary volume
// descriptor ("\1CD001" 16 sectors in); otherwise the first data track that does is mounted: toc->last is cut back to
// it, which is all cdrom_locate_data_track and fs_iso9660 use (file LBAs are absolute, so track 4 is still read).
#include <malloc.h>
#include <string.h>
static bool has_pvd(uint32_t fad)
{
    // a heap sector buffer for the mount only (a static one would cost 2 KB of KOS heap for the whole run)
    uint8_t* sec = (uint8_t*) memalign(32, 2048);
    if (!sec) return true;  // keep KOS's choice
    const bool pvd = cdrom_read_sectors_ex(sec, fad + 16, 1, true) == ERR_OK && !memcmp(sec, "\1CD001", 6);
    free(sec);
    return pvd;
}
static void mount_fs_track(cd_toc_t* toc)
{
    const int first = TOC_TRACK(toc->first), last = TOC_TRACK(toc->last);
    if (first < 1 || last > 99 || first > last) return;
    int t = last;
    while (t >= first && TOC_CTRL(toc->entry[t - 1]) != 4) --t;
    if (t < first || has_pvd(TOC_LBA(toc->entry[t - 1]))) return;  // the normal image: unchanged
    for (int u = first; u < t; ++u) {
        if (TOC_CTRL(toc->entry[u - 1]) != 4 || !has_pvd(TOC_LBA(toc->entry[u - 1]))) continue;
        re4dc_log("gdrom: /cd from data track %d (FAD %lu): the last data track %d has no file system (split image)\n",
                  u, (unsigned long) TOC_LBA(toc->entry[u - 1]), t);
        toc->last = (toc->last & ~0x00FF0000u) | ((uint32_t) u << 16);
        return;
    }
    re4dc_log("gdrom: no data track holds a file system\n");
}
#endif

#if defined(RE4DC_CACHE_COHERENT_DMA) && RE4DC_CACHE_COHERENT_DMA
// CACHE_COHERENT_DMA: the TOC lands in a 32-byte aligned private copy whose lines are purged before and invalidated
// after the call, so no stale operand-cache line of the caller's stack buffer is read back.
static int coherent_read_toc(cd_toc_t* toc, bool hd)
{
    static union { cd_toc_t t; char pad[(sizeof(cd_toc_t) + 31) & ~31u]; } u __attribute__((aligned(32)));
    dcache_purge_range((uintptr_t) &u, sizeof u);
    const int rv = __real_cdrom_read_toc(&u.t, hd);
    dcache_inval_range((uintptr_t) &u, sizeof u);
    *toc = u.t;
    return rv;
}
#define READ_TOC coherent_read_toc
#else
#define READ_TOC __real_cdrom_read_toc
#endif

extern "C" int __wrap_cdrom_read_toc(cd_toc_t* toc, bool high_density)
{
    if (!high_density) {
        int status = 0, type = -1;
        // fs_iso9660 calls this right after cdrom_reinit(); a busy status read
        // is retried a few times before falling back to the original request.
        for (int tries = 0; tries < 4 && cdrom_get_status(&status, &type) < 0; tries++) type = -1;
        if (type == CD_GDROM && READ_TOC(toc, true) == 0) {
#if defined(RE4DC_DISC_COMPAT) && RE4DC_DISC_COMPAT
            mount_fs_track(toc);
#endif
            const uint32_t fad = cdrom_locate_data_track(toc);
            if (fad) {
                static bool logged;
                if (!logged) {
                    logged = true;
                    re4dc_log("gdrom: /cd from high-density TOC, data track FAD %lu (LBA %lu)\n",
                              (unsigned long) fad, (unsigned long) (fad - 150));
                }
                return 0;
            }
        }
    }
    return READ_TOC(toc, high_density);
}
