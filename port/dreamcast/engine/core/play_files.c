/* play_files.c: disc access during play (lane eng-e1o, H-017.7; lane eng-e1p, H-018.4). Every boot file is looked up
   once, before the first picture; nothing opens or reads the disc inside a picture. Between the first and the last
   picture (e1_play_files_begin / _end, core/frame.cpp) three things are counted, each with the tick of the first:
   - opens: every fs_open of the image goes through this wrapper (-Wl,--wrap=fs_open, game/Makefile; KOS's own fopen
     reaches fs_open too), with the name of the first;
   - reads: fs_read on a disc-backed handle (opened under /cd, whenever it was opened: a handle opened before play and
     read in play counts), -Wl,--wrap=fs_read (newlib's read() reaches fs_read too); fs_close drops the handle's mark;
   - sector requests: the CD drive's read commands as the ISO filesystem of this KOS issues them (its block cache's
     cdrom_read_sectors_ex, its large-read stream cdrom_stream_start and cdrom_stream_request; game/Makefile wraps these
     and cdrom_read_sectors), and the table-of-contents reads (core/boot.c's cdrom_read_toc wrapper), each one request.
     A read the ISO cache answers is a read with no sector request; a sector request with no read is the drive used by
     something else.
   The report prints "E1 FILES in play: opens N reads R sector-requests S first-open-tick T first-read-tick T
   first-sector-tick T name X"; the console disc's selector fails a timing scene where any of the three is not 0
   (loader/selector.c).
   With SENDABLE=1 the console loop's data root (loader/cl_send.c cl_send_fs_open: /cd/<root>/<path> first) is called
   from here; without it the open goes straight to KOS. */
#include <kos.h>
#include <kos/fs.h>
#include <dc/cdrom.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

extern volatile uint32_t e1_tick;   /* core/main.cpp */
void e1_log(const char* fmt, ...);
file_t __real_fs_open(const char* fn, int mode);
ssize_t __real_fs_read(file_t fd, void* buf, size_t n);
int __real_fs_close(file_t fd);
int __real_cdrom_read_sectors(void* buffer, uint32_t sector, size_t cnt);
int __real_cdrom_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma);
int __real_cdrom_stream_start(int sector, int cnt, bool dma);
int __real_cdrom_stream_request(void* buffer, size_t size, bool block);
file_t cl_send_fs_open(const char* fn, int mode) __attribute__((weak));

static volatile int in_play;
static unsigned opens, open_tick, reads, read_tick, sectors, sector_tick;
static char first_name[40];
#define DISC_FDS 1024   /* KOS's FD_SETSIZE */
static uint32_t disc_fd[DISC_FDS / 32];   /* handles opened under /cd */

static int disc_backed(file_t fd) { return fd >= 0 && fd < DISC_FDS && (disc_fd[fd >> 5] >> (fd & 31) & 1u); }

file_t __wrap_fs_open(const char* fn, int mode)
{
    if (in_play) {
        if (!opens++) {
            open_tick = e1_tick;
            snprintf(first_name, sizeof(first_name), "%s", fn ? fn : "?");
        }
    }
    const file_t fd = cl_send_fs_open ? cl_send_fs_open(fn, mode) : __real_fs_open(fn, mode);
    if (fd >= 0 && fd < DISC_FDS) {
        if (fn && !strncmp(fn, "/cd/", 4)) disc_fd[fd >> 5] |= 1u << (fd & 31);
        else disc_fd[fd >> 5] &= ~(1u << (fd & 31));
    }
    return fd;
}

ssize_t __wrap_fs_read(file_t fd, void* buf, size_t n)
{
    if (in_play && disc_backed(fd) && !reads++) read_tick = e1_tick;
    return __real_fs_read(fd, buf, n);
}

int __wrap_fs_close(file_t fd)
{
    if (fd >= 0 && fd < DISC_FDS) disc_fd[fd >> 5] &= ~(1u << (fd & 31));
    return __real_fs_close(fd);
}

void e1_play_disc_request(void)   /* one CD drive read command (here, and core/boot.c's TOC read) */
{
    if (in_play && !sectors++) sector_tick = e1_tick;
}
int __wrap_cdrom_read_sectors(void* buffer, uint32_t sector, size_t cnt)
{
    e1_play_disc_request();
    return __real_cdrom_read_sectors(buffer, sector, cnt);
}
int __wrap_cdrom_read_sectors_ex(void* buffer, uint32_t sector, size_t cnt, bool dma)
{
    e1_play_disc_request();
    return __real_cdrom_read_sectors_ex(buffer, sector, cnt, dma);
}
int __wrap_cdrom_stream_start(int sector, int cnt, bool dma)
{
    e1_play_disc_request();
    return __real_cdrom_stream_start(sector, cnt, dma);
}
int __wrap_cdrom_stream_request(void* buffer, size_t size, bool block)
{
    e1_play_disc_request();
    return __real_cdrom_stream_request(buffer, size, block);
}

void e1_play_files_begin(void) { in_play = 1; }
void e1_play_files_end(void) { in_play = 0; }
void e1_play_files_report(void)
{
    e1_log("E1 FILES in play: opens %u reads %u sector-requests %u first-open-tick %u first-read-tick %u "
           "first-sector-tick %u name %s\n", opens, reads, sectors, opens ? open_tick : 0u, reads ? read_tick : 0u,
           sectors ? sector_tick : 0u, opens ? first_name : "-");
}
