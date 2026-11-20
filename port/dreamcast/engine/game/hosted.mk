# E1 hosted behaviour (SHELL_MAP section 5, variant B): the player and camera-decision seed files, rnd.cpp, and the
# handgun weapon module the player loads at run time (wep02 prolog -> Wep02_init -> cObjRuger, cObjWep), which the
# static closure could not see (a function pointer set by the module's prolog).
# Built from src/ unchanged, with every RE4DC_ knob off (host/e1_prelude.h: the endian adapter STAT_BE only).
#
# The partner (lane eng-e1b, E1 second slice): Ashley's original partner code, cSubChar (pl_npc.cpp: follow, wait,
# hide, carried, damage) and the pl11 module (cSubAshley, enemy id 3: em/pl11 + rel/pl11), whose REL entry is
# linked under its own name (Makefile: -D_prolog=pl11_prolog, as the reference build re4ref does).
ifeq ($(BOSS)$(FIGHT),)
PARTNER_SRCS := game/pl_npc pl11/pl11
endif
# Camera: cam_ctrl, cam_sys, cam_qfps and cam_extra are the camera's decisions (which camera, modes, rails, areas,
# targets). Their evaluation functions (rail spline, orientation matrices, attached camera) are the native camera
# service's: game/Makefile SPLIT_UNITS weakens them here. view.cpp, camera.cpp and cam_motion.cpp are not linked
# (lane eng-e1e: services/camera/camera_svc.cpp).
HOSTED_SRCS := \
	game/player game/pl_class game/pl_body game/pl_sub game/pl_leon game/pl_wep game/pl_dmg game/pl_push \
	game/pl_knife game/pl_debug game/pl_event game/cam_ctrl game/cam_sys game/cam_qfps game/cam_extra \
	wep/pl_handgun game/rnd \
	wep02/wep02 wep/objRuger game/objWep \
	$(PARTNER_SRCS)

# Services. Native and linked by game/Makefile, not compiled from src/:
#   - skeleton and the collision query cores (lane eng-e1c: services/skeleton, services/collision/col.cpp);
#   - cloth (lane eng-e1d: services/cloth; pendulum.cpp not linked);
#   - round 4 (lane eng-svc4, wired by lane eng-e1e; SERVICES.md sections 23-31): actor volumes (atariInfo, at_mod,
#     at_sub), collision response and managers (atari), routes (route_ck), the root-motion follower (cMotBase), model
#     records and pools (model), the camera (view, camera, cam_motion, motion's HermiteInterpolation) and input with
#     rumble (pad). motion.cpp's remaining functions are the skeleton service's (round 3). None of these units is linked.
# Not linked either: ik.cpp (native), shape.cpp (facial shape keys: the engine draws no shape keys).
#
# What is still compiled from src/ under the service boundary (no native service yet: the next services lane;
# tools/engine/check_link.py lists them as SERVICE):
#   - the leaf math (math_sub, sub2);
#   - pl_cloth.cpp: the behaviour's side of the cloth (each chain's links, lengths, wind tables and volumes, then the
#     PenCloth* calls; Leon's jacket, holster and hair, Ashley's hair, skirt and sweater) and the garment pose
#     (girlLapelMove). The boss image (BOSS=1) keeps its cloth stubs, as does the fight image (FIGHT=1, lane eng-e2).
#   - the SDK math and allocator, fdlibm (game/Makefile SDK_UNITS, FD_UNITS).
ifeq ($(BOSS)$(FIGHT),)
CLOTH_SRCS := game/pl_cloth
endif
SVC_ORIG_SRCS := \
	game/math_sub game/sub2 \
	$(CLOTH_SRCS)
