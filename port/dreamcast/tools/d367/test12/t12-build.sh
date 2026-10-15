#!/bin/bash
# t12-build.sh <arm>...: test 12 build arms (DRY RUN integration, 2026-10-15) = the test 11 recipe (test11/t11-build.sh
#   T11REC, unchanged) + the test 12 knobs ($T12), built from branch t12/rc-dry (lane/t11 20a3b047 + the READY lanes,
#   see C:\Game Dev\Emulators\TEST12-RC-DRYRUN.md). Every test 12 knob is default 0 in the Makefiles: with T12=""
#   (arm kP) the play image must be byte-identical to lane/t11's play image (arm cP, built from a lane/t11 checkout).
# Arms: pP preview play = tP + DCINV_PURGE=1 (T12 Preview console disc, 10-15; not the release recipe yet),
#       tP play (packaged), tW warp, mW warp + MCHECK_LEONGC=1 TEX_CHECK=2, tT trace,
#       kP knob-off play (identity vs cP), kT knob-off trace (STRICT control), cP lane/t11 control play (tree $CT).
# Env: T (tree, default $K/tree), CT (lane/t11 control tree, default $K/ctl), LP (label prefix, default t12rc),
#      T12 (test 12 knobs, default the recipe below), XON (extra knobs, test only), PAD_T / PAD_K (trace image pads).
set -u
K=${K:-/root/probe/lanes-20261014/t12rc}
T=${T:-$K/tree}
CT=${CT:-$K/ctl}
export SOURCE_DATE_EPOCH=1760000000
F="PACE_DEBUG=1 ROUTE_CH13=1 ROUTE_CH21=1 SBB_STUB=1 PVR_READY_STRICT=1 ACT_CAP=0 PS2_INTERIOR_ACTORS=2 GAME_ATLIST_OVERFLOW=1 GAME_ATLIST_512=1 LEON_NATIVE_PIPE=0 LEON_FACE_LAZY=0 NATIVE_LASER=1 ACTOR_GANADO_SOURCE_LIGHT=0 PRIM_CAP_R10B=327680"
LOOK="EFFECT_PS2_TOGGLE=1 LOOK_TOGGLE=1 FILTER00_DC=1 CHARBAKE_TOGGLE=1 CHARBAKE_HAIR=0"
PS2="PS2_LEON=1 PS2_LEON_DIR=/root/probe/lanes-20261011/pl08/assets/arm-a ACTOR_PL08_PACK=1 PS2_GANADO=1 PS2_GANADO_DIR=/root/probe/lanes-20261010/ps2cast-all-assets/pg5 PS2_GANADO_F=1 PS2_GIGANTE=1 PS2_DELLAGO=1 PS2_VERTEX_ALPHA=1"
P2="MOVIE_DISC_QUIET=1 EFFECT_HAZE_LEAN=3 EFFECT_HAZE_LEAN_TOGGLE=0 RENDER_OPTION=1 PS2_GANADO_LIT=1 CAST_MIPMAP=1 PS2_CROW=1 PS2_ANIMALS=1 PS2_WOLF=1 HEAP4_PARTS_RESERVE=1 DVD_READ_SAFE=1 LAKE_RIPPLES=1 VGA_SOFT=1 LETTERBOX_CLIP=1 PS2_PT_CUTOUT=1 PACE_VMU=1 PACE_VMU_GPU=1 UI_FRAG_RESERVE=1"
T9K="DOOR_FREEZE=1 LOAD_INDICATOR=1 VMU_CONTEXT=1 OPTION_ROW_STYLE=1 PT_BLEND_FIX=1 MODEL_STREAM_FIX=1 SS_MENU_ANIM_RT=1 PS2_ENEMY_RULES=1 ACT_CAP_TABLE=1 RENDER_QUALITY_ONLY=1 RESET_HEAP_FIX=1"
HANDS="LEON_HAND_POSES=1 LEON_HAND_PACK=1 LEON_SKIN_SLOTS=1"
# test 11 release recipe (test11/t11-build.sh T11REC at 20a3b047, unchanged)
T11REC="PS2_R100_SMX=1 PS2_R100_TR4=1 LAKE_ZBIAS=1.001 WORLD_HOLE_FIX=1 SPEED_VMU_OFF=2 TEX_REF_SELFKEY=1 MOVIE_HEAP_PREFLIGHT=1 PS2_FX_ROOMS=1 PS2_FX_STAGE1=1 PS2_FX_POPULATION=1 PS2_FX_ADDITIONS=1 PS2_FX_ROOMS_EXT=1 EFFECT_TORCH=1 RAIN_PS2=1 ACTOR_PROBE_LIGHT=1 LEON_SOURCE_LIGHT=1 LEON_LIGHT_HEADROOM=1 PS2_ENEMY_ROOMS=0x3f MV_SHADOWS=1"
# test 12 knobs (TEST12-SCOPE.md READY rows). The data set must match: T12_DATA in test11/t11-fix.py (tex.pak with the
# PS2 effect library + r101 world VQ + wrap-safe marks, objs r101.dar, merchant r102 files). PS2_CAST_MERCHANT_LIT stays 0
# (user look pending). D1 (eeef15ae) is code only, no knob. Round 2 (10-15): crowd12's exact render-only knobs
# GC_STUB_SKIP (5a887bb8), OWNER_SETUP_LEAN (ce5cfe7f + 1598a1de), TEX_IDENT_LEAN (33825081). Leon VQ is data (t12tex).
# Objs world knobs (lane objs-w, accepted 10-15): PS2_WORLD_LEAN=23 PS2_STRIP_GROUPS=1 PS2_ROOM_PIN=1 (data sg101 + objs12).
# Leon fill (light-p3 5ccb3a9b, user: "just dark... fix in 12"; 45 = GameCube brightness; needs ACTOR_PROBE_LIGHT=1).
# VRAM_ROOM_LOG=1 (lane vram12 D4 37326252): per-room VRAM report lines for vram_gate.py / fp_check.
# EFM_PS2_CUT=1 (lane items 24526dfb): the debris models the PS2 deleted are not drawn (render only; data items12).
# acc12 (fdc16424) and items are data: T12_DATA items12 + acc12d, packages in tex-t12d.pak. DCINV_PURGE (d6c6337f) stays
# 0 until the console confirms it (coordinator 10-15); DISC_READ_VERIFY / DISC_GD_ATOMIC stay 0 (their discs crash).
# STATIC_OBJ_BATCH=2 (lane crowd12 76ffb399, coordinator 10-15): static object display lists batched per lit group
# (render only; -1.74 ms MODELLED at cap 6; +2,368 B image, which ARENA_FIT takes from heap 4, not KOS).
# R101_ALIVE_CAP=6 (user rule 10-15: "Ganados at 6 instead should be the rule"; was 8).
# SS_FREEZE_RESERVE=1 (10-15, T12 Preview console HALT "MISSING sub screen pool freeze allocation" at the first radio
# call; user: "prob needs memory back"): the sub screen freeze copies + stand-in (12,248 B at r100) from a static 16 KiB
# block, not KOS. Costs 16 KiB of heap 4 (ARENA_FIT).
# VRAM lane D5 (vram12, 10-15; render only): VRAM_ROOM_LOG (D4 per-room VRAM lines), TEX_META_EVICT (one KOS block per
# texture package, an 8 KiB KOS reserve, native model slab before the preload), PRELOAD_LARGE_FIRST, ROOM_RESIDENT (data:
# dc/resident.bin in t12tex, from vram/resident/*.tsv by test12/t12-texpak.sh).
# Release candidate (10-15, user: publish test 12 as is): DCINV_PURGE=1 (console-confirmed with preview 2) and
# MAPLE_RECV_PURGE=1 (6dc50f58, controller / VMU detection at boot) join T12REC; arm pP is now the same image as tP.
# ARENA_FIT_KOS_BYTES=196608 (10-15, release blocker: preview 2 ran out of KOS memory in the r101 fight on the console;
# the release recipe left 7.2 KB KOS headroom at r101 setup, 8.5 KB in the fight): KOS keeps 64 KiB more, heap 4 64 KiB
# less (ARENA_FIT). T12_KOS overrides it for trials.
T12REC="UI_SOURCE_LRU=1 HW_FOG_HAZE=1 FX_SPRITE_TRIM=2 TEX_PAL4_ALPHA=1 FX_PS2_PACK=1 FX_FLIPBOOK=2 R101_ALIVE_CAP=6 TEX_WRAP_SAFE=1 PS2_CAST_MERCHANT=1 ACTOR_GANADO_APP0_GRIP=1 RENDER_FSAA=1 GC_STUB_SKIP=1 OWNER_SETUP_LEAN=1 TEX_IDENT_LEAN=1 PS2_WORLD_LEAN=23 PS2_STRIP_GROUPS=1 PS2_ROOM_PIN=1 LEON_LIGHT_FILL=45 VRAM_ROOM_LOG=1 EFM_PS2_CUT=1 STATIC_OBJ_BATCH=2 TEX_META_EVICT=1 PRELOAD_LARGE_FIRST=1 ROOM_RESIDENT=1 SS_FREEZE_RESERVE=1 DCINV_PURGE=1 MAPLE_RECV_PURGE=1 ARENA_FIT_KOS_BYTES=${T12_KOS:-196608}"
T12=${T12-$T12REC}
ON="$T9K PVR_LATCH=2 PVR_RECOVER=1 TA_HEADROOM=1 CRASH_TASK_DETAIL=1 $PS2 $P2 $HANDS"
MC="MCHECK_LEONGC=1 TEX_CHECK=2"
TR="DBG_WARP=1 PC_SAMPLER=1 LOGIC_TRACE=1 GAME_DECISION_TRACE=1 PACE_MODE=off TRACE_SS_MASK=1 TRACE_ALLOC=1 CODEC_READY_FIXTURE=1"
WP="DBG_WARP=1 PC_SAMPLER=1"
PL="DBG_WARP=0 PC_SAMPLER=0"
b() { lab=$1; tree=$2; shift 2; t0=$(date +%s); echo "== $lab $(date +%T) tree=$tree $*" >> $K/logs-build.txt
  (cd $tree && TREE=$tree bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh $lab $F $LOOK "$@" >> $K/logs-build.txt 2>&1)
  rc=$?; O=/root/probe/lanes/route/out-$lab
  end=$(/opt/toolchains/dc/sh-elf/bin/sh-elf-nm $O/re4dc-game.elf 2>/dev/null | awk '$3=="_end"{print $1}')
  echo "rc=$rc $lab $(cut -c1-16 $O/elf.sha256 2>/dev/null) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt 2>/dev/null) end=$end $(cd $tree && git rev-parse --short=8 HEAD) $*" | sed 's/PS2_LEON_DIR=[^ ]* //;s/PS2_GANADO_DIR=[^ ]* //' | tee -a $K/logs-build.txt | cut -c1-400
  echo "$end" > $O/end.txt; }
L=${LP:-t12rc}
for x in "$@"; do case $x in
  tP)  b ${L}tP  $T $ON $T11REC $T12 IMAGE_PAD_BYTES=0 $PL ;;
  pP)  b ${L}pP  $T $ON $T11REC $T12 DCINV_PURGE=1 IMAGE_PAD_BYTES=0 $PL ;;
  tW)  b ${L}tW  $T $ON $T11REC $T12 IMAGE_PAD_BYTES=0 $WP ${XON:-} ;;
  mW)  b ${L}mW  $T $ON $T11REC $T12 IMAGE_PAD_BYTES=0 $WP $MC ${XON:-} ;;
  tT)  b ${L}tT  $T $ON $T11REC $T12 IMAGE_PAD_BYTES=${PAD_T:-0} $TR ${XON:-} ;;
  kP)  b ${L}kP  $T $ON $T11REC IMAGE_PAD_BYTES=0 $PL ;;
  kT)  b ${L}kT  $T $ON $T11REC IMAGE_PAD_BYTES=${PAD_K:-0} $TR ;;
  cP)  b ${L}cP  $CT $ON $T11REC IMAGE_PAD_BYTES=0 $PL ;;
  *) echo "arm? $x" ;;
esac; done
