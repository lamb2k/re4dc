#!/bin/bash
# ab-build.sh <arm>...  (WSL) lane actorplan17 console A/B disc program = benchpub/bench-build.sh arm B on the test 16
# program source (72871476 + the actorplan17 commit, branch lane/actorplan17-t16) plus ACTOR_PLAN=1 ACTOR_PLAN_AB=1
# (four scenes; each scene's `actorplan 0|1` warp line turns the plan off / on in the same image).
# Arm K = the test 16 release make line alone from this tree: its image must equal test 16's (knob-off identity).
set -u
L=/root/probe/lanes-20261016/actorplan17
T=$L/t16tree
BASE=/root/probe/lanes/route/out-t16rcrP
K=$L/bench; mkdir -p $K/programs
export SOURCE_DATE_EPOCH=1760000000
REC=$(sed 's/^.*PC_SAMPLER=1 //' $BASE/candidate.txt)
ID=$(git -C $T rev-parse --short=8 HEAD)
BW="DBG_WARP=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144"
TOOL=/opt/toolchains/dc/sh-elf/bin
bin() { $TOOL/sh-elf-objcopy -R .stack -O binary $1 /tmp/ap17ab-$$.bin && sha256sum < /tmp/ap17ab-$$.bin | cut -c1-64; rm -f /tmp/ap17ab-$$.bin; }
b() { local lab=$1; shift; local t0=$(date +%s)
  (cd $T && TREE=$T ROUTE_PROGRAMS_DIR=$K/programs ROUTE_PROGRAMS_JSON= bash /root/probe/d367-buildslot.sh \
     bash port/dreamcast/tools/d367/route/route-build.sh $lab "$@") >> $K/logs-build.txt 2>&1
  local rc=$? O=/root/probe/lanes/route/out-$lab
  rm -rf $K/programs/candidate-route$lab
  echo "rc=$rc $lab elf=$(cut -c1-16 $O/elf.sha256 2>/dev/null) bin=$(bin $O/re4dc-game.elf | cut -c1-16) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt 2>/dev/null) tree=$(cd $T && git rev-parse --short=8 HEAD) dirty=$(cd $T && git status --short --untracked-files=no | wc -l)" | tee -a $K/logs-build.txt; }
for x in "$@"; do case $x in
  B) b ap17t16B $REC $BW ACTOR_PLAN=1 ACTOR_PLAN_AB=1 ;;
  K) b ap17t16K $REC
     a=$(bin /root/probe/lanes/route/out-ap17t16K/re4dc-game.elf); r=$(bin $BASE/re4dc-game.elf)
     [ "$a" = "$r" ] && echo "IDENTITY OK ap17t16K image $a == test 16 out-t16rcrP" || echo "IDENTITY FAIL ap17t16K $a != $r" ;;
  *) echo "arm? $x" ;;
esac; done
