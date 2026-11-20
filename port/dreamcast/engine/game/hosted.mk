# E1 hosted behaviour (SHELL_MAP section 5, variant B): the 19 player and camera seed files, rnd.cpp, and the
# handgun weapon module the player loads at run time (wep02 prolog -> Wep02_init -> cObjRuger, cObjWep), which the
# static closure could not see (a function pointer set by the module's prolog).
# Built from src/ unchanged, with every RE4DC_ knob off (host/e1_prelude.h: the endian adapter STAT_BE only).
#
# The partner (lane eng-e1b, E1 second slice): Ashley's original partner code, cSubChar (pl_npc.cpp: follow, wait,
# hide, carried, damage) and the pl11 module (cSubAshley, enemy id 3: em/pl11 + rel/pl11), whose REL entry is
# linked under its own name (Makefile: -D_prolog=pl11_prolog, as the reference build re4ref does).
ifneq ($(BOSS),1)
PARTNER_SRCS := game/pl_npc pl11/pl11
SVC_PARTNER_SRCS := game/route_ck
endif
HOSTED_SRCS := \
	game/player game/pl_class game/pl_body game/pl_sub game/pl_leon game/pl_wep game/pl_dmg game/pl_push \
	game/pl_knife game/pl_debug game/pl_event game/cam_ctrl game/cam_sys game/cam_qfps game/cam_extra \
	game/cam_motion game/camera game/view wep/pl_handgun game/rnd \
	wep02/wep02 wep/objRuger game/objWep \
	$(PARTNER_SRCS)

# Services (lane eng-e1c): the skeleton and the collision query cores are NATIVE (services/skeleton, services/collision,
# docs/engine/SERVICES.md; game/Makefile NATIVE_OBJS). What is still compiled from src/ under the service boundary:
#   - model.cpp, motion.cpp, atari.cpp with every function the native services replace made weak (game/Makefile
#     WEAK_*): the calls reach the native bodies and --gc-sections drops the originals. What stays of them is the part
#     SERVICES.md keeps original: model and parts allocation, the key decoder and the motion clock / root motion, and
#     the per-model collision logic above the native cores (check, getFloor, wallAdjust, adjust);
#   - cMotBase.cpp (root-motion follower), the actor volumes and capsules (atariInfo, at_mod, at_sub) and route_ck.cpp
#     (the partner's route points, lane eng-e1b): no native service exists and a stub would change gameplay (pushes
#     between characters, hits, the partner's follow);
#   - pad.cpp (input) and the leaf math (math_sub, sub2).
# Not linked: ik.cpp (native), shape.cpp (facial shape keys: the engine draws no shape keys).
# Cloth (lane eng-e1d): the NATIVE cloth service (services/cloth, round 3 of lane eng-svc3: cloth.cpp and the SH4ZAM
# chain kernel cloth_kernel.c, game/Makefile NATIVE_OBJS) gives PenClothSet / Move / Move3 / FixSet / FixClear their
# bodies, the link-against-volume tests included. pl_cloth.cpp is the behaviour's side of the cloth (each chain's
# links, lengths, wind tables and volumes, then the PenCloth* calls; Leon's jacket, holster and hair, Ashley's hair,
# skirt and sweater). pendulum.cpp is NOT linked: the wind globals (GlobalWind, GlobalWindAdd) are engine data at the
# original's defaults (no room wind setter is hosted) and the service's fallback for a chain it cannot resolve is a
# logged stub (host/e1_svc_stubs.cpp); PenClothMove2 (enemy flails) has no caller here. The boss image (BOSS=1) keeps
# its cloth stubs.
ifneq ($(BOSS),1)
CLOTH_SRCS := game/pl_cloth
endif
# route_ck.cpp (lane eng-e1b): the room's route points, which the partner's follow reads (RouteCkToPos); the boss image
# (BOSS=1) builds neither the partner nor this unit here (game/boss.mk adds route_ck itself).
SVC_ORIG_SRCS := \
	game/model game/motion game/cMotBase \
	game/atari game/atariInfo game/at_mod game/at_sub \
	game/pad \
	game/math_sub game/sub2 \
	$(SVC_PARTNER_SRCS) $(CLOTH_SRCS)
