# E1 hosted behaviour (SHELL_MAP section 5, variant B): the 19 player and camera seed files, rnd.cpp, and the
# handgun weapon module the player loads at run time (wep02 prolog -> Wep02_init -> cObjRuger, cObjWep), which the
# static closure could not see (a function pointer set by the module's prolog).
# Built from src/ unchanged, with every RE4DC_ knob off (host/e1_prelude.h: the endian adapter STAT_BE only).
#
# The partner (lane eng-e1b, E1 second slice): Ashley's original partner code, cSubChar (pl_npc.cpp: follow, wait,
# hide, carried, damage) and the pl11 module (cSubAshley, enemy id 3: em/pl11 + rel/pl11), whose REL entry is
# linked under its own name (Makefile: -D_prolog=pl11_prolog, as the reference build re4ref does).
PARTNER_SRCS := game/pl_npc pl11/pl11
HOSTED_SRCS := \
	game/player game/pl_class game/pl_body game/pl_sub game/pl_leon game/pl_wep game/pl_dmg game/pl_push \
	game/pl_knife game/pl_debug game/pl_event game/cam_ctrl game/cam_sys game/cam_qfps game/cam_extra \
	game/cam_motion game/camera game/view wep/pl_handgun game/rnd \
	wep02/wep02 wep/objRuger game/objWep \
	$(PARTNER_SRCS)

# Service evaluation, FIRST FORM (lane eng-e1, stated in the hand-back): the skeleton (motion, parts, IK, shape,
# cloth), collision (SAT/EAT queries, hit volumes), the actor/object managers' record code and the leaf math are the
# original evaluation units compiled under the engine's service boundary with --gc-sections (only what the hosted
# behaviour reaches is kept). The engine owns the calls, the records (the actor table, read in place by the
# renderer), the memory and the data; these units are the arithmetic reference a re-laid-out native service must
# match. Each unit's unresolved references are engine adapters (host/) or logged stubs.
# route_ck.cpp (lane eng-e1b): the room's route points, which the partner's follow reads (RouteCkToPos).
SVC_ORIG_SRCS := \
	game/model game/motion game/cMotBase game/ik game/shape game/pl_cloth game/pendulum \
	game/atari game/atariInfo game/at_mod game/at_sub \
	game/pad \
	game/math_sub game/sub2 \
	game/route_ck
