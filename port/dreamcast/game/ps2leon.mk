# D367 ps2leon (2026-10-10; tools/d367/ps2leon/README.md): better Leon render meshes on the owner path, test arms.
# PS2_LEON defaults to 0 and then contributes nothing (identical image).
#   PS2_LEON=1  arm A: the full PS2 Leon (pl00 / wep02 from the PS2 disc at the GC roles' arcs): 5,155 triangles (the
#               5,167 stored minus 12 zero-area strip joints), 3,115 positions, 8 owner draw runs (one hair run: the
#               PS2 draws all hair with one colour image), 298 palette matrices.
#   PS2_LEON=2  arm B: the PS2 Leon's budget redistributed (legs 924 -> 299; head/hair +420, back/shoulders +140,
#               arms +60), every part reduced from the GameCube sections with the cl lane's Blender pipeline: 5,162
#               triangles, 3,368 positions, 9 owner draw runs, 615 palette matrices.
#   Today's Leon (leon4k): 3,989 triangles, 2,785 positions, 21 owner draw runs (9 with CHARBAKE_HAIR=1), 665 palettes.
#   Both arms keep the skeleton (119 bones), the bind table and source signatures (the game's GC infos), the eight
#   roles and their immutable asset IDs, today's atlas ec255e66-76812316 and the hair colour / mask images (UVs mapped
#   into the same tiles), so every charbake texture variant applies as it is. Render only: collision, animation,
#   game state and AI read nothing here. Plan bytes: A 14,336 palette / 11,424 workspace, B 29,568 / 24,640 (today
#   32,000 / 26,112). Character data (play knobs, 6f9e0122): coarse_actor.o A -3,752 bytes, B +11,976 bytes; the
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
$(OBJDIR)/coarse_actor.o: $(PS2_LEON_DIR)/ps2leon_runtime.h $(PS2_LEON_DIR)/ps2leon_hair_runs.h
endif
