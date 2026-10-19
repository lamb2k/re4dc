set -euo pipefail
# actorplan19 builds: Test 18 line recipe, ACTOR_PLAN=0 (k) vs =1 (p), plus base t15/int 7ed4a44c (b).
export K=/root/work/lanes/actorplan19/k
T=/root/work/lanes/actorplan19/tree
B=/root/work/lanes/actorplan19/base
mkdir -p $K
T18="MOVIE_AUDIO_PRIME=1 ROOM_LEFTOVER_FIT=1 PS2_WORLD_SOURCE_TEX_VQ=1 LEON_SKIN_SLOTS=2 ROUTE_SOON_RETURN=1 LEON_HEADLESS=1 LEON_HEADLESS_DIR=/root/re4data/private/garr18-head-20261019 LEON_CLOTH_DRAWN=1 FX_MIST_PS2=1 HAZE_SPRITE_CUT=1 PS2_HDR_SETS=128"
PE=/root/re4data/private/ps2enemy-ch2-20261016
eval "$(grep '^CH2REC=' $T/port/dreamcast/tools/d367/ch2/ch2-build.sh)"
[ -d $B ] || git -C $T worktree add -q --detach $B 7ed4a44c
(cd $B && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
(cd $T && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
HWX="PACE_MODE=off PC_SAMPLER_BYTES=8192"
T=$B LP=a9b CH2="$CH2REC $T18" XON="" bash $B/port/dreamcast/tools/d367/ch2/ch2-build.sh rP | cut -c1-120
T=$T LP=a9k CH2="$CH2REC $T18" XON="" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP rT mW | cut -c1-120
T=$T LP=a9p CH2="$CH2REC $T18 ACTOR_PLAN=1" XON="" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP rT mW | cut -c1-120
T=$T LP=a9kh CH2="$CH2REC $T18" XON="$HWX" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120
T=$T LP=a9ph CH2="$CH2REC $T18 ACTOR_PLAN=1" XON="$HWX" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW | cut -c1-120
echo BUILDS DONE
