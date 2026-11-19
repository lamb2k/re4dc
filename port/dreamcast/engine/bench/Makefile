OUT ?= build
SHZ := ../../game/third_party/sh4zam/include
# Engine image build (E0): fast math with the SH-4 sine/cosine and reciprocal-root instructions, no debug
# asserts, link-time optimisation; size-optimised by default, the hot render files speed-optimised.
# -Wdouble-promotion lists every float promoted to double (a slow path under -m4-single).
COMMON := -g -std=gnu11 -Wall -Wdouble-promotion -fno-strict-aliasing -ffast-math -mfsca -mfsrra -DNDEBUG \
          -flto -fipa-pta -I../render -I$(SHZ)
SIZE := -Os
HOT := -O2
DEFS := -DRE4DC_ACTOR_LIGHT_N16=1
.PHONY: all packs
all: native
packs:
	@test -s "$(PRIVATE_PACK_DIR)/cross-m1.pak" -a -s "$(PRIVATE_PACK_DIR)/hayfork-m1.pak" || { echo "M1 missing private packs in PRIVATE_PACK_DIR"; exit 1; }
$(OUT):
	mkdir -p $@
$(OUT)/m1.elf: main.c ../../game/platform/avk_sh4.S ../render/render.c ../render/replay_pack.c ../render/replay.h ../render/indexed.inc | $(OUT)
	kos-cc -std=gnu11 -O2 -Wall -fno-strict-aliasing -I../render -I$(SHZ) $(EXTRA) $(DEFS) $(filter %.c %.S,$^) -Wl,--wrap=cdrom_read_toc -o $@ -lm

.PHONY: native native-packs
native: native-packs $(OUT)/native.elf
native-packs:
	@test -s "$(PRIVATE_PACK_DIR)/cross.pak" -a -s "$(PRIVATE_PACK_DIR)/hayfork.pak" || { echo "M1 missing native packs in PRIVATE_PACK_DIR"; exit 1; }
RENDER_DEPS := $(wildcard ../render/*.inc ../render/*.h)
$(OUT)/main.o: main.c $(RENDER_DEPS) | $(OUT)
	kos-cc $(COMMON) $(SIZE) $(EXTRA) $(DEFS) -DM1_NATIVE -c $< -o $@
$(OUT)/replay_pack.o: ../render/replay_pack.c $(RENDER_DEPS) | $(OUT)
	kos-cc $(COMMON) $(SIZE) $(EXTRA) $(DEFS) -DM1_NATIVE -c $< -o $@
$(OUT)/render.o: ../render/render.c $(RENDER_DEPS) | $(OUT)
	kos-cc $(COMMON) $(HOT) $(EXTRA) $(DEFS) -DM1_NATIVE -c $< -o $@
$(OUT)/native_world.o: ../render/native_world.c $(RENDER_DEPS) | $(OUT)
	kos-cc $(COMMON) $(HOT) $(EXTRA) $(DEFS) -DM1_NATIVE -c $< -o $@
$(OUT)/avk_sh4.o: ../../game/platform/avk_sh4.S | $(OUT)
	kos-cc -c $< -o $@
$(OUT)/stage_sh4.o: ../render/stage_sh4.S | $(OUT)
	kos-cc -c $< -o $@
NATIVE_OBJS := $(addprefix $(OUT)/,main.o replay_pack.o render.o native_world.o avk_sh4.o stage_sh4.o)
$(OUT)/native.elf: $(NATIVE_OBJS)
	kos-cc $(COMMON) $(SIZE) $(EXTRA) $^ -Wl,--wrap=cdrom_read_toc -o $@ -lm
