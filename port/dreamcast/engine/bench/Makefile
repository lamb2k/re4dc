OUT ?= build
SHZ := ../../game/third_party/sh4zam/include
FLAGS := -std=gnu11 -O2 -Wall -fno-strict-aliasing -I../render -I$(SHZ)
.PHONY: all packs
all: packs $(OUT)/m1.elf
packs:
	@test -s "$(PRIVATE_PACK_DIR)/cross-m1.pak" -a -s "$(PRIVATE_PACK_DIR)/hayfork-m1.pak" || { echo "M1 missing private packs in PRIVATE_PACK_DIR"; exit 1; }
$(OUT):
	mkdir -p $@
$(OUT)/m1.elf: main.c ../render/render.c ../render/replay_pack.c ../render/replay.h | $(OUT)
	kos-cc $(FLAGS) $(EXTRA) $(filter %.c,$^) -Wl,--wrap=cdrom_read_toc -o $@ -lm

