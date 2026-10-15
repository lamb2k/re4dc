#!/bin/bash
# t14-build.sh <arm>...: test 14 build arms (t14/rc, 2026-10-15; scope C:\Game Dev\Emulators\TEST14-SCOPE.md: tranche 1 of
#   PERF-BACKLOG-CH1-2-20261015.md) = the test 13 recipe (test13/t13-build.sh arm rP, unchanged: BASE + T13REC) + the
#   test 14 knobs ($T14). Every test 14 knob is default 0 in the Makefiles: with T14="" (arm kP) the play image must be
#   byte-identical to test 13's (objcopy -R .stack image c1ae83dd, out-t13mrP, tag test-05e5ff76-20261015).
# Arms: rP release play (packaged by test14/t14-package.sh), rW warp, mW warp + MCHECK_LEONGC=1 TEX_CHECK=2, rT trace,
#       kP knob-off play (identity vs 13), kT knob-off trace (the STRICT reference for rT: no test 14 knob changes
#       gameplay). The benchmark disc variant is benchpub/bench-build.sh on the definitive bench program with $T14.
# Env: T (tree, default $K/tree), LP (label prefix, default t14rc), T14 (test 14 knobs, default T14REC), XON (extra knobs,
#      test only), PAD_T / PAD_K (trace image pads).
# The data set must match: T14_DATA in test11/t11-fix.py (= T13_DATA + res14r3: dc/resident.bin with the r101 + r103
# resident lists and the r000 core set).
set -u
K=${K:-/root/probe/lanes-20261015/t14rc}
T=${T:-$K/tree}
export SOURCE_DATE_EPOCH=1760000000
F="PACE_DEBUG=1 ROUTE_CH13=1 ROUTE_CH21=1 SBB_STUB=1 PVR_READY_STRICT=1 ACT_CAP=0 PS2_INTERIOR_ACTORS=2 GAME_ATLIST_OVERFLOW=1 GAME_ATLIST_512=1 LEON_NATIVE_PIPE=0 LEON_FACE_LAZY=0 NATIVE_LASER=1 ACTOR_GANADO_SOURCE_LIGHT=0 PRIM_CAP_R10B=327680"
LOOK="EFFECT_PS2_TOGGLE=1 LOOK_TOGGLE=1 FILTER00_DC=1 CHARBAKE_TOGGLE=1 CHARBAKE_HAIR=0"
PS2="PS2_LEON=1 PS2_LEON_DIR=/root/probe/lanes-20261011/pl08/assets/arm-a ACTOR_PL08_PACK=1 PS2_GANADO=1 PS2_GANADO_DIR=/root/probe/lanes-20261010/ps2cast-all-assets/pg5 PS2_GANADO_F=1 PS2_GIGANTE=1 PS2_DELLAGO=1 PS2_VERTEX_ALPHA=1"
P2="MOVIE_DISC_QUIET=1 EFFECT_HAZE_LEAN=3 EFFECT_HAZE_LEAN_TOGGLE=0 RENDER_OPTION=1 PS2_GANADO_LIT=1 CAST_MIPMAP=1 PS2_CROW=1 PS2_ANIMALS=1 PS2_WOLF=1 HEAP4_PARTS_RESERVE=1 DVD_READ_SAFE=1 LAKE_RIPPLES=1 VGA_SOFT=1 LETTERBOX_CLIP=1 PS2_PT_CUTOUT=1 PACE_VMU=1 PACE_VMU_GPU=1 UI_FRAG_RESERVE=1"
T9K="DOOR_FREEZE=1 LOAD_INDICATOR=1 VMU_CONTEXT=1 OPTION_ROW_STYLE=1 PT_BLEND_FIX=1 MODEL_STREAM_FIX=1 SS_MENU_ANIM_RT=1 PS2_ENEMY_RULES=1 ACT_CAP_TABLE=1 RENDER_QUALITY_ONLY=1 RESET_HEAP_FIX=1"
HANDS="LEON_HAND_POSES=1 LEON_HAND_PACK=1 LEON_SKIN_SLOTS=1"
T11REC="PS2_R100_SMX=1 PS2_R100_TR4=1 LAKE_ZBIAS=1.001 WORLD_HOLE_FIX=1 SPEED_VMU_OFF=2 TEX_REF_SELFKEY=1 MOVIE_HEAP_PREFLIGHT=1 PS2_FX_ROOMS=1 PS2_FX_STAGE1=1 PS2_FX_POPULATION=1 PS2_FX_ADDITIONS=1 PS2_FX_ROOMS_EXT=1 EFFECT_TORCH=1 RAIN_PS2=1 ACTOR_PROBE_LIGHT=1 LEON_SOURCE_LIGHT=1 LEON_LIGHT_HEADROOM=1 PS2_ENEMY_ROOMS=0x3f MV_SHADOWS=1"
T12REC="UI_SOURCE_LRU=1 HW_FOG_HAZE=1 FX_SPRITE_TRIM=2 TEX_PAL4_ALPHA=1 FX_PS2_PACK=1 FX_FLIPBOOK=2 R101_ALIVE_CAP=6 TEX_WRAP_SAFE=1 PS2_CAST_MERCHANT=1 ACTOR_GANADO_APP0_GRIP=1 RENDER_FSAA=1 GC_STUB_SKIP=1 OWNER_SETUP_LEAN=1 TEX_IDENT_LEAN=1 PS2_WORLD_LEAN=23 PS2_STRIP_GROUPS=1 PS2_ROOM_PIN=1 LEON_LIGHT_FILL=45 VRAM_ROOM_LOG=1 EFM_PS2_CUT=1 STATIC_OBJ_BATCH=2 TEX_META_EVICT=1 PRELOAD_LARGE_FIRST=1 ROOM_RESIDENT=1 SS_FREEZE_RESERVE=1 DCINV_PURGE=1 MAPLE_RECV_PURGE=1 ARENA_FIT_KOS_BYTES=196608"
T122="RETIRE_KOS_FLOOR=65536"
# Test 13 knobs (TEST13-SCOPE.md items 1..6; item 7 is a tool):
#   6 ROOM_CHANGE_EVICT=60 (T13_6; lane t13-rce bdb2b431; render only, needs TEX_KEEP=1: LRU order across a room change,
#     the old room's leftovers not drawn in its last 60 frames are evicted at the next room's first preload pass)
#   1 STATIC_OBJ_BAKE=1 + PS2_PLACE_GATE=1 (lane crowd12-t13 ce0b7a82; render only; data bake13), and
#     STATIC_OBJ_BATCH_WORDCMP=1 (the same branch's 5149da0a word compare for STATIC_OBJ_BATCH, which was not behind a knob
#     and changed the 12.2 image; the RC put it behind this knob so that kP stays identical; exact, render only)
#   3 PS2_ASHLEY=2 PS2_ASHLEY_ROOMS=1 (lane ps2cast3 d940cbc0; render only; data ashley13; user choice B: PS2 model, rest face)
#   4 PS2_CH1_ENEMY=1 (lane alivecap-1015 659f2280; GAMEPLAY by design: PS2 chapter 1 enemy rules + ALIVE_CAP=6 +
#     ALIVE_CAP_PARK + R101_CAP_WAVES; gated by the decisions check of ALIVECAP-20261015.md, not by STRICT)
#   5 GAME_LQ_MEMO=1 (exact, logic; STRICT), LEON_FACE_LAZY=1 (exact, render), PS2_AREA_HIDE=1 (r107, render only)
#     (the GC render census removals of item 5 were never built: no knob)
#   2 objs13 is data only (objs13d)
#   8 UI_FRAG_WINDOW=3 (user pull-in 10-15 under release rule 1; t11 lane vr knob + the RC's =3, render only): an upload of
#     128 KiB or more refused for fragmentation releases one idle window of the size instead of LRU evictions; fixes the
#     r105 chapter 1-2 results picture (eaf5d457 495x150, "no contiguous block", 120-frame latch) that objs13's r105
#     layout exposed. =1 (all sizes) dropped r100 s20 effect sprites (H2 guard_p 0 -> 11/15); =3 proof 10-15: r105 0
#     no-contiguous, loaded once; H2 r100 guard_p 0 (arms t13w0rW / t13w3rW / t13y1rW). =2 stays out (test 11 crash).
T13R="STATIC_OBJ_BAKE=1 PS2_PLACE_GATE=1 STATIC_OBJ_BATCH_WORDCMP=1 PS2_ASHLEY=2 PS2_ASHLEY_ROOMS=1 GAME_LQ_MEMO=1 LEON_FACE_LAZY=1 PS2_AREA_HIDE=1 UI_FRAG_WINDOW=3"
T13G="PS2_CH1_ENEMY=1"
T13_6=${T13_6-ROOM_CHANGE_EVICT=60}
T13REC="$T13R $T13G $T13_6"
T13=${T13-$T13REC}
# Test 14 knobs (TEST14-SCOPE.md rows; all render, I/O or exact: STRICT rT vs kT, identity kP vs test 13):
#   1  (knobs out, see below) SS_HOLD_RESTORE=1 CORE_PIN=1 + data res14 (lane t14-r101res; VRAM rule: r101 resident list complete, the sub screen
#      hold restores the evicted room keys at the close, the HUD core set is never evicted)
#   17 MOTION_COLD_POOL=262144 + data res14r3 (lane t14-r103res c9dc83ed: cold motion keys in heap 4 instead of slab
#      eviction; the r103 resident list)
#   15 G1_DIAG_INLINE=1 G1_FP_UNSIGNED=1 G1_PRESORT_LAZY=1 (lane g1parts 7979c550; exact; PRESORT_LAZY needs
#      PVR_READY_STRICT=1, which F sets)
#   -  ACTOR_NO_CLEAR=1 (lane memlay d270ca82; render only; T14_NC, in only if its gates pass on the merge). Row 14
#      MEMSET_LEAN stays 0 (ACTOR_NO_CLEAR covers its clear).
#   11/12 subset: DISC_COMPAT=1 DISC_READ_FALLBACK=0 (lane discread 2cfb535d; forces KOS_DISC_FIX=1: the KOS GD-DMA
#      completion fix + fs_iso9660 mutex; the timing-neutral subset, STRICT in Flycast). Product number unchanged (T0000).
#   18 GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1 (lane sh4zam-direct e4e3336c; render only, not bit-exact: STRICT logic, the
#      look accepted by the user 10-15)
#   Row 1's knobs are OUT after the RC gates on the intermediate candidate (bb2c4c51, 10-15): CORE_PIN=1 kept the 4 HUD
#   keys pinned through r105's chapter 1-2 results screen, which then found no contiguous 512 KiB block for its 631x169
#   picture (texchk FAIL, crash suite ch12) and refused 63-102 effect sprites (guard_p; test 13: 8). SS_HOLD_RESTORE=1
#   alone matched test 13 there (8) but restores nothing without CORE_PIN (lane note: the HUD is hidden before the
#   post-bell call); without both r105 refuses 0. Row 1's data (the r101 list in res14r3) stays: r101 bell 0 uploads
#   after the preload (test 13: 4).
T14_1=${T14_1-}
T14_18="GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1"
T14_17="MOTION_COLD_POOL=262144"
# RC fix 10-15 (coordinator option b): ROOM_REENTRY_EVICT=1, the r101 death / Continue re-entry fragmentation (crash death)
T14_RE=${T14_RE-ROOM_REENTRY_EVICT=1}
T14_15="G1_DIAG_INLINE=1 G1_FP_UNSIGNED=1 G1_PRESORT_LAZY=1"
T14_NC=${T14_NC-ACTOR_NO_CLEAR=1}
# T14_DISC="" (env): the variant without the disc items (KOS_DISC_FIX=0), ready in case the console verdict on
# KOS_DISC_FIX goes against it (LinkOrder2 console halt 10-15, "invalid prepared enemy motion archive", under analysis).
T14_DISC=${T14_DISC-DISC_COMPAT=1 DISC_READ_FALLBACK=0}
T14REC="$T14_1 $T14_17 $T14_15 $T14_NC $T14_DISC $T14_18 $T14_RE MEMSET_LEAN=0"
T14=${T14-$T14REC}
ON="$T9K PVR_LATCH=2 PVR_RECOVER=1 TA_HEADROOM=1 CRASH_TASK_DETAIL=1 $PS2 $P2 $HANDS"
BASE="$ON $T11REC $T12REC $T122"
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
L=${LP:-t14rc}
mkdir -p $K
for x in "$@"; do case $x in
  rP)  b ${L}rP  $T $BASE $T13 $T14 IMAGE_PAD_BYTES=0 $PL ;;
  rW)  b ${L}rW  $T $BASE $T13 $T14 IMAGE_PAD_BYTES=0 $WP ${XON:-} ;;
  mW)  b ${L}mW  $T $BASE $T13 $T14 IMAGE_PAD_BYTES=0 $WP $MC ${XON:-} ;;
  rT)  b ${L}rT  $T $BASE $T13 $T14 IMAGE_PAD_BYTES=${PAD_T:-0} $TR ${XON:-} ;;
  kP)  b ${L}kP  $T $BASE $T13 IMAGE_PAD_BYTES=0 $PL ;;
  kW)  b ${L}kW  $T $BASE $T13 IMAGE_PAD_BYTES=0 $WP ${XON:-} ;;
  kT)  b ${L}kT  $T $BASE $T13 IMAGE_PAD_BYTES=${PAD_K:-0} $TR ${XON:-} ;;
  *) echo "arm? $x" ;;
esac; done
