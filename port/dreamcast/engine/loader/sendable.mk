# sendable.mk: SENDABLE=1 build option for engine images (lane eng-loop2, 2026-11-20; docs/engine/CONSOLE_LOOP.md
# section 10). Include it from an image Makefile with OUT set, then add $(CL_SEND_OBJS) to the link and
# $(CL_SEND_LDFLAGS) to its flags. Adds the client library (hand-off area, way back to the loader), cl_send.c (text
# report, end line, data root on the loader disc) and the KOS disc fixes; no image source changes. The image still
# boots from its own disc as before (everything stays off unless the loader started it).
#   CL_SEND_END / CL_SEND_FAIL: the image's last line / refusal lines, "a|b" (defaults in cl_send.c)
CL_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CL_OUT := $(OUT)/cl
KOSFIX := $(CL_OUT)/kosfix
include $(CL_DIR)/kosfix.mk
CL_SEND_DEFS := $(if $(CL_SEND_END),-DCL_SEND_END='"$(CL_SEND_END)"') $(if $(CL_SEND_FAIL),-DCL_SEND_FAIL='"$(CL_SEND_FAIL)"')
CL_SEND_OBJS := $(CL_OUT)/client.o $(CL_OUT)/cl_util.o $(CL_OUT)/cl_send.o $(KOSFIX_OBJS)
CL_SEND_LDFLAGS := -Wl,--wrap=fs_open -Wl,--wrap=arch_abort
$(CL_OUT)/client.o: $(CL_DIR)/client.c $(CL_DIR)/cl_client.h $(CL_DIR)/cl_core.h $(CL_DIR)/cl_handoff.h
	@mkdir -p $(dir $@)
	kos-cc -std=gnu11 -Os -Wall -DCL_WRAP_ABORT -c $< -o $@
$(CL_OUT)/cl_util.o: $(CL_DIR)/cl_util.c $(CL_DIR)/cl_core.h $(CL_DIR)/cl_proto.h $(CL_DIR)/cl_handoff.h
	@mkdir -p $(dir $@)
	kos-cc -std=gnu11 -Os -Wall -c $< -o $@
$(CL_OUT)/cl_send.o: $(CL_DIR)/cl_send.c $(CL_DIR)/cl_client.h $(CL_DIR)/cl_core.h $(CL_DIR)/cl_handoff.h
	@mkdir -p $(dir $@)
	kos-cc -std=gnu11 -Os -Wall $(CL_SEND_DEFS) -c $< -o $@
$(KOSFIX)/cdrom.c $(KOSFIX)/fs_iso9660.c: | $(KOSFIX)/.dir
$(KOSFIX)/.dir:
	@mkdir -p $(dir $@) && touch $@
