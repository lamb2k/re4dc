set -euo pipefail
# bb.sh (WSL; lane scenery19): console A/B bench programs on the current Test 19/20 line play recipe of this tree.
#   A = recipe with every scenery19 knob off (SCENERY_CHUNK=0 SG_SELECT_LEAN=0), B = recipe + SCENERY_DEDUP=2
#   SCENERY_UNIT_CONCAT=1 (SCENERY_CHUNK=1 SG_SELECT_LEAN=1 as in the recipe). Five scenes (BENCH_SCENES=5).
#   AH / BH: the same with PACE_MODE=off for hwproject (MODELLED numbers).
# Env: RECIPE_OUT = a route out dir whose candidate.txt is the current recipe with all scenery19 knobs on but no
#   SCENERY_DEDUP / SCENERY_UNIT_CONCAT.
T=/root/work/lanes/scenery19
K=/root/work/lanes/scenery19-scratch/bench; mkdir -p $K/programs
export SOURCE_DATE_EPOCH=1760000000
ID=$(git -C $T rev-parse --short=8 HEAD)
BW="DBG_WARP=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144 BENCH_SCENES=5"
TOOL=/opt/toolchains/dc/sh-elf/bin
RO=${RECIPE_OUT:?}
b() { local lab=$1; shift; local t0=$(date +%s)
  (cd $T && TREE=$T ROUTE_PROGRAMS_DIR=$K/programs ROUTE_PROGRAMS_JSON= bash /root/probe/d367-buildslot.sh \
     bash port/dreamcast/tools/d367/route/route-build.sh $lab "$@") >> $K/logs-build.txt 2>&1 || true
  local O=/root/probe/lanes/route/out-$lab
  rm -rf "${K:?}/programs/candidate-route$lab"
  echo "$lab elf=$(cut -c1-16 $O/elf.sha256) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt) end=$($TOOL/sh-elf-nm $O/re4dc-game.elf | awk '$3=="_end"{print $1}') stack=$(head -1 $O/stack.txt | cut -c1-8)"; }
R=$(sed 's/^.*PC_SAMPLER=1 //' $RO/candidate.txt)
RA="$R SCENERY_CHUNK=0 SG_SELECT_LEAN=0"
RB="$R SCENERY_DEDUP=2 SCENERY_UNIT_CONCAT=1"
HWX="PACE_MODE=off PC_SAMPLER_BYTES=8192"
for a in ${ARMS:-A B}; do case $a in
  A) b s19bA $RA $BW ;;
  B) b s19bB $RB $BW ;;
  AH) b s19bAH $RA $BW $HWX ;;
  BH) b s19bBH $RB $BW $HWX ;;
esac; done
for a in ${ARMS:-A B}; do echo "$a: $(grep -o 'SCENERY_[A-Z_]*=[0-9]\|SG_SELECT_LEAN=[0-9]\|BENCH_SCENES=[0-9]' /root/probe/lanes/route/out-s19b$a/candidate.txt | tr '\n' ' ')"; done
echo BENCH BUILDS DONE
