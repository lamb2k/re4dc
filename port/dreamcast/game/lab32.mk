# lab32.mk (lane lab32, 2026-11-17; included by Makefile before game30.mk): the console lab disc.
# LAB32=1 (QA discs only, default 0 = nothing compiled, the image is byte-identical with or without this file):
#   every speed switch that can be chosen at run time is compiled in at its widest setting and gated by one byte of
#   re4dc_lab32_k[] (platform/include/lab32.h). The QA link command `KNOB <name> <value>` / `KNOB PRESET <name>` /
#   `KNOBS` (qa_menu.cpp) sets them; the boot state is the Test 27.2 release behaviour (control). Same ELF for every arm,
#   so build-layout noise cancels. Compile-time only, so NOT arms of the lab disc: GANADO_LOD_BUF31 / ESP_NUMLIST31 (memory
#   layout only; ON in the lab ELF), LAKE_FAR / CPU_BACKFACE / VIEW and other room-table switches.
#   Needs QA_MENU=1 (the link) and the knobs below at their widest; `LAB32_FXCUT_LIST` is the FXCUT_ROOMS room list.
LAB32 ?= 0
# LAB32_BOOT=<n> (gate twins only, default 0): the knob bytes start at preset n of qa_menu.cpp kPre (1 = fix4, 2 = all31, ...), not control.
LAB32_BOOT ?= 0
LAB32_OBJS_GAME := $(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/motion.o $(OBJDIR)/src/game/pendulum.o $(OBJDIR)/src/game/id_sys.o $(OBJDIR)/pace.o $(OBJDIR)/coarse.o
# the hooks in those files expand to nothing outside LAB32 builds; lab32.h is found through this include path in every build
$(LAB32_OBJS_GAME): GAME_CPPFLAGS += -I$(CURDIR)/platform/include
ifneq ($(filter $(LAB32),0 1),$(LAB32))
$(error LAB32 must be 0 or 1)
endif
ifeq ($(LAB32),1)
ifneq ($(QA_MENU),1)
$(error LAB32=1 needs QA_MENU=1 (and the QA link))
endif
LAB32_FXCUT_LIST ?= 0x105,0x108,0x10a,0x10d,0x118,0x11a,0x11b,0x200
R10B_FX_DEAD ?= 3
R10B_FX_CUT ?= 7
R10B_FX_UNLIVE ?= 1
R10B_FX_SPAWNCAP ?= 255
ESP_MAP_WORDS ?= 57
FXCUT_ROOMS ?= 3
FXCUT_ROOM_LIST ?= $(LAB32_FXCUT_LIST)
R10B_ROPE_HALF ?= 1
FX_TRANS_SKIP31 ?= 1
FX_DORMANT31 ?= 1
ESP_NUMLIST31 ?= 1
GANADO_LOD_BUF31 ?= 1
PS31_SKIN_MEMO ?= 1
PS31_GATE_MAT ?= 1
CHAR_VIS31 ?= 2
SKEL_IK_PASS ?= 1
CASTLE_ACTOR_PREGATE ?= 1
PEN_CLOTH_LOD_SUB ?= 1
WORLD_STILL ?= 1
$(LAB32_OBJS_GAME): GAME_CPPFLAGS += -DRE4DC_LAB32=1
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/qa_menu.o: PLATFORM_CPPFLAGS += -DRE4DC_LAB32=1 -I$(CURDIR)/platform/include
ifneq ($(LAB32_BOOT),0)
$(OBJDIR)/qa_menu.o: PLATFORM_CPPFLAGS += -DRE4DC_LAB32_BOOT=$(LAB32_BOOT)
endif
endif
