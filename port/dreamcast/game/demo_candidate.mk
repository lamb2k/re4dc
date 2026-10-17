# Candidate-only source fragment. Not applied to any checkout or build recipe.
ACTOR_TRANSACTION ?= 0
ACTOR_LEON_NATIVE_LOOK ?= 0
ACTOR_GANADO_DEATH_FADE ?= 0
# Include after the Makefile's base GAME_CPPFLAGS / PLATFORM_CPPFLAGS assignments.
# GFLAGS is not consumed by this recipe. Both game and platform TUs need these.
GAME_CPPFLAGS += -DRE4DC_ACTOR_TRANSACTION=$(ACTOR_TRANSACTION) -DRE4DC_ACTOR_LEON_NATIVE_LOOK=$(ACTOR_LEON_NATIVE_LOOK)
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_TRANSACTION=$(ACTOR_TRANSACTION) -DRE4DC_ACTOR_LEON_NATIVE_LOOK=$(ACTOR_LEON_NATIVE_LOOK)
ifeq ($(filter $(ACTOR_TRANSACTION),0 1),)
$(error ACTOR_TRANSACTION must be 0 or 1)
endif
ifeq ($(filter $(ACTOR_LEON_NATIVE_LOOK),0 1),)
$(error ACTOR_LEON_NATIVE_LOOK must be 0 or 1)
endif
ifeq ($(ACTOR_TRANSACTION),1)
# The Leon owner guard needs the real generated native/frontend configuration.
# These target-local imports and source-ledger values are absent from the
# historical coarse_actor recipe; never replace the guard with assumed ones.
$(OBJDIR)/coarse_actor.o: $(OBJDIR)/native-actor.h $(OBJDIR)/frontend30.h
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -include $(OBJDIR)/native-actor.h -include $(OBJDIR)/frontend30.h -DRE4DC_COARSE_SOURCE_ACTORS=$(COARSE_SOURCE_ACTORS) -DRE4DC_ACTOR_SWAP=$(ACTOR_SWAP)
ifneq ($(COARSE_SOURCE_ACTORS) $(COARSE_LEON) $(COARSE_GANADO) $(COARSE_GANADO_CAST) $(COARSE_ONE_SUBMIT) $(COARSE_SKIN_FTRV) $(NATIVE_ACTOR_FAST),1 1 1 1 1 1 1)
$(error ACTOR_TRANSACTION requires source actors, Leon, Ganado cast, one submit, skin FTRV=1 and native actor fast)
endif
ifneq ($(ACTOR_SWAP),0)
$(error ACTOR_TRANSACTION requires ACTOR_SWAP=0)
endif
ifeq ($(filter $(FRONT_NATIVE),0 1),)
$(error ACTOR_TRANSACTION is incompatible with FRONT_NATIVE replay/check modes)
endif
endif
ifeq ($(ACTOR_LEON_NATIVE_LOOK),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_LEON_NATIVE_LOOK requires ACTOR_TRANSACTION=1)
endif
endif

# ROOT-OWNED proposal. Insert after Makefile assigns GAME_CPPFLAGS and
# PLATFORM_CPPFLAGS (Makefile includes game30.mk after those assignments).
VMU_DIALOG ?= 0
ifneq ($(VMU_DIALOG),0)
ifneq ($(VMU_DIALOG),1)
$(error VMU_DIALOG must be 0 or 1)
endif
endif
ifeq ($(VMU_DIALOG),1)
ifneq ($(VMU_SAVE),1)
$(error VMU_DIALOG=1 requires VMU_SAVE=1)
endif
endif
GAME_CPPFLAGS += -DRE4DC_VMU_DIALOG=$(VMU_DIALOG)
PLATFORM_CPPFLAGS += -DRE4DC_VMU_DIALOG=$(VMU_DIALOG)
# The exact English memcard.das words (vmu_dialog_english.inc) are private source text, kept
# outside the repository with the other private assets.
VMU_DIALOG_TEXT_DIR ?= $(COARSE_ACTOR_ASSET_DIR)
ifeq ($(VMU_DIALOG),1)
ifeq ($(wildcard $(VMU_DIALOG_TEXT_DIR)/vmu_dialog_english.inc),)
$(error VMU_DIALOG=1 needs VMU_DIALOG_TEXT_DIR with the private vmu_dialog_english.inc)
endif
GAME_CPPFLAGS += -I$(VMU_DIALOG_TEXT_DIR)
endif

ifeq ($(PAD_PROMPT_MANUAL_ART),1)
ifneq ($(PAD_PROMPTS),1)
$(error PAD_PROMPT_MANUAL_ART=1 requires PAD_PROMPTS=1)
endif
endif
# Every evidence build must use a fresh, unique object directory.
# The shared stamp below also invalidates these knobs on an ordinary rebuild.
# Source proposal only. Include at END of game/demo_candidate.mk, whose parent
# Makefile include is immediately AFTER `include pace.mk` (frozen v7 line 830).
# Defaults/CPPFLAGS/guards for all five knobs must precede this fragment.
# Reading this file performs no shell/file operation. Recipes run only when a
# dependent object is requested by a separately authorized make invocation.

