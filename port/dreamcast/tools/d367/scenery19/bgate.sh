set -euo pipefail
# scenery19 gate builds (WSL): base b = origin/t15/int at BASE (knob-off identity reference), k = lane tree knob off,
# p = lane tree SCENERY_CHUNK=1. Arms rP rT mW (+ k/p already have hrW from b1.sh).
T=/root/work/lanes/scenery19
B=/root/work/lanes/scenery19-scratch/base
BASE=${BASE:?}
export K=/root/work/lanes/scenery19-scratch/k
mkdir -p $K
T18="MOVIE_AUDIO_PRIME=1 ROOM_LEFTOVER_FIT=1 PS2_WORLD_SOURCE_TEX_VQ=1 LEON_SKIN_SLOTS=2 ROUTE_SOON_RETURN=1 LEON_HEADLESS=1 LEON_HEADLESS_DIR=/root/re4data/private/garr18-head-20261019 LEON_CLOTH_DRAWN=1 FX_MIST_PS2=1 HAZE_SPRITE_CUT=1 PS2_HDR_SETS=128 ACTOR_PLAN=1"
PE=/root/re4data/private/ps2enemy-ch2-20261016
eval "$(grep '^CH2REC=' $T/port/dreamcast/tools/d367/ch2/ch2-build.sh)"
if [ ! -d $B ]; then git -C $T worktree add -q --detach $B $BASE; fi
(cd $B && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
for a in ${ARMS:-b k p}; do
  case $a in
    b) T=$B LP=s9b CH2="$CH2REC $T18" XON="" bash $B/port/dreamcast/tools/d367/ch2/ch2-build.sh rP | cut -c1-120 ;;
    k) T=$T LP=s9k CH2="$CH2REC $T18" XON="" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP rT mW | cut -c1-120 ;;
    p) T=$T LP=s9p CH2="$CH2REC $T18 ${PEXTRA:-SCENERY_CHUNK=1}" XON="" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP rT mW | cut -c1-120 ;;
  esac
done
echo GATE BUILDS DONE
