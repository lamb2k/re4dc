# D367 generic native models (2026-10-03): NATIVE_MODEL_REGISTRY on the ACTOR_TRANSACTION owner path
# (coarse_actor_owner_registry.inc; registry branches in coarse_actor_transaction.inc, coarse_actor_material.inc,
# actor_lifetime.inc, actor_material_records.inc, coarse_actor_geometry_once.inc). Default 0: no -D is added and the
# image is unchanged. Render only: the source simulation, skeleton, collision, AI, events and animation cadence run as
# before; an admitted actor's presentation is drawn from a validated pack instead of the source preparation.
#
# NATIVE_MODEL_REGISTRY=1: actors whose every source info the archive adoption proof binds to one descriptor's exact
#              source BIN + TPL rows, whose skeleton has the descriptor's bone count / parents / rest rotations and
#              that pass the transaction (layout, semantics, immutable chunk proof, the material certificate's
#              registry branch, the shared leases and preflight) draw the descriptor's chunks. Anything else keeps
#              the whole source path. Unregistered model ids are rejected by an O(1) id mask.
# NATIVE_MODEL_REGISTRY=2: compare mode: the same admission plus the palette build into a scratch buffer; the actor
#              keeps the source path (no lease, no native TA submission); "would" counts what =1 would draw.
#              Requires NATIVE_MODEL_REGISTRY_CENSUS=1 (its only output is the census).
# NATIVE_MODEL_REGISTRY_CENSUS (diagnostic, default 0; never in a cost or production image): "NMRD" / "NMRU" / "NMRS"
#              lines (every 600 UI frames and at room changes): per descriptor planned / admitted / would / declined
#              by reason and the largest accepted rest-inverse deviation, and the scene census of every model whose
#              first OT pass reaches the transaction (native, crowd-skip, declined, registry-declined, absent).
#              With 0 none of the census storage, counters or the per-actor scene walk is compiled.
# NATIVE_MODEL_REGISTRY_CENSUS_PERIOD (diagnostic, default 600): the census report period in UI frames (a one-minute
#              room check reaches a report before its deadline with e.g. 150). Only with the census; 600 adds no define.
# NATIVE_MODEL_REGISTRY_DIR: a private bundle from tools/d367/model_registry.py (native_model_registry.h, the three
#              source-row includes, tex/). Stage its tex/*.re4tex on the disc (dc/tex/<crc>-<fnv>.re4tex).
# NATIVE_MODEL_REGISTRY_PACK (default 0: the compiled provider above, kept as a diagnostic):
#   =1: no registry data is compiled in (no NATIVE_MODEL_REGISTRY_DIR; no geometry or identity arrays in the ELF).
#       At every room enter (ui_bridge.cpp re4dc_room_enter, before the room's archives load) the room's package
#       dc/native/r<room>/registry.re4nmr (tools/d367/model_registry.py --package-room) is read into one heap-4 room
#       cell (re4dc_static_alloc: the room storage and its 80 KiB source reserve) and validated completely (header
#       and payload hashes, section table, every count, offset, alignment, capacity, identifier and cross reference,
#       duplicate geometry, finite binds and weights, the chunk preflight and the skin build) before anything is
#       published. Its identity rows then join the material / lifetime rows for that room generation
#       (actor_material_records.inc). Any failure publishes nothing: every actor keeps the whole source path. At
#       room leave (re4dc_room_leave, before the heap-4 close) the rows, the adopted records using them, the registry
#       bindings and the immutable chunk proofs of its IDs are retired and the cell is freed. Needs NATIVE_STATIC=1.
# NATIVE_MODEL_REGISTRY_TX (default 0; needs NATIVE_MODEL_REGISTRY=1 and NATIVE_MODEL_REGISTRY_PACK=1; render only):
#              one registry actor transaction proves each thing once. The decisions are the =0 decisions:
#   - the palette build reuses the plan's registry_bind proof (shape, revision, role rows, skeleton parents / rest
#     inverse / finite matrices) of the SAME re4dc_actor_transaction_draw call (a one-use token: call serial, model,
#     binding slot, room generation) instead of running it a second time; anything else runs the whole proof;
#   - the pass that acquired the actor keeps the actor_semantics verdict it got before actor_acquire (a later pass,
#     another OT group, proves it again);
#   - the skeleton's finite test skips the rest inverses (the bind comparison already fails NaN / inf: no
#     -ffinite-math-only in this image) and tests the current matrices and the palette outputs with an exact integer
#     reduction of coarse_finite;
#   - a registry appearance's role-row scans visit only the info's set role bits (info_current's first clause);
#   - the registry plan is built in the transaction's plan (no second zeroed plan, no whole-plan copy).
#   Audit (plan -> palettes / semantics, one call): actor_plan_layout (writes the plan), actor_semantics (reads),
#   actor_acquire: re4dc_bind_actor_frame (native frame scratch), texture / workspace / palette-arena / prim-tail
#   leases, the palette build, re4dc_actor_skin_acquire, actor_source_lighting (reads GX state), preflight; then
#   re4dc_actor_transaction_choose (the ledger's presentation choice, not its membership). None runs source code or
#   writes cModel / cParts / cModelInfo, the lifetime records or the room rows; the room leave clears the token.
#   =2: compare build: every reused or reduced verdict is also computed the =0 way, the =0 verdict decides, and
#   "NMRTX" lines (every 600 frames and at room leave) count uses and differences (bind_bad, skeleton_bad, finite_bad,
#   semantics_bad, roles_bad must be 0).
# NATIVE_MODEL_REGISTRY_PALBOUND (default 0; needs NATIVE_MODEL_REGISTRY_TX=1; render only): the registry palette
#              build tests its used bone matrices T (|t| < 2^125, finite) instead of every palette output element when
#              every weight of the descriptor lies in [0, 1] (checked once per room generation at the skin build):
#              each output element is a sum of at most 4 products w*t (coarse_skin_sh4.S groups: FTRV of (w0,w1,w2,0)
#              through used-bone rows; one-bone entries copy), so it is finite. Otherwise the whole output test runs.
#              The verdict equals the output test's. =2: compare build (the output test decides; "NMRPB" lines count
#              bounded chunks whose outputs are not finite, which must be 0, and bound misses that ran the test).
#              The source's own per-info palettes (trans.cpp MakeWeightPalette + re4dc_skin_defer_lazy) are NOT
#              reusable here: the pack's weight groups differ from the source BIN's (generic-models/wcmp.py).
NATIVE_MODEL_REGISTRY_PALBOUND ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_PALBOUND),0 1 2),)
$(error NATIVE_MODEL_REGISTRY_PALBOUND must be 0, 1 or 2)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_PALBOUND),0)
ifneq ($(NATIVE_MODEL_REGISTRY_TX),1)
$(error NATIVE_MODEL_REGISTRY_PALBOUND needs NATIVE_MODEL_REGISTRY_TX=1)
endif
endif
NATIVE_MODEL_REGISTRY ?= 0
NATIVE_MODEL_REGISTRY_CENSUS ?= 0
NATIVE_MODEL_REGISTRY_CENSUS_PERIOD ?= 600
NATIVE_MODEL_REGISTRY_PACK ?= 0
NATIVE_MODEL_REGISTRY_TX ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_TX),0 1 2),)
$(error NATIVE_MODEL_REGISTRY_TX must be 0, 1 or 2)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_TX),0)
ifneq ($(NATIVE_MODEL_REGISTRY)$(NATIVE_MODEL_REGISTRY_PACK),11)
$(error NATIVE_MODEL_REGISTRY_TX needs NATIVE_MODEL_REGISTRY=1 and NATIVE_MODEL_REGISTRY_PACK=1)
endif
endif
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_PACK),0 1),)
$(error NATIVE_MODEL_REGISTRY_PACK must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY),0)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),0)
$(error NATIVE_MODEL_REGISTRY_PACK needs NATIVE_MODEL_REGISTRY=1 or 2)
endif
endif
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_CENSUS),0 1),)
$(error NATIVE_MODEL_REGISTRY_CENSUS must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY),0)
ifneq ($(NATIVE_MODEL_REGISTRY_CENSUS),0)
$(error NATIVE_MODEL_REGISTRY_CENSUS needs NATIVE_MODEL_REGISTRY=1 or 2)
endif
endif
ifneq ($(NATIVE_MODEL_REGISTRY_CENSUS_PERIOD),600)
ifneq ($(NATIVE_MODEL_REGISTRY_CENSUS),1)
$(error NATIVE_MODEL_REGISTRY_CENSUS_PERIOD needs NATIVE_MODEL_REGISTRY_CENSUS=1)
endif
ifeq ($(shell echo '$(NATIVE_MODEL_REGISTRY_CENSUS_PERIOD)' | grep -E '^[1-9][0-9]{1,4}$$'),)
$(error NATIVE_MODEL_REGISTRY_CENSUS_PERIOD must be 10..99999 UI frames)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_CENSUS_PERIOD=$(NATIVE_MODEL_REGISTRY_CENSUS_PERIOD)
endif
ifneq ($(NATIVE_MODEL_REGISTRY),0)
ifeq ($(filter $(NATIVE_MODEL_REGISTRY),1 2),)
$(error NATIVE_MODEL_REGISTRY must be 0, 1 or 2)
endif
ifneq ($(ACTOR_TRANSACTION),1)
$(error NATIVE_MODEL_REGISTRY extends the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
ifneq ($(COARSE_SKIN_FTRV),1)
$(error NATIVE_MODEL_REGISTRY builds its palettes with COARSE_SKIN_FTRV=1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY_PACK),0)
ifndef NATIVE_MODEL_REGISTRY_DIR
$(error NATIVE_MODEL_REGISTRY_DIR must point at a private bundle from tools/d367/model_registry.py)
endif
else
ifneq ($(NATIVE_STATIC),1)
$(error NATIVE_MODEL_REGISTRY_PACK=1 loads into the native static room storage (NATIVE_STATIC=1))
endif
ifdef NATIVE_MODEL_REGISTRY_DIR
$(error NATIVE_MODEL_REGISTRY_PACK=1 compiles no bundle: unset NATIVE_MODEL_REGISTRY_DIR and stage the room package)
endif
endif
ifeq ($(NATIVE_MODEL_REGISTRY)$(NATIVE_MODEL_REGISTRY_CENSUS),20)
$(error NATIVE_MODEL_REGISTRY=2 reports only through the census (NATIVE_MODEL_REGISTRY_CENSUS=1))
endif
# The entry gate: trans.cpp's re4dc_actor_transaction_candidate (platform/include/source_actor_owner_hooks.inc)
# also nominates registry ids, so their OT callbacks leave the FRONT_NATIVE fast return for the transaction.
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_MODEL_REGISTRY=$(NATIVE_MODEL_REGISTRY)
ifeq ($(NATIVE_MODEL_REGISTRY_PACK),0)
NATIVE_MODEL_REGISTRY_FILES := $(addprefix $(NATIVE_MODEL_REGISTRY_DIR)/,native_model_registry.h \
  native_model_registry_facts.inc native_model_registry_roles.inc native_model_registry_blobs.inc)
