/* KOS boot flags of the E1 image (kept apart: <kos.h> cannot share a unit with the original headers). */
#include <kos.h>
KOS_INIT_FLAGS(INIT_DEFAULT);
/* The bench disc layout (track 3 at LBA 45000 in the high-density area): read the TOC of the high-density area
   first (as the E0 bench does, bench/main.c). */
int __real_cdrom_read_toc(cd_toc_t*, bool);
int __wrap_cdrom_read_toc(cd_toc_t* toc, bool hd)
{
    int rc = __real_cdrom_read_toc(toc, true);
    return rc && !hd ? __real_cdrom_read_toc(toc, false) : rc;
}
