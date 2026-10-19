set -euo pipefail
# bb19.sh (WSL): engine19 console A/B bench programs = benchpub B arm on the Test 18 line play recipe of this tree:
#   A = out-e19xrP's make line (knob off), B = out-e19wrP's (ENEMY_VIS_CULL=1); AQ/BQ = KOS squeeze twins.
T=/root/work/lanes/engine19
K=/root/work/lanes/engine19-scratch/bench; mkdir -p $K/programs
export SOURCE_DATE_EPOCH=1760000000
ID=$(git -C $T rev-parse --short=8 HEAD)
BW="DBG_WARP=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144 BENCH_SCENES=4"
TOOL=/opt/toolchains/dc/sh-elf/bin
b() { local lab=$1; shift; local t0=$(date +%s)
  (cd $T && TREE=$T ROUTE_PROGRAMS_DIR=$K/programs ROUTE_PROGRAMS_JSON= bash /root/probe/d367-buildslot.sh \
     bash port/dreamcast/tools/d367/route/route-build.sh $lab "$@") >> $K/logs-build.txt 2>&1 || true
  local O=/root/probe/lanes/route/out-$lab
  rm -rf "${K:?}/programs/candidate-route$lab"
  echo "$lab elf=$(cut -c1-16 $O/elf.sha256) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt) end=$($TOOL/sh-elf-nm $O/re4dc-game.elf | awk '$3=="_end"{print $1}') stack=$(head -1 $O/stack.txt | cut -c1-8)"; }
RA=$(sed 's/^.*PC_SAMPLER=1 //' /root/probe/lanes/route/out-e19xrP/candidate.txt)
RB=$(sed 's/^.*PC_SAMPLER=1 //' /root/probe/lanes/route/out-e19wrP/candidate.txt)
for a in ${ARMS:-A B AQ BQ}; do case $a in
  A) b e19bA $RA $BW ;;
  B) b e19bB $RB $BW ;;
  AQ) b e19bAQ $RA $BW KOS_SQUEEZE=1 KOS_WATCH=1 ;;
  BQ) b e19bBQ $RB $BW KOS_SQUEEZE=1 KOS_WATCH=1 ;;
esac; done
for a in A B; do echo "$a: $(grep -o 'ENEMY_VIS_CULL=[0-9]\|BENCHMARK=1' /root/probe/lanes/route/out-e19b$a/candidate.txt | tr '\n' ' ')"; done
echo BENCH BUILDS DONE