$(OBJDIR)/coarse_actor.o: $(NATIVE_MODEL_REGISTRY_FILES)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_MODEL_REGISTRY=$(NATIVE_MODEL_REGISTRY)   -DRE4DC_NATIVE_MODEL_REGISTRY_CENSUS=$(NATIVE_MODEL_REGISTRY_CENSUS) -I$(NATIVE_MODEL_REGISTRY_DIR)
else
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_MODEL_REGISTRY=$(NATIVE_MODEL_REGISTRY)   -DRE4DC_NATIVE_MODEL_REGISTRY_CENSUS=$(NATIVE_MODEL_REGISTRY_CENSUS) -DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1
ifneq ($(NATIVE_MODEL_REGISTRY_TX),0)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_MODEL_REGISTRY_TX=$(NATIVE_MODEL_REGISTRY_TX)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_PALBOUND),0)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_MODEL_REGISTRY_PALBOUND=$(NATIVE_MODEL_REGISTRY_PALBOUND)
endif
# The room hooks: re4dc_room_enter opens and re4dc_room_leave retires the room's package (coarse_actor_registry_pack.inc).
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1
endif
endif

# NATIVE_MODEL_REGISTRY_BONES=<n> (lane ps2cast-all, 2026-10-10; default 48: nothing changes; needs
#              NATIVE_MODEL_REGISTRY_PACK=1): the room package's skeleton capacity (kRegBones: the bindings' part lists,
#              the palette build's bone matrices and jobs, the loader's parents / binds caps). 64 takes El Gigante (em2b
#              type 0: 64 parts); the package generator takes the same value (model_registry.py --pack-bones).
# NATIVE_MODEL_REGISTRY_SHIFT=1 (lane ps2cast-all; default 0; needs NATIVE_MODEL_REGISTRY_PACK=1; render only): a
#              package descriptor carries its chunks' position fraction bits in descriptor word 44 (0 = 4, the 1/16 mm
#              of every cast and the =0 rule; 1..4 allowed) and the owned part takes it (coarse_actor_transaction.inc
#              base.shift; native_actor_fast.cpp dequantizes by base.shift as it does for source parts). Models whose
#              source positions exceed +-2048 mm (El Gigante, Del Lago: GC shift 2) need 2. Leon and the Ganado cast
#              keep 4. Packages without the word are unchanged.
# PS2_GIGANTE=1 (lane ps2cast-all; default 0; render only): the runtime side of El Gigante's PS2 mesh (em2b type 0, a
#              64-bone, shift-2 model): NATIVE_MODEL_REGISTRY_BONES=64 NATIVE_MODEL_REGISTRY_SHIFT=1. The mesh itself is
#              disc data: the r119 room package dc/native/r119/registry.re4nmr (model_registry.py --package-room 119
#              --pack-bones 64 over the ps2_cast.py regcast cast) and its atlas in dc/tex.pak. Without the package
#              El Gigante keeps the source path.
PS2_GIGANTE ?= 0
ifeq ($(filter $(PS2_GIGANTE),0 1),)
$(error PS2_GIGANTE must be 0 or 1)
endif
ifeq ($(PS2_GIGANTE),1)
ifeq ($(ROUTE_CH23),1)
NATIVE_MODEL_REGISTRY_BONES ?= 96
else
NATIVE_MODEL_REGISTRY_BONES ?= 64
endif
NATIVE_MODEL_REGISTRY_SHIFT ?= 1
ifneq ($(filter 1,$(ROUTE_CH23) $(ROUTE_CH3)),)
# Mendez has 83 bones (ROUTE_CH23); the island U-3 (em32, ROUTE_CH3 disc 2) has 97 (lane cast16 10-17). A larger
# existing registry capacity still admits the 64-bone Gigante. ROUTE_CH3 keeps 64 unless the recipe asks for more.
ifeq ($(ROUTE_CH23),1)
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_BONES),96 128),)
$(error PS2_GIGANTE=1 with ROUTE_CH23=1 needs registry capacity 96 or 128 for Mendez)
endif
else
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_BONES),64 96 128),)
$(error PS2_GIGANTE=1 with ROUTE_CH3=1 needs registry capacity 64, 96 or 128)
endif
endif
ifneq ($(NATIVE_MODEL_REGISTRY_SHIFT),1)
$(error PS2_GIGANTE=1 needs NATIVE_MODEL_REGISTRY_SHIFT=1)
endif
else
ifneq ($(NATIVE_MODEL_REGISTRY_BONES)$(NATIVE_MODEL_REGISTRY_SHIFT),641)
$(error PS2_GIGANTE=1 needs NATIVE_MODEL_REGISTRY_BONES=64 (or unset) and NATIVE_MODEL_REGISTRY_SHIFT=1)
endif
endif
endif
# PS2_DELLAGO=1 (lane ps2cast-2; default 0; render only): the runtime side of Del Lago's PS2 mesh (em2f type 0, 35 bones,
#              shift 2): NATIVE_MODEL_REGISTRY_SHIFT=1 plus NATIVE_MODEL_REGISTRY_DROP_BUMP for em2f (its GC materials
#              carry a bump stage, which the source path never draws either: trans.cpp bumpSetup only reaches the GX
#              stubs and model_bridge binds the colour texture alone; model_registry.py "source_drops"). The mesh is disc
#              data: the r10b room package dc/native/r10b/registry.re4nmr (model_registry.py --package-room 10b) and its
#              atlas in dc/tex.pak. Without the package Del Lago keeps the source path.
# Lighting (lane ps2cast-2): PS2_GIGANTE / PS2_DELLAGO also set NATIVE_MODEL_REGISTRY_SOURCE_LIGHT (bit 0 em2b, bit 1
#              em2f): the registry boss takes the source GX lighting record (LightSetModel's lights, ambient, material
#              colour, TEV scale; coarse_actor_transaction.inc actor_source_lighting) instead of the constant colour, so
#              it is lit like the source-path boss (GIGANTE_LIGHTS folds em2b the same way). Without it the boss drew
#              unlit (flat, lighter).
# Culling (lane ps2cast-3): PS2_DELLAGO also sets RE4DC_NMR_SOURCE_CULL (bit 1 em2f): the registry draw takes the source
#              cull (model_bridge.cpp re4dc_model_cull of the material CullMode: back faces) instead of the owner paths'
#              cull none. In the r10b fight the camera goes inside the body (tick 2440: vertices 7.1 m behind it); the
#              source culls the inner faces and shows the legs, cull none filled the screen with the body's inside.
#              The PS2 mesh keeps the GC winding (the same faces cull in an offline render of both meshes).
PS2_DELLAGO ?= 0
ifeq ($(filter $(PS2_DELLAGO),0 1),)
$(error PS2_DELLAGO must be 0 or 1)
endif
ifeq ($(PS2_DELLAGO),1)
NATIVE_MODEL_REGISTRY_SHIFT ?= 1
ifneq ($(NATIVE_MODEL_REGISTRY_SHIFT),1)
$(error PS2_DELLAGO=1 needs NATIVE_MODEL_REGISTRY_SHIFT=1 (or unset))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_DROP_BUMP=1
endif
# NATIVE_MODEL_REGISTRY_MASK=1 (lane ps2cast-3, 2026-10-11; default 0; needs NATIVE_MODEL_REGISTRY_PACK=1; render only): a
#              package section may be drawn as two runs (package ref word 12): its opaque triangles with the chunk
#              texture and its alpha-masked triangles (hair cards) with a colour + I4 mask pair, the material the Leon
#              hair draws in the native look (TR, SRC_ALPHA/INV_SRC_ALPHA, no depth write, same-UV mask; the ARGB4444
#              pair package keyed as native_ui.cpp model_mask_key derives it). Both runs index the section's positions /
#              normals / palettes (the loader checks equal bytes); a plan with such runs meets the source's mask and
#              second-pass needs in the material certificate. tools/ps2_mask_runs.py builds the runs and the pair from
#              the GC colour + mask images; model_registry.py "mask_runs" packages them.
# PS2_GANADO_F=1 (lane ps2cast-3; default 0; render only): the female Ganado (em17 / em16 type 0xc, r108 r118 r111 r113
#              r11d) through the registry owner path with the PS2 mesh and the GC hair mask: NATIVE_MODEL_REGISTRY_MASK=1.
#              The mesh is disc data: the room package dc/native/r1xx/registry.re4nmr, its atlas and the hair pair in
#              dc/tex.pak. Without the package she keeps the source path.
PS2_GANADO_F ?= 0
ifeq ($(filter $(PS2_GANADO_F),0 1),)
$(error PS2_GANADO_F must be 0 or 1)
endif
ifeq ($(PS2_GANADO_F),1)
NATIVE_MODEL_REGISTRY_MASK ?= 1
endif
NATIVE_MODEL_REGISTRY_MASK ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_MASK),0 1),)
$(error NATIVE_MODEL_REGISTRY_MASK must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY_MASK),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),1)
$(error NATIVE_MODEL_REGISTRY_MASK needs NATIVE_MODEL_REGISTRY_PACK=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_MASK=1
endif
# PS2_ANIMALS=1 (lane ps2cast-4, 2026-10-11; default 0; render only): the stage-1 animals (dog em21, cow em26, chicken em28)
#              from their PS2 meshes. Disc data only: the r100 / r101 / r103 room packages dc/native/r1xx/registry.re4nmr
#              (model_registry.py --package-room over tools/d367/model-registry/ps2-animals.json, the ps2_cast.py regcast
#              of the PS2 presets dog-00/01, cow-00/01, chicken-00/01) and their atlases in dc/tex.pak replace today's cast
#              packages with the same descriptor names, rows and room lists; they draw flat and cull none exactly as the
#              cast animals do today, so the image is unchanged by the knob (it only checks the registry pack path). The
#              crow (em23) is not converted: its GC materials need bump + an unknown material program + the wing mask
#              (a material contract, see docs/lanes/ps2cast.md "Lane ps2cast-4").
PS2_ANIMALS ?= 0
ifeq ($(filter $(PS2_ANIMALS),0 1),)
$(error PS2_ANIMALS must be 0 or 1)
endif
ifeq ($(PS2_ANIMALS),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),1)
$(error PS2_ANIMALS=1 draws the animals from room packages (NATIVE_MODEL_REGISTRY=1 NATIVE_MODEL_REGISTRY_PACK=1))
endif
endif
# PS2_WOLF=1 (lane ps2cast-4; default 0; render only): the parasite dog (Colmillos, em22, r11b r118) through the registry
#              owner path with its PS2 mesh (1,735 tris vs GC 3,978; 42 bones). Today em22 draws on the source path, so its
#              registry plan takes the source lighting record (NATIVE_MODEL_REGISTRY_SOURCE_LIGHT bit 4) and the source cull
#              (RE4DC_NMR_SOURCE_CULL bit 4). The mesh is disc data: dc/native/r11b|r118/registry.re4nmr (model_registry.py
#              over tools/d367/model-registry/ps2-wolf.json) and its atlas in dc/tex.pak; without a package em22 keeps
#              the source path. The back parasites (cObj16, ARC 0x39 / 0x47) stay on the source path.
PS2_WOLF ?= 0
ifeq ($(filter $(PS2_WOLF),0 1),)
$(error PS2_WOLF must be 0 or 1)
endif
ifeq ($(PS2_WOLF),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),1)
$(error PS2_WOLF=1 needs NATIVE_MODEL_REGISTRY=1 NATIVE_MODEL_REGISTRY_PACK=1)
endif
endif
# PS2_CROW=1 (Phase 2 A3, 2026-10-11; default 0; render only): the crow (em23; r100, r105, r108, r109) through the registry
#              owner path with its PS2 mesh (folded 750 / spread 668 tris: body 540 + wings 210 / 128; 24 bones). Today em23
#              draws on the source path, so its registry plan takes the source lighting record and the source cull (bit 8 of
#              NATIVE_MODEL_REGISTRY_SOURCE_LIGHT / RE4DC_NMR_SOURCE_CULL). Its GC materials need bump + alternate specular
#              (body flag 0x83) and the folded wing's I4 mask pass; user decision 2026-10-11: accept the solid PS2 wing and
#              drop the GX-only bump and alternate specular (RE4DC_NMR_CROW: the certificate's twin of model_registry.py
#              source_drops "bump", "alt-specular", "mask"). The mesh is disc data: dc/native/r100/registry.re4nmr from
#              tools/d367/model-registry/ps2-crow.json (dog-01 + crow-folded + crow-spread: r100 keeps one package) and the
#              crow atlas in dc/tex.pak; without a package the crow keeps the source path.
PS2_CROW ?= 0
ifeq ($(filter $(PS2_CROW),0 1),)
$(error PS2_CROW must be 0 or 1)
endif
ifeq ($(PS2_CROW),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),1)
$(error PS2_CROW=1 needs NATIVE_MODEL_REGISTRY=1 NATIVE_MODEL_REGISTRY_PACK=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_CROW=1
endif
ifneq ($(PS2_DELLAGO)$(PS2_WOLF)$(PS2_CROW),000)
# RE4DC_NMR_SOURCE_CULL bits: 2 em2f (PS2_DELLAGO), 8 em23 (PS2_CROW), 16 em22 (PS2_WOLF)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_SOURCE_CULL=$(shell echo $$(( $(if $(filter 1,$(PS2_DELLAGO)),2,0) + $(if $(filter 1,$(PS2_CROW)),8,0) + $(if $(filter 1,$(PS2_WOLF)),16,0) )))
endif
# PS2_CAST_MERCHANT_LIT=1 (lane ps2cast 2026-10-14; default 0; render only; needs PS2_CAST_MERCHANT=1): bit 5 of
#              NATIVE_MODEL_REGISTRY_SOURCE_LIGHT - the merchant's registry plan (em18) takes the source GX lighting record
#              (actor_source_lighting) like the bosses / em17 / em22 / em23 above, instead of the constant colour that makes
#              his PS2 robe brown-black where PS2 shows it blue-black under r102's night light. His robe / coat infos carry
#              be_flag 0x20 (own material colour) but keep the constructor white, so the one-material check accepts them;
#              any record the check refuses declines the whole merchant to the source path (ATD reason 26), as for the others.
PS2_CAST_MERCHANT_LIT ?= 0
ifeq ($(filter $(PS2_CAST_MERCHANT_LIT),0 1),)
$(error PS2_CAST_MERCHANT_LIT must be 0 or 1)
endif
ifeq ($(PS2_CAST_MERCHANT_LIT),1)
ifneq ($(PS2_CAST_MERCHANT),1)
$(error PS2_CAST_MERCHANT_LIT=1 needs PS2_CAST_MERCHANT=1)
endif
endif
ifneq ($(PS2_GIGANTE)$(PS2_DELLAGO)$(PS2_GANADO_F)$(PS2_WOLF)$(PS2_CROW)$(PS2_CAST_MERCHANT_LIT)$(filter 1,$(NATIVE_MODEL_REGISTRY_POOL)),000000)
# bit 6 (NATIVE_MODEL_REGISTRY_POOL): every pool plan (the zealots, soldiers) takes the source lighting record (unlit, the
# zealot face under the hood drew pale where the source and the PS2 shade it).
# bit 2 (PS2_GANADO_F): the female Ganado's registry plan (em17 / em16) is lit like her source path today; bit 3
# (PS2_CROW): em23 likewise; bit 4 (PS2_WOLF): em22 likewise.
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_SOURCE_LIGHT=$(shell echo $$(( $(if $(filter 1,$(PS2_GIGANTE)),1,0) + $(if $(filter 1,$(PS2_DELLAGO)),2,0) + $(if $(filter 1,$(PS2_GANADO_F)),4,0) + $(if $(filter 1,$(PS2_CROW)),8,0) + $(if $(filter 1,$(PS2_WOLF)),16,0) + $(if $(filter 1,$(PS2_CAST_MERCHANT_LIT)),32,0) + $(if $(filter 1,$(NATIVE_MODEL_REGISTRY_POOL)),64,0) )))
endif
NATIVE_MODEL_REGISTRY_BONES ?= 48
NATIVE_MODEL_REGISTRY_SHIFT ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_SHIFT),0 1),)
$(error NATIVE_MODEL_REGISTRY_SHIFT must be 0 or 1)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_BONES)$(NATIVE_MODEL_REGISTRY_SHIFT),480)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),1)
$(error NATIVE_MODEL_REGISTRY_BONES / NATIVE_MODEL_REGISTRY_SHIFT need NATIVE_MODEL_REGISTRY_PACK=1)
endif
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_BONES),48 64 80 96 128),)
$(error NATIVE_MODEL_REGISTRY_BONES must be 48, 64, 80, 96 or 128)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_BONES),48)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_BONES=$(NATIVE_MODEL_REGISTRY_BONES)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_SHIFT),0)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_SHIFT=1
endif
endif

