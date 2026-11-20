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
.PHONY: all
all: native
$(OUT):
	mkdir -p $@

.PHONY: native native-packs
native: native-packs $(OUT)/native.elf
native-packs:
	@test -s "$(PRIVATE_PACK_DIR)/cross.pak" -a -s "$(PRIVATE_PACK_DIR)/hayfork.pak" || { echo "M1 missing native packs in PRIVATE_PACK_DIR"; exit 1; }
RENDER_DEPS := $(wildcard ../render/*.inc ../render/*.h)
$(OUT)/main.o: main.c memmap.h $(RENDER_DEPS) | $(OUT)
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
# lane eng-loop2: SENDABLE=1 links the console loop's client (loader/sendable.mk) for the console disc and the loader
ifeq ($(SENDABLE),1)
include ../loader/sendable.mk
.DEFAULT_GOAL := all
endif
$(OUT)/native.elf: $(NATIVE_OBJS) $(CL_SEND_OBJS)
	kos-cc $(COMMON) $(SIZE) $(EXTRA) $^ $(CL_SEND_LDFLAGS) -Wl,--wrap=cdrom_read_toc -Wl,--wrap=malloc,--wrap=calloc,--wrap=memalign,--wrap=realloc,--wrap=free -o $@ -lm
