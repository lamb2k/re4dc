# kosfix.mk: the release game's KallistiOS disc fixes (game/Makefile KOS_DISC_FIX=1) for the console loop's programs
# (lane eng-loop2, 2026-11-20). Patched copies of KOS cdrom.c (exec_cmd_timed's abort deadlock, reinit's endless retry,
# a settle delay after a drive reset, no stale GD DMA completion: kos-804b319-cdrom-hang-fixes / -cdrom-dma-done) and
# fs_iso9660.c (upstream aeee10d9) are linked in place of libkallisti's; KOS itself is not modified. Without them a
# program that reads a file sector by sector after the loader's jump stops under console-like Flycast's GDEMU profile
# (stale DMA completions pile up: "SH4 exception when blocked"), the console failure the game fixed on 10-15.
#   include with KOSFIX := <dir>; link $(KOSFIX_OBJS)
KOSFIX_PATCHES := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))../../patches)
KOSFIX_OBJS := $(KOSFIX)/cdrom.o $(KOSFIX)/fs_iso9660.o
$(KOSFIX)/fs_iso9660.c: $(KOS_BASE)/kernel/arch/dreamcast/fs/fs_iso9660.c $(KOSFIX_PATCHES)/kos-804b319-fs-iso9660-aeee10d9.patch
	@rm -rf $(KOSFIX)/p-fs && mkdir -p $(KOSFIX)/p-fs/kernel/arch/dreamcast/fs
	cp $< $(KOSFIX)/p-fs/kernel/arch/dreamcast/fs/
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-fs < $(KOSFIX_PATCHES)/kos-804b319-fs-iso9660-aeee10d9.patch
	cp $(KOSFIX)/p-fs/kernel/arch/dreamcast/fs/fs_iso9660.c $@
$(KOSFIX)/cdrom.c: $(KOS_BASE)/kernel/arch/dreamcast/hardware/cdrom.c $(KOSFIX_PATCHES)/kos-804b319-cdrom-hang-fixes.patch $(KOSFIX_PATCHES)/kos-804b319-cdrom-dma-done.patch
	@rm -rf $(KOSFIX)/p-cd && mkdir -p $(KOSFIX)/p-cd/kernel/arch/dreamcast/hardware
	cp $< $(KOSFIX)/p-cd/kernel/arch/dreamcast/hardware/
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-cd < $(KOSFIX_PATCHES)/kos-804b319-cdrom-hang-fixes.patch
	patch --fuzz=0 -s -p1 -d $(KOSFIX)/p-cd < $(KOSFIX_PATCHES)/kos-804b319-cdrom-dma-done.patch
	cp $(KOSFIX)/p-cd/kernel/arch/dreamcast/hardware/cdrom.c $@
$(KOSFIX)/%.o: $(KOSFIX)/%.c
	kos-cc $(KOS_CFLAGS) -O2 -fmacro-prefix-map=$(KOSFIX)/=kosfix/ -c $< -o $@