# PS2_CAST_MERCHANT=1 (lane ps2cast2 2026-10-14; default 0; render only): the merchant (em18; r102, later r10d r10e r112)
#              through the registry owner path with his PS2 mesh (closed / open coat descriptors merchant18-c0 / -o0: 61
#              bones, 7 sections, robe + coat mask runs; tools/d367/model-registry/ps2-merchant-ch1.json over Codex's
#              ps2_cast.py regcast-merchant18). Runtime side: 40 source material facts per room package (RE4DC_NMR_FACTS;
#              the merchant needs 35, the default cap is 32), the source robe / coat material-colour flag (be_flag 0x20)
#              that em18_R0_Init / em18ClothPartsSet set (re4dc_registry_merchant_robe, the ROUTE_CH23 rule) and the
#              registry skeleton capacity >= 64. Mask runs need NATIVE_MODEL_REGISTRY_MASK=1. RE4DC_NMR_PARK_UNRELOCATED
#              (actor_swap_park.inc): r102 reads em18 ahead and opens the shop sub screen before setEm(0x4C) creates the
#              merchant, so his archive's BINs are not relocated yet when the screen parks the archive; the unpark required
#              every parked asset to be current() and revoked the whole archive (the merchant then drew GC for the rest of
#              the room). Unrelocated-at-open assets are republished unchanged (the bytes hash already proves it). The mesh is disc data:
#              dc/native/r102/registry.re4nmr and its atlases; without the package the merchant keeps the source path.
PS2_CAST_MERCHANT ?= 0
ifeq ($(filter $(PS2_CAST_MERCHANT),0 1),)
$(error PS2_CAST_MERCHANT must be 0 or 1)
endif
ifeq ($(PS2_CAST_MERCHANT),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK)$(NATIVE_MODEL_REGISTRY_MASK),11)
$(error PS2_CAST_MERCHANT=1 needs NATIVE_MODEL_REGISTRY_PACK=1 and NATIVE_MODEL_REGISTRY_MASK=1)
endif
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_BONES),64 80 96 128),)
$(error PS2_CAST_MERCHANT=1 needs NATIVE_MODEL_REGISTRY_BONES >= 64 (61-bone merchant))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_MERCHANT=1 -DRE4DC_NMR_PARK_UNRELOCATED=1
endif
# PS2_CAST_BOAT=1 (lane ps2cast 2026-10-15; default 0; render only): the lake boat (pl0f, model id 0x0f; r10b, then r11b)
#              through the registry owner path with its PS2 mesh (boat-pl0f-00: 1,210 tris as GC, position shift 3, the PS2
#              atlas; tools/d367/model-registry/ps2-boat-r10b.json = the released Del Lago descriptor + the boat). Its GC
#              material needs bump and the alternate specular (flag 0x80): both reach only GX stubs on the DC source path,
#              so the certificate accepts their absence for registry model 0x0f (RE4DC_NMR_BOAT, the twin of
#              model_registry.py source_drops "bump", "alt-specular"; the crow's rule). Leon's harpoon hand (pl0f ARC 8,
#              cPlBody::initWepHand) is already the PS2 hand of LEON_HAND_PACK (pose 7). Disc data: dc/native/r10b/
#              registry.re4nmr (80,448 B, heap-4 arena 84,176 B) + the boat atlas, and em/pl0f.drs texture-prepared
#              (prepare_enemy_motions.py SMALL, textures only; heap-4 body 807,520 -> 757,664 B). Without the package the
#              boat keeps the source path. Needs PS2_DELLAGO=1 (the bump drop rule block and position shift).
PS2_CAST_BOAT ?= 0
ifeq ($(filter $(PS2_CAST_BOAT),0 1),)
$(error PS2_CAST_BOAT must be 0 or 1)
endif
ifeq ($(PS2_CAST_BOAT),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK)$(PS2_DELLAGO),11)
$(error PS2_CAST_BOAT=1 needs NATIVE_MODEL_REGISTRY_PACK=1 and PS2_DELLAGO=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_BOAT=1
endif
# PS2_CAST_CH1=1 (lane ps2cast 2026-10-15; default 0; render only): the chapter 1 small cast through the registry owner path with
#              PS2 meshes: traps (em2a), snakes (em24), fish (em27), bats (em29), crawlers (em2e) in r100 r105 r106 r107 r108
#              r10a r10b r11a r11b. Their GC materials and the PS2 sections match (same mesh and texels); the snake's and the
#              fish's material needs bump, which reaches only GX stubs on the DC source path, so the certificate accepts its
#              absence for registry models 0x24 / 0x27 (RE4DC_NMR_CH1CAST, the twin of model_registry.py source_drops "bump",
#              Del Lago's rule). The bats are ot_type 1 (OT 0x11, the same ModelRender callback): the registry model check
#              admits that for model 0x29 (RE4DC_REGISTRY_OT_OK). Traps and crawlers need no code: their room package and texture-prepared archive
#              (prepare_enemy_motions.py SMALL, textures only) are disc data. Without the knob a snake / fish descriptor is
#              declined by the certificate (GC model, as before). Needs PS2_DELLAGO=1 (the bump drop rule block).
PS2_CAST_CH1 ?= 0
ifeq ($(filter $(PS2_CAST_CH1),0 1),)
$(error PS2_CAST_CH1 must be 0 or 1)
endif
ifeq ($(PS2_CAST_CH1),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK)$(PS2_DELLAGO),11)
$(error PS2_CAST_CH1=1 needs NATIVE_MODEL_REGISTRY_PACK=1 and PS2_DELLAGO=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_CH1CAST=1
endif
# ACTOR_PALETTE_BANK=<KiB> (lane ps2cast 2026-10-15; default 64 = the image before; render only): the native actor palette
#              bank funded once per frame from the primitive buffer's tail (coarse_actor_transaction.inc kActorPaletteCap).
#              Palette leases are released after each actor's synchronous submit, so the bank holds one or two actors at a
#              time: measured peak use (ACTOR_TRANSACTION_DIAG "APAL", Flycast) 18,976 B on benchmark-r101 (6 Ganados +
#              Leon), 16,288 B in r107. The unused rest of the 64 KiB bank is tail the per-actor records cannot use: with
#              the chapter 1 traps (PS2_CAST_CH1) r107's tail reached its limit and Ganados / traps declined to the GC model
#              in 60 of 900 frames (PRIM_WATER). 40 frees 24 KiB of primitive tail per frame in every room.
ACTOR_PALETTE_BANK ?= 64
ifeq ($(filter $(ACTOR_PALETTE_BANK),16 24 32 40 48 56 64),)
$(error ACTOR_PALETTE_BANK must be one of 16 24 32 40 48 56 64 (KiB))
endif
ifneq ($(ACTOR_PALETTE_BANK),64)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_PALETTE_BANK=$(ACTOR_PALETTE_BANK)
endif
# NATIVE_MODEL_REGISTRY_POOL=1 (lane ps2cast 2026-10-15; default 0; render only): pool descriptors. A Ganado-class actor
#              whose source infos vary per spawn (em10SetAccesory hoods / caps / accessories by cEm::flag, em10HandSet
#              grip poses, the stage-3 soldiers' heads) has one package descriptor whose sections are a POOL of source BIN +
#              TPL identities (package descriptor word 44 bit 24; one role row and one chunk per pool section, up to 48):
#              the body, every head, every hand pose, every accessory the source can attach. The actor is admitted when
#              each of its 1..8 source infos proves exactly one current pool row of that appearance
#              (actor_lifetime.inc re4dc_actor_pool_bindings: the per-info proof of re4dc_actor_role_bindings), no two
#              infos the same row and the first info, and only it, the body (section 0); its plan keeps source info order
#              and names each role's pool section (Re4dcActorPlan::pool / section, in every object), and the certificate,
#              the palette build and the run checks read the chunk and role row of that section
#              (coarse_actor_owner_registry.inc registry_plan_shape, coarse_actor_material.inc RE4DC_PLAN_ROLE). Nothing
#              lists combinations: an accessory or hand the pool lacks declines the actor to the whole source path, as
#              before. Capacities with the pool: 128 role bits (66 room rows; needs the wide identity), 64 chunks / geometries,
#              48 source BIN models, 64 texture facts, 160 part facts per package. A package with a pool descriptor is
#              refused (whole package, every actor keeps its source path) by an image without the knob: stage pool
#              packages only with it. Needs NATIVE_MODEL_REGISTRY_PACK=1.
NATIVE_MODEL_REGISTRY_POOL ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_POOL),0 1),)
$(error NATIVE_MODEL_REGISTRY_POOL must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY_POOL),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),1)
$(error NATIVE_MODEL_REGISTRY_POOL=1 needs NATIVE_MODEL_REGISTRY_PACK=1)
endif
GAME_CPPFLAGS += -DRE4DC_NMR_POOL=1
PLATFORM_CPPFLAGS += -DRE4DC_NMR_POOL=1
# Pool sections with a source bump stage (bump-only texture rows keyed 0-0, the drop rule) and up to three mask pairs
# beside the atlas.
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_DROP_BUMP=1
GAME_CPPFLAGS += -DRE4DC_ACTOR_MATERIALS=4
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_MATERIALS=4
endif
# NATIVE_MODEL_REGISTRY_ROLES5=1 (lane cast16 2026-10-16; default 0; render only; needs NATIVE_MODEL_REGISTRY_POOL=1): wide room packages,
#              the Info::roles mask takes 5 words (160 role bits, 98 room rows) and the chunk table 96 (package refs) for rooms whose pools load many types
#              (r227: em14 types 6..9; island r320 / r327). It also widens the package loader for the wide castle rooms:
#              32 package textures, a 128-bit asset template mask (two-word BlobMask), 64 source BIN models, 224 part facts
#              and a 384 KiB package + skin arena (heap 4 takes the actual size; r214 340 KiB, r227 291 KiB, r216 182 KiB).
#              Packages over 66 room rows (model_registry.py --roles5) are refused whole by an image without it. Knob off:
#              the image is unchanged.
# NATIVE_BUMP_FLAT=1 (lane cast16 2026-10-16; default 0; render only): every registry plan meets the source bump need
#              with no bump stage (the DC source path draws none either), for descriptors that declare source_drops
#              "bump" outside a pool. Knob off: the image is unchanged.
# NATIVE_MODEL_REGISTRY_BIN_DIAG=1 (lane cast16 2026-10-16; default 0; diagnostic): an info with no live record logs its
#              source BIN / TPL archive entry numbers (NMRBIN lines, 48 at most). Knob off: the image is unchanged.
NATIVE_MODEL_REGISTRY_BIN_DIAG ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_BIN_DIAG),1)
GAME_CPPFLAGS += -DRE4DC_NMR_BIN_DIAG=1
PLATFORM_CPPFLAGS += -DRE4DC_NMR_BIN_DIAG=1
endif
NATIVE_BUMP_FLAT ?= 0
ifeq ($(NATIVE_BUMP_FLAT),1)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_BUMP_FLAT=1
endif
NATIVE_MODEL_REGISTRY_ROLES5 ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_ROLES5),1)
ifneq ($(NATIVE_MODEL_REGISTRY_POOL),1)
$(error NATIVE_MODEL_REGISTRY_ROLES5=1 needs NATIVE_MODEL_REGISTRY_POOL=1)
endif
GAME_CPPFLAGS += -DRE4DC_NMR_ROLES5=1
PLATFORM_CPPFLAGS += -DRE4DC_NMR_ROLES5=1
endif
# NMR_R202_CAST_CAPACITY=1 (castle18, default 0): retain the complete original r202 source cast:
# em11 type7/8 pools, both Merchant18 appearances, and all three Ashley hand appearances.
# Their unchanged packages need 69 unique geometries. Eight additional static records are reserved;
# validation permits at most 69 in r202, keeps 64 elsewhere, and preserves every other bound/proof.
NMR_R202_CAST_CAPACITY ?= 0
ifeq ($(filter $(NMR_R202_CAST_CAPACITY),0 1),)
$(error NMR_R202_CAST_CAPACITY must be 0 or 1)
endif
ifeq ($(NMR_R202_CAST_CAPACITY),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK)$(NATIVE_MODEL_REGISTRY_POOL)$(NATIVE_MODEL_REGISTRY_ROLES5),111)
$(error NMR_R202_CAST_CAPACITY=1 needs NATIVE_MODEL_REGISTRY_PACK=1 NATIVE_MODEL_REGISTRY_POOL=1 NATIVE_MODEL_REGISTRY_ROLES5=1)
endif
GAME_CPPFLAGS += -DRE4DC_NMR_R202_CAST_CAPACITY=1
PLATFORM_CPPFLAGS += -DRE4DC_NMR_R202_CAST_CAPACITY=1
endif
# NATIVE_MODEL_REGISTRY_ROLE_TEX23=1 (lane geodrop17 2026-10-17; default 0; render only; needs NATIVE_MODEL_REGISTRY_ROLES5=1):
#   a role's source TPL may have 23 images (the r320 helicopter em3d TPL 6; ROLES5 allows 19). A package validation bound
#   only (model_registry.py --role-tex23). Knob off: the image is unchanged.
NATIVE_MODEL_REGISTRY_ROLE_TEX23 ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_ROLE_TEX23),1)
ifneq ($(NATIVE_MODEL_REGISTRY_ROLES5),1)
$(error NATIVE_MODEL_REGISTRY_ROLE_TEX23=1 needs NATIVE_MODEL_REGISTRY_ROLES5=1)
endif
GAME_CPPFLAGS += -DRE4DC_NMR_ROLE_TEX23=1
PLATFORM_CPPFLAGS += -DRE4DC_NMR_ROLE_TEX23=1
endif
# NATIVE_MODEL_REGISTRY_FIRST=1 (lane cast16 2026-10-16; default 0; render only; needs NATIVE_MODEL_REGISTRY_POOL=1): a
#   Ganado-class actor (id 0x10..0x20) whose id a room package descriptor names tries that package's plan BEFORE the
#   Ganado cast plan. Without it the Ganado plan claims em16 type 11 (r11d) by its em15-type-11 meshes and then the
#   certificate declines it (source_appearance_type: em16 t11 is not an alias, its sack / whood entries are em16's own),
#   so the actor draws GC every frame and the room's ganado-em16-0bp pool never runs. A registry plan that does not bind
#   (any other type of that id) falls through to the Ganado plan exactly as before.
NATIVE_MODEL_REGISTRY_FIRST ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_FIRST),0 1),)
$(error NATIVE_MODEL_REGISTRY_FIRST must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY_FIRST),1)
ifneq ($(NATIVE_MODEL_REGISTRY_POOL),1)
$(error NATIVE_MODEL_REGISTRY_FIRST=1 needs NATIVE_MODEL_REGISTRY_POOL=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_FIRST=1
endif
# NATIVE_MODEL_REGISTRY_LOD=1 (lane cast16 2026-10-16; default 0; render only; needs NATIVE_MODEL_REGISTRY_POOL=1): boss
#   gameplay levels. A room package descriptor with word 44 bit 25 is a gameplay level of the earlier descriptor named
#   by bits 16..23 (model_registry.py spec "lod_of": same source BINs / TPLs / skeleton, a reduced mesh). The search
#   never binds a level directly; registry_lod_want draws the level outside in-engine events and the full descriptor
#   while one holds the game (Status_flg[1] 0x10000000, the GANADO_LOD rule: cutscenes keep the full model). User
#   10-16: a boss whose fight room projects < 30 fps gets a reduced gameplay model. An image without the knob refuses
#   a package that carries a level (word 44 check), so stage level packages only with it.
NATIVE_MODEL_REGISTRY_LOD ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_LOD),0 1),)
$(error NATIVE_MODEL_REGISTRY_LOD must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY_LOD),1)
ifneq ($(NATIVE_MODEL_REGISTRY_POOL),1)
$(error NATIVE_MODEL_REGISTRY_LOD=1 needs NATIVE_MODEL_REGISTRY_POOL=1)
endif
GAME_CPPFLAGS += -DRE4DC_NMR_LOD=1
endif
# NMR_POOL_LOD=1 (lane lod26b 2026-10-26; default 0: no code; render only; needs NATIVE_MODEL_REGISTRY_LOD=1 and
#   GANADO_LOD=1): numbered gameplay levels of POOL descriptors (the chapter 2 registry Ganados em16 / em17). Package
#   word 44 bits 26..29 = the level's number in the GANADO_LOD order (2 g70, 3 g50); model_registry.py spec
#   "lod_level" with "lod_of" (the level repeats its full descriptor's pool sections in order, body / head reduced by
#   glod_rung.py). registry_lod_want draws, for a pool Ganado, the numbered level with the highest number not above the
#   level the cast Ganados draw now (re4dc_ganado_lod_level: GANADO_LOD_LEVEL, its event rule, GANADO_EVENT_KEEP_LOD),
#   else the full descriptor: one knob for every Ganado. An image without the knob refuses a numbered level package.
NMR_POOL_LOD ?= 0
ifeq ($(filter $(NMR_POOL_LOD),0 1),)
$(error NMR_POOL_LOD must be 0 or 1)
endif
ifeq ($(NMR_POOL_LOD),1)
ifneq ($(NATIVE_MODEL_REGISTRY_LOD)$(GANADO_LOD),11)
$(error NMR_POOL_LOD=1 needs NATIVE_MODEL_REGISTRY_LOD=1 GANADO_LOD=1)
endif
GAME_CPPFLAGS += -DRE4DC_NMR_POOL_LOD=1
endif
# NATIVE_MODEL_REGISTRY_NO_GC_FRONT=1 (lane fix-mendez-door24 2026-10-24; default 0; render only; needs
#   NATIVE_MODEL_REGISTRY=1): an actor the registry owns (a live registry binding: earlier frames drew it from its PS2
#   package) never falls back to the GameCube FRONT_NATIVE path. On a frame where the source ledger has not prepared it
#   (re4dc_actor_transaction_identity 0: the frame the door demo starts, the stopped game ran no emTrans) the actor
#   nominated nothing, so trans.cpp ModelRender drew it GC through frontNativeRender. r11f after the Mendez fight: em35's
#   GC material pair 7d4e1e92-052bdc2e (purged from tex.pak), TEXCHK FAIL at the area 00 door. That frame now draws
#   nothing for the actor (it is the first frame of the door fade). Knob off: the image is unchanged.
NATIVE_MODEL_REGISTRY_NO_GC_FRONT ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_NO_GC_FRONT),0 1),)
$(error NATIVE_MODEL_REGISTRY_NO_GC_FRONT must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY_NO_GC_FRONT),1)
GAME_CPPFLAGS += -DRE4DC_NMR_NO_GC_FRONT=1
endif
# LEON_NO_GC_FRONT=1 (lane cast-ps2-25 2026-10-25; default 0; render only; needs NATIVE_MODEL_REGISTRY_NO_GC_FRONT=1):
#   the same rule for Leon (pPL). On r100's first frames after the s20 movie the source ledger is not active
#   (re4dc_actor_transaction_identity 0), so Leon was not a transaction candidate and trans.cpp ModelRender drew him GC
#   through frontNativeRender (GC-ASSET r100: his weapon hand BIN ef82164d). Those frames draw no Leon. The macro is
#   always defined (0 / 1 / 2) so the check sits on an existing source line: knob off, the image is unchanged.
# LEON_NO_GC_FRONT=2 (round 4): Leon's PS2 owner also plans without the source ledger (source_actor_owner_hooks.inc):
#   on images with no coarse ledger (those r100 frames) the player draws PS2, not nothing. The =1 guard stays.
LEON_NO_GC_FRONT ?= 0
ifeq ($(filter $(LEON_NO_GC_FRONT),0 1 2),)
$(error LEON_NO_GC_FRONT must be 0, 1 or 2)
endif
ifneq ($(LEON_NO_GC_FRONT),0)
ifneq ($(NATIVE_MODEL_REGISTRY_NO_GC_FRONT),1)
$(error LEON_NO_GC_FRONT=$(LEON_NO_GC_FRONT) needs NATIVE_MODEL_REGISTRY_NO_GC_FRONT=1)
endif
endif
GAME_CPPFLAGS += -DRE4DC_LEON_NO_GC_FRONT=$(LEON_NO_GC_FRONT)
# NATIVE_MODEL_REGISTRY_GRAB_FULL=1 (lane castlerender19 2026-10-19; default 0; render only; needs
#   NATIVE_MODEL_REGISTRY_LOD=1): registry_lod_want also draws the full descriptor while the player runs the custom
#   damage routine this actor started (pl_sub.cpp SetPlDamage: routine 0 == 4, dmgType = the enemy). r221 Verdugo's
#   grab, kick, tail and critical hit (em2c.cpp 4601 / 5040 / 5083 / 5100) never set the event bit
#   Status_flg[1] 0x10000000, so they drew the gameplay level. Knob off: the image is unchanged.
NATIVE_MODEL_REGISTRY_GRAB_FULL ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_GRAB_FULL),1)
ifneq ($(NATIVE_MODEL_REGISTRY_LOD),1)
$(error NATIVE_MODEL_REGISTRY_GRAB_FULL=1 needs NATIVE_MODEL_REGISTRY_LOD=1)
endif
GAME_CPPFLAGS += -DRE4DC_NMR_GRAB_FULL=1
endif
# NATIVE_MODEL_REGISTRY_OT5=1 (lane castlerender19 2026-10-19; default 0; render only): the registry certificate also
#   admits ot_type 5 for the r221 Verdugo (em2c, model 0x2c; em2c.cpp 1144). trans.cpp ModelTrans case 5 registers the
#   same ModelRender callback once, AddOtDirect(0x10, m, ModelRender, 0, 2): one source call per frame at OT 0x10,
#   like ot_type 0 / 1, and the owner path draws inside that callback, so the source order is kept. Other models keep
#   the ot_type 5 refusal. Knob off: the image is unchanged.
NATIVE_MODEL_REGISTRY_OT5 ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_OT5),1)
GAME_CPPFLAGS += -DRE4DC_NMR_OT5=1
endif
# PS2_ASHLEY=1|2 (lane ps2cast 2026-10-14; default 0; render only): Ashley (pl11, the partner pSUB, model id 3; r117
#              first) through the registry owner path with her PS2 mesh (tools/ps2_ashley.py: PS2 geometry / UVs / weights,
#              the PS2 cloth influences moved onto the GC cloth links the source solver already moves - no second solver,
#              no extra PenCloth call, no game RNG). Her GC skeleton has 141 joints (parents > 127, more than any registry
#              capacity), so the package carries a draw-slot descriptor (RE4DC_NMR_SLOTS; model_registry.py --slots): the
#              skeleton proof walks and checks all 141 source joints (parent + rest inverse) in a 255-entry scratch list,
#              the binding keeps the 64 drawn joints as slots (the recipe's kRegBones 64 holds them: PS2_GIGANTE pins 64
#              outside ROUTE_CH23; ps2_ashley.py folds the six lightest GC skirt links into their parents), every other capacity is
#              unchanged. Also: the partner nomination for pSUB id 3 (source_actor_owner_hooks.inc), 32 source texture facts
#              per package / 17 per role (pl11 TPL 5), 10 source BIN models (three setHand sets: one descriptor each), 72
#              source part facts, and a 256 KiB package + skin ceiling (the loader allocates the actual size: the r117
#              package is 229,952 B, heap-4 arena 239,656 B; the texture-prepared pl11.drs frees 241,408 B of resident
#              archive). Static cost (warp arm): +288 B of coarse_actor.o character data (inside its 16 KiB padding slack), _end +960 B.
#              =1: everything above, but the head info keeps its shape bit (be_flag 2), so the transaction declines her
#              (actor_semantics clause 20) and she stays on the source path: a proof / census build only.
#              =2: also admits the head (role 1, BIN 7) drawn at the PS2 rest face: her GC face expressions (setFace shapes
#              0x6C / 0x6D) are not shown. USER LOOK DECISION PENDING; not for a release before that decision.
#              Needs NATIVE_MODEL_REGISTRY_PACK=1, MASK=1 (head / hair / extra 9 mask runs) and the bump drop rule
#              (RE4DC_NMR_DROP_BUMP, set here: the DC source path never draws the GC bump stage). Disc data:
#              dc/native/r117/registry.re4nmr + its atlas and three pair packages; pl/pl11.drs must be texture-prepared.
#              Not with NATIVE_MODEL_REGISTRY=2 (compare mode).
#              Runtime (2026-10-15, Flycast census, r117 follow warp): =2 admits her on every drawn frame (2400/2400,
#              0 declines, TEX_CHECK 0 fails) after four fixes: four owner materials (atlas + three mask pairs;
#              RE4DC_ACTOR_MATERIALS=4 below), her source TEV group 1 (as Luis), the head's shape bit / Morph need and
#              the bump drop in the certificate (coarse_actor_material.inc), and the slot palettes' bind (one inverse
#              per SOURCE joint: slot b uses its joint's; coarse_actor_owner_registry.inc registry_palettes).
PS2_ASHLEY ?= 0
# Ashley's PS2 bind and authored weights, with the existing game cloth simulation
# adapted by tools/ps2_ashley.py --rig. Private rig headers pin all three hand sets.
ASHLEY_PS2_RIG ?= 0
ASHLEY_PS2_RIG_DIR ?=
ifeq ($(filter $(ASHLEY_PS2_RIG),0 1),)
$(error ASHLEY_PS2_RIG must be 0 or 1)
endif
ifeq ($(ASHLEY_PS2_RIG),1)
ifneq ($(PS2_ASHLEY),2)
$(error ASHLEY_PS2_RIG needs PS2_ASHLEY=2)
endif
ifeq ($(strip $(ASHLEY_PS2_RIG_DIR)),)
$(error ASHLEY_PS2_RIG needs ASHLEY_PS2_RIG_DIR from tools/d367/ashley_rig27/rig_header.py)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ASHLEY_PS2_RIG=1 -I$(ASHLEY_PS2_RIG_DIR)
$(OBJDIR)/coarse_actor.o: $(ASHLEY_PS2_RIG_DIR)/ashley_ps2_rig27.h
endif
ASHLEY_LOD ?= 0
ifeq ($(filter $(ASHLEY_LOD),0 1),)
$(error ASHLEY_LOD must be 0 or 1)
endif
# Playable cPlAshley has its own player-family/archive contract. It must never
# inherit the partner's model3 predicate or distance LOD policy.
ASHLEY_PLAYABLE_PS2_RIG ?= 0
ASHLEY_PLAYABLE_PS2_RIG_DIR ?=
ifeq ($(filter $(ASHLEY_PLAYABLE_PS2_RIG),0 1),)
$(error ASHLEY_PLAYABLE_PS2_RIG must be 0 or 1)
endif
ifeq ($(ASHLEY_PLAYABLE_PS2_RIG),1)
ifneq ($(PS2_ASHLEY)$(NATIVE_MODEL_REGISTRY_PL_ASHLEY),21)
$(error ASHLEY_PLAYABLE_PS2_RIG needs PS2_ASHLEY=2 NATIVE_MODEL_REGISTRY_PL_ASHLEY=1)
endif
ifeq ($(strip $(ASHLEY_PLAYABLE_PS2_RIG_DIR)),)
$(error ASHLEY_PLAYABLE_PS2_RIG needs ASHLEY_PLAYABLE_PS2_RIG_DIR from tools/d367/ashley_playable27/rig_header.py)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ASHLEY_PLAYABLE_PS2_RIG=1 -I$(ASHLEY_PLAYABLE_PS2_RIG_DIR)
$(OBJDIR)/coarse_actor.o: $(ASHLEY_PLAYABLE_PS2_RIG_DIR)/ashley_playable_ps2_rig27.h
endif
ifeq ($(ASHLEY_LOD),1)
ifneq ($(ASHLEY_PS2_RIG)$(NMR_POOL_LOD)$(NATIVE_MODEL_REGISTRY_ROLES5),111)
$(error ASHLEY_LOD needs ASHLEY_PS2_RIG=1 NMR_POOL_LOD=1 NATIVE_MODEL_REGISTRY_ROLES5=1)
endif
ifneq ($(NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS),1)
$(error ASHLEY_LOD needs NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ASHLEY_LOD=1
endif
# PS2_ASHLEY_ROOMS=1 (lane ps2cast 2026-10-15; default 0; render only; needs PS2_ASHLEY=1|2): Ashley in the chapter 2-2 /
#              2-3 rooms whose own registry package already carries other PS2 actors (r111 / r113 crows, r112 merchant,
#              r118 Ganados + wolf, r11c Luis, r11f Mendez). Her package is the room's SECOND package,
#              dc/native/r<room>/partner.re4nmr, read and validated with the room's registry.re4nmr before either is
#              published (RE4DC_NMR_PARTNER: pack_validate places the partner's records after the room package's; one
#              view; two heap-4 cells, the room cell holding both skin arenas). A room without registry.re4nmr publishes
#              the partner alone; a refused partner leaves the room package published. Chunk capacity 48 (r112: 14 + 21).
#              Without the knob a partner.re4nmr on the disc is never opened.
#              =2 (lane ashley17 2026-10-17): =1 with a 32-entry registry texture table (was 16). r11c's Luis package has
#              11 textures and Ashley's partner 6: 17 > 16 refused her ("NMRPACK partner refuse room=011c why=table
#              detail=4", rsweep17 x-r11c), so she fell back to the GC path. Cost: 16 more pack_tex (16 B) and
#              registry_tokens (4 B) entries, 320 B bss. =1 is unchanged.
PS2_ASHLEY_ROOMS ?= 0
ifeq ($(filter $(PS2_ASHLEY_ROOMS),0 1 2),)
$(error PS2_ASHLEY_ROOMS must be 0, 1 or 2)
endif
ifneq ($(PS2_ASHLEY_ROOMS),0)
ifeq ($(PS2_ASHLEY),0)
$(error PS2_ASHLEY_ROOMS=$(PS2_ASHLEY_ROOMS) needs PS2_ASHLEY=1 or 2)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_PARTNER=$(PS2_ASHLEY_ROOMS)
endif
ifeq ($(filter $(PS2_ASHLEY),0 1 2),)
$(error PS2_ASHLEY must be 0, 1 or 2)
endif
# NATIVE_MODEL_REGISTRY_PL_ASHLEY=1 (lane castlerender19 2026-10-19, castle item 4; default 0; render only; needs
#   PS2_ASHLEY=2): the typed contract for PLAYABLE Ashley (chapter 3-4: cPlAshley, the player pPL, model id 0, ot_type 7)
#   on the registry owner path. A draw-slot descriptor of model 0 over her complete 141-joint source owner (the cloth
#   owner is kept: no skeleton replacement, no link folding is implied here) with seven sections admits:
#   - the face, role 1 = BIN 7 / TPL 9 (Body->pShape, be_flag 2), as PS2_ASHLEY=2 admits the partner's head: drawn at
#     the package's rest face while the source ShapeMove still runs (playable setFace is a no-op in the source);
#   - the skirt, role 3 = BIN 8 / TPL 5, with its source be_flag 0x40 (cPlAshley::setModel): the transaction draws it in
#     the ot_type 7 second pass (m->be_flag 0x08000000), as trans.cpp does.
#   Every other role keeps the plain certificate; a 0x40 or shape bit on any other role or ordinal still declines.
#   Leon (model 0, 119 joints) never matches the descriptor. No package exists yet (castle18 owns the pl01 conversion):
#   without one the knob changes nothing at runtime. Knob off: the image is unchanged.
NATIVE_MODEL_REGISTRY_PL_ASHLEY ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_PL_ASHLEY),1)
ifneq ($(PS2_ASHLEY),2)
$(error NATIVE_MODEL_REGISTRY_PL_ASHLEY=1 needs PS2_ASHLEY=2)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_PL_ASHLEY=1
endif
ifneq ($(PS2_ASHLEY),0)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK)$(NATIVE_MODEL_REGISTRY_MASK),11)
$(error PS2_ASHLEY needs NATIVE_MODEL_REGISTRY_PACK=1 and NATIVE_MODEL_REGISTRY_MASK=1)
endif
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_BONES),64 80 96 128),)
$(error PS2_ASHLEY needs NATIVE_MODEL_REGISTRY_BONES >= 64 (64 draw slots))
endif
ifeq ($(NATIVE_MODEL_REGISTRY),2)
$(error PS2_ASHLEY is not modelled by NATIVE_MODEL_REGISTRY=2 (compare mode))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_ASHLEY=$(PS2_ASHLEY) -DRE4DC_NMR_SLOTS=1 -DRE4DC_NMR_DROP_BUMP=1 -DRE4DC_NMR_FACTS=72
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_NMR_ASHLEY=$(PS2_ASHLEY)
# Her descriptors plan four materials (the PS2 atlas + head / hair / extra 9 mask pairs; the default owner capacity is
# three, which declined her at the third mask run: census NMRD plan=). Every object, as the plan crosses objects.
GAME_CPPFLAGS += -DRE4DC_ACTOR_MATERIALS=4
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_MATERIALS=4
else
ifneq ($(PS2_CAST_MERCHANT),0)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_FACTS=40
endif
endif

