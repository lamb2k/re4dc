# D367 W11: the sub screen (inventory, map, examine, files) and its memory backing, plus
# the W11 test instrumentation. Included at the end of the Makefile. Every knob defaults to
# 0 and then contributes nothing: the default image is byte-identical.
#   SUBSCREEN=1    link the Sscrn REL into the image (static module id 71; its constructors
#                  run per link from its own _prolog, tools/gen_modules.py PER_LINK_CTORS) and
#                  replace the GameCube ARAM swap of the sub screen area (SubScreenExec /
#                  SubScreenExitCore: 3 MiB at pG->pStFnt <-> ARAM 0xD00000) with a Dreamcast
#                  backing (sscrn_bridge.cpp, platform/subscreen_backing.cpp): while the screen
#                  is open the live game bytes of that area (heaps 2/3/4, free cells skipped)
#                  are held in VRAM - the second TA vertex bank, idle with TA_DOUBLEBUF=0, then
#                  a texture-pool block - and checked on the way back; the screen's own files
#                  (ss_cmmn, ss_pzzl) are read from disc at open instead of being kept in ARAM.
#                  The ARAM preload at game start (1.75 MB of reads with nowhere to go) is
#                  skipped. Needs the sub screen data converted (le_mirror ss/ handlers) and
#                  its texture packages on the disc.
#                  The card screen's cDataSwap (a typewriter save swaps ~250 KB of the room heap
#                  out) uses the same backing when its heap copy does not fit (VMU design S0).
#   W11_FIXTURE=1  test instrumentation, never in a product image: /cd/dc/w11.txt (death /
#                  life fixture through the source damage entry), heap/VRAM/KOS census around
#                  every sub screen open and close and every death, frame-time windows per
#                  phase, and "w11 shot:" markers for framebuffer captures.
#   SUBSCREEN_OVL=1 (needs SUBSCREEN=1) takes the Sscrn module (~122 KB) out of the resident
#                  image: it is linked as one section outside RAM (gen_modules.py <mod>:ovl),
#                  tools/link.sh links the image twice at two overlay addresses, proves that only
#                  the overlay's own absolute words differ (the image holds no pointer into it),
#                  writes sscrn.ovl (bytes + relocation list) next to the ELF and strips the
#                  section. Each open reads it into offset 0 of the sub screen area, where the
#                  GameCube's Sscrn.rel sat, and relocates it (sscrn_bridge.cpp). Heap 4 gains the
#                  module's size; stage.sh puts sscrn.ovl on the disc as /cd/dc/sscrn.ovl.
#   SS_POOL_HIGH=1 (needs SUBSCREEN=1) allocates the room's effect pools (cEspSystem, the esp pool,
#                  the Espgen controller pool) above the 3 MiB sub screen window at pG->pStFnt.
#                  On the GameCube the stage font and the room archive fill that window, so those
#                  pools always sit above it; the port's arena fit frees the archive's unused tail
#                  and they could land inside, where the sub screen's own files overwrite them
#                  while its main loop keeps running EspgenMove / EspMove (the r101 first-visit
#                  call reset). The room's light works (LightMgr, moved by the sub screen loop too)
#                  are moved above it right after their allocation. Same pools, same sizes, only
#                  the address differs.
#   SS_PACK=1      (needs SUBSCREEN=1, TEX_RESIDENT=1) the sub screen stores the area LZ4-packed: about
#                  1.6:1 on r100 play, so the 3 MiB fit the 2 MiB bank and pool blocks are taken only for
#                  the rest (free pool memory first). Without it each call or inventory open carved a
#                  contiguous 1 MiB out of the room's textures (r21n r100 call: 159 uploads / 2.3 MB
#                  released, 207 reloaded in 5.8 s after the close). Same bytes back, checked by the hash.
#   SS_BG_BLACK=1  (needs SUBSCREEN=1) black PVR background while the sub screen hides the room
#                  (Status_flg[1] bit 1, SubScreenExec step 2 .. SubScreenExit step 4). FOG_BACKGROUND
#                  makes the background the fog colour; on the GameCube the copy clear is black and the
#                  fog colour only tints geometry, so with every Disp_flg hide bit set the GC shows black
#                  and the port showed a full tan (r100 fog) frame before each call / inventory, held on
#                  screen through the backing save. Render only. =2: no change, logs what =1 would do.
SUBSCREEN ?= 0
# Typed original slot-1 completion and answer fields for the port ABI.
SS_MSG_FIELDS ?= $(if $(filter 1,$(SUBSCREEN)),1,0)
ifeq ($(filter $(SS_MSG_FIELDS),0 1),)
$(error SS_MSG_FIELDS must be 0 or 1)
endif
ifeq ($(SS_MSG_FIELDS),1)
ifneq ($(SUBSCREEN),1)
$(error SS_MSG_FIELDS=1 requires SUBSCREEN=1)
endif
$(OBJDIR)/mod/Sscrn/src/Sscrn/ss_pzzl.o: GAME_CPPFLAGS += -DRE4DC_SS_MSG_FIELDS=1
endif
# Preserve original actor inputs while the inventory backing owns their memory.
# Original successful-Use motion resets run only after the checked restore.
SS_ACTOR_LIFETIME ?= $(if $(filter 1,$(SUBSCREEN)),1,0)
ifeq ($(filter $(SS_ACTOR_LIFETIME),0 1),)
$(error SS_ACTOR_LIFETIME must be 0 or 1)
endif
ifeq ($(SS_ACTOR_LIFETIME),1)
ifneq ($(SUBSCREEN),1)
$(error SS_ACTOR_LIFETIME=1 requires SUBSCREEN=1)
endif
$(OBJDIR)/sscrn_bridge.o $(OBJDIR)/src/game/cockpit.o $(OBJDIR)/src/game/pl_npc.o $(OBJDIR)/mod/Sscrn/src/Sscrn/ss_pzzl.o: GAME_CPPFLAGS += -DRE4DC_SS_ACTOR_LIFETIME=1
endif
SS_PACK ?= 0
# SS_DATA_LZ=1 (lane inv23 2026-10-22, user-approved option A; default 0 = image unchanged; needs SUBSCREEN=1): each
# sub screen open reads SS/<lang>/ss_cmmn.lz and ss_pzzl.lz (data set sslz23, tools/d367/inv23/ss_lz.py: one LZ4 block
# each) into the area's free tail and decodes them, instead of the 1,443,744 B of ss_cmmn.dat + ss_pzzl.dat
# (822,053 B packed, -43% disc bytes per open). A disc without the .lz files, or a bad file, reads the .dat files.
SS_DATA_LZ ?= 0
ifeq ($(filter $(SS_DATA_LZ),0 1),)
$(error SS_DATA_LZ must be 0 or 1)
endif
ifeq ($(SS_DATA_LZ),1)
ifneq ($(SUBSCREEN),1)
$(error SS_DATA_LZ=1 requires SUBSCREEN=1)
endif
$(OBJDIR)/sscrn_bridge.o: GAME_CPPFLAGS += -DRE4DC_SS_DATA_LZ=1
$(OBJDIR)/platform/subscreen_backing.o: PLATFORM_CPPFLAGS += -DRE4DC_SS_DATA_LZ=1
endif
# SS_HOLD_RESTORE=1 (test 14 #1, needs SS_PACK=1; render only, default 0 = image unchanged): VRAM graphics memory rule.
# The packed backing holds the room preload while the sub screen is open (re4dc_ui_vram_hold), and the preload runs
# again after the close only when the hold released uploads (claim_released). The sub screen's own pictures (r101
# post-bell call: 430 KB, loaded while paused) evict room uploads through load() without counting there, so the
# room's resident-list keys they evicted (4 HUD pictures) reloaded on first sight in play after the call. With it the
# uploads load() evicts during the hold that the room drew in the 60 frames before it are remembered (up to 64), and
# after the close a preload pass restricted to them brings them back before play resumes (a load point, as at room
# entry). A full room pass instead reloaded 95 r101 keys at the close (1.6 s in Flycast), most of them not in view.
SS_HOLD_RESTORE ?= 0
# CORE_PIN=1 (test 14 #1, needs ROOM_RESIDENT=1; render only, default 0 = image unchanged): dc/resident.bin's room 0
# records (vram/resident/r000.tsv; room 0 with width 0 pads the file) are the core set: the HUD pictures every room
# draws (r101 post-bell call: 4 of them, ~7 KB, evicted by the call's pictures and reloaded on first sight after it).
# They join every room's resident list, and load() never picks them as an eviction victim.
# CORE_PIN=2 (t15/int, test 14 open item): as =1, but the core keys yield to the fragmented-upload retry of a picture of
# 128 KiB or more (the r105 chapter 1-2 results screen, which =1 left without a contiguous 512 KiB block).
CORE_PIN ?= 0
ifeq ($(filter $(CORE_PIN),0 1 2),)
$(error CORE_PIN must be 0, 1 or 2)
endif
ifneq ($(CORE_PIN),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CORE_PIN=$(CORE_PIN)
endif
ifneq ($(SS_HOLD_RESTORE),0)
ifneq ($(SS_PACK),1)
$(error SS_HOLD_RESTORE needs SS_PACK=1)
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_SS_HOLD_RESTORE=1
endif
# SS11_PRELOAD=1 (lane resident16 10-16; render only, default 0 = image unchanged; in T15REC): VRAM graphics memory rule.
# The chapter title card and the chapter-end results / save screens live in SS heap 11; their pictures evict the room's
# set, which then came back from disc one first sight at a time in play (r105 after the chapter 1-2 save screen: 81
# uploads). With it MemDestroyHeap(11) asks native_ui for a room preload pass, so the set comes back in one pass before
# play resumes, as at room entry.
SS11_PRELOAD ?= 0
ifneq ($(SS11_PRELOAD),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_SS11_PRELOAD=1
$(OBJDIR)/src/game/main_mem.o: GAME_CPPFLAGS += -DRE4DC_SS11_PRELOAD=1
endif
SS_BG_BLACK ?= 0
ifneq ($(SS_BG_BLACK),0)
ifneq ($(SUBSCREEN),1)
$(error SS_BG_BLACK needs SUBSCREEN=1)
endif
endif
# Trans() skips the room's obj / em list walks while the sub screen window is swapped (src/game/trans.cpp,
# r21v console fault 0xE0). With the sub screen built the hook is a strong reference and tools/link.sh fails
# the link if re4dc_ss_ui_order would become a generated stub.
ifeq ($(SUBSCREEN),1)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_TRANS_SS_GUARD=1
endif
W11_FIXTURE ?= 0
# SS_MENU_ANIM_RT=1 (test 9, user: play the inventory command menu's opening flash at GameCube speed): the
# command menu's ID class (PieceCommand, Equip / Examine / Combine / Discard; ss_pzzl.cpp) steps its curves
# once per elapsed game tick (60 Hz vblanks / GetSystemVcnt(), 2 = the GameCube's 30 Hz sub screen) instead
# of once per drawn frame, so the white panel flash ends in GameCube wall time at any frame rate. UI only:
# the game is stopped while the sub screen runs and no logic reads those units' curves. Default 0.
SS_MENU_ANIM_RT ?= 0
ifneq ($(filter-out 0 1,$(SS_MENU_ANIM_RT)),)
$(error SS_MENU_ANIM_RT must be 0 or 1)
endif
ifeq ($(SS_MENU_ANIM_RT),1)
ifneq ($(SUBSCREEN),1)
$(error SS_MENU_ANIM_RT=1 requires SUBSCREEN=1)
endif
$(OBJDIR)/mod/Sscrn/src/Sscrn/ss_pzzl.o: GAME_CPPFLAGS += -DRE4DC_SS_MENU_ANIM_RT=1
endif
# RADIO_SUB_RT=1 (test 15, console report "the radio call subtitles are very slow", lane radiosub16): the codec call's
# subtitle sequence (ss_term.cpp OpeMesMove: TermSeq page times and clear countdowns, GameCube 30 Hz sub screen ticks)
# follows the voice's clock (KOS timer since the AICA stream began to sound, audio_aica.cpp re4dc_aica_stream_started)
# instead of the call's drawn frames, so the pages stay with the real-time voice when a call frame takes longer than 2
# vblanks. At 30 Hz it runs one tick per frame as before. UI only: the game is stopped under the sub screen and nothing
# else reads these counters. Needs AICA_AUDIO=1 AICA_STREAMS=1 (the voice clock). Default 0.
# RADIO_SUB_LOG=1 (test only): "radiosub: play / seq" lines (vblanks and KOS timer ms) for the drift measurement.
RADIO_SUB_RT ?= 0
RADIO_SUB_LOG ?= 0
ifneq ($(filter-out 0 1,$(RADIO_SUB_RT) $(RADIO_SUB_LOG)),)
$(error RADIO_SUB_RT and RADIO_SUB_LOG must be 0 or 1)
endif
ifneq ($(RADIO_SUB_RT)$(RADIO_SUB_LOG),00)
ifneq ($(SUBSCREEN),1)
$(error RADIO_SUB_RT / RADIO_SUB_LOG require SUBSCREEN=1)
endif
$(OBJDIR)/mod/Sscrn/src/Sscrn/ss_term.o: GAME_CPPFLAGS += -DRE4DC_RADIO_SUB_RT=$(RADIO_SUB_RT) -DRE4DC_RADIO_SUB_LOG=$(RADIO_SUB_LOG)
endif
ifeq ($(RADIO_SUB_RT),1)
ifneq ($(AICA_AUDIO)$(AICA_STREAMS),11)
$(error RADIO_SUB_RT=1 requires AICA_AUDIO=1 AICA_STREAMS=1 (the voice clock))
endif
$(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_RADIO_SUB_RT=1
endif
SUBSCREEN_OVL ?= 0
SS_POOL_HIGH ?= 0
# SS_POOL_TOP=1 (needs SS_POOL_HIGH=1; lane ch3found16 2026-10-16, default 0): the SS_POOL_HIGH pools (cEspSystem, esp,
#   Espgen, light works, primitive buffer) take the top end of heap 4's highest free cell instead of the first cell
#   above the window, so the window's free tail joins the free space above it (r221: em2c's 2.89 MB found 2.49 MB
#   largest of 3.64 MB free). Same pools and sizes; addresses only.
SS_POOL_TOP ?= 0
ifeq ($(SS_POOL_TOP),1)
ifneq ($(SS_POOL_HIGH),1)
$(error SS_POOL_TOP=1 needs SS_POOL_HIGH=1)
endif
$(OBJDIR)/sscrn_bridge.o $(OBJDIR)/src/game/main_mem.o: GAME_CPPFLAGS += -DRE4DC_SS_POOL_TOP=1
endif
# Source-ordered UI/model compositing only while the subscreen area is swapped.
SS_UI_ORDER ?= 0
ifeq ($(SS_UI_ORDER),1)
ifneq ($(SUBSCREEN),1)
$(error SS_UI_ORDER=1 requires SUBSCREEN=1)
endif
endif
ifeq ($(SUBSCREEN),1)
ifneq ($(TA_DOUBLEBUF),0)
# The backing borrows bank 1 while a sub screen is open: TA_DOUBLEBUF=1 switches the TA to one bank
# for that time (design-doublebuf), through the KOS vbuf-switch patch (patches/README.md).
SUBSCREEN_TA_SWITCH = 1
endif
ifeq ($(SUBSCREEN_OVL),1)
MODULES += Sscrn:ovl
export RE4DC_LINK_OVERLAY += .ovl_Sscrn
else
MODULES += Sscrn
endif
else ifeq ($(SUBSCREEN_OVL),1)
$(error SUBSCREEN_OVL=1 needs SUBSCREEN=1)
else ifeq ($(SS_POOL_HIGH),1)
$(error SS_POOL_HIGH=1 needs SUBSCREEN=1)
endif
ifeq ($(SS_PACK),1)
ifneq ($(SUBSCREEN)$(TEX_RESIDENT),11)
$(error SS_PACK=1 needs SUBSCREEN=1 TEX_RESIDENT=1)
endif
endif
.PHONY: subscreen-force
$(OBJDIR)/subscreen.h: subscreen-force
	@mkdir -p $(dir $@)
	@if [ "$(SUBSCREEN_TA_SWITCH)" = 1 ]; then test "$$($(KOS_CC_BASE)/bin/$(KOS_CC_PREFIX)-nm -g --defined-only $(KOS_BASE)/lib/$(KOS_ARCH)/libkallisti.a | grep -c ' T _pvr_set_vbuf_doublebuf$$')" -eq 1 || { echo 'SUBSCREEN=1 with TA_DOUBLEBUF=1 requires the KOS vbuf-switch patch (patches/kos-804b319-vbuf-switch.patch)' >&2; exit 1; }; fi
	@printf '#define RE4DC_SUBSCREEN %s\n#define RE4DC_W11_FIXTURE %s\n#define RE4DC_SUBSCREEN_OVL %s\n#define RE4DC_SS_POOL_HIGH %s\n#define RE4DC_SS_UI_ORDER %s\n' '$(SUBSCREEN)' '$(W11_FIXTURE)' '$(SUBSCREEN_OVL)' '$(SS_POOL_HIGH)' '$(SS_UI_ORDER)' > $@.tmp
	@printf '#define RE4DC_SS_PACK %s\n' '$(SS_PACK)' >> $@.tmp
	@printf '#define RE4DC_SS_BG_BLACK %s\n' '$(SS_BG_BLACK)' >> $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
# A knob change regenerates the module list.
$(MODULES_MK): $(OBJDIR)/subscreen.h
SUBSCREEN_GAME = $(OBJDIR)/src/game/sscrn.o $(OBJDIR)/ui_bridge.o $(OBJDIR)/src/game/cDataSwap.o \
                 $(OBJDIR)/src/game/espgen.o $(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/eff_sys.o \
                 $(OBJDIR)/src/game/game.o
$(SUBSCREEN_GAME) $(OBJDIR)/platform/modules.o: $(OBJDIR)/subscreen.h
$(SUBSCREEN_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/subscreen.h
$(OBJDIR)/platform/modules.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/subscreen.h
# native_ui: backing reclaim; native_motion: residency; native_static: exclude subscreen models from room replacement.
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_motion.o $(OBJDIR)/platform/native_static.o: $(OBJDIR)/subscreen.h
$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_motion.o $(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/subscreen.h
# motion_bridge.cpp / native_motion.cpp: residency held while open, heap-12 clips dropped at close.
$(OBJDIR)/motion_bridge.o $(OBJDIR)/parts_bridge.o: $(OBJDIR)/subscreen.h
$(OBJDIR)/motion_bridge.o $(OBJDIR)/parts_bridge.o: GAME_CPPFLAGS += -include $(OBJDIR)/subscreen.h
# platform/subscreen_backing.cpp is in the platform wildcard: with both knobs 0 it compiles empty.
$(OBJDIR)/platform/subscreen_backing.o: $(OBJDIR)/subscreen.h $(OBJDIR)/pipeline30.h
$(OBJDIR)/platform/subscreen_backing.o: PLATFORM_CPPFLAGS += -include $(OBJDIR)/subscreen.h -include $(OBJDIR)/pipeline30.h
ifneq ($(SUBSCREEN)$(W11_FIXTURE),00)
PLATFORM_OBJS += $(OBJDIR)/sscrn_bridge.o
# Included after the link rule: name the object as its prerequisite here.
$(TARGET): $(OBJDIR)/sscrn_bridge.o
$(OBJDIR)/sscrn_bridge.o: sscrn_bridge.cpp $(OBJDIR)/subscreen.h $(OBJDIR)/pipeline30.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -include $(OBJDIR)/subscreen.h -include $(OBJDIR)/pipeline30.h -MMD -MP -c $< -o $@
-include $(OBJDIR)/sscrn_bridge.d
endif
