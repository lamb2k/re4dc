# qalink.mk: the RE4 engine's layer on dc-qalink 0.2 (lane eng-link2, 2026-11-23; docs/engine/CONSOLE_LOOP.md
# section 17). Included by game/Makefile after loader/sendable.mk when SENDABLE=1. QA and test builds only:
#   DCQL_ENABLE (default: the value of SENDABLE) = 1 adds engine/qalink/e1_qalink.cpp (live data, the PC's commands,
#   warps, RE4's menu pages), dc-qalink's in-game menu (lib/dcql_menu.c) and network disc (lib/dcql_disc.c), and
#   compiles core/main.cpp's three calls into it (E1_QALINK). DCQL_ENABLE=0 with SENDABLE=1: the loop's client alone
#   (report, way back, lines), no live data, menu or network disc: the "link off" control build.
# A build without SENDABLE (the default, FIGHT=1 and BOSS=1 images as the release recipe builds them) does not include
# this file: none of dc-qalink is linked (check: no dcql_ or cl_ symbol in its e1.map).
DCQL_ENABLE ?= $(SENDABLE)
ifeq ($(DCQL_ENABLE),1)
QL_DIR := $(ENG)/loader/dc-qalink
QL_LAYER_OBJS := $(OUT)/ql/e1_qalink.o $(CL_OUT)/dcql_menu.o $(CL_OUT)/dcql_disc.o
ENG_FLAGS += -DE1_QALINK=1 -I$(ENG)/qalink
CL_SEND_OBJS += $(QL_LAYER_OBJS)
$(OUT)/ql/e1_qalink.o: $(ENG)/qalink/e1_qalink.cpp $(ENG)/qalink/e1_qalink.h $(ENG_HDRS) $(CL_HDRS) \
		$(QL_DIR)/lib/dcql_menu.h $(QL_DIR)/lib/dcql_disc.h
	@mkdir -p $(dir $@)
	kos-c++ $(ENG_FLAGS) $(ORIG_INC) -I$(ENG)/render -I$(ENG)/core -I$(ENG)/services $(NATIVE_INC) $(CL_CLIENT_CFLAGS) -c $< -o $@
$(CL_OUT)/dcql_menu.o: $(QL_DIR)/lib/dcql_menu.c $(QL_DIR)/lib/dcql_menu.h $(QL_DIR)/lib/font/spleen8x16.h $(CL_HDRS)
	@mkdir -p $(dir $@)
	kos-cc -std=gnu11 -Os -Wall $(CL_CLIENT_CFLAGS) -c $< -o $@
$(CL_OUT)/dcql_disc.o: $(QL_DIR)/lib/dcql_disc.c $(QL_DIR)/lib/dcql_disc.h $(CL_HDRS)
	@mkdir -p $(dir $@)
	kos-cc -std=gnu11 -Os -Wall $(CL_CLIENT_CFLAGS) -c $< -o $@
endif
