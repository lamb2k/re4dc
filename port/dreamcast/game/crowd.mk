# D367 lane crowd (2026-09-30): Ganado draw cost and crowd draw policy on the ACTOR_TRANSACTION owner path
# (coarse_actor_transaction.inc, coarse_actor_owner_ganado.inc). All default off: no -D is added and the
# default image is unchanged. Render only: every Ganado still exists, moves, animates its skeleton and collides
# exactly as before (logic trace STRICT); these knobs only decide whether its cast mesh is skinned and submitted.
#
# CROWD_CULL=1 (exact, look unchanged): a Ganado whose every visible chunk is provably off-screen (COARSE_PREGATE's
#              per-bone balls against the actor path's culling planes: a screen edge, or a far plane at the fog
#              gate's cull depth, the fogged View far, which the GC clips) is not
#              acquired: no bones, palettes, texture pins, preflight or submission. re4dc_actor_submit would have
#              emitted nothing for it, so the image is the same. Applies only after the owner path admitted the
#              actor (plan + semantics), so no Ganado changes path. =2 check build: nothing is skipped; each actor the
#              cull would skip must emit no triangle over both passes ("CROWDCULL" lines: violations must stay 0).
# CROWD_CENSUS=1 (diagnostic): one "CROWDC" line per frame in the UI-frame window CROWD_CENSUS_FROM..TO: Ganados
#              seen by the owner path, admitted, culled off-screen, drawn, drawn with no output, distance bands.
# CROWD_DRAW_MAX=N (look change, user's call; -1 = off): at most N Ganados drawn a frame, the nearest by the previous
#              frame's camera distances among those the cull keeps; the rest are not drawn (still simulated).
# CROWD_DRAW_M=D (look change, user's call; 0 = off): Ganados farther than D metres from the camera are not drawn.
# CROWD_READOPT=1 (fix; look change vs today's play build): a Ganado info with no live material-lifetime record is
#              proved again (the load-time proof) when its actor plans, so it stops falling back to the source path.
#              =1 Ganados only; =2 Ganados and Leon (Leon then also leaves the lit source path for the flat owner path).
# CROWD_FOGSKIP=1 (look change, user's call): a Ganado whose root is more than 2.5 m beyond the fogged View far
#              (where the GC clips) is not drawn; the actor path otherwise emits some of them fully fogged.
# CROWD_FAR_M=D (look change, user's call; 0 = off): a Ganado farther than D metres draws the far tier (the external
#              cast's lighter v4-fit level, ganado_far_runtime.h in the asset dir: tools/d367/crowd/far_header.py).
# CROWD_NEAR_MAX=N (look change, user's call; -1 = off): only the N nearest Ganados (previous frame's distances among
#              those drawn) draw the near tier; the rest draw the far tier. Either knob sets RE4DC_CROWD_FAR.
# CROWD_FREEZE_AT=N (look sheets only): the CPU stops in game frame N's first owner draw; frame N-1 stays on screen.
#              CROWD_FREEZE_HOLD=S: resume after S seconds (0 = never); CROWD_FREEZE_AT2=M: hold again at frame M.
#
# ACTOR_APPEARANCE_ALIAS=1 (native scene coverage, 2026-10-03; default 0): the owner path also admits the Ganado
#              (module, model type) pairs listed in actor_appearance_aliases.inc, which tools/native_appearance_alias.py
#              generates only for types whose EmXXSet loads byte-identical source entries (every model slot mot[0..20]
#              and every reachable role BIN/TPL) to an already certified appearance: em12 types 0/3/4 = the em15
#              type 0/3/4 casts (r100, r103). Every role/owner/material/semantics proof still runs per draw; gore,
#              unknown hands, fades and other states still fall back to the source path. Render only.
#              Every enabled row is rendered with the owner path's Ganado lighting (see ACTOR_GANADO_SOURCE_LIGHT).
#              =2 (native scene coverage extension, 2026-10-03): the same check, reading actor_appearance_aliases_ext.inc
#              (the same generator, --knob 2: em12 0/3/4, em13 0/1/3/4, em16 3/4, em17 0/1/3, em10 0/3/4; em16 11 and
#              em10 1 are held out because their sack accessory differs from the certified type's).
# ACTOR_GANADO_SOURCE_LIGHT=1 (native look fidelity, 2026-10-03; default 0; look change vs today's play build, the
#              user's call): every Ganado drawn by the owner path (appearances 0..4, Leon excluded) is lit with the
#              source's own GX lighting (LightSetModel's lights / channel / ambient / material, nrm = part.mv^-T,
#              TEV scale gxCsScale) through the existing lit kernel instead of the approved flat constant colour.
#              A Ganado whose roles disagree on matrix or material colour, or that uses vertex colour sources,
#              falls back to the source path (ATD 26). Specular is still omitted, as in the flat look. Render only.
#              (Hunk copied from the sup-native-scene worker's helper; with NATIVE_MODEL_REGISTRY it also lights
#              the registry descriptors: every non-Leon plan.)
ACTOR_APPEARANCE_ALIAS ?= 0
ACTOR_GANADO_SOURCE_LIGHT ?= 0
ifeq ($(filter $(ACTOR_APPEARANCE_ALIAS),0 1 2),)
$(error ACTOR_APPEARANCE_ALIAS must be 0, 1 or 2)
endif
ifeq ($(filter $(ACTOR_GANADO_SOURCE_LIGHT),0 1),)
$(error ACTOR_GANADO_SOURCE_LIGHT must be 0 or 1)
endif
ifeq ($(ACTOR_APPEARANCE_ALIAS),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_APPEARANCE_ALIAS acts on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_APPEARANCE_ALIAS=1
endif
ifeq ($(ACTOR_APPEARANCE_ALIAS),2)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_APPEARANCE_ALIAS acts on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_APPEARANCE_ALIAS=2
endif
# ACTOR_PL08=1 (native scene coverage, 2026-10-04; default 0): the no-jacket Leon (pl08.drs, NINE source infos) on the
#              ACTOR_TRANSACTION owner path (coarse_actor_owner_pl08.inc). Plans only when the 0x108 role rows
#              (actor_material_records_pl08*.inc, generated from the original pl08.drs) prove all nine infos; otherwise the
#              whole model keeps the source path. Role capacity 8 -> 9 and owner runs 21 -> 22 for every TU (layouts with
#              0 unchanged). ACTOR_PL08_DIR = private dir with leon_pl08_runtime.h; the disc must carry the pl08 atlas
#              dc/tex/7/7506e95f-68cf2211.re4tex (else the texture lease declines and the source path draws).
# ACTOR_PL08_PACK=1 (2026-10-04; default 0; needs ACTOR_PL08=1 and NATIVE_STATIC=1): the three pl08-only immutable chunks
#              (roles 0 / 1 / 8, 33,916 B) are not compiled in. They are read from dc/native/pl08/leon_pl08.re4cp
#              (tools/d367/pl08_pack.py from the frozen leon_pl08_runtime.h) into one heap-4 room cell only while the
#              bound player archive is pl08 (ReadPlayerData file 0x5A), validated against actor_pl08_pack_identity.inc
#              (every field and array hash) and preflighted before anything publishes; retired at room leave, unpublished
#              by a bind away from pl08 (coarse_actor_pl08_pack.inc, actor_pl08_pack_check.inc). Missing or refused:
#              pl08 keeps the whole source path. ACTOR_PL08_DIR is not used.
ACTOR_PL08_PACK ?= 0
ACTOR_PL08 ?= 0
# LEON_HAND_POSES=1 (issue #26, 2026-10-13; default 0: no effect; render only): Leon (pl00 0x100 / pl08 0x108) keeps the
#              PS2 owner path in every hand pose. The player's current right / left hand infos (cPlBody pRight / pLeft:
#              setRightHand / setLeftHand, weapon grips, the empty hand, the r10b boat hand) are roles 5 / 6 whatever
#              pose data they show, in any source info order (a swap re-appends its info at the end of the list);
#              the certificate checks their live state and the player hand TPL against the standard hand row, not
#              the pose geometry; the plan draws the PS2 hand of that pose (LEON_HAND_DIR's ps2leon_hands.h) or the
#              PS2 standard hand when the pose has none. Before: any hand other than the handgun grip (wep02/10) and
#              the left grip pl00/24 sent the whole Leon to the GameCube body until the next room load.
#              LEON_HAND_DIR: the private dir with ps2leon_hands.h (tools/d367/ps2leon/build_hands.py); unset = the
#              PS2 standard hands for every pose.
LEON_HAND_POSES ?= 0
LEON_HAND_DIR ?=
ifeq ($(filter $(LEON_HAND_POSES),0 1),)
$(error LEON_HAND_POSES must be 0 or 1)
endif
ifeq ($(LEON_HAND_POSES),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error LEON_HAND_POSES acts on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_HAND_POSES=1
ifneq ($(LEON_HAND_DIR),)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_HAND_TABLE=1 -I$(LEON_HAND_DIR)
$(OBJDIR)/coarse_actor.o: $(LEON_HAND_DIR)/ps2leon_hands.h
endif
endif
# LEON_OT_WATER=1 (castle lane 2026-10-15; default 0: no effect; render only; needs LEON_HAND_POSES=1): the player's
#              model also keeps the PS2 owner path at ot_type 5. R205Main and R229Main (src/st2) set pPL->ot_type = 5
#              (the water ordering table) every frame, so before this Leon went to the GameCube body for the whole
#              room (cx32c r205: LEONGC why=4, NMRS id=00 ot=5 declined 1199/1200). The native path draws its own TA
#              lists, so ot 5 is drawn as the ot 0 ride case already is: one pass, every part.
#   =2 (lane ch4found16 2026-10-16): also ot_type 1, which R219Init sets for the player for the whole room (cxc4amW
#              r219: LEONGC why=4, NMRS id=00 ot=1 declined 600/600); =1 images are unchanged.
LEON_OT_WATER ?= 0
ifeq ($(filter $(LEON_OT_WATER),0 1 2),)
$(error LEON_OT_WATER must be 0, 1 or 2)
endif
ifneq ($(LEON_OT_WATER),0)
ifneq ($(LEON_HAND_POSES),1)
$(error LEON_OT_WATER needs LEON_HAND_POSES=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_OT_WATER=$(LEON_OT_WATER)
endif
# LEON_HAND_PACK=1 (issue #26 follow-up, 2026-10-13; default 0: no effect; render only; needs LEON_HAND_POSES=1, PS2_LEON=1,
#              ACTOR_PL08=1, no LEON_HAND_DIR): the hands with no image growth. Every hand pose of the outfit, the
#              standard hands included, is the disc package dc/native/pl00/leon_hands_pl00.re4hp (tools/d367/ps2leon/
#              hands_pack.py pack; pl08's hands are byte-identical to pl00's); the image keeps two fixed draw slots
#              (6,144 + 6,400 B) instead of the standard hands' arrays (hands_pack.py derive builds the arm header
#              without them) and a 1.6 KB directory. A 4-cell cache in AICA RAM (25,088 B: per side the home pose, pl00
#              arc 0x12 / 0x14, and the last other pose) makes real-time swaps a G2 copy; prefetch at room load and at
#              each weapon equip (ReadWepData); other poses are read from the disc when first drawn. The cells are
#              freed at movie open (the stream takes the whole 64 KiB movie reserve) and before a runtime sound bank
#              conversion, and refilled on the next Leon draw (coarse_actor_leon_hands.inc).
# LEON_SKIN_SLOTS=1 (issue #26, 2026-10-13; default 0: no effect; render only): the per-frame skin registry
# (platform/native_actor_fast.cpp kSkins) holds 80 entries instead of 64 (+960 B). r119, the first frame after movie
# 11900: 64 skins were registered before Leon's transaction asked for its 9, the lease declined and Leon went to the
# GameCube path (MCHECK_LEONGC: acq=14 / SKINACQ why=4). Knob-off and pack-off arms showed the same.
# LEON_SKIN_SLOTS=2 (lane fix18 item 9, 2026-10-18; render only): kSkins sized to the measured r119 peak plus a margin
# (see native_actor_fast.cpp). r119 frames 945-1011 of the fight filled all 80 (SKINACQ why=4) and Leon + El Gigante
# went MIXED (GC) for 66 frames.
LEON_SKIN_SLOTS ?= 0
ifeq ($(filter $(LEON_SKIN_SLOTS),0 1 2),)
$(error LEON_SKIN_SLOTS must be 0, 1 or 2)
endif
ifneq ($(LEON_SKIN_SLOTS),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_LEON_SKIN_SLOTS=$(LEON_SKIN_SLOTS)
endif
LEON_HAND_PACK ?= 0
ifeq ($(filter $(LEON_HAND_PACK),0 1),)
$(error LEON_HAND_PACK must be 0 or 1)
endif
ifeq ($(LEON_HAND_PACK),1)
ifneq ($(LEON_HAND_POSES)$(PS2_LEON)$(ACTOR_PL08),111)
$(error LEON_HAND_PACK needs LEON_HAND_POSES=1 PS2_LEON=1 ACTOR_PL08=1)
endif
ifneq ($(LEON_HAND_DIR),)
$(error LEON_HAND_PACK replaces LEON_HAND_DIR: unset LEON_HAND_DIR)
endif
LEON_HAND_PACK_HDR := $(OBJDIR)/leon_hands/ps2leon_runtime_handpack.h
$(LEON_HAND_PACK_HDR): $(PS2_LEON_DIR)/ps2leon_runtime.h ../tools/d367/ps2leon/hands_pack.py
	@mkdir -p $(dir $@)
	python3 ../tools/d367/ps2leon/hands_pack.py derive $< $@
$(OBJDIR)/coarse_actor.o: $(LEON_HAND_PACK_HDR)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_HAND_PACK=1 -I$(OBJDIR)/leon_hands
$(OBJDIR)/src/game/read.o $(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_LEON_HAND_PACK=1
$(OBJDIR)/platform/native_movie.o $(OBJDIR)/platform/audio_aica.o: PLATFORM_CPPFLAGS += -DRE4DC_LEON_HAND_PACK=1
endif
# LEON_HAND_RETAIN=1 (default off): demand-priority two-cell hand retention,
# current-slot/cached reuse and stale-job admission; same package/AICA bytes.
LEON_HAND_RETAIN ?= 0
ifeq ($(filter $(LEON_HAND_RETAIN),0 1),)
$(error LEON_HAND_RETAIN must be 0 or 1)
endif
ifeq ($(LEON_HAND_RETAIN),1)
ifneq ($(LEON_HAND_PACK),1)
$(error LEON_HAND_RETAIN needs LEON_HAND_PACK=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_HAND_RETAIN=1
endif
# LEON_HEADLESS=1 (lane garr18, 2026-10-19; default 0: no effect; render only; needs ACTOR_PL08=1 PS2_LEON=1
#              LEON_HAND_POSES=1 and LEON_HEADLESS_DIR, a space-free private dir holding ps2leon_neck.h from
#              tools/d367/ps2leon/build_neck.py): Leon after his head comes off (cPlLeon::setHead(0): chainsaw / claw /
#              scythe / parasite kills, overseas regions) draws natively. setHead(0) deletes the head shape, hair and eye
#              infos and appends the neck (player arc 0xB, TPL 7): 7 infos, which the 9-role pl08 plan declined, so the
#              whole Leon went to the GameCube path for the death (rule 7). The pl08 owner plans appearance 0x109 instead
#              (actor_material_records_leon_headless_roles.inc: pl08's roles 0..2 / 8, the two hand rows and the neck,
#              GC identity rows from gen_neck_records.py); the neck geometry is the PS2 disc's pl00 arc 0xB (37 triangles,
#              964 B) in arm A's atlas tile of the head.
#              v2 (data set garr18-head-20261019): the flying head the deaths throw (SetObj01(player arc 0xC, TPL 7),
#              cObj01) draws natively as appearance 0x10A. The data set's pl00.drs / pl08.drs (build_head.py) replace arc
#              0xC (55,232 B) by a stub the source loads and never draws plus the PS2 head (1,727 triangles: a face run on
#              Leon's atlas and a hair run on hair material 1) inside the same archive entry (46,720 B: the archive heap
#              shrinks 8,512 B; no static image growth). The aux allowlist row (source_actor_owner_hooks.inc) nominates
#              it; re4dc_stub_payload proves magic / size / CRC. Without the v2 archives the head stays the GC original.
# LEON_HEAD_FORCE_DECLINE=1 (test only, never in a recipe): the head plan always declines (the source path must draw
#              nothing from the stub, and not crash).
LEON_HEADLESS ?= 0
LEON_HEAD_FORCE_DECLINE ?= 0
ifeq ($(LEON_HEAD_FORCE_DECLINE),1)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_HEAD_FORCE_DECLINE=1
endif
ifeq ($(filter $(LEON_HEADLESS),0 1),)
$(error LEON_HEADLESS must be 0 or 1)
endif
ifeq ($(LEON_HEADLESS),1)
ifneq ($(LEON_HAND_POSES)$(PS2_LEON)$(ACTOR_PL08),111)
$(error LEON_HEADLESS needs LEON_HAND_POSES=1 PS2_LEON=1 ACTOR_PL08=1)
endif
ifndef LEON_HEADLESS_DIR
$(error LEON_HEADLESS=1 needs LEON_HEADLESS_DIR (the private dir with ps2leon_neck.h))
endif
GAME_CPPFLAGS += -DRE4DC_LEON_HEADLESS=1
PLATFORM_CPPFLAGS += -DRE4DC_LEON_HEADLESS=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -I$(LEON_HEADLESS_DIR)
$(OBJDIR)/coarse_actor.o: $(LEON_HEADLESS_DIR)/ps2leon_neck.h actor_material_records_leon_neck.inc actor_material_records_leon_headless_roles.inc actor_material_records_leon_head.inc
endif
# AUX_OBJ_NATIVE=1 (lane garr18, 2026-10-19; default 0: no effect; render only; needs ACTOR_TRANSACTION=1): allowlisted
#              ObjMgr objects that are character parts (first row: the Garrador core, em10SetParasite cObj16, id 0x16
#              type 4, 14 parts) take the ordinary actor transaction through their own small per-frame presentation
#              table (platform/include/source_actor_owner_hooks.inc kAuxKinds, 4 entries) instead of the GameCube path.
#              The EmMgr ledger, its counts and the native reserve are unchanged (coordinator 10-19).
AUX_OBJ_NATIVE ?= 0
ifeq ($(filter $(AUX_OBJ_NATIVE),0 1),)
$(error AUX_OBJ_NATIVE must be 0 or 1)
endif
ifeq ($(AUX_OBJ_NATIVE),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error AUX_OBJ_NATIVE acts on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
GAME_CPPFLAGS += -DRE4DC_AUX_OBJ_NATIVE=1
endif
ifeq ($(filter $(ACTOR_PL08),0 1),)
$(error ACTOR_PL08 must be 0 or 1)
endif
ifeq ($(filter $(ACTOR_PL08_PACK),0 1),)
$(error ACTOR_PL08_PACK must be 0 or 1)
endif
ifeq ($(ACTOR_PL08)$(ACTOR_PL08_PACK),01)
$(error ACTOR_PL08_PACK=1 needs ACTOR_PL08=1)
endif
ifeq ($(ACTOR_PL08),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_PL08 acts on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
ifeq ($(ACTOR_PL08_PACK),0)
ifndef ACTOR_PL08_DIR
$(error ACTOR_PL08=1 needs ACTOR_PL08_DIR (the private dir with leon_pl08_runtime.h))
endif
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_PL08=1
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_PL08=1
ifeq ($(ACTOR_PL08_PACK),0)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -I$(ACTOR_PL08_DIR)
$(OBJDIR)/coarse_actor.o: $(ACTOR_PL08_DIR)/leon_pl08_runtime.h coarse_actor_owner_pl08.inc actor_material_records_pl08.inc     actor_material_records_pl08_roles.inc actor_material_records_pl08_blobs.inc
else
ifneq ($(NATIVE_STATIC),1)
$(error ACTOR_PL08_PACK=1 loads into the native static room storage (NATIVE_STATIC=1))
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_PL08_PACK=1
$(OBJDIR)/coarse_actor.o: coarse_actor_owner_pl08.inc coarse_actor_pl08_pack.inc actor_pl08_pack_check.inc actor_pl08_pack_identity.inc     actor_material_records_pl08.inc actor_material_records_pl08_roles.inc actor_material_records_pl08_blobs.inc
endif
endif
ifeq ($(ACTOR_GANADO_SOURCE_LIGHT),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_GANADO_SOURCE_LIGHT acts on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_GANADO_SOURCE_LIGHT=1
endif
# SS_CERT=1 (native scene, 2026-10-04; default 0; needs ACTOR_TRANSACTION=1 and SUBSCREEN=1): room archive
#              certificates survive the sub screen memory swap (actor_swap_park.inc). At open the records of every
#              archive in the 3 MiB window leave the live tables; frees inside the window while it is swapped (heap 12)
#              do not touch them; at close they are published again under new serials only when their bytes hash as
#              at open and nothing retired, replaced or overlapped them meanwhile. Otherwise the source path draws them,
#              as without the knob (first-visit r101: the cow after the entry inventory).
SS_CERT ?= 0
ifeq ($(filter $(SS_CERT),0 1),)
$(error SS_CERT must be 0 or 1)
endif
ifeq ($(SS_CERT),1)
ifneq ($(ACTOR_TRANSACTION)$(SUBSCREEN),11)
$(error SS_CERT=1 needs ACTOR_TRANSACTION=1 and SUBSCREEN=1)
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/sscrn_bridge.o: GAME_CPPFLAGS += -DRE4DC_SS_CERT=1
$(OBJDIR)/coarse_actor.o: actor_swap_park.inc
endif
# SS_CERT_PARTNER_CAPACITY=1: 32 parked source assets for a full Castle monk archive plus Ashley.
# Default off; only storage grows, with all SS_CERT ownership and restore checks unchanged.
SS_CERT_PARTNER_CAPACITY ?= $(if $(filter 1,$(SS_CERT)),1,0)
ifneq ($(words $(SS_CERT_PARTNER_CAPACITY)),1)
$(error SS_CERT_PARTNER_CAPACITY must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(SS_CERT_PARTNER_CAPACITY)),)
$(error SS_CERT_PARTNER_CAPACITY must be 0 or 1)
endif
ifeq ($(SS_CERT_PARTNER_CAPACITY),1)
ifneq ($(SS_CERT),1)
$(error SS_CERT_PARTNER_CAPACITY=1 needs SS_CERT=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_SS_CERT_PARTNER_CAPACITY=1
endif
CROWD_CULL ?= 0
CROWD_CENSUS ?= 0
CROWD_CENSUS_FROM ?= 900
CROWD_CENSUS_TO ?= 1380
CROWD_DRAW_MAX ?= -1
CROWD_DRAW_M ?= 0
CROWD_FREEZE_AT ?= 0
CROWD_FREEZE_AT2 ?= 0
CROWD_FREEZE_HOLD ?= 0
CROWD_READOPT ?= 0
# CROWD_READOPT_MEMO=1 (perf-20261004 candidate 3; render only, exact; needs CROWD_READOPT): a re-adoption proof that
#              failed with its asset current is not run again until the lifetime epoch moves or the info's pData /
#              tpl_addr / TPL descriptor word / asset current() change (actor_lifetime.inc). The r100 h-fight s03
#              corpse (id 0x12) failed it every drawn tick (~0.76 hw ms) and then drew through the source path anyway.
CROWD_READOPT_MEMO ?= 0
ifeq ($(filter $(CROWD_READOPT_MEMO),0 1),)
$(error CROWD_READOPT_MEMO must be 0 or 1)
endif
ifeq ($(CROWD_READOPT_MEMO)$(CROWD_READOPT),10)
$(error CROWD_READOPT_MEMO=1 needs CROWD_READOPT=1 or 2)
endif
# ACTOR_BIND_REUSE=1 (perf-20261004 candidate 11, the 2026-10-04 actor-preparation handover's POC; render only, exact):
#              a Ganado's palette build reuses its plan's owner binding (role search, source BINs) within the same
#              actor transaction when the token, the lifetime serial, the Ganado slot, the live info list and the
#              lifetime binding (read-only) all still match; the finite-matrix scan runs live; any miss runs the full
#              bind (coarse_actor_owner_ganado.inc). =2 check build: the full bind decides, "ABR" lines count hits whose
#              reuse would have differed (bad must be 0).
ACTOR_BIND_REUSE ?= 0
ifeq ($(filter $(ACTOR_BIND_REUSE),0 1 2),)
$(error ACTOR_BIND_REUSE must be 0, 1 or 2)
endif
ifneq ($(ACTOR_BIND_REUSE),0)
ifneq ($(ACTOR_TRANSACTION)$(COARSE_GANADO_CAST),11)
$(error ACTOR_BIND_REUSE acts on the ACTOR_TRANSACTION Ganado cast owner path (ACTOR_TRANSACTION=1 COARSE_GANADO_CAST=1))
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_BIND_REUSE=$(ACTOR_BIND_REUSE)
endif
CROWD_FOGSKIP ?= 0
CROWD_FAR_M ?= 0
CROWD_NEAR_MAX ?= -1
CROWD_KNOBS := $(filter-out 0,$(CROWD_CULL) $(CROWD_CENSUS) $(CROWD_DRAW_M) $(CROWD_FREEZE_AT) $(CROWD_READOPT) $(CROWD_FOGSKIP) $(CROWD_FAR_M)) $(filter-out -1,$(CROWD_DRAW_MAX) $(CROWD_NEAR_MAX))
ifneq ($(strip $(CROWD_KNOBS)),)
ifneq ($(ACTOR_TRANSACTION),1)
$(error CROWD_* knobs act on the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
ifneq ($(COARSE_PREGATE)$(COARSE_GATE_ONCE),11)
$(error CROWD_* knobs reuse the cast Ganado pregate (COARSE_PREGATE=1 COARSE_GATE_ONCE=1))
endif
ifeq ($(filter $(CROWD_CULL),0 1 2),)
$(error CROWD_CULL must be 0, 1 or 2)
endif
CROWD_DEFS := -DRE4DC_CROWD_CULL=$(CROWD_CULL) -DRE4DC_CROWD_CENSUS=$(CROWD_CENSUS) \
  -DRE4DC_CROWD_CENSUS_FROM=$(CROWD_CENSUS_FROM) -DRE4DC_CROWD_CENSUS_TO=$(CROWD_CENSUS_TO) \
  -DRE4DC_CROWD_DRAW_MAX=$(CROWD_DRAW_MAX) -DRE4DC_CROWD_DRAW_M=$(CROWD_DRAW_M) -DRE4DC_CROWD_FREEZE_AT=$(CROWD_FREEZE_AT) -DRE4DC_CROWD_FREEZE_AT2=$(CROWD_FREEZE_AT2) -DRE4DC_CROWD_FREEZE_HOLD=$(CROWD_FREEZE_HOLD) -DRE4DC_CROWD_READOPT=$(CROWD_READOPT) -DRE4DC_CROWD_FOGSKIP=$(CROWD_FOGSKIP) -DRE4DC_CROWD=1 \
  -DRE4DC_CROWD_FAR_M=$(CROWD_FAR_M) -DRE4DC_CROWD_NEAR_MAX=$(CROWD_NEAR_MAX)
ifneq ($(filter-out 0,$(CROWD_FAR_M))$(filter-out -1,$(CROWD_NEAR_MAX)),)
CROWD_DEFS += -DRE4DC_CROWD_FAR=1
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += $(CROWD_DEFS)
ifeq ($(CROWD_READOPT_MEMO),1)
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_CROWD_READOPT_MEMO=1
endif
# The census and the cull check read native_ui.cpp's emitted-triangle total (otherwise a silent missing-symbol stub).
ifneq ($(CROWD_CENSUS)$(filter 2,$(CROWD_CULL)),0)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CROWD_OUTPUT=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_CROWD_OUTPUT=1
endif
endif

# CROWD_INVIS_SKIP=1 (lane iv 2026-10-05; render only, exact; default 0): a Ganado the player cannot see gets no
#              drawing-side work after the game's own view test. ModelTrans (trans.cpp), once AddOt has queued the
#              Ganado (everything that test writes is kept), asks re4dc_invis_decide (coarse_actor_owner_ganado.inc)
#              before the screen matrices. An owner-path Ganado (its last draw admitted the cast plan) is skipped
#              when the crowd policy would cull it anyway (CROWD_FOGSKIP's root test, CROWD_CULL's pregate balls with
#              the fog far plane); the CROWD_LOD ranking then sees the same models. A Ganado whose last draw the owner
#              plan declined (source path) is skipped when every per-bone sphere of its source mesh (all drawn infos,
#              built once from vtxOrig / weights / bind matrices) lies outside one screen edge or the near plane,
#              and every part its draw would hand to the native parts is settled (converted in place, no LOD build
#              waiting: native_actor_fast.cpp re4dc_actor_part_settled), so the skip leaves the part streams and the
#              frame's LOD build budget as the draw would.
#              A skipped Ganado keeps commonScreenMat's texture animation / UV scroll advance; an owner-path one
#              loses its OT entry (as the screen-matrix failure path), a source-path one keeps it and its ModelRender
#              replays only the texture-object cache step (TPL / cTexChg) the source draw would have taken and notes
#              it in the CROWD_LOD ranking as its parts would have (native_actor_fast.cpp re4dc_actor_crowd_note). The view
#              is the next Render's: projection from pG->Cam.ProjMat, viewport and fogged far as the previous Render
#              saw them (the fog only while LightEnv predicts the same value). Never with shadow lights, morphs,
#              render-to-texture or foot shadows (needs FX_LEAN=1).
#              =2 (check build): nothing is skipped; each Ganado the knob would skip must emit 0 triangles in its
#              ModelRender and take the predicted path under the predicted projection / viewport / fog ("INVIS2"
#              lines: violations and mismatches must stay 0).
CROWD_INVIS_SKIP ?= 0
ifeq ($(filter $(CROWD_INVIS_SKIP),0 1 2),)
$(error CROWD_INVIS_SKIP must be 0, 1 or 2)
endif
ifneq ($(CROWD_INVIS_SKIP),0)
ifneq ($(CROWD_CULL)$(FX_LEAN)$(ACTOR_FOG_GATE)$(SCENERY_GATE),1111)
$(error CROWD_INVIS_SKIP needs CROWD_CULL=1 FX_LEAN=1 ACTOR_FOG_GATE=1 SCENERY_GATE=1)
endif
$(OBJDIR)/src/game/trans.o $(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_CROWD_INVIS_SKIP=$(CROWD_INVIS_SKIP)
# re4dc_actor_crowd_note (and the =2 peek): a skipped source-path Ganado keeps its CROWD_LOD crowd entry;
# re4dc_actor_part_settled: the source path's settled-parts condition.
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_CROWD_INVIS_SKIP=$(CROWD_INVIS_SKIP)
ifeq ($(CROWD_INVIS_SKIP),2)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CROWD_OUTPUT=1
endif
endif

# ACTOR_EARLY_COARSE=1: labelled four-role Ganado coarse path, selected before
# source preparation only through the existing complete source/material proof.
# A next-frame texture ticket lives in the existing source frame ledger. Other
# actors keep the original complete source/owner route. No default/play adoption.
ACTOR_EARLY_COARSE ?= 0
ACTOR_EARLY_COARSE_DIAG ?= 0
ifeq ($(filter $(ACTOR_EARLY_COARSE),0 1),)
$(error ACTOR_EARLY_COARSE must be 0 or 1)
endif
ifeq ($(filter $(ACTOR_EARLY_COARSE_DIAG),0 1),)
$(error ACTOR_EARLY_COARSE_DIAG must be 0 or 1)
endif
ifeq ($(ACTOR_EARLY_COARSE),1)
ifneq ($(ACTOR_TRANSACTION)$(COARSE_SOURCE_ACTORS)$(COARSE_GANADO_CAST)$(COARSE_SKIN_FTRV)$(COARSE_ONE_SUBMIT),11111)
$(error ACTOR_EARLY_COARSE needs the existing transaction owner, source ledger, cast, FTRV and grouped submit)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_EARLY_COARSE=1 -DRE4DC_ACTOR_EARLY_COARSE_DIAG=$(ACTOR_EARLY_COARSE_DIAG)
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_EARLY_COARSE=1 -DRE4DC_ACTOR_EARLY_COARSE_DIAG=$(ACTOR_EARLY_COARSE_DIAG)
endif
# ACTOR_TEX_PREP: completed-source-ledger atlas residency hints before opening
# the native scene. No early callbacks, binding, bones or owner choice. Default
# off adds no compiler flags, preserving the existing disabled program bytes.
ACTOR_TEX_PREP ?= 0
ACTOR_TEX_PREP_DIAG ?= 0
# Optional Ganado preloads require successful source OT/screen preparation.
ACTOR_TEX_PREP_DRAW ?= 0
ifeq ($(filter $(ACTOR_TEX_PREP_DRAW),0 1),)
$(error ACTOR_TEX_PREP_DRAW must be 0 or 1)
endif
ifeq ($(ACTOR_TEX_PREP_DRAW),1)
ifneq ($(ACTOR_TEX_PREP)$(COARSE_SOURCE_ACTORS)$(ACTOR_TRANSACTION),111)
$(error ACTOR_TEX_PREP_DRAW needs ACTOR_TEX_PREP=1 COARSE_SOURCE_ACTORS=1 ACTOR_TRANSACTION=1)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_TEX_PREP_DRAW=1
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_TEX_PREP_DRAW=1
endif
# Standard Leon joins the existing player-first pre-scene atlas preparation.
ACTOR_TEX_PREP_LEON ?= 0
ACTOR_SKIN_DIAG ?= 0
ifeq ($(filter $(ACTOR_SKIN_DIAG),0 1),)
$(error ACTOR_SKIN_DIAG must be 0 or 1)
endif
ifeq ($(ACTOR_SKIN_DIAG),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_SKIN_DIAG needs ACTOR_TRANSACTION=1)
endif
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_SKIN_DIAG=1
endif
ifeq ($(filter $(ACTOR_TEX_PREP_LEON),0 1),)
$(error ACTOR_TEX_PREP_LEON must be 0 or 1)
endif
ifeq ($(ACTOR_TEX_PREP_LEON),1)
ifneq ($(ACTOR_TEX_PREP)$(ACTOR_PL08)$(PS2_LEON)$(LEON_HAND_POSES),1111)
$(error ACTOR_TEX_PREP_LEON needs ACTOR_TEX_PREP=1 ACTOR_PL08=1 PS2_LEON=1 LEON_HAND_POSES=1)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_TEX_PREP_LEON=1
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_TEX_PREP_LEON=1
endif
ifeq ($(filter $(ACTOR_TEX_PREP),0 1),)
$(error ACTOR_TEX_PREP must be 0 or 1)
endif
ifeq ($(filter $(ACTOR_TEX_PREP_DIAG),0 1),)
$(error ACTOR_TEX_PREP_DIAG must be 0 or 1)
endif
ifeq ($(ACTOR_TEX_PREP),1)
ifneq ($(ACTOR_TRANSACTION)$(COARSE_SOURCE_ACTORS)$(COARSE_GANADO_CAST)$(PS2_GANADO),1111)
$(error ACTOR_TEX_PREP needs the transaction owner, completed source ledger and PS2 Ganado cast)
endif
ifneq ($(ACTOR_EARLY_COARSE),0)
$(error ACTOR_TEX_PREP does not enable or combine with ACTOR_EARLY_COARSE)
endif
ifneq ($(TEX_RESIDENT)$(PVR_STREAM),11)
$(error ACTOR_TEX_PREP needs TEX_RESIDENT=1 PVR_STREAM=1 for the existing preload/cache owner)
endif
GAME_CPPFLAGS += -DRE4DC_ACTOR_TEX_PREP=1 -DRE4DC_ACTOR_TEX_PREP_DIAG=$(ACTOR_TEX_PREP_DIAG)
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_TEX_PREP=1 -DRE4DC_ACTOR_TEX_PREP_DIAG=$(ACTOR_TEX_PREP_DIAG)
endif

# PS2_GANADO_LIT=1 (Phase 2 A1; render only; default 0: nothing changes): the cast Ganados (owner appearances < 0x100)
#              are lit per vertex like the PS2 lights its characters: the source's GX light set (LightSetModel lights,
#              ambient, material colour, TEV scale; coarse_actor_transaction.inc actor_source_lighting) folded to the
#              3 strongest directional lights + ambient per part (native_actor_fast.cpp gigante_keep, ids 0x10..0x20),
#              evaluated by the skinned fast-light kernel (one FIPR per light per vertex). PS2_GANADO_DIR must then be
#              a bundle with real normals (ps2_cast.py without PS2CAST_FLAT_NORMALS); a flat bundle draws evenly lit.
PS2_GANADO_LIT ?= 0
ifneq ($(PS2_GANADO_LIT),0)
ifneq ($(PS2_GANADO_LIT)$(PS2_GANADO)$(ACTOR_TRANSACTION),111)
$(error PS2_GANADO_LIT=1 needs PS2_GANADO=1 ACTOR_TRANSACTION=1)
endif
ifeq ($(filter $(GIGANTE_LIGHTS),1 2),)
$(error PS2_GANADO_LIT=1 needs GIGANTE_LIGHTS=1 or 2 (the light fold))
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_PS2_GANADO_LIT=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_GANADO_LIGHT_FOLD=1
endif
# LEON_SOURCE_LIGHT=1 (light lane; render only; default 0: nothing changes): Leon's owner draw takes the source GX
#              light set (actor_source_lighting) instead of the constant colour; a record the kernel cannot take
#              keeps the constant colour (no decline, so no GameCube fallback). Logs LEON_LIGHT lines.
LEON_SOURCE_LIGHT ?= 0
ifneq ($(LEON_SOURCE_LIGHT),0)
ifneq ($(ACTOR_TRANSACTION),1)
$(error LEON_SOURCE_LIGHT=1 needs ACTOR_TRANSACTION=1)
endif
ifeq ($(LEON_NATIVE_PIPE),1)
$(error LEON_SOURCE_LIGHT=1 needs LEON_NATIVE_PIPE=0; the lean acquisition path does not capture source lighting)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_SOURCE_LIGHT=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_LEON_SOURCE_LIGHT=1
endif

# ACTOR_PROBE_LIGHT=1/2 (lane lp2, character lighting phase 2; render only; default 0: nothing changes): one light probe
#              per actor per frame instead of the per-part light fold. The actor's GX light set (LightSetModel's lights,
#              ambient, material, TEV scale: the LEON_SOURCE_LIGHT / PS2_GANADO_LIT records, dynamic lights included) is
#              evaluated once at the actor's origin into ambient + one directional light (L0 + L1 fit); each part lights
#              with that one direction in its own normal space through the existing fast kernel (never the exact
#              per-vertex evaluator). =1 Leon; =2 Leon + the Ganado classes 0x10..0x20 (near tier per vertex, mid/far one
#              colour per part from the probe, as CROWD_FLAT). Logs PROBE_LIGHT lines. Needs LEON_SOURCE_LIGHT=1 (Leon's
#              capture) and, for =2, PS2_GANADO_LIT=1 CROWD_LOD=1. See docs/ACTOR_PROBE_LIGHT.md.
ACTOR_PROBE_LIGHT ?= 0
ifeq ($(filter $(ACTOR_PROBE_LIGHT),0 1 2),)
$(error ACTOR_PROBE_LIGHT must be 0, 1 or 2)
endif
ifneq ($(ACTOR_PROBE_LIGHT),0)
ifneq ($(LEON_SOURCE_LIGHT),1)
$(error ACTOR_PROBE_LIGHT needs LEON_SOURCE_LIGHT=1 (the capture of Leon's GX light set))
endif
ifeq ($(ACTOR_PROBE_LIGHT),2)
ifneq ($(PS2_GANADO_LIT)$(CROWD_LOD),11)
$(error ACTOR_PROBE_LIGHT=2 needs PS2_GANADO_LIT=1 CROWD_LOD=1)
endif
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_PROBE_LIGHT=$(ACTOR_PROBE_LIGHT)
# The shared probe API (platform/include/actor_light_probe.h: re4dc_actor_light_probe) exists only in these builds; a
# consumer (the shadow lane) guards its call with RE4DC_ACTOR_LIGHT_PROBE_API (unresolved symbols link to silent stubs).
GAME_CPPFLAGS += -DRE4DC_ACTOR_LIGHT_PROBE_API=1
PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_LIGHT_PROBE_API=1
endif

# LEON_LIGHT_HEADROOM=1 (lane lp2; render only; default 0: nothing changes): Leon's lighting gets 2x headroom. The disc
#              must carry Leon's textures at 2x (tools/d367/charbake/cb_headroom.py: every Leon atlas / hair key at
#              double the stored levels, same keys and sizes, 0 VRAM); Leon's constant colour becomes 128 and his lit
#              colour matrix x0.5 (native_actor_fast.cpp), so flat looks as before and lit vertices reach 2.0x like the
#              GameCube TEV x2/x4 and the PS2 GS. A headroom binary needs the 2x pak, and the 2x pak needs a headroom
#              binary (else Leon draws at half / double brightness). Needs ACTOR_TRANSACTION=1.
# LEON_LIGHT_TOGGLE=1 (debug only, never in a release recipe): the Leon lighting mode cycles live (hold X, hold D-pad
#              right, press START; warp `leonlight <n>`): FLAT (test 10), PROBE, PROBE + HEADROOM, FLAT WARM (room
#              lights). Needs LEON_LIGHT_HEADROOM=1, ACTOR_PROBE_LIGHT=1/2, LOOK_TOGGLE=1, DBG_WARP=1.
LEON_LIGHT_HEADROOM ?= 0
LEON_LIGHT_TOGGLE ?= 0
ifneq ($(filter-out 0 1,$(LEON_LIGHT_HEADROOM))$(filter-out 0 1,$(LEON_LIGHT_TOGGLE)),)
$(error LEON_LIGHT_HEADROOM / LEON_LIGHT_TOGGLE are 0 or 1)
endif
ifeq ($(LEON_LIGHT_HEADROOM),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error LEON_LIGHT_HEADROOM=1 needs ACTOR_TRANSACTION=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_LEON_LIGHT_HEADROOM=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_LEON_LIGHT_HEADROOM=1
# Every other draw of Leon's 2x textures (radio-call portrait, source fallback) is halved in re4dc_model_submit.
$(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_LEON_LIGHT_HEADROOM=1
$(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_ui.o: charbake_variants.h
endif
ifeq ($(LEON_LIGHT_TOGGLE),1)
ifneq ($(LEON_LIGHT_HEADROOM)$(LOOK_TOGGLE)$(DBG_WARP),111)
$(error LEON_LIGHT_TOGGLE=1 needs LEON_LIGHT_HEADROOM=1 LOOK_TOGGLE=1 DBG_WARP=1 (debug builds only))
endif
ifeq ($(ACTOR_PROBE_LIGHT),0)
$(error LEON_LIGHT_TOGGLE=1 needs ACTOR_PROBE_LIGHT=1 or 2)
endif
GAME_CPPFLAGS += -DRE4DC_LEON_LIGHT_TOGGLE=1
PLATFORM_CPPFLAGS += -DRE4DC_LEON_LIGHT_TOGGLE=1
endif
# LEON_LIGHT_FILL=F (lane lp2; Leon only; render only; default 0: nothing changes): a camera-side fill light on Leon,
#              F% (0..100) of his probe's total colour (directional + ambient), in the fast kernel's spare second
#              direction (native_actor_fast.cpp probe_lights): lifts the side of Leon facing the camera that the one-
#              direction probe leaves at ambient. No new pass, no shared-record change. Needs ACTOR_PROBE_LIGHT=1/2.
LEON_LIGHT_FILL ?= 0
ifneq ($(shell [ "$(LEON_LIGHT_FILL)" -ge 0 ] 2>/dev/null && [ "$(LEON_LIGHT_FILL)" -le 100 ] 2>/dev/null && echo ok),ok)
$(error LEON_LIGHT_FILL must be an integer 0..100)
endif
ifneq ($(LEON_LIGHT_FILL),0)
ifeq ($(ACTOR_PROBE_LIGHT),0)
$(error LEON_LIGHT_FILL needs ACTOR_PROBE_LIGHT=1 or 2)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_LEON_LIGHT_FILL=$(LEON_LIGHT_FILL)
endif
# GANADO_LIT=1 (lane ganlit 2026-10-16; villagers lit by the room's lights; render only; default 0: nothing changes):
#              with ACTOR_PROBE_LIGHT=2 (each Ganado's probe from its own GX light set), only the GANADO_LIT_NEAREST
#              nearest Ganado models light per vertex; every other Ganado (and every one when NEAREST=0) takes one colour
#              per part from its probe. NEAREST=-1 (default) = every near-tier Ganado, as ACTOR_PROBE_LIGHT=2 alone.
# GANADO_LIT_TOGGLE=1 (debug only, never in a release recipe): warp `ganlit <m>` sets the mode at load (0 = test 15:
#              Ganados off the probe, build_lights + CROWD_FLAT; 1..8 = the m-1 nearest; 9 = every near-tier one), for
#              look sheets and same-binary cost pairs. Needs GANADO_LIT=1 DBG_WARP=1.
# GANADO_LIT_FILL=F (0..100, default 0; needs GANADO_LIT=1): Leon's camera fill (LEON_LIGHT_FILL) for the probe-lit
#              Ganados, F% of each Ganado's probe total in the kernel's spare second direction (no new pass): brings
#              the shaded Ganados back toward the flat test 15 brightness under the PVR's 1.0x vertex-colour cap.
GANADO_LIT ?= 0
GANADO_LIT_NEAREST ?= -1
GANADO_LIT_FILL ?= 0
GANADO_LIT_TOGGLE ?= 0
ifneq ($(filter-out 0 1,$(GANADO_LIT))$(filter-out 0 1,$(GANADO_LIT_TOGGLE)),)
$(error GANADO_LIT / GANADO_LIT_TOGGLE are 0 or 1)
endif
ifeq ($(GANADO_LIT),1)
ifneq ($(ACTOR_PROBE_LIGHT),2)
$(error GANADO_LIT=1 needs ACTOR_PROBE_LIGHT=2 (PS2_GANADO_LIT=1 CROWD_LOD=1))
endif
ifeq ($(filter $(GANADO_LIT_NEAREST),-1 0 1 2 3 4 5 6 7),)
$(error GANADO_LIT_NEAREST must be -1..7)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_GANADO_LIT=1 -DRE4DC_GANADO_LIT_NEAREST=$(GANADO_LIT_NEAREST)
ifneq ($(shell [ "$(GANADO_LIT_FILL)" -ge 0 ] 2>/dev/null && [ "$(GANADO_LIT_FILL)" -le 100 ] 2>/dev/null && echo ok),ok)
$(error GANADO_LIT_FILL must be an integer 0..100)
endif
ifneq ($(GANADO_LIT_FILL),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_GANADO_LIT_FILL=$(GANADO_LIT_FILL)
else ifeq ($(GANADO_LIT_TOGGLE),1)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_GANADO_LIT_FILL=-1
endif
else ifneq ($(GANADO_LIT_FILL),0)
$(error GANADO_LIT_FILL needs GANADO_LIT=1)
endif
ifeq ($(GANADO_LIT_TOGGLE),1)
ifneq ($(GANADO_LIT)$(DBG_WARP),11)
$(error GANADO_LIT_TOGGLE=1 needs GANADO_LIT=1 DBG_WARP=1 (debug builds only))
endif
GAME_CPPFLAGS += -DRE4DC_GANADO_LIT_TOGGLE=1
PLATFORM_CPPFLAGS += -DRE4DC_GANADO_LIT_TOGGLE=1
endif

# Isolate transaction skin entries from the ordinary 64-entry lazy/eager table.
# Default off keeps the original registry and adds no compiler flags. The pool
# is fixed at the existing workspace owner limit times the maximum plan roles.
ACTOR_SKIN_OWNER_POOL ?= 0
ifeq ($(filter $(ACTOR_SKIN_OWNER_POOL),0 1),)
$(error ACTOR_SKIN_OWNER_POOL must be 0 or 1)
endif
ifeq ($(ACTOR_SKIN_OWNER_POOL),1)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_SKIN_OWNER_POOL needs ACTOR_TRANSACTION=1)
endif
ifeq ($(ACTOR_SKIN_RESERVE),1)
# cx-integrate: the pool replaces native_actor_owner_registry.inc, so native_actor_skin_reserve.inc (D36/P) is not
# compiled and trans.cpp's re4dc_actor_skin_reserve call would link to a silent missing-symbol stub.
$(error ACTOR_SKIN_OWNER_POOL=1 and ACTOR_SKIN_RESERVE=1 are exclusive (the reserve indexes the shared registry))
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_SKIN_OWNER_POOL=1
endif

# UI_HASH_DIAG=1 (lane crowd12 2026-10-14; test only, default 0: no effect): native_ui.cpp logs "uihash:" lines every 60
# UI frames: how many image_key() lookups hashed an image's texels (no source-table hit, no external identity), how many
# bytes, whether the source table (kSourceCount) was full, and the heaviest images with load()'s caller (symbolize with
# sh-elf-addr2line on the build's ELF). Found: r101 cross view spends ~8 hw ms/frame in hash_bytes (lp2 wide runs).
UI_HASH_DIAG ?= 0
ifeq ($(filter $(UI_HASH_DIAG),0 1),)
$(error UI_HASH_DIAG must be 0 or 1)
endif
ifeq ($(UI_HASH_DIAG),1)
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_HASH_DIAG=1
endif

# UI_SOURCE_LRU=1 (lane crowd12 2026-10-14; exact, render only, default 0: no effect; needs COPY_LEAN=1): native_ui.cpp's
# source table (sources[], kSourceCount = 128 with PVR_STREAM) maps an image descriptor to its texture key so a lookup
# does not hash the texels again. Once full (r101: from about room frame 60), every new descriptor was hashed on every
# lookup, every frame (r101 burning-cross view: ~650 hashes / 3 MB per 60 drawn frames; hash_bytes 8 hw ms/frame in the
# lp2 wide runs). =1: a new descriptor replaces the least recently used entry instead. Keys are unchanged (the hash of
# the texels when first seen, as for the first 128 descriptors); an indexed image cached this way also keeps its
# palette's FNV and is hashed again when the palette changed. =2 (check build): every hit on a replaced entry also
# hashes and compares ("UISRC check ... bad=" lines; bad must stay 0).
UI_SOURCE_LRU ?= 0
ifeq ($(filter $(UI_SOURCE_LRU),0 1 2),)
$(error UI_SOURCE_LRU must be 0, 1 or 2)
endif
ifneq ($(UI_SOURCE_LRU),0)
ifneq ($(COPY_LEAN),1)
$(error UI_SOURCE_LRU needs COPY_LEAN=1 (the source hints))
endif
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_UI_SOURCE_LRU=$(UI_SOURCE_LRU)
endif

# ACC_CROWD_TIER=N (lane crowd12 2026-10-15; render only, default 0; needs ACTOR_CROWD): a Ganado's hanging accessory
# (cObj12 sack / lantern / bucket from em10SetAccesory) is not drawn while that Ganado's crowd tier is >= N (2: mid and
# far, 3: far only). The accessory still moves and renders on the source side; only the native draw is skipped.
# 1 (measurement only, a look change): no Ganado accessory is drawn (their whole render cost, for the PS2 conversion).
ACC_CROWD_TIER ?= 0
ifneq ($(filter-out 0 1 2 3,$(ACC_CROWD_TIER)),)
$(error ACC_CROWD_TIER is 0, 1, 2 or 3)
endif
ifneq ($(ACC_CROWD_TIER),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACC_CROWD_TIER=$(ACC_CROWD_TIER)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_ACC_CROWD_TIER=$(ACC_CROWD_TIER)
endif

# MEMSET_LEAN=1 (lane crowd12 2026-10-15; render only, default 0): repeated per-part clears that MEMPROF found are
# narrowed to the fields that are read: the light fold (native_actor_fast.cpp lights_reset) no longer zeroes
# Lights::prepared (read only on the exact path, which assigns it first).
MEMSET_LEAN ?= 0
ifneq ($(MEMSET_LEAN),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_MEMSET_LEAN=$(MEMSET_LEAN)
endif

# GCOBJ_SKIP=N (MEASUREMENT ONLY, a look change; lane crowd12 2026-10-15; default 0): GC-path object models (doors,
# racks, windows, boxes, rack rifles, cObj00 [static]; enemy weapons, cObj12, items) are not drawn, to cost a batched
# object draw path. 1 all / 2 static, skipped at ModelRender; 3 all / 4 static, skipped at re4dc_draw_model_part.
GCOBJ_SKIP ?= 0
ifneq ($(GCOBJ_SKIP),0)
$(OBJDIR)/src/game/trans.o $(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_GCOBJ_SKIP=$(GCOBJ_SKIP)
endif

# GC_STUB_SKIP=1 (lane crowd12 2026-10-15; render only, exact; default 0): a GC-path model part with fewer than 3
# positions (cannot form a triangle; r101's objs-fixture cObj00 stubs) skips re4dc_draw_model_part's per-part work.
GC_STUB_SKIP ?= 0
ifneq ($(GC_STUB_SKIP),0)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_GC_STUB_SKIP=$(GC_STUB_SKIP)
endif

# OWNER_SETUP_LEAN=1 (lane crowd12 2026-10-15; render only, exact; default 0): the Ganados' behind-the-house-walls
# bound (coarse_actor_owner_ganado.inc invis_interior / invis_owner_interior) is not built while the Trans-time
# interior cell state is inactive, when its hidden test returns 0 anyway.
OWNER_SETUP_LEAN ?= 0
ifneq ($(OWNER_SETUP_LEAN),0)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_OWNER_SETUP_LEAN=$(OWNER_SETUP_LEAN)
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_OWNER_SETUP_LEAN=$(OWNER_SETUP_LEAN)
endif

# TEX_IDENT_LEAN=1 (lane crowd12 2026-10-15; render only, exact; default 0): texture identity lookups
# (room/texture_package.cpp SourceIdentityTable::lookup) test an entry's bounds before reading its tag.
TEX_IDENT_LEAN ?= 0
ifneq ($(TEX_IDENT_LEAN),0)
$(OBJDIR)/native-reuse/texture_package.o: PLATFORM_CPPFLAGS += -DRE4DC_TEX_IDENT_LEAN=$(TEX_IDENT_LEAN)
endif

# SOB_DIAG=1 (diagnostic only, lane crowd12 2026-10-15): SOBPART lines (the static object classes' GC part records)
# every 600 frames, for the STATIC_OBJ_BATCH design.
SOB_DIAG ?= 0
ifneq ($(SOB_DIAG),0)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_SOB_DIAG=1
endif

# STATIC_OBJ_BATCH=1 (lane crowd12 2026-10-15; render only, default 0): the static GC-path object classes (doors,
# boxes, racks, windows, rack rifles) submit each run of identical-record display lists of one info as one actor
# part (model_bridge.cpp sob::), from a copy of the raw GX lists in a heap-4 room cell (freed at room leave).
# Matrices, poses and lights stay live; any mismatch submits the lists one by one as before. =1 merges only groups
# whose lighting is centre-independent (exact); =2 also lit groups (lights folded at the merged centre).
STATIC_OBJ_BATCH ?= 0
ifneq ($(STATIC_OBJ_BATCH),0)
$(OBJDIR)/model_bridge.o $(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_STATIC_OBJ_BATCH=$(STATIC_OBJ_BATCH)
endif
# STATIC_OBJ_BATCH_WORDCMP=1 (lane crowd12 5149da0a, put behind a knob by the test 13 RC so that the 12.2 recipe's image
# stays byte-identical; render only, exact, default 0): sob::same compares the held record and the lighting record with
# a word loop instead of newlib memcmp (a byte loop; ~0.2 ms MODELLED at r101), same equality. Needs STATIC_OBJ_BATCH.
STATIC_OBJ_BATCH_WORDCMP ?= 0
ifneq ($(STATIC_OBJ_BATCH_WORDCMP),0)
ifeq ($(STATIC_OBJ_BATCH),0)
$(error STATIC_OBJ_BATCH_WORDCMP needs STATIC_OBJ_BATCH=1 or 2)
endif
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_SOB_WORDCMP=1
endif

# KOS_TRACE=N (diagnostic only, lane crowd12 2026-10-15; default 0): "kos trace:" every N room frames (KOS malloc free
# and sbrk room), to read the headroom after events such as the r101 bell. No static data.
KOS_TRACE ?= 0
ifneq ($(KOS_TRACE),0)
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_KOS_TRACE=$(KOS_TRACE)
endif

# SOB_DUMP=1 (diagnostic only, lane crowd12 2026-10-15; default 0): first-draw capture of the static etc object parts
# (arrays, raw GX list, matrices, texture key) as "SOBX" hex lines, input of the offline STATIC_OBJ_BAKE.
SOB_DUMP ?= 0
ifneq ($(SOB_DUMP),0)
$(OBJDIR)/model_bridge.o $(OBJDIR)/model_asset_bridge.o $(OBJDIR)/platform/native_ui.o: GAME_CPPFLAGS += -DRE4DC_SOB_DUMP=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_SOB_DUMP=1
endif

# STATIC_OBJ_BAKE=1 (render only, lane crowd12 2026-10-15; default 0): the room's static etc objects (doors, boxes,
# racks, windows, kind-1 0x21) baked offline into its PS2 world package draw from it while the game asks to draw them
# at the baked rest pose (bit-identical matrices); opened / broken / pushed / picked up / moved = the live draw.
# Needs PS2_PLACE_GATE=1 and the baked package staged (r101: re4-assets-private/crowd12-bake-20261015/r101).
STATIC_OBJ_BAKE ?= 0
ifneq ($(STATIC_OBJ_BAKE),0)
ifeq ($(PS2_PLACE_GATE),0)
$(error STATIC_OBJ_BAKE needs PS2_PLACE_GATE=1)
endif
$(OBJDIR)/src/game/trans.o $(OBJDIR)/model_bridge.o $(OBJDIR)/model_asset_bridge.o $(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_STATIC_OBJ_BAKE=1
endif

# ACTOR_REPLAY_SKIN=1 (lane cast-ps2-25, 2026-10-26; default 0: no effect; render only; needs NATIVE_ACTOR_FAST,
#              MODEL_STREAM_FIX and NATIVE_ACTOR_SKIN_LAZY): a skinned part declined by the actor path because its
#              info's lazy palette was already materialized this frame (h2: the translucent room model replayed after
#              the codec screen) gets that palette registered for its arrays and goes through the actor path instead
#              of the generic GX walker (which, by the GC-ASSET rule, carries no member proof).
ACTOR_REPLAY_SKIN ?= 0
ifeq ($(filter $(ACTOR_REPLAY_SKIN),0 1),)
$(error ACTOR_REPLAY_SKIN must be 0 or 1)
endif
ifeq ($(ACTOR_REPLAY_SKIN),1)
$(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_REPLAY_SKIN=1
endif
