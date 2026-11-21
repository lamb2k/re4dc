// em_compress.cpp (lane eng-e1h): the Ganado's dissolving-corpse squash on the native skeleton. em10.cpp's
// em10ScaleCompress (run by cEm10::move right after partsWorldCalc) decides it, in Die_Lost (r_no_0 3, r_no_1 3), with
// the factor its death routine fades (Em10Work::Compress_y); the squash itself is pose work and goes to the skeleton
// service (skel.cpp skel_compress_y), which keeps the table the palette and the renderer read. The hosted em10 unit's own
// body is made weak where it is linked (game/Makefile WEAKEN_em10/em10; hostref svc.mk weak6/), so this one is reached.
#include "em10.h"
#include "skel.h"

void em10ScaleCompress(cEm10* em)
{
    Em10Work* w = EM10_WK(em);
    if (em->r_no_0 == 3) {
        if (em->r_no_1 == 3) skel_compress_y(em, w->Compress_y);
    }
}
