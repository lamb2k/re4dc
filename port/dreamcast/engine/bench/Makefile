OUT ?= build
SHZ := ../../game/third_party/sh4zam/include
FLAGS := -std=gnu11 -O2 -Wall -fno-strict-aliasing -I../render -I$(SHZ)
.PHONY: all packs
all: packs $(OUT)/m1.elf
packs:
	@test -s "$(PRIVATE_PACK_DIR)/cross-m1.pak" -a -s "$(PRIVATE_PACK_DIR)/hayfork-m1.pak" || { echo "M1 missing private packs in PRIVATE_PACK_DIR"; exit 1; }
$(OUT):
	mkdir -p $@
$(OUT)/m1.elf: main.c ../../game/platform/avk_sh4.S ../render/render.c ../render/replay_pack.c ../render/replay.h ../render/indexed.inc | $(OUT)
	kos-cc $(FLAGS) $(EXTRA) -DRE4DC_ACTOR_LIGHT_N16=1 $(filter %.c %.S,$^) -Wl,--wrap=cdrom_read_toc -o $@ -lm

.PHONY: native
native: native-packs $(OUT)/native.elf
.PHONY: native-packs
native-packs:
	@test -s "$(PRIVATE_PACK_DIR)/cross.pak" -a -s "$(PRIVATE_PACK_DIR)/hayfork.pak" || { echo "M1 missing native packs in PRIVATE_PACK_DIR"; exit 1; }
$(OUT)/native.elf: main.c ../render/render.c ../render/replay_pack.c ../render/native_world.c ../../game/platform/avk_sh4.S ../render/native_scene.inc ../render/native_draw.inc ../render/native_actor.inc ../render/native_layers.inc ../render/native_world.h ../render/native_scene.h | $(OUT)
	kos-cc $(FLAGS) $(EXTRA) -DM1_NATIVE -DRE4DC_ACTOR_LIGHT_N16=1 $(filter %.c %.S,$^) -Wl,--wrap=cdrom_read_toc -o $@ -lm
