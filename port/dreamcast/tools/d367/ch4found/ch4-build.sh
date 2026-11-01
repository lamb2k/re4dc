#!/bin/bash
# ch4-build.sh <arm>...  (WSL; lane ch4found16, 2026-10-17): chapter 4 (castle 4-1..4-4) arms = the test 15 recipe
#   (test15/t15-build.sh T15REC, read from that script, never retyped) + the castle / chapter 4 knobs ($CH4), as
#   ch2/ch2-build.sh does for chapter 2. With CH4="" an arm is the test 15 release recipe itself (identity arm xP).
# Arms (same letters as t15-build.sh): rP play, rW warp, mW warp + MCHECK_LEONGC=1 TEX_CHECK=2, rT trace;
#   xP / xW / xT = the same with CH4="" (knob-off identity and STRICT references on this tree).
# Env: T (tree, default this checkout), K (logs, default /root/probe/lanes-20261016/ch4found/k), LP (label prefix,
#      default c4), CH4 (chapter 4 knobs, default CH4REC below), XON (extra test knobs), PE2 / PE3 / PE4 (private PS2
#      enemy include dirs for chapters 2 / 3 / 4: generated game data, never committed).
# Data set: CH4-FOUNDATIONS-20261016.md (ch3found's ch3f-c + fix/ch4-add*.json).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
export T=${T:-$(cd "$HERE/../../../../.." && pwd)}
export K=${K:-/root/probe/lanes-20261016/ch4found/k}
PE2=${PE2:-/root/probe/codex-ch23-20261013/private-include}
PE3=${PE3:-/root/probe/lanes-20261015/castle/private-include}
PE4=${PE4:-/root/probe/lanes-20261016/ch4found/private-include}
# CH4REC: the route to the castle (ROUTE_CH22 / ROUTE_CH23 / EM10_SHARED), chapter 3 (ROUTE_CH31 / ROUTE_CH32, its
#   movies, PS2_CH3_ENEMY, FOG_OFF_CLEAR, WORLD_ROOM_MODULES, STAGE_OVL, SS_POOL_TOP, ROUTE_BOSS4), chapter 4
#   (ROUTE_CH41, ROUTE_MOVIES_CH4, PS2_CH4_ENEMY with the shared cap 4, LEON_OT_WATER=2 for r219), the castle disc's single
#   stream file (CH3 + CH4, 73 entries: AICA_STR_ENT_MAX=80, aica_banks.py --streams castle; coordinator 10-17) and the
#   castle cold-pool margin MOTION_COLD_POOL_CASTLE=131072 (r226 em11: no slab thrash; coordinator 10-17).
#   Castle cast (lane cast16, coordinator 10-17): NATIVE_MODEL_REGISTRY_DYING=1 (a dying registry-planned enemy keeps
#   its PS2 model through the death fade instead of the GameCube model: r218 em1c 5,073 GC frames -> 0, r227 / r21b
#   0), NATIVE_MODEL_REGISTRY_RUN_SHARE=1 (a pool mask run shared by two sections with byte-identical roles shares
#   its chunk proof: em1c 09h acc38-b), NATIVE_MODEL_REGISTRY_BLENDTBL=1 (em2d Novistador camouflage idle blend
#   table: r213 / r21d native). Render only; STRICT r218 / r227 / r213; kills identical.
#   PRIM_CAP_R226=327680 (lane ch4found16, coordinator 10-17): r226's primitive buffer (room value 442,368 B) at its
#   150 s fight peak x ~1.1 (PRIM_WATER peak 300,928 B cast on, overflow 0), heap 4 for the statue fight.
# Recovered cast16 packages need the same source-selection/role bounds as their qualified castle arms:
# FIRST selects registry Ganados, LOD keeps reviewed gameplay boss levels, ROLES5 admits r216's 201 part facts
# and r227's 329920-byte pack. BUMP_FLAT preserves the reviewed dropped-bump source contract; STATUE_LIGHTS=2
# is the approved r226 statue evaluator. All already gated together on c18amW and its 48KiB KOS twin.
# Ashley uses the chapter 2 bounded v3 archive unchanged throughout the castle.
# The exact-source v3 admission remains behind its existing default-off knob;
# without it, the castle runtime rejects the same archive chapter 2 accepts.
# I-006: Novistadors share the existing four Ganado slots. All four effective Novis rooms
# pass matched source progress/pointer gates; extras remain queued, never deleted.
# EVENT_SWAP_RELOAD remains separate pending the full event route gate.
# Complete r202 monks + both Merchant appearances + full Ashley need 69 geometry entries.
# Host loader15cases, paired r202 CAST/TEX/zero-late/KOS and current343 r10148KiB/min5160 qualified.
# Linked joint fallback preserves source indexing; current343 busy-r10148KiB min5000,
# exact off11payload identity and fresh native-r202 fragmented37part/finite matrices qualified.
CH4REC="ROUTE_CH22=1 ROUTE_CH23=1 MOTION_BOUNDED_R11F=1 EM10_SHARED=1 ROUTE_CH31=1 ROUTE_CH32=1 ROUTE_MOVIES=1 ROUTE_MOVIES_CH3=1 LEON_OT_WATER=2 FOG_OFF_CLEAR=1 PS2_CH3_ENEMY=1 WORLD_ROOM_MODULES=1 ROUTE_BOSS4=1 ROUTE_CH41=1 STAGE_OVL=1 SS_POOL_TOP=1 PS2_ENEMY_CH22_DIR=$PE2 PS2_ENEMY_CH23_DIR=$PE2 PS2_ENEMY_CH3_DIR=$PE3 PS2_CH4_ENEMY=1 PS2_ENEMY_CH4_DIR=$PE4 ROUTE_MOVIES_CH4=1 AICA_STR_ENT_MAX=80 MOTION_COLD_POOL_CASTLE=131072 NATIVE_MODEL_REGISTRY_DYING=1 NATIVE_MODEL_REGISTRY_RUN_SHARE=1 NATIVE_MODEL_REGISTRY_BLENDTBL=1 PRIM_CAP_R226=327680 NATIVE_MODEL_REGISTRY_FIRST=1 NATIVE_MODEL_REGISTRY_LOD=1 NATIVE_MODEL_REGISTRY_ROLES5=1 NATIVE_BUMP_FLAT=1 STATUE_LIGHTS=2 ALIVE_CAP=4 ALIVE_CAP_NOVIS=1 LEON_SKIN_SLOTS=2 NMR_R202_CAST_CAPACITY=1 ALIVE_CAP_R202_GATE=1 PARTS_LINKED_FLAG=1 SS_CERT_PARTNER_CAPACITY=1 FX_MIST_PS2=1 HAZE_SPRITE_CUT=1 PS2_HDR_SETS=128 ACTOR_PLAN=1 ALIVE_CAP_DEFER_FLAGS=1 TEX_PKG_SKIP_LISTED=1 PS2_ASHLEY=2 NATIVE_MODEL_REGISTRY_PL_ASHLEY=1"
CH4=${CH4-$CH4REC}
# T15REC as test15/t15-build.sh defines it (its assignments only, up to the arm table).
T15REC=$(bash -c "set -u; $(sed -n '/^K=/,/^T15REC=/p' "$T/port/dreamcast/tools/d367/test15/t15-build.sh" | grep -v '^K=\|^T=') ; echo \"\$T15REC\"")
[ -n "$T15REC" ] || { echo "ch4-build: T15REC not found"; exit 2; }
mkdir -p "$K"
L=${LP:-c4}
for x in "$@"; do
  case $x in
    rP|rW|mW|rT) T15="$T15REC $CH4" LP=$L XON="${XON:-}" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" $x ;;
    xP) T15="$T15REC" LP=${L}x XON="" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" rP ;;
    xW) T15="$T15REC" LP=${L}x XON="${XON:-}" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" rW ;;
    xT) T15="$T15REC" LP=${L}x XON="${XON:-}" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" rT ;;
    *) echo "arm? $x" ;;
  esac
done
