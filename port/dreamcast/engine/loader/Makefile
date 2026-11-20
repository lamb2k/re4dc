# Console-loop loader (lane eng-loop, 2026-11-19; docs/engine/CONSOLE_LOOP.md). Needs the KOS environment
# (port/dreamcast/kos-env.sh with RE4DC_KOS_BASE=/root/work/kos-re4dc-d367).
#   make OUT=<dir>            loader.elf, LOADER.BIN, testprog.elf
#   make OUT=<dir> host       cl_host (the protocol core on the PC, for tools/consoleloop/test_consoleloop.py)
OUT ?= build
BUILD ?= dev
CFLAGS_L := -std=gnu11 -Os -Wall -Wextra -Wno-unused-parameter -DLOADER_BUILD=\"$(BUILD)\"
# KOS libppp from source with the QA link's four redirections (game/qalink.mk), here pointing at link.c
PPP_DIR := $(KOS_BASE)/addons/libppp
PPP_SRC := ppp.c lcp.c pap.c ipcp.c ppp_modem.c
PPP_OBJS := $(addprefix $(OUT)/ppp/,$(PPP_SRC:.c=.o))
PPP_DEFS := -Dthd_create=loader_link_thd_create -Dthd_pass=loader_link_thd_pass \
            -Dmodem_write_data=loader_link_modem_write -Dmodem_read_data=loader_link_modem_read \
            -Dsem_wait_timed=loader_link_sem_wait_timed
# lane eng-loop2: the release game's KOS disc fixes in both programs (kosfix.mk)
.DEFAULT_GOAL := all
KOSFIX := $(OUT)/kosfix
include kosfix.mk
LOADER_OBJS := $(addprefix $(OUT)/,main.o link.o cl_core.o cl_util.o) $(PPP_OBJS) $(KOSFIX_OBJS)
TEST_OBJS := $(addprefix $(OUT)/,testprog.o client.o cl_util.o) $(KOSFIX_OBJS)
# lane eng-loop2: the console disc's scene runner (selector.c; tools/engine/build_console_disc.sh)
SEL_OBJS := $(addprefix $(OUT)/,selector.o cl_util.o) $(KOSFIX_OBJS)
WRAPS := -Wl,--wrap=createChainBuffer -Wl,--wrap=destroyChainBuffer -Wl,--wrap=thd_worker_create_ex \
         -Wl,--wrap=cdrom_read_toc

.PHONY: all host selector
all: $(OUT)/loader.elf $(OUT)/LOADER.BIN $(OUT)/testprog.elf $(OUT)/testprog.bin $(OUT)/selector.elf $(OUT)/SELECTOR.BIN
selector: $(OUT)/selector.elf $(OUT)/SELECTOR.BIN

$(OUT)/ppp/%.o: $(PPP_DIR)/%.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -Os -I$(PPP_DIR) -I$(KOS_BASE)/kernel/net $(PPP_DEFS) -c $< -o $@
$(OUT)/%.o: %.c cl_proto.h cl_handoff.h cl_core.h link.h cl_client.h
	@mkdir -p $(dir $@)
	kos-cc $(CFLAGS_L) -c $< -o $@
$(OUT)/client.o: client.c cl_client.h cl_core.h cl_handoff.h
	@mkdir -p $(dir $@)
	kos-cc $(CFLAGS_L) -DCL_WRAP_ABORT -c $< -o $@
$(OUT)/loader.elf: $(LOADER_OBJS)
	kos-cc $(CFLAGS_L) $^ $(WRAPS) -o $@
$(OUT)/LOADER.BIN: $(OUT)/loader.elf
	sh-elf-objcopy -R .stack -O binary $< $@
$(OUT)/testprog.elf: $(TEST_OBJS)
	kos-cc $(CFLAGS_L) $^ -Wl,--wrap=cdrom_read_toc -Wl,--wrap=arch_abort -o $@
$(OUT)/testprog.bin: $(OUT)/testprog.elf
	sh-elf-objcopy -R .stack -O binary $< $@
$(OUT)/selector.elf: $(SEL_OBJS)
	kos-cc $(CFLAGS_L) $^ -Wl,--wrap=cdrom_read_toc -o $@
$(OUT)/SELECTOR.BIN: $(OUT)/selector.elf
	sh-elf-objcopy -R .stack -O binary $< $@

host: $(OUT)/cl_host
$(OUT)/cl_host: host.c cl_core.c cl_util.c cl_core.h cl_proto.h cl_handoff.h
	@mkdir -p $(OUT)
	gcc -std=c99 -D_DEFAULT_SOURCE -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer \
	  -o $@ host.c cl_core.c cl_util.c