DEMO_PRESENTATION_KNOBS := ACTOR_TRANSACTION ACTOR_LEON_NATIVE_LOOK ACTOR_GANADO_DEATH_FADE PAD_PROMPTS PAD_PROMPT_MANUAL_ART VMU_DIALOG
# Keep stamp values single, literal booleans; no shell quoting of arbitrary text.
$(foreach k,$(DEMO_PRESENTATION_KNOBS),$(if $(filter 1,$(words $($(k)))),$(if $(filter 0 1,$($(k))),,$(error $(k) must be 0 or 1)),$(error $(k) must be one value: 0 or 1)))

DEMO_PRESENTATION_STAMP := $(OBJDIR)/demo-presentation-knobs.txt
.PHONY: demo-presentation-knobs-force
$(DEMO_PRESENTATION_STAMP): demo-presentation-knobs-force
	@mkdir -p $(dir $@)
	@printf '%s\n' \
	  'ACTOR_TRANSACTION=$(strip $(ACTOR_TRANSACTION))' \
	  'ACTOR_LEON_NATIVE_LOOK=$(strip $(ACTOR_LEON_NATIVE_LOOK))' \
	  'ACTOR_GANADO_DEATH_FADE=$(strip $(ACTOR_GANADO_DEATH_FADE))' \
	  'PAD_PROMPTS=$(strip $(PAD_PROMPTS))' \
	  'PAD_PROMPT_MANUAL_ART=$(strip $(PAD_PROMPT_MANUAL_ART))' \
	  'VMU_DIALOG=$(strip $(VMU_DIALOG))' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp

# OBJS includes game/native-reuse/platform objects, direct additions such as
# quality_picker and aggregate REL objects. CENSUS_OBJS covers source census
# targets. Aggregate REL dependencies ALONE are insufficient: their C++ leaf
# objects include model.h and may contain knob-dependent inline functions.
# gen_modules.py emits MOD_<name>_OBJS for every module/overlay/shared group.
# Snapshot these final lists only after modules.mk and all late *.mk includes.
DEMO_PRESENTATION_MODULE_VARS := $(filter MOD_%_OBJS,$(.VARIABLES))
DEMO_PRESENTATION_OBJECTS := $(sort $(OBJS) $(CENSUS_OBJS) $(foreach v,$(DEMO_PRESENTATION_MODULE_VARS),$($(v))))
$(DEMO_PRESENTATION_OBJECTS): $(DEMO_PRESENTATION_STAMP)

# Append after demo_candidate.mk actor prerequisites; use a NEW OBJDIR.
ACTOR_TRANSACTION_DIAG ?= 0
ifeq ($(filter $(ACTOR_TRANSACTION_DIAG),0 1),)
$(error ACTOR_TRANSACTION_DIAG must be 0 or 1)
endif
ifeq ($(ACTOR_TRANSACTION_DIAG),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_TRANSACTION_DIAG requires ACTOR_TRANSACTION=1)
endif
endif
# Lifetime/source-state observations are owned by coarse_actor; actual source
# alpha and queue/list observations run in these two existing translation units.
$(OBJDIR)/coarse_actor.o $(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_TRANSACTION_DIAG=$(ACTOR_TRANSACTION_DIAG)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_TRANSACTION_DIAG=$(ACTOR_TRANSACTION_DIAG)

# Storage priority for all sealed source-plan native nominees; candidate, default off.
ACTOR_SKIN_RESERVE ?= 0
ifeq ($(filter $(ACTOR_SKIN_RESERVE),0 1),)
$(error ACTOR_SKIN_RESERVE must be 0 or 1)
endif
ifeq ($(ACTOR_SKIN_RESERVE),1)
ifneq ($(ACTOR_TRANSACTION)$(NATIVE_ACTOR_FAST)$(NATIVE_ACTOR_SKIN_LAZY),111)
$(error ACTOR_SKIN_RESERVE requires ACTOR_TRANSACTION=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN_LAZY=1)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_SKIN_RESERVE=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_SKIN_RESERVE=1
$(OBJDIR)/platform/native_actor_fast.o: platform/include/native_actor_skin_reserve.inc
endif

# Exact existing source-selected appearance-zero grip roles; candidate, default off.
ACTOR_GANADO_APP0_GRIP ?= 0
ifeq ($(filter $(ACTOR_GANADO_APP0_GRIP),0 1),)
$(error ACTOR_GANADO_APP0_GRIP must be 0 or 1)
endif
ifeq ($(ACTOR_GANADO_APP0_GRIP),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_GANADO_APP0_GRIP requires ACTOR_TRANSACTION=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_GANADO_APP0_GRIP=1
$(OBJDIR)/coarse_actor.o: actor_material_records_app0_grip.inc
endif

# G1 candidate: the reviewed id13 death fades retain source FIFO order. Off
# adds no compiler define or implementation dependency to existing objects.
ifeq ($(ACTOR_GANADO_DEATH_FADE),1)
ifneq ($(ACTOR_TRANSACTION)$(D349_RENDERER_STACK)$(PVR_STREAM)$(NATIVE_ACTOR_SKIN_LAZY)$(SKIN_PALETTE_LAZY)$(PS2_GANADO_LIT),111111)
$(error ACTOR_GANADO_DEATH_FADE requires ACTOR_TRANSACTION=1 D349_RENDERER_STACK=1 PVR_STREAM=1 NATIVE_ACTOR_SKIN_LAZY=1 SKIN_PALETTE_LAZY=1 PS2_GANADO_LIT=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_GANADO_DEATH_FADE=1 -DRE4DC_AGDF_G1=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_GANADO_DEATH_FADE=1
endif
