# sendable.mk: SENDABLE=1 build option for engine images (lane eng-loop2, 2026-11-20; lane eng-link1, 2026-11-22;
# docs/engine/CONSOLE_LOOP.md sections 10 and 15). Include it from an image Makefile with OUT set, then add
# $(CL_SEND_OBJS) to the link and $(CL_SEND_LDFLAGS) to its flags. Adds dc-qalink's client library (dc-qalink/loader/
# client.mk: the hand-off area, every way back to the loader through the return stub, the watchdog, and on the
# broadband adapter the live link: serial lines, stills and the PC's files as /pc), cl_send.c (text report, end line,
# data roots, src=pc, the stills hand-over) and the KOS disc fixes; no image source changes. The image still boots from
# its own disc as before (everything stays off unless the loader or the scene runner started it).
#   CL_SEND_END / CL_SEND_FAIL: the image's last line / refusal lines, "a|b" (defaults in cl_send.c)
CL_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CL_OUT := $(OUT)/cl
KOSFIX := $(CL_OUT)/kosfix
include $(CL_DIR)/kosfix.mk
include $(CL_DIR)/dc-qalink/loader/client.mk
CL_SEND_DEFS := $(if $(CL_SEND_END),-DCL_SEND_END='"$(CL_SEND_END)"') $(if $(CL_SEND_FAIL),-DCL_SEND_FAIL='"$(CL_SEND_FAIL)"')
CL_SEND_OBJS := $(CL_CLIENT_OBJS) $(CL_OUT)/cl_send.o $(KOSFIX_OBJS)
CL_SEND_LDFLAGS := -Wl,--wrap=fs_open $(CL_CLIENT_LDFLAGS)
$(CL_OUT)/cl_send.o: $(CL_DIR)/cl_send.c $(CL_HDRS)
	@mkdir -p $(dir $@)
	kos-cc -std=gnu11 -Os -Wall $(CL_CLIENT_CFLAGS) $(CL_SEND_DEFS) -c $< -o $@
$(KOSFIX)/cdrom.c $(KOSFIX)/fs_iso9660.c: | $(KOSFIX)/.dir
$(KOSFIX)/.dir:
	@mkdir -p $(dir $@) && touch $@