# ACTOR_PROOF_LEAN (default 0; needs ACTOR_TRANSACTION=1; render only; independent of the registry knobs): one actor
# transaction proves each thing once, for Leon, the Ganado cast and registry plans alike. The decisions are the =0
# decisions:
#   - the pass that acquired the actor in the SAME re4dc_actor_transaction_draw call keeps its pre-acquire
#     actor_semantics verdict and the modelviews actor_acquire computed, while the lifetime serial (life::next: adopt,
#     retire, revoke, forget, stream pending, binding refresh) has not moved since that verdict; a later pass (Leon's
#     second OT group) and any lifetime change run the whole proof (coarse_actor_transaction.inc has the audit);
#   - the material certificate looks up each role's current row once per evaluation: the owner proof is implied by the
#     unique current row, and the Ganado run loop and source material reuse it (coarse_actor_material.inc).
#   Role rows are held per plan info slot (sizeof Re4dcActorPlan::info), not a fixed role count.
#   =2: compare build: the =0 proofs also run and decide; "APL" lines (every 600 frames) count every reuse and how often
#   the =0 result differed (semantics_bad, mv_bad, owner_bad, rows_bad, materials_bad must be 0). Not with
#   NATIVE_MODEL_REGISTRY_TX=2 (a separate compare build).
ACTOR_PROOF_LEAN ?= 0
ifeq ($(filter $(ACTOR_PROOF_LEAN),0 1 2),)
$(error ACTOR_PROOF_LEAN must be 0, 1 or 2)
endif
ifneq ($(ACTOR_PROOF_LEAN),0)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_PROOF_LEAN acts on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_PROOF_LEAN=$(ACTOR_PROOF_LEAN)
endif

