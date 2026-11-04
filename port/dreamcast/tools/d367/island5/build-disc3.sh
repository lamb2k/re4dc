#!/bin/bash
# build-disc3.sh <arm>...  (WSL; lane world-ch5, 2026-11-02): the Disc 3 (island, chapter 5) program on the release line.
# Settled layout (user 10-16): Disc 1 village (1-1..2-3), Disc 2 castle (3-1..4-4), Disc 3 island + final chapter; all
# game discs ship in the one game zip. Disc 1 and Disc 2 programs are unchanged: DISC_SET=1 (already in the release
# recipe with RR_DISC2=1) asks for disc 3 once pG->chapter >= 14 (game.cpp StageInit), i.e. after r22a's
# SceSetChapterEnd(CHAPTER_4_4) when r300 loads.
# Program = rr/recipe.conf CH2 (release recipe, DISC_SET=1) + D3REC below:
#   ROUTE_CH3 STAGE_OVL ROUTE_MOVIES  the island room code (st3_0..3 overlays) and its movie hooks;
#   DISC3_MODULES                     drop the stage-1 modules (DISC2=1's list) and keep the dc/disc.id identity;
#   PS2_ENEMY_ST3=23                  the chapter's PS2 spawn logic, one knob (r30f, r301 waves, r327 camp, r311 skip);
#   ALIVE_CAP=4 ALIVE_CAP_PARK=1      the cap of 4 on top (soldiers, Ganados and Novistadors share it);
#   PRIM_MIN_ST3 PRIM_CAP_R320        island TA primitive budgets (ch5found16);
#   FOG_OFF_CLEAR EVENT_SWAP_RELOAD   island room fixes from ch5found16 / island18;
#   NATIVE_MODEL_REGISTRY_*    the PS2 cast registry (soldiers em1d/em1e/em1f via role packages);
#   AICA_SPILL AICA_SHARED_BGM1 AICA_STR_ENT_MAX=56  the island stream file (island18-r333-route-streams), r332 BGM1;
#   ARENA_KOS_BYTES=53248             as island18's recipe (KOS 48 KiB squeeze held 49152 B in its r317/U-3 runs);
#   MOTION_LARGE_CLIPS                U-3 (em32) clips up to 128 KiB (island18-u3large / u3sound data);
#   ROUTE_FINAL NMR_PRELOAD_SKIP      final chapter r332 code (data not on Disc 3 yet) and registry preload skip;
#   RESIDENT_SHARED_R327              r327's one shared resident key (island18 H-007).
#   LEON_WOUND LEON_WOUND_DIR         Leon's chapter 5 wound overlay (setWound: r317 on) on the native pl08 plan with the
#                                     PS2 wound (appearance 0x10B; data set wound in D3_DATA; lane bosscast-wound).
# D3CARRY = the program-wide CH4REC (Disc 2) knobs that are not castle route code, so the chapter 1-4 fixes ride Disc 3
# too (CH-FIXES-CARRY.md rows 3 4 5 8 11 12 15): NO_GC_FRONT cast path, Ashley PS2, cap 4 Novistador / defer rules,
# SS pool top, statue lights, PS2 mist / haze cut, registry dying / run share / blend table, NATIVE_BUMP_FLAT (on Disc 2).
# island18/recipe.sh test-only knobs (ALIVE_CAP_LOG HEAP4_WATER WARP_JUMP MOTION_MISS_LOG CENSUS_PERIOD) stay out; DISC2=1 is
# replaced by DISC3_MODULES=1 (DISC_SET excludes DISC2).
# Usage: LP=<fresh label> K=/abs/logdir bash build-disc3.sh rP|rW|mW|rT
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export T=${T:-$(cd "$HERE/../../../../.." && pwd)}
export K=${K:?Set K to the build log directory}
export LP=${LP:?Set a fresh LP label}
source "$T/port/dreamcast/tools/d367/rr/recipe.conf"
D3REC="ACTOR_CAST_SHADOW_EMPTY=1 ROUTE_CH3=1 STAGE_OVL=1 ROUTE_MOVIES=1 DISC3_MODULES=1 PS2_ENEMY_ST3=23 ALIVE_CAP=4 R101_ALIVE_CAP=4 ALIVE_CAP_PARK=1 PRIM_MIN_ST3=393216 PRIM_CAP_R320=327680 FOG_OFF_CLEAR=1 NATIVE_MODEL_REGISTRY_FIRST=1 NATIVE_MODEL_REGISTRY_LOD=1 NATIVE_MODEL_REGISTRY_ROLES5=1 NATIVE_MODEL_REGISTRY_ROLE_TEX23=1 NATIVE_MODEL_REGISTRY_BONES=128 EVENT_SWAP_RELOAD=1 AICA_SPILL=1 AICA_SHARED_BGM1=1 AICA_STR_ENT_MAX=56 ARENA_KOS_BYTES=53248 MOTION_LARGE_CLIPS=1 ROUTE_FINAL=1 NMR_PRELOAD_SKIP=1 RESIDENT_SHARED_R327=1 MOTION_LARGE_EM39=1 LEON_WOUND=1 LEON_WOUND_DIR=/root/re4data/private/wound-20261103"
D3CARRY="SS_POOL_TOP=1 LEON_OT_WATER=2 NATIVE_MODEL_REGISTRY_DYING=1 NATIVE_MODEL_REGISTRY_RUN_SHARE=1 NATIVE_MODEL_REGISTRY_BLENDTBL=1 NATIVE_BUMP_FLAT=1 STATUE_LIGHTS=2 ALIVE_CAP_NOVIS=1 LEON_SKIN_SLOTS=2 PARTS_LINKED_FLAG=1 SS_CERT_PARTNER_CAPACITY=1 FX_MIST_PS2=1 HAZE_SPRITE_CUT=1 PS2_HDR_SETS=128 ACTOR_PLAN=1 ALIVE_CAP_DEFER_FLAGS=1 TEX_PKG_SKIP_LISTED=1 PS2_ASHLEY=2 NATIVE_MODEL_REGISTRY_PL_ASHLEY=1"
case " $CH2 " in *" DISC_SET=1 "*) ;; *) CH2="$CH2 DISC_SET=1" ;; esac
export CH2="$CH2 $D3CARRY $D3REC ${D3_EXTRA:-}"
mkdir -p "$K"
printf '%s\n' "$CH2" > "$K/disc-knobs-$LP.txt"
bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" "$@"
