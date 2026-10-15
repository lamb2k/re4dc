// Force-included into crash_screen.cpp (game/Makefile): the crash screen's stage row names the GD DMA completion
// counters of kos-804b319-cdrom-dma-done.patch with KOS_DISC_FIX=1 ("gd s<drained stale> e<closed early>"), and nothing
// otherwise. A header so crash_screen.cpp keeps its line numbers (__LINE__ in its halts).
#pragma once
#if defined(RE4DC_KOS_DMA_COUNTERS) && RE4DC_KOS_DMA_COUNTERS
extern "C" unsigned re4dc_cdrom_stale_done, re4dc_cdrom_early_done;
#define RE4DC_GD_FMT "  gd s%u e%u"
#define RE4DC_GD_ARGS , re4dc_cdrom_stale_done, re4dc_cdrom_early_done
#else
#define RE4DC_GD_FMT
#define RE4DC_GD_ARGS
#endif