# ACTOR_MATERIAL_RECORD (default 0; private prototype; needs ACTOR_PROOF_LEAN=1; render only): the material
# certificate keeps, per model (16 records, 44 bytes each), what is fixed while the lifetime epoch is unchanged: each
# role's lifetime record slot and unique current row and info()'s archive verdict (TPL descriptors / headers / R4xREF
# / CLUT and ModelPart header bytes inside the owner archives) with its required bits. Every adopt / retire / revoke /
# forget / room rows publish or retire / swap park or unpark moves the epoch (life::changed); a hit also needs each
# plan info in the model's list and info_current() true for its row now. Everything else (model and info modifiers,
# ModelData header, shapes, gxCsScale, frame owner, registry model / runs, source materials, plan materials,
# capability) is evaluated every time. coarse_actor_material.inc has the audit. The decisions are the =0 decisions.
#   =2: compare build: the whole certificate also runs and decides; "AMR" lines (every 600 frames) count evaluations,
#   hits, stores and hits whose result differed (bad must be 0).
ACTOR_MATERIAL_RECORD ?= 0
ifeq ($(filter $(ACTOR_MATERIAL_RECORD),0 1 2),)
$(error ACTOR_MATERIAL_RECORD must be 0, 1 or 2)
endif
ifneq ($(ACTOR_MATERIAL_RECORD),0)
ifneq ($(ACTOR_PROOF_LEAN),1)
$(error ACTOR_MATERIAL_RECORD extends the ACTOR_PROOF_LEAN=1 certificate (ACTOR_PROOF_LEAN=1))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_MATERIAL_RECORD=$(ACTOR_MATERIAL_RECORD)
endif

