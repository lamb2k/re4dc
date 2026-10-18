#!/bin/bash
# fp_twin.sh <play-out-dir> <label> [extra twin knobs...]   (WSL; tools/d367/fullplay)
# Builds, from the commit the release ELF was built from (out-dir/stack.txt; a clean tree is required):
#   out-fp<label>P  the release recipe again (out-dir/candidate.txt): its binary must equal the release 1ST_READ.BIN
#                   (proves this worktree reproduces the release image), and
#   out-fp<label>W  the TWIN: the same recipe + diagnostic knobs only (DBG_WARP=1 WARP_JUMP=1 PC_SAMPLER=0, plus
#                   TEX_CHECK=1 / MCHECK_LEONGC=1 where the tree has them, plus the extra knobs given).
# Worktrees: $FP_TREES/<sha12> (detached). Builds go through /root/probe/d367-buildslot.sh (2 slots, -j4).
# Env: FP_TREES (default /root/probe/lanes-20261014/fullplay/trees), FP_TREE=<dir> uses that checkout instead
# (it must be at the stack.txt commit and clean), FP_SKIP_IDENTITY=1 skips the P build (never for a release gate).
set -euo pipefail
# the release recipes (t9-build.sh and copies) pin the build date
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1760000000}
OUT=${1:?play out dir}; LAB=${2:?label}; shift 2
TWIN_EXTRA="$*"
FP_TREES=${FP_TREES:-/root/probe/lanes-20261014/fullplay/trees}
[ -s $OUT/re4dc-game.elf ] && [ -s $OUT/candidate.txt ] && [ -s $OUT/stack.txt ] || { echo "fp_twin: $OUT is not a route build" >&2; exit 2; }
SHA=$(head -1 $OUT/stack.txt)
[ $(wc -l < $OUT/stack.txt) -le 1 ] || { echo "fp_twin: $OUT was built from a dirty tree:"; cat $OUT/stack.txt; exit 2; } >&2
here=$(cd "$(dirname "$0")" && pwd)
if [ -n "${FP_TREE:-}" ]; then T=$FP_TREE
else
  T=$FP_TREES/${SHA:0:12}
  if [ ! -d $T ]; then
    mkdir -p $FP_TREES
    git -C "$here" worktree prune  # a deleted twin tree (disk hygiene) leaves a stale registration that blocks the add
    git -C "$here" worktree add --detach $T $SHA >/dev/null 2>&1 || { echo "fp_twin: worktree $SHA failed" >&2; exit 2; }
    # test 16 on: SH4ZAM is a git submodule (game/third_party/sh4zam); trees before it have none
    [ ! -f $T/.gitmodules ] || git -C $T submodule update -q --init || { echo "fp_twin: submodule init in $T failed" >&2; exit 2; }
  fi
fi
# Submodules (SH4ZAM: game/third_party/sh4zam since t15/int e22bf562): a new worktree has them empty and the build stops.
git -C $T submodule update --init --recursive >/dev/null 2>&1 || { echo "fp_twin: submodules of $T failed" >&2; exit 2; }
[ "$(git -C $T rev-parse HEAD)" = "$SHA" ] || { echo "fp_twin: $T is not at $SHA" >&2; exit 2; }
[ -z "$(git -C $T status --short --untracked-files=no)" ] || { echo "fp_twin: $T has local changes" >&2; exit 2; }
# The release command line minus nothing: route-build.sh prepends its own defaults, the candidate's later tokens win.
REC=$(cat $OUT/candidate.txt)
G=$T/port/dreamcast/game
DIAG="DBG_WARP=1 WARP_JUMP=1 PC_SAMPLER=0"
grep -q '^TEX_CHECK' $G/Makefile $G/*.mk 2>/dev/null && DIAG="$DIAG TEX_CHECK=1"
if grep -q '^MCHECK_LEONGC' $G/*.mk 2>/dev/null && grep -q '^ACTOR_TRANSACTION=1' $OUT/resolved-knobs.txt; then DIAG="$DIAG MCHECK_LEONGC=1"; fi
TOOL=/opt/toolchains/dc/sh-elf/bin
build() { local lab=$1; shift
  (cd $T && TREE=$T bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh $lab "$@") | tail -3
  local O=/root/probe/lanes/route/out-$lab
  [ -s $O/re4dc-game.elf ] || { echo "fp_twin: build $lab failed" >&2; return 1; }
  [ ! -s $O/missing.txt ] || { echo "fp_twin: $lab has missing symbols:" >&2; cat $O/missing.txt >&2; return 1; }
}
bin() { $TOOL/sh-elf-objcopy -R .stack -O binary $1 /tmp/fp-$$.bin && sha256sum < /tmp/fp-$$.bin | cut -c1-64; rm -f /tmp/fp-$$.bin; }
REL=$(bin $OUT/re4dc-game.elf)
# one tree builds one image at a time (route-build.sh writes the tree's game/obj/missing.txt)
build fp${LAB}W $REC $DIAG $TWIN_EXTRA
if [ "${FP_SKIP_IDENTITY:-0}" != 1 ]; then
  build fp${LAB}P $REC
  ID=$(bin /root/probe/lanes/route/out-fp${LAB}P/re4dc-game.elf)
  if [ "$ID" = "$REL" ]; then echo "IDENTITY OK fp${LAB}P binary $ID == release build $OUT"
  else echo "IDENTITY FAIL fp${LAB}P binary $ID != release build $REL"; exit 1; fi
fi
W=/root/probe/lanes/route/out-fp${LAB}W
for k in $DIAG $TWIN_EXTRA; do
  n=${k%%=*}; v=${k#*=}
  grep -qx "$n=$v" $W/resolved-knobs.txt || { echo "fp_twin: twin knob $k did not resolve" >&2; exit 1; }
done
echo "TWIN fp${LAB}W tree=$T sha=$SHA diag=\"$DIAG $TWIN_EXTRA\" end=$($TOOL/sh-elf-nm $W/re4dc-game.elf | awk '$3=="_end"{print $1}') release_end=$($TOOL/sh-elf-nm $OUT/re4dc-game.elf | awk '$3=="_end"{print $1}')"
