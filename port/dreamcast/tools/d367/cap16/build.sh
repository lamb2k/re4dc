# build.sh <arm...>: lane cap16 arms with the test 16 recipe (test16/t16-build.sh)
#  B = cap comparison disc program (rW + BENCHMARK + CAP_COMPARE)
#  G = gameplay warp program (rW + CAP_COMPARE runtime cap + cap logs) for the bell gate
#  K = knob-off release play image (rP) for the identity check against test 16 (out-t16rcrP, program 72871476)
set -u
T=/root/probe/lanes-20261016/cap16/tree
K=/root/probe/lanes-20261016/cap16/k
mkdir -p $K
ID=$(git -C $T rev-parse --short=8 HEAD)
BX="WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144 CAP_COMPARE=1 MIST_CUT=1 TA_HASH=4 PC_SAMPLER=0 ${EXTRA:-}"
GX="CAP_COMPARE=1 R101_CAP_LOG=1 ALIVE_CAP_LOG=1 ${EXTRA:-}"
for a in "$@"; do case $a in
  B) T=$T K=$K LP=cap16b XON="$BX" bash $T/port/dreamcast/tools/d367/test16/t16-build.sh rW ;;
  G) T=$T K=$K LP=cap16g XON="$GX" bash $T/port/dreamcast/tools/d367/test16/t16-build.sh rW ;;
  K) T=$T K=$K LP=cap16k bash $T/port/dreamcast/tools/d367/test16/t16-build.sh rP ;;
esac; done
