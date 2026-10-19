set -euo pipefail
# actorplan19 console A/B/C bench programs = benchpub/bench-build.sh's B and Q arms on the Test 18 line play recipe
# (out-a9krP / out-a9prP candidate.txt), plus C = B + cap 6 (INFO only).
T=/root/work/lanes/actorplan19/tree
K=/root/work/lanes/actorplan19/bench; mkdir -p $K/programs
export SOURCE_DATE_EPOCH=1760000000
ID=$(git -C $T rev-parse --short=8 HEAD)
BW="DBG_WARP=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=262144"
TOOL=/opt/toolchains/dc/sh-elf/bin
bin() { $TOOL/sh-elf-objcopy -R .stack -O binary $1 $K/img.bin && sha256sum < $K/img.bin | cut -c1-16; rm -f $K/img.bin; }
b() { local lab=$1; shift; local t0=$(date +%s)
  (cd $T && TREE=$T ROUTE_PROGRAMS_DIR=$K/programs ROUTE_PROGRAMS_JSON= bash /root/probe/d367-buildslot.sh \
     bash port/dreamcast/tools/d367/route/route-build.sh $lab "$@") >> $K/logs-build.txt 2>&1 || true
  local O=/root/probe/lanes/route/out-$lab
  rm -rf "${K:?}/programs/candidate-route$lab"
  echo "$lab elf=$(cut -c1-16 $O/elf.sha256) bin=$(bin $O/re4dc-game.elf) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt) end=$($TOOL/sh-elf-nm $O/re4dc-game.elf | awk '$3=="_end"{print $1}')"; }
RA=$(sed 's/^.*PC_SAMPLER=1 //' /root/probe/lanes/route/out-a9krP/candidate.txt)
RB=$(sed 's/^.*PC_SAMPLER=1 //' /root/probe/lanes/route/out-a9prP/candidate.txt)
C6="ALIVE_CAP=6 R101_ALIVE_CAP=6"
b ab18A $RA $BW
b ab18AQ $RA $BW KOS_SQUEEZE=1 KOS_WATCH=1
b ab18B $RB $BW
b ab18BQ $RB $BW KOS_SQUEEZE=1 KOS_WATCH=1
b ab18C $RB $BW $C6
b ab18CQ $RB $BW $C6 KOS_SQUEEZE=1 KOS_WATCH=1
for a in A B C; do echo "$a: $(grep -o 'ACTOR_PLAN=1\|ALIVE_CAP=[0-9]\|BENCHMARK=1' /root/probe/lanes/route/out-ab18$a/candidate.txt | tr '\n' ' ')"; done
echo BENCH BUILDS DONE
