# QA_LINK=1 (lane qalink27, 2026-10-27; QA discs only, never a release image; needs QA_MENU=1): the QA remote link.
#   The QA menu gets a row "REMOTE LINK: OFF / DIALLING / UP ...". ON dials the built-in 56k modem (a DreamPi answers),
#   PPP gives the console an address, and one UDP socket (port 52040) carries text both ways: once a second the
#   Diagnostics page's rows (DRAW_SETUP_AUDIT rows included) and new RAM log lines out; PING / TELEPORT / QA <row>
#   <value> / RECORD <ticks> / MENU / RESUME / DIAG in, run on the game thread through the QA menu's own handlers.
#   Settings: /cd/dc/qa/link.txt (optional): `number <digits>`, `host <a.b.c.d|peer>`, `port <n>`, `auto 1` (dial at the
#   first game tick, for harness runs). Pi side and setup: tools/qalink/README.md.
#   Files: qa_link.cpp (modem + PPP + UDP; a dial thread, the PPP thread and two rings), qa_menu.cpp (#if RE4DC_QA_LINK:
#   the row and the protocol), dbgwarp_bridge.cpp (#if RE4DC_QA_LINK: qa_poll calls re4dc_qa_link_tick each tick).
#   PPP: KOS's own libppp sources (the pinned $(KOS_BASE)/addons/libppp), compiled here with four names redirected to
#   qa_link.cpp (thread stack from BSS, a sleeping receive loop that also moves the datagrams, a modem write that cannot
#   spin on a dropped line, counted reads); libppp.a is not linked. The KOS network stack is used without net_init()
#   (no work-queue thread, no DHCP). The modem driver's buffers and timeout worker stack come from BSS (--wrap below).
#   Cost (lane qalink27, Flycast): ~0.12 ms a frame and 2.5 KiB KOS heap while the link is up, 0 while off; image +94 KiB
#   (code 53 KiB, BSS 41 KiB) on QA discs. KOS 48 KiB squeeze gate PASS with the link up (5 scenes x 2).
#   Default 0: nothing is compiled or linked; the image is byte-identical with or without this file.
QA_LINK ?= 0
ifneq ($(filter $(QA_LINK),0 1),$(QA_LINK))
$(error QA_LINK must be 0 or 1)
endif
ifeq ($(QA_LINK),1)
ifneq ($(QA_MENU),1)
$(error QA_LINK=1 needs QA_MENU=1 (the link drives the QA menu's handlers))
endif
# Console transport fix from 7acd7d8f, without importing bench/default-policy changes.
# Both experimental arms retain this same 4 KiB KOS reserve.
QA_LINK_KOS_BYTES ?= 4096
$(OBJDIR)/platform/mem.o: PLATFORM_CPPFLAGS += -DRE4DC_QA_LINK_KOS_BYTES=$(QA_LINK_KOS_BYTES)
QALINK_PPP_DIR := $(KOS_BASE)/addons/libppp
QALINK_PPP_OBJS := $(OBJDIR)/qalink/ppp.o $(OBJDIR)/qalink/lcp.o $(OBJDIR)/qalink/pap.o $(OBJDIR)/qalink/ipcp.o \
                   $(OBJDIR)/qalink/ppp_modem.o
QALINK_PPP_DEFS := -Dthd_create=re4dc_qalink_thd_create -Dthd_pass=re4dc_qalink_thd_pass \
                   -Dmodem_write_data=re4dc_qalink_modem_write -Dmodem_read_data=re4dc_qalink_modem_read
# QA_LINK_DEBUG=1: libppp's own trace (PPP_DEBUG) into the game's RAM log (the LCP / IPCP options of each packet)
QA_LINK_DEBUG ?= 0
ifeq ($(QA_LINK_DEBUG),1)
QALINK_PPP_DEFS += -DPPP_DEBUG -Ddbglog=re4dc_qalink_dbglog
$(OBJDIR)/qa_link.o: PLATFORM_CPPFLAGS += -DRE4DC_QA_LINK_DEBUG=1
endif
PLATFORM_OBJS += $(OBJDIR)/qa_link.o $(QALINK_PPP_OBJS)
# the modem driver's chain buffers and its timeout worker's stack from BSS (qa_link.cpp): no KOS heap for them
GAME_LDFLAGS += -Wl,--wrap=createChainBuffer -Wl,--wrap=destroyChainBuffer -Wl,--wrap=thd_worker_create_ex
$(TARGET): $(OBJDIR)/qa_link.o $(QALINK_PPP_OBJS)
$(OBJDIR)/qa_menu.o: PLATFORM_CPPFLAGS += -DRE4DC_QA_LINK=1
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_QA_LINK=1
# PAD/GOTO/position authority from e6f69b9c, only in the explicit link profile.
$(OBJDIR)/platform/pad.o $(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_QA_LINK=1
$(OBJDIR)/qa_link.o: qa_link.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@
-include $(OBJDIR)/qa_link.d
$(OBJDIR)/qalink/%.o: $(QALINK_PPP_DIR)/%.c
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -Os -I$(QALINK_PPP_DIR) -I$(KOS_BASE)/kernel/net $(QALINK_PPP_DEFS) -c $< -o $@
endif