# LEON_NATIVE_PIPE (default 0; lane ln 2026-10-05 experiment; needs ACTOR_TRANSACTION=1 and COARSE_ONE_SUBMIT=1; render
# only, exact): Leon (pl00) through the owner transaction with what it repeats done once (coarse_actor_leon_pipe.inc,
# platform/include/native_actor_leon_pipe.inc): one owner_leon_bind per pass-1 call with its finite test as one exponent
# sweep; the plan and the record's fixed parts kept per binding; actor_semantics' fixed terms (immutable chunk proofs,
# counts, bytes, run order) proved once per plan, its per-frame terms and the live certificate in every pass; the
# palette finite scan replaced by a sufficient bound on the bone matrices (outside it the scan decides); the run
# preflight's fixed terms proved once per plan by the full preflight, then its per-frame terms per material (pass 1's
# submission does not repeat acquisition's); one_chunk takes the lease's registry entry instead of one_qualifies; the
# hair's material changes inside one store-queue window (native_ui.cpp re4dc_leon_direct_switch: the same header
# words and counters as closing and reopening). Same leases, allocations, ledger choices, kernels, inputs and order:
# the TA receives the same words. Not with the transaction diagnostic / census / compare builds.
LEON_NATIVE_PIPE ?= 0
ifeq ($(filter $(LEON_NATIVE_PIPE),0 1),)
$(error LEON_NATIVE_PIPE must be 0 or 1)
endif
ifneq ($(LEON_NATIVE_PIPE),0)
ifneq ($(ACTOR_TRANSACTION)$(COARSE_ONE_SUBMIT),11)
$(error LEON_NATIVE_PIPE acts on the ACTOR_TRANSACTION owner path with COARSE_ONE_SUBMIT=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_NATIVE_PIPE=$(LEON_NATIVE_PIPE)
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_LEON_NATIVE_PIPE=$(LEON_NATIVE_PIPE)
endif

# Private r11f v2 packages may alias complete immutable position/normal/UV/weight
# arrays with equal kind/count/stride/palette/bone context. Geometry identities,
# every mutable stream, skin work and source facts remain separate. v1 unchanged.
# The paired package is mandatory: old images reject v2 and use source fallback.
NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS ?= 0
ifeq ($(filter $(NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS),0 1),)
$(error NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS must be 0 or 1)
endif
ifeq ($(NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS),1)
ifneq ($(NATIVE_MODEL_REGISTRY_PACK),1)
$(error NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS needs NATIVE_MODEL_REGISTRY_PACK=1)
endif
ifneq ($(ROUTE_CH23),1)
$(error NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS is qualified only for ROUTE_CH23 r11f)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_IMMUTABLE_ALIAS=1
endif

# OT_PROF=1 (lane cast16 2026-10-17; diagnostic, default 0): per OT callback CPU time and PVR stream bytes (OTP lines
#              every 120 UI frames; trans_ot.cpp ExecOt). Knob off: the image is unchanged.
OT_PROF ?= 0
ifeq ($(OT_PROF),1)
GAME_CPPFLAGS += -DRE4DC_OT_PROF=1
PLATFORM_CPPFLAGS += -DRE4DC_OT_PROF=1
endif
# TEX_PKG_SKIP=1 (lane cast16 2026-10-17; render only, default 0; needs NATIVE_MODEL_REGISTRY_PACK): the room-entry
#              preload (enemy pass and resident list) skips the GC TPL textures that the published room package's role
#              rows name (its descriptors draw their own atlas); a source-path draw still loads one on first sight.
#              Logs TEXPKG lines. Knob off: the image is unchanged.
TEX_PKG_SKIP ?= 0
ifeq ($(TEX_PKG_SKIP),1)
GAME_CPPFLAGS += -DRE4DC_TEX_PKG_SKIP=1
PLATFORM_CPPFLAGS += -DRE4DC_TEX_PKG_SKIP=1
endif
# TEX_PKG_SKIP_LISTED=1 (lane castlerender19 2026-10-19; render only, default 0; needs TEX_PKG_SKIP=1): VRAM rule. A key of
#              the room's own resident list (dc/resident.bin, room != 0: a texture the room's scenes loaded on first
#              sight) is preloaded at room entry even when a package role row names it. Registry actors still draw
#              those source textures on some frames (r207: the inventory open drew 16 zealot / Ashley role TPLs from
#              disc in play). The enemy pass and core keys keep TEX_PKG_SKIP. Logs "TEXPKG listed kept=". Knob off:
#              the image is unchanged.
TEX_PKG_SKIP_LISTED ?= 0
ifeq ($(TEX_PKG_SKIP_LISTED),1)
ifneq ($(TEX_PKG_SKIP),1)
$(error TEX_PKG_SKIP_LISTED=1 needs TEX_PKG_SKIP=1)
endif
PLATFORM_CPPFLAGS += -DRE4DC_TEX_PKG_SKIP_LISTED=1
endif
# NATIVE_MODEL_REGISTRY_DYING=1 (lane cast16 2026-10-17; render only, default 0): a Ganado-class enemy (Ganado cast or registry plan)
#              (ids 0x10..0x20) keeps its PS2 plan while its whole-model fade runs (death: invisible_factor < 1), drawn
#              through ACTOR_GANADO_DEATH_FADE's G1 ticket (its source FIFO position, TR list, the source alpha) instead
#              of declining to the GC path (CAST-GC "semantics"). Compiles the G1 machinery; the reviewed id13 G1
#              eligibility stays off unless ACTOR_GANADO_DEATH_FADE=1 too. Knob off: the image is unchanged.
# NATIVE_MODEL_REGISTRY_RUN_SHARE=1 (lane cast16 2026-10-17; render only, default 0): an identical pool mask run drawn by
#              two sections whose role chunks hold byte-identical arrays shares its immutable proof (the r218 em1c 09h
#              0x217 colours 0x218 / 0x219; before, the second section declined, semantics 24). Knob off: unchanged.
NATIVE_MODEL_REGISTRY_RUN_SHARE ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_RUN_SHARE),1)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_RUN_SHARE=1
endif
# NATIVE_MODEL_REGISTRY_BLENDTBL=1 (lane cast16 2026-10-17; render only, default 0): a registry actor whose info holds an
#              idle texture blend table (flagsDC 4, blendRatio 0, blendType 0: the source draws the base textures) keeps
#              its plan: the castle Novistador em2d (r213 / r21d declined on semantics 16 every frame). Knob off: unchanged.
NATIVE_MODEL_REGISTRY_BLENDTBL ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_BLENDTBL),1)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_NMR_BLENDTBL=1
endif
NATIVE_MODEL_REGISTRY_DYING ?= 0
ifeq ($(NATIVE_MODEL_REGISTRY_DYING),1)
ifneq ($(NATIVE_MODEL_REGISTRY)$(ACTOR_TRANSACTION)$(D349_RENDERER_STACK)$(PVR_STREAM)$(NATIVE_ACTOR_SKIN_LAZY)$(SKIN_PALETTE_LAZY)$(PS2_GANADO_LIT),1111111)
$(error NATIVE_MODEL_REGISTRY_DYING requires NATIVE_MODEL_REGISTRY=1 ACTOR_TRANSACTION=1 D349_RENDERER_STACK=1 PVR_STREAM=1 NATIVE_ACTOR_SKIN_LAZY=1 SKIN_PALETTE_LAZY=1 PS2_GANADO_LIT=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_GANADO_DEATH_FADE=1 -DRE4DC_NMR_DYING=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_GANADO_DEATH_FADE=1
endif
# PROP_PROF=1 (lane cast16 2026-10-17; diagnostic, default 0): re4dc_model_submit time / bytes per model and route
#              (PPF lines). Knob off: the image is unchanged.
PROP_PROF ?= 0
ifeq ($(PROP_PROF),1)
GAME_CPPFLAGS += -DRE4DC_PROP_PROF=1
PLATFORM_CPPFLAGS += -DRE4DC_PROP_PROF=1
endif
# PROP_PLAN=1 (lane cast16 2026-10-17; render only, exact, default 0): rigid parts whose model box is wholly outside
#              one clip plane are not submitted (model_bridge.cpp pplan). Knob off: the image is unchanged.
PROP_PLAN ?= 0
ifneq ($(PROP_PLAN),0)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_PROP_PLAN=$(PROP_PLAN)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_PROP_PLAN=$(PROP_PLAN)
endif
# PROP_PLAN=2 (diagnostic): submit the parts PROP_PLAN would skip and count any that emit bytes (PPLAN bad=, must be 0).
# PROP_GATE=1 (lane farmprop17 2026-10-17; render only, exact, default 0; needs SCENERY_GATE, FRONT_LEAN (FRONT_NATIVE),
#              SKIN_PALETTE_LAZY, NATIVE_ACTOR_SKIN_LAZY and ACTOR_FOG_GATE): a lazily skinned room object (cObj kind 1;
#              the r103 farm props) whose whole bound lies beyond the native actor fog gate's cull depth skips its part
#              walk (trans.cpp propGate) instead of preparing every part's skinned frame only to cull it. Logs PGATE lines.
#              =2 (check build): the walk runs anyway; PGATE bad= counts parts of gated models not culled by the fog gate
#              (must be 0). Knob off: the image is unchanged.
PROP_GATE ?= 0
ifneq ($(PROP_GATE),0)
ifneq ($(PROP_GATE),1)
ifneq ($(PROP_GATE),2)
$(error PROP_GATE must be 0, 1 or 2)
endif
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PROP_GATE=$(PROP_GATE)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_PROP_GATE=$(PROP_GATE)
endif
