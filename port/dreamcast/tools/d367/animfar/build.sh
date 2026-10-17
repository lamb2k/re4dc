# build.sh <arm...>: lane animfar17 arms on the test 17 recipe (ch2/ch2-build.sh)
#  0 = base rP (34f6e0a6, knob off; identity reference)   K = this tree rP (knob off)
#  B = bench (cap compare) knob off   N = bench ANIMAL_FAR_RATE=${RATE:-2}
set -u
T=/root/probe/lanes-20261017/animfar/tree
TB=/root/probe/lanes-20261017/animfar/base
K=/root/probe/lanes-20261017/animfar/k
mkdir -p $K
ID=$(git -C $T rev-parse --short=8 HEAD)
BX="WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144 CAP_COMPARE=1 MIST_CUT=1 TA_HASH=4 PC_SAMPLER=0 ALIVE_CAP_LOG=1"
for a in "$@"; do case $a in
  0) T=$TB K=$K LP=af0 bash $TB/port/dreamcast/tools/d367/ch2/ch2-build.sh rP ;;
  K) T=$T K=$K LP=afk bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rP ;;
  B) T=$T K=$K LP=afb XON="$BX" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW ;;
  N) T=$T K=$K LP=afn${RATE:-2} XON="$BX ANIMAL_FAR_RATE=${RATE:-2}" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh rW ;;
esac; done
