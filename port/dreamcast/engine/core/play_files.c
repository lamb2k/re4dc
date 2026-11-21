/* play_files.c: files opened during play (lane eng-e1o, H-017.7). Every boot file is looked up once, before the first
   picture; nothing opens a file inside a picture. Every fs_open of the image goes through this wrapper
   (-Wl,--wrap=fs_open, game/Makefile; KOS's own fopen reaches fs_open too): between the first and the last picture
   (e1_play_files_begin / _end, core/frame.cpp) each open is counted, with the tick and name of the first. The report
   prints "E1 FILES in play: opens N first tick T name X"; the console disc's selector fails a timing scene where N is
   not 0 (loader/selector.c).
   With SENDABLE=1 the console loop's data root (loader/cl_send.c cl_send_fs_open: /cd/<root>/<path> first) is called
   from here; without it the open goes straight to KOS. */
#include <kos.h>
#include <kos/fs.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

extern volatile uint32_t e1_tick;   /* core/main.cpp */
void e1_log(const char* fmt, ...);
file_t __real_fs_open(const char* fn, int mode);
file_t cl_send_fs_open(const char* fn, int mode) __attribute__((weak));

static volatile int in_play;
static unsigned opens, first_tick;
static char first_name[40];

file_t __wrap_fs_open(const char* fn, int mode)
{
    if (in_play) {
        if (!opens++) {
            first_tick = e1_tick;
            snprintf(first_name, sizeof(first_name), "%s", fn ? fn : "?");
        }
    }
    return cl_send_fs_open ? cl_send_fs_open(fn, mode) : __real_fs_open(fn, mode);
}

void e1_play_files_begin(void) { in_play = 1; }
void e1_play_files_end(void) { in_play = 0; }
void e1_play_files_report(void)
{
    e1_log("E1 FILES in play: opens %u first tick %u name %s\n", opens, opens ? first_tick : 0u, opens ? first_name : "-");
}
