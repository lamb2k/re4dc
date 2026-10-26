# D367 ps2leon (2026-10-10; tools/d367/ps2leon/README.md): better Leon render meshes on the owner path, test arms.
# PS2_LEON defaults to 0 and then contributes nothing (identical image).
#   PS2_LEON=1  arm A: the full PS2 Leon (pl00 / wep02 from the PS2 disc at the GC roles' arcs): 5,155 triangles (the
#               5,167 stored minus 12 zero-area strip joints), 3,115 positions, 8 owner draw runs (one hair run: the
#               PS2 draws all hair with one colour image, so the plans declare two materials, not three: the header's
#               material_mask), 298 palette matrices.
#   PS2_LEON=2  arm B: the PS2 Leon's budget redistributed (legs 924 -> 299; head/hair +420, back/shoulders +140,
#               arms +60), every part reduced from the GameCube sections with the cl lane's Blender pipeline: 5,162
#               triangles, 3,368 positions, 9 owner draw runs, 615 palette matrices.
#   Today's Leon (leon4k): 3,989 triangles, 2,785 positions, 21 owner draw runs (9 with CHARBAKE_HAIR=1), 665 palettes.
#   Both arms keep the skeleton (119 bones), the bind table and source signatures (the game's GC infos), the eight
#   roles and their immutable asset IDs, today's atlas ec255e66-76812316 and the hair colour / mask images (UVs mapped
#   into the same tiles), so every charbake texture variant applies as it is. Render only: collision, animation,
#   game state and AI read nothing here. Plan bytes: A 14,336 palette / 11,424 workspace, B 29,568 / 24,640 (today
#   32,000 / 26,112). Character data (play knobs, 6f9e0122): coarse_actor.o A -3,924 bytes, B +11,976 bytes; the
#   CHAR_DATA_BLOCK pads in 16 KiB steps: A keeps 442,368 bytes, B takes one more step (458,752: heap 4 -16 KiB).
#   PS2_LEON_DIR: the private directory holding the arm's ps2leon_runtime.h and ps2leon_hair_runs.h
#   (re4-assets-private/ps2leon-20261010/arm-a or arm-b; tools/d367/ps2leon/pack_arm.py writes them).
PS2_LEON ?= 0
PS2_LEON_DIR ?=
ifeq ($(filter $(PS2_LEON),0 1 2),)
$(error PS2_LEON must be 0, 1 or 2)
endif
ifneq ($(PS2_LEON),0)
ifneq ($(COARSE_LEON)$(ACTOR_TRANSACTION),11)
$(error PS2_LEON needs COARSE_LEON=1 ACTOR_TRANSACTION=1 (the owner path draws the arm's chunks and hair runs))
endif
ifneq ($(LEON_NATIVE_PIPE),0)
$(error PS2_LEON is not proved with LEON_NATIVE_PIPE=1)
endif
ifneq ($(CHARBAKE_HAIR),0)
$(error PS2_LEON brings its own hair runs (ps2leon_hair_runs.h): CHARBAKE_HAIR must be 0)
endif
ifeq ($(strip $(PS2_LEON_DIR)),)
$(error PS2_LEON=$(PS2_LEON) needs PS2_LEON_DIR (the private dir with ps2leon_runtime.h and ps2leon_hair_runs.h))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_PS2_LEON=$(PS2_LEON) -I$(PS2_LEON_DIR)
# PS2_LEON=1 also covers the no-jacket costume (pl08 rooms, ACTOR_PL08=1 ACTOR_PL08_PACK=1; 2026-10-11): pl08's own
# roles 0, 1, 8 are the PS2 pl08 sections (BIN4 body 2,890 triangles, BIN10 47, BIN16 82; tools/d367/ps2leon/
# build_arm_a_pl08.py + pack_pl08.py) instead of the GameCube-derived 1,138 / 27 / 94. They load from the package
# dc/native/pl08/leon_pl08_ps2.re4cp (61,184 B, validated against PS2_LEON_DIR/ps2leon_pl08_pack_identity.inc); the
# arm's ps2leon_runtime.h carries the matching pl08 plan constants (pack_arm.py --pl08). A disc without that package
# leaves pl08 on the source path. PS2_LEON=2 keeps today's pl08 body.
ifeq ($(PS2_LEON)$(ACTOR_PL08),11)
ifneq ($(ACTOR_PL08_PACK),1)
$(error PS2_LEON=1 with ACTOR_PL08=1 needs ACTOR_PL08_PACK=1 (the PS2 pl08 body is the package leon_pl08_ps2.re4cp))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_PS2_LEON_PL08=1
$(OBJDIR)/coarse_actor.o: $(PS2_LEON_DIR)/ps2leon_pl08_pack_identity.inc
endif
$(OBJDIR)/coarse_actor.o: $(PS2_LEON_DIR)/ps2leon_runtime.h $(PS2_LEON_DIR)/ps2leon_hair_runs.h
endif
# LEON_PS2_RIG=1 (lane cast-ps2-25, 2026-10-26; default 0: no effect; render only; needs PS2_LEON=1 and a rig arm in
#              PS2_LEON_DIR: build_arm_a.py --rig + pack_arm.py, whose header carries leon4k::rig_ps2): Leon on the PS2
#              pl00 rig. Body, head, face and hands bind with the PS2 skeleton rests (the arm bind table); every PS2
#              section keeps its own weights (no GameCube re-weighting of the jacket / hair); the PS2 jacket (69-75)
#              and hair (64-68) bones are driven by the game's GameCube cloth / hair simulation (code): their weights
#              sit on the simulated bones (build_arm_a.py RIG_MAP), which bind with the game's own matrices.
#              Animation and game state are untouched.
LEON_PS2_RIG ?= 0
ifeq ($(filter $(LEON_PS2_RIG),0 1),)
$(error LEON_PS2_RIG must be 0 or 1)
endif
ifeq ($(LEON_PS2_RIG),1)
ifneq ($(PS2_LEON),1)
$(error LEON_PS2_RIG needs PS2_LEON=1 (a rig arm in PS2_LEON_DIR))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_PS2_RIG=1
endif
# LEON_LOD=1 (lane leonlod, 2026-10-15; default 0: no effect; render only; needs PS2_LEON=1 LEON_HAND_PACK=1): Leon's
#              render mesh rungs from one disc package, dc/native/pl00/leon_lod.re4lp (tools/d367/leonlod/lod_pack.py
#              pack; LEON_LOD_PACK names the host copy the image header is derived from). Roles 0-4 / 7 and the hair run
#              leave the image (lod_pack.py derive) and one buffer the size of the largest rung (arm A, today's Leon)
#              holds the rung drawn now: memory neutral. The level is a run-time variable: re4dc_leon_lod_set(n)
#              (warp `leonlod <n>`, poc101 rows) applies at the next room enter; LEON_LOD_LEVEL is the boot level
#              (default 0 = arm A, today's mesh). Package level order (lod_pack.py show): 0 A, 1 sel, 2 sel30, 3 u85,
#              4 u70, 5 u55, 6 u40. Skeleton, animation, hands and game state are untouched.
LEON_LOD ?= 0
LEON_LOD_LEVEL ?= 0
LEON_LOD_PACK ?=
ifeq ($(filter $(LEON_LOD),0 1),)
$(error LEON_LOD must be 0 or 1)
endif
ifeq ($(LEON_LOD),1)
ifneq ($(PS2_LEON)$(LEON_HAND_PACK),11)
$(error LEON_LOD needs PS2_LEON=1 LEON_HAND_PACK=1)
endif
ifeq ($(strip $(LEON_LOD_PACK)),)
$(error LEON_LOD=1 needs LEON_LOD_PACK (the leon_lod.re4lp staged at dc/native/pl00))
endif
LEON_LOD_HDR := $(OBJDIR)/leon_lod/ps2leon_runtime_lod.h
$(LEON_LOD_HDR): $(LEON_HAND_PACK_HDR) $(PS2_LEON_DIR)/ps2leon_hair_runs.h $(LEON_LOD_PACK) ../tools/d367/leonlod/lod_pack.py
	@mkdir -p $(dir $@)
	python3 ../tools/d367/leonlod/lod_pack.py derive $(LEON_HAND_PACK_HDR) $(PS2_LEON_DIR)/ps2leon_hair_runs.h $(LEON_LOD_PACK) $(dir $@)
$(OBJDIR)/coarse_actor.o: $(LEON_LOD_HDR)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_LOD=1 -DRE4DC_LEON_LOD_LEVEL=$(LEON_LOD_LEVEL) -I$(OBJDIR)/leon_lod
$(OBJDIR)/ui_bridge.o $(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_LEON_LOD=1
endif
# GANADO_LOD=1 (lane leonlod, 2026-10-15; default 0: no effect; render only; needs PS2_GANADO=1 ACTOR_TRANSACTION=1
#              COARSE_SKIN_FTRV=1, no CROWD_FAR tier): the PS2 cast Ganados' body / head meshes from one disc package,
#              dc/native/ganado/ganado_lod.re4gl (tools/d367/leonlod/glod_rung.py + glod_native.sh + glod_pack.py pack;
#              GANADO_LOD_PACK names the host copy the image header is derived from). Roles 0 / 1 of every appearance
#              leave the image (glod_pack.py derive) and one buffer the size of the largest level (level 0, today's
#              meshes) holds the level drawn now: memory neutral. Every cast Ganado draws the loaded level. Run-time:
#              re4dc_ganado_lod_set(n) (warp `glod <n>`, `lodat <frame> <leon> <ganado>`, poc101 GANADOLOD row) loads at
#              the next actor retirement; GANADO_LOD_LEVEL is the boot level (default 0 = today). Package level order
#              (glod_pack.py show): 0 today, 1 g85, 2 g70, 3 g55. Skeleton, motions, hands, gore and game state are
#              untouched; each level's palettes and triangles per chunk are at most today's.
GANADO_LOD ?= 0
GANADO_LOD_LEVEL ?= 0
GANADO_LOD_PACK ?=
ifeq ($(filter $(GANADO_LOD),0 1),)
$(error GANADO_LOD must be 0 or 1)
endif
ifeq ($(GANADO_LOD),1)
ifneq ($(PS2_GANADO),1)
$(error GANADO_LOD needs PS2_GANADO=1)
endif
ifeq ($(strip $(GANADO_LOD_PACK)),)
$(error GANADO_LOD=1 needs GANADO_LOD_PACK (the ganado_lod.re4gl staged at dc/native/ganado))
endif
GANADO_LOD_HDR := $(OBJDIR)/ganado_lod/ganado_cast_runtime_lod.h
$(GANADO_LOD_HDR): $(PS2_GANADO_DIR)/ganado_cast_runtime.h $(GANADO_LOD_PACK) ../tools/d367/leonlod/glod_pack.py
	@mkdir -p $(dir $@)
	python3 ../tools/d367/leonlod/glod_pack.py derive $(PS2_GANADO_DIR)/ganado_cast_runtime.h $(GANADO_LOD_PACK) $(dir $@)
$(OBJDIR)/coarse_ganado.o: $(GANADO_LOD_HDR)
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_GANADO_LOD=1 -DRE4DC_GANADO_LOD_LEVEL=$(GANADO_LOD_LEVEL) -I$(OBJDIR)/ganado_lod
$(OBJDIR)/coarse_actor.o $(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_GANADO_LOD=1
endif

# Ganados keep the gameplay LOD level through in-engine events (no package reload at event start/end).
# Render-only approximation, default off (user 2026-10-22 option 1).
GANADO_EVENT_KEEP_LOD ?= 0
ifneq ($(filter 0 1,$(GANADO_EVENT_KEEP_LOD)),$(GANADO_EVENT_KEEP_LOD))
$(error GANADO_EVENT_KEEP_LOD must be 0 or 1)
endif
ifeq ($(GANADO_EVENT_KEEP_LOD),1)
ifneq ($(GANADO_LOD),1)
$(error GANADO_EVENT_KEEP_LOD needs GANADO_LOD=1)
endif
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_GANADO_EVENT_KEEP_LOD=1
endif

# Selected square128 Leon body tile isolation. Experimental, render only.
# No production recipe enables this. Data is emitted by texture_atlas21/runtime_header.py.
LEON_ATLAS_SPLIT ?= 0
LEON_ATLAS_SPLIT_DIR ?=
ifneq ($(words $(LEON_ATLAS_SPLIT)),1)
$(error LEON_ATLAS_SPLIT must be 0 or 1)
endif
ifneq ($(filter 0 1,$(LEON_ATLAS_SPLIT)),$(LEON_ATLAS_SPLIT))
$(error LEON_ATLAS_SPLIT must be 0 or 1)
endif
ifeq ($(LEON_ATLAS_SPLIT),1)
ifneq ($(PS2_LEON),1)
$(error LEON_ATLAS_SPLIT needs PS2_LEON=1)
endif
ifneq ($(ACTOR_PL08),1)
$(error LEON_ATLAS_SPLIT needs ACTOR_PL08=1)
endif
ifneq ($(ACTOR_PL08_PACK),1)
$(error LEON_ATLAS_SPLIT needs ACTOR_PL08_PACK=1)
endif
ifneq ($(LEON_LOD),0)
$(error LEON_ATLAS_SPLIT has no alternate LEON_LOD package qualification)
endif
ifeq ($(strip $(LEON_ATLAS_SPLIT_DIR)),)
$(error LEON_ATLAS_SPLIT needs LEON_ATLAS_SPLIT_DIR)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_ATLAS_SPLIT=1 -I$(LEON_ATLAS_SPLIT_DIR)
$(OBJDIR)/coarse_actor.o: $(LEON_ATLAS_SPLIT_DIR)/leon_atlas_split_data.h ../tools/d367/texture_atlas21/atlas_bind.h coarse_actor_atlas_split.inc
endif
