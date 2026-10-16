#!/bin/bash
# ch2-build.sh <arm>...  (WSL; lane ch2code16, 2026-10-16): chapter 2 (2-2 / 2-3) code-complete arms = the test 15 recipe
#   (test15/t15-build.sh T15REC, read from that script, never retyped) + the chapter 2 knobs ($CH2). With CH2="" an arm is
#   the test 15 release recipe itself (identity arm xP: its image must equal t15/int's rP).
# Arms (same letters as t15-build.sh): rP play, rW warp, mW warp + MCHECK_LEONGC=1 TEX_CHECK=2, rT trace;
#   xP / xW / xT = the same with CH2="" (knob-off identity and STRICT references on this tree).
# Env: T (tree, default this checkout), K (logs, default /root/probe/lanes-20261016/ch2/k), LP (label prefix, default c2),
#      CH2 (chapter 2 knobs, default CH2REC below), XON (extra test knobs), PE (PS2 enemy include dir).
# Data set: test11/t11-fix.py T15_DATA + ch2 (CH2-CODE-COMPLETE-20261016.md).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
export T=${T:-$(cd "$HERE/../../../../.." && pwd)}
export K=${K:-/root/probe/lanes-20261016/ch2/k}
# The qualified PS2 enemy rows (private generated game data, never committed): Codex's ch22/ch23 tables (codex-ch23-20261013/private-include), copied
# here and to the private store re4-assets-private/ps2enemy-ch2-20261016 (no spaces allowed in a make knob path).
PE=${PE:-/root/re4data/private/ps2enemy-ch2-20261016}
# CH2REC: ROUTE_CH22 / ROUTE_CH23 (the 2-2 / 2-3 room code, pl14 Luis, em3b / em35 overlays, st2_0, em16 r11d Ganados),
#   PS2_CH2_ENEMY (the chapter's PS2 enemy rules + cap 6 / park, one knob), the r11f boss memory knobs the 10-14 lane
#   proved (MOTION_BOUNDED_R11F needs the bounded pl11/em35 archives of data set ch2), the r200 source world owner +
#   texture prep (r200 VRAM), and the 53-entry chapter 1+2 stream file (aica_banks --streams ch2: needs >= 53; test 15
#   keeps 48 with snd16, whose 45 entries are this file's first 45 byte for byte).
CH2REC="ROUTE_CH22=1 ROUTE_CH23=1 PS2_CH2_ENEMY=1 PS2_ENEMY_CH22_DIR=$PE PS2_ENEMY_CH23_DIR=$PE MOTION_BOUNDED_R11F=1 NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS=1 PS2_WORLD_SOURCE_OWNER=1 PS2_WORLD_SOURCE_TEX_PREP=1 AICA_STR_ENT_MAX=56"
CH2=${CH2-$CH2REC}
# T15REC as test15/t15-build.sh defines it (its assignments only, up to the arm table).
T15REC=$(bash -c "set -u; $(sed -n '/^K=/,/^T15REC=/p' "$T/port/dreamcast/tools/d367/test15/t15-build.sh" | grep -v '^K=\|^T=') ; echo \"\$T15REC\"")
[ -n "$T15REC" ] || { echo "ch2-build: T15REC not found"; exit 2; }
mkdir -p "$K"
L=${LP:-c2}
for x in "$@"; do
  case $x in
    rP|rW|mW|rT) T15="$T15REC $CH2" LP=$L XON="${XON:-}" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" $x ;;
    xP) T15="$T15REC" LP=${L}x XON="" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" rP ;;
    xW) T15="$T15REC" LP=${L}x XON="${XON:-}" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" rW ;;
    xT) T15="$T15REC" LP=${L}x XON="${XON:-}" bash "$T/port/dreamcast/tools/d367/test15/t15-build.sh" rT ;;
    *) echo "arm? $x" ;;
  esac
done
