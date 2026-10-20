# edemo18 standalone KOS stress demo. Not part of the game build.
#   RE4DC_KOS_BASE=/root/work/kos-re4dc-d336 bash -c '. ../../kos-env.sh && make OUT=<objdir>'
# The ELF is OUT/edemo.elf. -O2, -m4-single (KOS), no fast-math (the plain-C arm keeps FDIV / FSQRT).
OUT ?= build
SHZ := ../../game/third_party/sh4zam/include
CFLAGS_E := -O2 -std=gnu11 -Wall -Wextra -Wno-unused-parameter -fno-strict-aliasing -I$(SHZ) -I.. $(EXTRA)

all: $(OUT)/edemo.elf

$(OUT):
	mkdir -p $@

$(OUT)/edemo_engine.o: ../edemo_engine.c ../edemo_engine.h | $(OUT)
	kos-cc $(CFLAGS_E) -c $< -o $@

$(OUT)/edemo_main.o: edemo_main.c ../edemo_engine.h | $(OUT)
	kos-cc $(CFLAGS_E) -c $< -o $@

ifneq ($(EMBED_PAK),)
EMBED_OBJ := $(OUT)/edemo_embed.o
CFLAGS_E += -DEDEMO_EMBED=1
$(OUT)/edemo_embed.o: edemo_embed.S $(EMBED_PAK) $(EMBED_ARMS) | $(OUT)
	kos-cc -c -DEMBED_PAK='"$(EMBED_PAK)"' -DEMBED_ARMS='"$(EMBED_ARMS)"' $< -o $@
endif

$(OUT)/edemo.elf: $(OUT)/edemo_main.o $(OUT)/edemo_engine.o $(EMBED_OBJ)
	kos-cc -o $@ $^ -lm
