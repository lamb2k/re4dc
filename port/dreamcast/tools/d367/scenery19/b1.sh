set -euo pipefail
# scenery19 builds (WSL): the Test 18 line recipe (ch2-build.sh CH2REC + T18 knobs) + ACTOR_PLAN=1 (Test 19 stack),
# SCENERY_CHUNK=0 (k) vs =1 (p). ARMS picks arms: hk/hp = PACE_MODE=off warp (hwproject), k/p = rP rT mW.
T=/root/work/lanes/scenery19
export K=/root/work/lanes/scenery19-scratch/k
mkdir -p $K
T18="MOVIE_AUDIO_PRIME=1 ROOM_LEFTOVER_FIT=1 PS2_WORLD_SOURCE_TEX_VQ=1 LEON_SKIN_SLOTS=2 ROUTE_SOON_RETURN=1 LEON_HEADLESS=1 LEON_HEADLESS_DIR=/root/re4data/private/garr18-head-20261019 LEON_CLOTH_DRAWN=1 FX_MIST_PS2=1 HAZE_SPRITE_CUT=1 PS2_HDR_SETS=128 ACTOR_PLAN=1"
PE=/root/re4data/private/ps2enemy-ch2-20261016
eval "$(grep '^CH2REC=' $T/port/dreamcast/tools/d367/ch2/ch2-build.sh)"
(cd $T && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
HWX="PACE_MODE=off PC_SAMPLER_BYTES=8192"
SC=${SC:-SCENERY_CHUNK=1}
for a in ${ARMS:-hk hp}; do
  case $a in
    hk) T=$T LP=s9kh CH2="$CH2REC $T18" XON="$HWX" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-160 ;;
    hp) T=$T LP=s9ph${SUF:-} CH2="$CH2REC $T18 $SC" XON="$HWX" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-160 ;;
    k) T=$T LP=s9k CH2="$CH2REC $T18" XON="" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP rT mW | cut -c1-160 ;;
    p) T=$T LP=s9p CH2="$CH2REC $T18 $SC" XON="" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP rT mW | cut -c1-160 ;;
  esac
done
echo BUILDS DONE
