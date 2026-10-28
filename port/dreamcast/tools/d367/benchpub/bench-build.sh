#!/bin/bash
# bench-build.sh <arm>...   (WSL; tools/d367/benchpub) public benchmark disc builds (BENCHMARK=1, game/bench.mk).
# The disc runs the release play recipe of $BASE (out-<label>/candidate.txt: the test release's exact make line, which
# ends DBG_WARP=0 PC_SAMPLER=0) plus the benchmark knobs, which come later on the command line and win:
#   BW = DBG_WARP=1 WARP_AFTER_RESET=1 (the scenes are warp fixtures, each armed from a soft reset)
#        GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 (the Phases disc meters: CPU per tick, disc reads)
#        BENCHMARK=1 BENCH_ID=<tree sha8> BENCH_SCENES=<count of sceneN-warp.txt here> (scene 3 = r10b Del Lago, lake20 10-20)
#        QA_LINK=1 (lane link28 10-28): the modem remote link; bench-package.sh writes /dc/link.txt `auto 1`, so the disc
#        dials a DreamPi on its own and sends the result rows (game/qa_link_bench.cpp, tools/qalink/README.md)
#        ARENA_FIT_KOS_BYTES=262144 ($BENCH_KOS): KOS keeps 64 KiB more than the release (196608), heap 4 64 KiB less.
#        Why: the soft reset between the scenes carries r101's KOS use (~126 KB, the "phase=enter drift kos=" line) into
#        the r100 load, and the KOS out-of-memory gate at 48 KiB failed on the 196608 split (0270a29d: "Out of memory"
#        in the r100 load after the reset, and at the r101 entry with 4 KiB pieces, 12 KB thread stack). The release
#        r101 -> r100 backtrack carries the same use; that is a release finding, not changed here.
# Arms (label prefix $LP, default bp):
#   B  the benchmark disc program
#   Q  B + KOS_SQUEEZE=1 KOS_WATCH=1 (the KOS out-of-memory gate twin; a "squeeze <bytes> <frag>" warp line sets it)
#   K  knob-off identity: the release make line alone from this tree; its binary must equal $BASE's
# Env: T (tree, default this checkout), BASE (release out dir, default out-t121tP = test 12.1), LP, BENCH_ID.
set -u
here=$(cd "$(dirname "$0")" && pwd)
T=${T:-$(cd "$here/../../../../.." && pwd)}
BASE=${BASE:-/root/probe/lanes/route/out-t121tP}
LP=${LP:-bp}
K=${K:-/root/probe/bench-public}
mkdir -p $K/programs
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1760000000}
REC=$(sed 's/^.*PC_SAMPLER=1 //' $BASE/candidate.txt)
ID=${BENCH_ID:-$(git -C $T rev-parse --short=8 HEAD)}
BW="DBG_WARP=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 BENCHMARK=1 QA_LINK=1 BENCH_ID=$ID ARENA_FIT_KOS_BYTES=${BENCH_KOS:-262144} BENCH_SCENES=$(ls $here/scene*-warp.txt | wc -l)"
TOOL=/opt/toolchains/dc/sh-elf/bin
bin() { $TOOL/sh-elf-objcopy -R .stack -O binary $1 /tmp/bp-$$.bin && sha256sum < /tmp/bp-$$.bin | cut -c1-64; rm -f /tmp/bp-$$.bin; }
b() { local lab=$1; shift; local t0=$(date +%s)
  (cd $T && TREE=$T ROUTE_PROGRAMS_DIR=$K/programs ROUTE_PROGRAMS_JSON= bash /root/probe/d367-buildslot.sh \
     bash port/dreamcast/tools/d367/route/route-build.sh $lab "$@") >> $K/logs-build.txt 2>&1
  local rc=$? O=/root/probe/lanes/route/out-$lab
  rm -rf $K/programs/candidate-route$lab
  echo "rc=$rc $lab elf=$(cut -c1-16 $O/elf.sha256 2>/dev/null) bin=$(bin $O/re4dc-game.elf | cut -c1-16) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt 2>/dev/null) tree=$(cd $T && git rev-parse --short=8 HEAD) dirty=$(cd $T && git status --short --untracked-files=no | wc -l)" | tee -a $K/logs-build.txt; }
for x in "$@"; do case $x in
  B) b ${LP}B $REC $BW ;;
  Q) b ${LP}Q $REC $BW KOS_SQUEEZE=1 KOS_WATCH=1 ;;
  K) b ${LP}K $REC
     a=$(bin /root/probe/lanes/route/out-${LP}K/re4dc-game.elf); r=$(bin $BASE/re4dc-game.elf)
     [ "$a" = "$r" ] && echo "IDENTITY OK ${LP}K binary $a == $BASE" || echo "IDENTITY FAIL ${LP}K binary $a != $BASE $r" ;;
  *) echo "arm? $x" ;;
esac; done
