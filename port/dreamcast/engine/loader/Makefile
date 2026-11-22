# The RE4 console loop's programs (lane eng-loop, 2026-11-19; lane eng-link1, 2026-11-22: docs/engine/CONSOLE_LOOP.md).
# Needs the KOS environment (port/dreamcast/kos-env.sh with RE4DC_KOS_BASE=/root/work/kos-re4dc-d367).
# The loader, its return stub, the client library, the protocol and the PC tool are dc-qalink 0.2 (the submodule
# dc-qalink/, game-neutral, public: github.com/lamb2k/dc-qalink); what is RE4's stays here: the console disc's scene
# runner (selector.c), cl_send.c (sendable.mk) and the release game's KOS disc fixes (kosfix.mk), linked into all.
#   make OUT=<dir>            loader.elf, LOADER.BIN, testprog.elf, testprog.bin, stub.bin, selector.elf, SELECTOR.BIN
#   make OUT=<dir> selector   the scene runner only (tools/engine/build_console_disc.sh)
#   make OUT=<dir> host       cl_host (the protocol core on the PC, for dc-qalink/tests/test_loop.py)
OUT ?= build
BUILD ?= dev
HERE := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
QL := $(HERE)/dc-qalink
AOUT := $(abspath $(OUT))
.DEFAULT_GOAL := all
KOSFIX := $(AOUT)/kosfix
include kosfix.mk
QLINC := -I$(QL)/include -I$(QL)/loader -I$(QL)/lib
CFLAGS_L := -std=gnu11 -Os -Wall -Wextra -Wno-unused-parameter $(QLINC) -DLOADER_BUILD=\"$(BUILD)\"
# dc-qalink's own Makefile, with the RE4 title and the KOS disc fixes linked into the loader and the test program
QLMAKE = $(MAKE) -C $(QL)/loader OUT=$(AOUT)/ql BUILD="$(BUILD)" TITLE="RE4DC CONSOLE LOOP LOADER" \
         EXTRA_OBJS="$(KOSFIX_OBJS)"
SEL_QL := $(AOUT)/ql/cl_util.o $(AOUT)/ql/cl_arm.o $(AOUT)/ql/stub_blob.o
SEL_OBJS := $(AOUT)/selector.o $(SEL_QL) $(KOSFIX_OBJS)

.PHONY: all host selector loader ql-objs
all: loader selector
loader: $(KOSFIX_OBJS)
	$(QLMAKE) all
	cp $(AOUT)/ql/loader.elf $(AOUT)/ql/LOADER.BIN $(AOUT)/ql/testprog.elf $(AOUT)/ql/testprog.bin $(AOUT)/ql/stub.bin $(AOUT)/
selector: $(AOUT)/selector.elf $(AOUT)/SELECTOR.BIN

ql-objs:
	$(QLMAKE) $(SEL_QL)
$(SEL_QL): ql-objs
$(AOUT)/selector.o: selector.c $(QL)/include/dcql_loop.h $(QL)/loader/cl_core.h $(QL)/loader/cl_arm.h
	@mkdir -p $(dir $@)
	kos-cc $(CFLAGS_L) -c $< -o $@
$(AOUT)/selector.elf: $(SEL_OBJS) ql-objs
	kos-cc $(CFLAGS_L) $(SEL_OBJS) -Wl,--wrap=cdrom_read_toc -o $@
$(AOUT)/SELECTOR.BIN: $(AOUT)/selector.elf
	sh-elf-objcopy -R .stack -O binary $< $@

host:
	$(MAKE) -C $(QL)/loader OUT=$(AOUT)/ql host
	cp $(AOUT)/ql/cl_host $(AOUT)/
