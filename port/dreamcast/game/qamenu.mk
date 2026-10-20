# QA_MENU=1 (lane qa20, user 10-20; the tester QA disc only, never in a release image): a QA menu over the warp rig.
#   Boot: a menu screen (KOS framebuffer, before pvr_init) offers "Start the game normally" or a teleport preset
#   (chapter -> place). In game: hold L + R and press D-pad Down to open the same menu (the frame loop stops while it
#   is open; it opens only in free play: not in an event, a movie, the inventory or a door load). Entries: teleport
#   (a preset loads through a soft reset and the warp rig's fixture, with the story state the fixture sets), return to
#   the title, refill health, Leon / partner / enemies invincible (runtime, default off), speed display.
#   Presets are files on the disc: /cd/dc/qa/menu.txt (tools/d367/qa20/mkqa.py writes it and the fixtures).
#   A disc with /cd/dc/warp.txt (test harness bases) skips the boot menu and runs that fixture as before.
#   Files: qa_menu.cpp (screens, toggles), dbgwarp_bridge.cpp (#if RE4DC_QA_MENU hooks), platform/native_ui.cpp (the
#   QA name banner on the title, RE4DC_QA_BANNER).
#   Needs DBG_WARP=1 and WARP_AFTER_RESET=1; not with BENCHMARK=1 (both own the OSInit wrap and the banner).
#   QA_NAME="RE4DC QA <test> <sha8>" is shown on the boot menu, the in-game menu header and the title banner.
#   Default 0: nothing is compiled or linked; the image is byte-identical with or without this file.
QA_MENU ?= 0
# QA_TEST / QA_SRC (no spaces: build-r21.sh passes knobs unquoted) make the name, e.g. QA_TEST=21 QA_SRC=5f26453a.
QA_TEST ?= dev
QA_SRC ?= local
QA_NAME ?= RE4DC QA TEST $(QA_TEST) $(QA_SRC)
ifneq ($(filter $(QA_MENU),0 1),$(QA_MENU))
$(error QA_MENU must be 0 or 1)
endif
ifeq ($(QA_MENU),1)
ifneq ($(DBG_WARP),1)
$(error QA_MENU=1 needs DBG_WARP=1 (presets are warp rig fixtures))
endif
ifneq ($(WARP_AFTER_RESET),1)
$(error QA_MENU=1 needs WARP_AFTER_RESET=1 (a teleport arms its fixture at the soft reset))
endif
ifeq ($(BENCHMARK),1)
$(error QA_MENU=1 and BENCHMARK=1 both wrap OSInit and own the banner)
endif
PLATFORM_OBJS += $(OBJDIR)/qa_menu.o
$(TARGET): $(OBJDIR)/qa_menu.o
GAME_LDFLAGS += -Wl,--wrap=OSInit
ifeq ($(CRASH_SCREEN),1)
# the crash screen's hang watchdog reads re4dc_ui_frame: the menu moves it while it holds the frame loop
GAME_LDFLAGS += -Wl,--wrap=re4dc_ui_frame
QA_MENU_UI_WRAP := -DRE4DC_QA_UI_WRAP=1
endif
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_QA_MENU=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_QA_BANNER=1
.PHONY: qamenu-force
$(OBJDIR)/qa_menu.h: qamenu-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_QA_NAME "%s"\n' '$(QA_NAME)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
$(OBJDIR)/qa_menu.o: qa_menu.cpp $(OBJDIR)/qa_menu.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) $(QA_MENU_UI_WRAP) -include $(OBJDIR)/qa_menu.h -MMD -MP -c $< -o $@
-include $(OBJDIR)/qa_menu.d
endif
