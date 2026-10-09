#!/bin/bash
# The r21 candidate recipe (landed 2026-09-28, 4fb68a8..36e28e0): the canonical LH + M1 + PERF knobs,
# the r19 playability integration, the PS2 r101 world through R4IM (PS2_WORLD_MESH=1), the HUD source
# mask with the 230 lens alpha, MESH_PRIME_LAZY=1 (2026-09-28). Traced (LOGIC_TRACE=1, the STRICT gate build) by
# default; release measurement adds: LOGIC_TRACE=0 GAME_DECISION_TRACE=0 ACTOR_TRANSACTION_DIAG=0 GAME_PWC_DIAG=0.
# MESH_CLIP_LEAN=1 (user 2026-10-03; the architect review had found the 2026-09-28 note claiming it while the make
# line never had it): strips wholly outside a frustum plane skip the near/far clipper. H2 58.71 -> 56.53 hw ms (scenery
# 9.10 -> 6.44), STRICT 120/120 + whole r100 1391/1391; house and r101 square off/on captures draw the same scenery. MODEL_DRAW_PLANS is forced to 1 by D349_RENDERER_STACK=1 (Makefile
# override): the line says 1 to match; it was 0 here and built the same image. Every build writes the knobs as make
# resolved them to $OUT/resolved-knobs.txt (game/knobs.mk).
# PLAYER_RESIDENT_BYTES=869728 (route lane 2026-10-01): pl08, Leon without the jacket in every room after r106, prepared
# textures-only (869,728 B); kite gate r15 vs c9 position-identical, heap 4 free -23,072 B.
# CRASH_SCREEN=1 (hardware readiness, user 2026-10-02: in every play build): a fault, a source HALT() or 30 s
# without a new frame draws a report asking the player to raise a ticket with a photo (platform/crash_screen.cpp).
# SS_PACK=1 MOVIE_HEAP_EVICT=1 (2026-10-02, user r21n play): the sub screen (calls, inventory) packs its 3 MiB into
# TA bank 1 instead of releasing ~2.3 MB of room textures (5-6 s of reloads per call); a route movie short of heap 4
# evicts unpinned motion keys (the r100 s30 cliff cutscene failed without it).
# CLOSED_PASS_KEEP=1 (2026-10-03, user r21o play): an opaque draw after the translucent list opened stays in the
# open list instead of halting ("native closed pass requested"). PS2_PRELOAD_LEAN=1 (2026-10-03): PS2 world rooms
# preload the package's textures, not the room archive's GameCube scenery (r100 route preload 16.3 -> 7.2 s).
# TEX_PACK=1 (2026-10-03): texture packages load from dc/tex.pak when the disc has one (route/pack-fixture.sh),
# per file otherwise (r100 room entry 6.5 -> 2.7 s).
# MOVIE_WINDOW=1 (route lane 2026-10-02): a route movie's VRAM claim releases one cheapest window of room textures
# (and only the picture's rows) instead of 0.5-1.1 MB of LRU uploads that reloaded after every movie.
# CROWD_READOPT=2 CROWD_CULL=1 CROWD_FOGSKIP=1 (user 2026-10-03, implementation handoff WP2): Leon re-opts into the
# native actor path (H2 -7.09 hw ms), crowd members outside the view and past the fog are not drawn. Gate on ed818b8e:
# H2 STRICT 120/120 + whole room 1391/1391, r101 bell STRICT, r100 calls / r101 bell / r103 entry HALT 0 MISSING 0.
# r21v (user 2026-10-04): the supervisor's 82.65 ms knob set (the last line of the list; route doc "r21v"). Its disc needs
# dc/native/r10{0,1,3}/registry.re4nmr, dc/native/pl08/leon_pl08.re4cp and the registry / pl08 textures in dc/tex.pak;
# without them those actors keep the source path. Flycast: r100 24.3 -> 25.9 fps, r101 bell steady 27.1 -> 24.8 ms.
# r21x (user 2026-10-04, first console play of r21v; the last line of the list): COARSE_SAT_SCENERY_ONLY=1 (no flat grey
# collision walls over the PS2 world: the r100 bridge "tan block"), SS_BG_BLACK=1 (black, not the fog colour, while a
# call / the inventory hides the room) and PACE_VMU=1 (the speed page on the VMU LCD: drawn fps, game speed, CPU ms per
# tick; user: the VMU fps build is the main build). The sub screen guard in Trans (r21v console fault 0xE0) needs no
# knob (SUBSCREEN=1). Its disc needs bgm/aica_str.dat with the radio call voices (tools/aica_banks.py disc
# --call-voices, stage.sh AICA_CALL_VOICES=1); without them every call is silent.
# Perf lanes 2026-10-04/05 (integration perf/int-20261005; the last line of the list; render-only or exact, logic STRICT):
# SKIN_PALETTE_LAZY=1 (sk), ESP_SPRITE_FAST=1 ESP47_SKIP_LEAN=1 (fx), MODEL_PREP_KEEP=1 CROWD_READOPT_MEMO=1
# ACTOR_BIND_REUSE=1 (cl; =2 check build 0 bad on r100-h-fight + perf-r101sq), PS2_WORLD_HDR_CACHE=1 MESH_CLIP_ACCEPT=1
# PS2_PASS_MASK=1 (wd; PS2_FOLIAGE_FAR stays off: a pending user look decision), GAME_HF_REG=1 GAME_CLOTH_SPRING=1
# GAME_SND_WALL_ALT=1 (logic; SE wall occlusion every other frame: audio only), with LINK_ORDER regenerated for them
# (r21z-perf-c3-8k.ld). Route doc "2026-10-05: integrated perf lanes".
# GAME_ROT_FSCA=1 (user 2026-10-05, lane fm; on the perf-lanes line): last-bit FSCA local matrices in
# cModel::partsMatCalc (one hand-scheduled SH-4 loop), -1.18 hw ms per tick in the fight (function level, drawn and
# skipped); decisions identical on H2, the bell and r100-h-fight. LINK_ORDER regenerated for it (r22-fsca-c3-8k.ld).
# Route doc "2026-10-05: GAME_ROT_FSCA adopted" and docs/lanes/fm-20261005.md.
# CROWD_INVIS_SKIP=1 EFFECT_FADE_CLAMP=1 (user 2026-10-05; the last line of the list): lane iv, no drawing-side work for
# a Ganado the next Render draws nothing of (render-only, TA streams identical, fight about -2.0 hw ms per drawn tick);
# lane ph, port fix: the near-fade colour of an effect inside its near distance saturates to 0 as the GameCube's psq_st
# (GQR2) does, instead of ftrc + extu.b wrapping to ~254 (sprites within ~1 m drew near-opaque: the white upstairs-window
# glare). EFFECT_PS2_HAZE / EFFECT_PS2_STREAK are in (user 2026-10-06, below); GAME_LQ_MEMO (lane el) stays off.
# WEAPON_RESIDENT_BYTES=275424 WEAPON_MODULES=1 (issue lamb2k/re4dc#1, r22c console halt 2026-10-05: equipping the
# r101 shotgun and leaving the inventory halted "asset exceeds selected resident budget": the 247,776 B weapon block
# held only the compact handgun, and only wep02 was a linked module). 275,424 B = wep07, the largest chapter 1-1
# weapon (Punisher 261,344; Red9 uses wep02; grenades 173,408). Heap 4 span -67 KB; r100 s30 still plays. The full
# stage-1 value 404,608 (rifle + the r104 scope; rocket 382,688, TMP + stock 299,200, TMP 289,248) made the r100 s30
# movie fail for heap 4. WEAPON_HEAP4=1 (option 3, 2026-10-06): those bigger bodies (rifle, TMP, rocket launcher) load
# into heap 4, the room heap, and are read again at each door (about +0.3 s per door while held); heap 4 short ->
# the equip reverts to the previous weapon. r107 keeps only ~100-109 KB of heap 4 with one held, and the scoped
# rifle can revert to the plain rifle there. PRIM_CAP_R107=327680 WEAPON_HEAP4_TOP=1 (2026-10-06, decision b): r107's
# primitive buffer is capped from its room value 589,824 B (peak use per frame 269,824 B, the native actor tail never
# declines) and a heap-4 weapon body is carved from the top of the highest free cell, so the scoped rifle fits in
# r107 with >= 360 KB of heap 4 left (no revert). Logic STRICT, r107 frozen look pixel-identical to knob-off.
# EFFECT_PS2_HAZE=1 EFFECT_PS2_STREAK=2 (PS2 haze and the PS2 light shaft, user 2026-10-06; lane ph 88f30aaf, render-only):
# the camera haze drawn as the PS2 release has it, and r100's house window streaks replaced by the PS2 light shafts
# (texture e9, in tex.pak). r103 is slightly heavier than GC (GPU proxy 16.7 vs 14.1 ms), accepted as PS2-faithful.
# PS2_INTERIOR_CULL=1 PS2_INTERIOR_ACTORS=1 (lane pc, coordinator 2026-10-06; render-only, logic STRICT): inside the first
# r100 house, an offline cell (170 sub-cells, 1186 portals: tools/d367/ps2world/interior) skips the outdoor PS2 world
# draws and the source-path Ganados hidden behind its walls. The cell is the disc file dc/native/r100/interior.cell
# (interior-r100.cell; pack-fixture.sh / room_fixture.py / interior/add_cell.py stage it; without it nothing is culled),
# read into an r100-only heap-4 block that every route movie borrows, so heap_before at r100 s30 equals the knob-off
# value. hw ms per drawn tick: stair foot -8.6, h-quiet -0.2 (its cell tests cost +0.42 with nothing culled), fight /
# square ~-1 (layout). Look caveats accepted: a 1 px wall-seam crack at the stair foot is not drawn; 4 px of one RGB565
# step. LINK_ORDER stays r22-fsca-c3-8k.ld (a regenerated order measured +0.1..0.5 worse). docs/lanes/pc-20261005.md.
# PS2_INTERIOR_ACTORS=2 (2026-10-07): also rejects wholly hidden owner-path Ganados, preserving
# admission and crowd ranking. Identity capture invalidates the prior cull mark. H2/bell decisions
# match; checker 1494 displayed scans and 191 replay checks are clean. Stair ascent frames 1760..1839:
# drawn 55.756->53.908 modeled ms, skipped 22.771->22.829, balanced mean 39.264->38.369.
# Linked image +8256 B; matched untraced s30 completes 340/340 at 67680 B free, then radio handoff passes.
# PS2_WORLD_DYNAMIC=1 (user 2026-10-06, issue lamb2k/re4dc#3: the r105 emblem never turned and its door looked shut): the
# PS2 world follows the scenery the room code moves or hides. Each PS2 placement carries its SMD scroll id
# (tools/ps2_room_ids.py writes dc/native/rXXX/ps2-world.ids next to each package); a hidden id is skipped and a moved
# one is drawn with its object's matrix. Render-only, logic STRICT; without the ids file a room draws as before. Part
# animation (chest lids) is not followed.
# MOVIE_STAGE_ORDER=1 (2026-10-06, adapted from 25c4cd0f into c36a08cc; render and memory only, logic STRICT): a route
# movie stages its heap 4 pieces largest first, so a fragmented heap 4 still fits them. PS2_WORLD_PARTS part pose
# storage had left r100 s30 failing to stage at 84,064 B free; with the order s30 plays 340/340 at that level. Gates
# at landing: H2 STRICT 0..740 / 1218..5696 / 1450..1569 with decision_cmp MUST-IDENTICAL, bell STRICT, New Game
# 1971 / 2360 / 1175. On 631cb271 (catalog pack d87983e1, ACT_CAP=0): s30 340/340 at heap_before 55,392, and 55,904
# with the scoped rifle armed (the rifle stays equipped); after s30 the first call in normal order (r101 first
# visit, call 0xC, voice stream 1:152) plays to its end and its sub screen closes with the backing restored; the
# Playing Manual follows as in the source, and after it Leon walks in r101.
#   ASSETS=<private asset dir: leon4k/ganado runtime headers, ganado_source_extras.h, vmu_dialog_english.inc>
#   OBJDIR=<fresh objdir per knob set: never seed one objdir from another (its .d files name the old
#          targets, so edited headers/includes silently keep stale objects)>  OUT=<elf dir>
#   build-r21.sh [extra make knobs, e.g. PC_SAMPLER=1]
# Disc media: the PS2 package ps2-world.re4mesh + ps2-world.r4pw (tools/ps2_world_r4im.py) go to
# /cd/dc/native/r101/ (fixture kite-mesh-fixture-r21.json in the private evidence).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
: "${ASSETS:?private asset dir}" "${OBJDIR:?objdir}" "${OUT:?output dir}"
mkdir -p "$OBJDIR" "$OUT"
cd "$ROOT"
export RE4DC_KOS_BASE=${RE4DC_KOS_BASE:-/root/work/kos-re4dc-d367}
export PATH=$RE4DC_KOS_BASE/utils/build_wrappers:/opt/toolchains/dc/sh-elf/bin:/usr/bin:/bin
source port/dreamcast/kos-env.sh
R21=(
  MESH_PRIME_LAZY=1 ACTOR_FOG_GATE=1 ACTOR_LEON_NATIVE_LOOK=1 ACTOR_SKIN_FTRV=1 ACTOR_SWAP=0 ACTOR_TRANSACTION=1
  ACTOR_VTX_KERNEL=1 ACT_CAP=0 AICA_AUDIO=1 AICA_STREAMS=1 ARENA_FIT=1 BRIDGE_LEAN=1 CHAR_DATA_BLOCK=1 COARSE=1
  COARSE_ACTOR_ASSET_DIR=$ASSETS COARSE_GANADO=1 COARSE_GANADO_CAST=1 COARSE_GANADO_LIMIT=-1 COARSE_GATE_ONCE=1
  COARSE_LEON=1 COARSE_NO_STD_SCENERY=0 COARSE_ONE_SUBMIT=1 COARSE_PREGATE=1 COARSE_SKIN_FTRV=1
  COARSE_SOURCE_ACTORS=1 COARSE_SOURCE_OBJECTS=1 COARSE_WORLD=0 COPY_LEAN=1
  CORE_RESIDENT_BYTES=1360608 CROWD_FLAT=1 CROWD_LOD=1 CROWD_MID_M=12 CROWD_NEAR=2 CROWD_NEAR_M=5
  D349_RENDERER_STACK=1 DBG_WARP=1 EFFECT_LEAN=1 EFFECT_SPRITES=1 EM10_SHARED=1 ENEMY_DEMAND=1 EVENT_FILES=1
  FOG_FAR=25000 FRONT_LEAN=1 FRONT_NATIVE=1 FX_LEAN=1 GAME_ACOS_LEAN=1 GAME_ATCHK=1 GAME_ATCHK_CACHE=1
  GAME_ATCHK_LIST=1 GAME_ATRECT_FAR=1 GAME_COLD_OS=1 GAME_COL_PREFETCH=1 GAME_CONCAT_COL=1 GAME_CPU=1
  GAME_CUBE_MEMO=1 GAME_DECISION_TRACE=1 GAME_EM10_IDFIRST=1 GAME_EMHIT_LIST=1 GAME_ESP_OWNER=1
  GAME_FP_CONTRACT=off GAME_FP_SCHED=1 GAME_FX_MOVE=1 GAME_FX_SCAN=1 GAME_HERMITE_FAST=1 GAME_HF_ASM=0
  GAME_HF_INLINE=1 GAME_HF_PF=1 GAME_ID_LISTS=1 GAME_LIGHT_LAZY=1 GAME_LINE_LEAF=1 GAME_LINE_LEAF2=1
  GAME_LINE_PIECE=1 GAME_LINE_TAIL=1 GAME_LINE_WALK=1 GAME_LINE_WALK_PF=1 GAME_LINE_YROW=1 GAME_MOTION_INDEX=1
  GAME_MTXINV_SCHED=1 GAME_MULTVEC_SCHED=1 GAME_O2=hot GAME_OBJHIT_IDFIRST=1 GAME_OBJHIT_LIST=1 GAME_OB_DECODE=1
  GAME_OB_MAT=1 GAME_OB_NEAR=1 GAME_OB_PATH=1 GAME_OB_SCAN=1 GAME_OT_MASK=1 GAME_PMC_KERNEL=1 GAME_PWC_DIAG=1
  GAME_PWC_KERNEL=3 GAME_PWC_PF=1 GAME_PWC_SCHED=1 GAME_ROTVEC_MEMO=1 GAME_ROT_CACHE=1 GAME_SCEAT_LIST=1
  GAME_SINCOS=1 GAME_SKEL_FTRV=1 GAME_SPHERE_WALK=1 GAME_TRIG=1 GAME_TRIG_LEAN=1 GAME_VEC_INLINE=1
  GAME_VEC_NORM_INLINE=1 GAME_WORKAT_INLINE=1 GROUND_LIGHT_FIX=0 HW_LEAN=1
  LINK_ORDER=$ROOT/port/dreamcast/game/link-order/r22-fsca-c3-8k.ld LOGIC_TRACE=1 LOGIC_TRACE_MASK_RENDER=1
  MESH_DIRECT=1 MESH_LOD=1 MESH_LOD_PX=3 MESH_TEXTURES=1 MODELINFO_DEMAND=1 MODEL_DRAW_PLANS=1
  MODEL_POSITION_CACHE=1 MODEL_ROOM_STRIPS=1 MODEL_SLAB_LATCH=1 MOTION_FAST_READ=1
  MOTION_LEASE_LEAN=0 NATIVE_ACTOR=1 NATIVE_ACTOR_DIRECT=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_LOD=1
  NATIVE_ACTOR_PRELIT=1 NATIVE_ACTOR_SKIN=1 NATIVE_ACTOR_SKIN_LAZY=1 NATIVE_FOG=1 NATIVE_MES=1 NATIVE_MESH=1
  NATIVE_PKG_HIGH=1 NATIVE_RENDER_PROFILE=0 NATIVE_REUSE_AUDIT=0 NATIVE_STATIC=1 NATIVE_STATIC_OWNERS=0x7F
  NO_EH=1 OBJDIR=$OBJDIR OBJECT_DEMAND=1 OPTION_RESIDENT_BYTES=149920 PACE_CATCHUP=2
  PACE_FORCE=0 PACE_MODE=off PACE_TRANS_SKIP=4063 PAD_PROMPTS=1 PAD_PROMPT_MANUAL_ART=1 PARTS_DEMAND=1
  PC_SAMPLER=0 PLAN_ADMIT_LEAN=1 PLAYER_RESIDENT_BYTES=869728 PVR_FAST_WAKE=1 PVR_PIPELINE=2
  PVR_STREAM=1 QUALITY=1 QUALITY_ASSETS=1 R100_DEFER_EVENTS=1 RELEASE_FLAGS=1 ROUTE_MOVIES=1 SCENERY_GATE=1
  SOUND_REGION_BYTES=0x60000 SS_POOL_HIGH=1 SS_UI_ORDER=1 SUBSCREEN=1 SUBSCREEN_OVL=1
  TARGET=$OUT/re4dc-game.elf TA_DIRECT=1 TA_DOUBLEBUF=1 TA_VERTBUF_KB=2048 TEX_RESIDENT=1 TREE_IMPOSTOR=1
  UI_FRAG_LATCH=1 UI_HANDLES=1 UI_HEADERS=1 UI_HEAP_LAZY=30 UI_OVERLAY_SLAB_KB=24 UI_PALETTE_SLOTS=32
  UI_QUAD_LEAN=1 UI_VRAM=1 VMU_DEBUG_SLOT=1 VMU_DIALOG=1 VMU_SAVE=1 VRAM_PAGES=1 WEAPON_RESIDENT_BYTES=275424 WEAPON_MODULES=1 WEAPON_HEAP4=1
  PRIM_CAP_R107=327680 WEAPON_HEAP4_TOP=1
  EFFECT_PS2_HAZE=1 EFFECT_PS2_STREAK=2
  ACTOR_TRANSACTION_DIAG=1 MOTION_PRESSURE_BYTES=262144 MOTION_OOM_EVICT=1 MOTION_RESERVE=1
  MOTION_RESERVE_SPILL=524288 COARSE_FX_SPRITES=2 COARSE_SCENERY_FALLBACK=1 AVK_RIGID6=1 GAME_WPAL_FAST=3
  GAME_SK1_ASM=1 ACTOR_STATS_LEAN=1 PS2_WORLD_DRAW=1 TA_GUARD=0 PS2_WORLD_KERNEL=0 PS2_WORLD_MESH=1
  PS2_WORLD_ROOMS=2 TEX_KEEP=1 IO_ALIGNED=1 DVD_WAIT=1 UI_HUD_MASK=1 UI_HUD_LENS_ALPHA=230 EFFECT_ROOM=7
  CROWD_READOPT=2 CROWD_CULL=1 CROWD_FOGSKIP=1 MESH_CLIP_LEAN=1
  TEX_SLOTS=448 MOVIE_WINDOW=1 IO_SERIAL=1 CRASH_SCREEN=1 SS_PACK=1 MOVIE_HEAP_EVICT=1 CLOSED_PASS_KEEP=1
  PS2_PRELOAD_LEAN=1 TEX_PACK=1
  PS2_WORLD_REGISTRY=1 PS2_OPEN_READ=1 SCENERY_ENCODING=1 PS2_WORLD_FOG_SOURCE=1 ACTOR_APPEARANCE_ALIAS=2
  ACTOR_GANADO_SOURCE_LIGHT=0 ACTOR_LIGHT_N16=1 NATIVE_MODEL_REGISTRY=1 NATIVE_MODEL_REGISTRY_PACK=1
  NATIVE_MODEL_REGISTRY_TX=1 NATIVE_MODEL_REGISTRY_PALBOUND=1 ACTOR_PL08=1 ACTOR_PL08_PACK=1 SS_CERT=1
  MESH_VP_SCHED=1 ACTOR_PROOF_LEAN=1 MESH_STRIP_LEAN=1 ACTOR_MATERIAL_RECORD=1
  COARSE_SAT_SCENERY_ONLY=1 SS_BG_BLACK=1 PACE_VMU=1
  SKIN_PALETTE_LAZY=1 ESP_SPRITE_FAST=1 ESP47_SKIP_LEAN=1 MODEL_PREP_KEEP=1 CROWD_READOPT_MEMO=1 ACTOR_BIND_REUSE=1
  PS2_WORLD_HDR_CACHE=1 MESH_CLIP_ACCEPT=1 PS2_PASS_MASK=1 GAME_HF_REG=1 GAME_CLOTH_SPRING=1 GAME_SND_WALL_ALT=1 GAME_ROT_FSCA=1
  CROWD_INVIS_SKIP=1 EFFECT_FADE_CLAMP=1 NATIVE_LASER=1
  PS2_INTERIOR_CULL=1 PS2_INTERIOR_ACTORS=2
  GAME_ATLIST_OVERFLOW=1 GAME_ATLIST_512=1
  PS2_WORLD_DYNAMIC=1
  PS2_WORLD_PARTS=1 ITEM_UI_ORDER=1 MOVIE_STAGE_ORDER=1
)
# Every recipe and caller knob must be a name the makefiles read (assigned, expanded, or tested with ifdef / ifndef /
# origin): a dead or misspelled knob would build without its effect and never show in resolved-knobs.txt (review
# 2026-10-04, which dropped COARSE_WORLD_LAYERS, MOTION_HASH, NATIVE_STATIC_PROBE_SKIP, PS2_SOURCE_SPANS and
# SOURCE_CENSUS: all 0 here and read by nothing).
KNOWN=$(cat port/dreamcast/game/Makefile port/dreamcast/game/*.mk |
  grep -oE '\$[({][A-Z][A-Z0-9_]*[)}]|^[[:space:]]*(override[[:space:]]+|export[[:space:]]+)?[A-Z][A-Z0-9_]*[[:space:]]*[?:+]?=|^[[:space:]]*if(n)?def[[:space:]]+[A-Z][A-Z0-9_]*|origin[[:space:]]+[A-Z][A-Z0-9_]*' |
  grep -oE '[A-Z][A-Z0-9_]*' | sort -u)
DEAD=
for kv in "${R21[@]}" "$@"; do
  case "$kv" in [A-Z]*=*) k=${kv%%=*}; grep -qx -- "$k" <<<"$KNOWN" || DEAD="$DEAD $k" ;; esac
done
[ -z "$DEAD" ] || { echo "build-r21.sh: knobs no makefile reads (dead or misspelled):$DEAD" >&2; exit 1; }
make -C port/dreamcast/game -j4 all "${R21[@]}" "$@"
# The knobs as make resolved them (defaults, this line, the caller's overrides, Makefile overrides).
NAMES=$(sed -nE 's/^(override +)?([A-Z][A-Z0-9_]*) *[?:]?=( .*)?$/\2/p' port/dreamcast/game/Makefile port/dreamcast/game/*.mk | sort -u | tr '\n' ' ')
make -s -C port/dreamcast/game re4dc-knobs "${R21[@]}" "$@" KNOBS_FILE="$OUT/resolved-knobs.txt" KNOB_NAMES="$NAMES"
