#!/bin/bash
# Lane eng-ref: the old game's reference build WITH the random-number split (owner 2026-11-19 "Split it").
# The release recipe + LOGIC_TRACE=1 + DBG_WARP=1 + the EM window, exactly as eng-e1b's refbuild.sh, built from an
# exported copy of this worktree's HEAD (git archive) that tools/plays_right/refsplit/refsplit.py patches.
# src/ and include/ in git are never edited. Output: .ref/route/out-refsplit; patch + site list in E:\...\build.
set -eu
L=/root/work/lanes/eng-ref
R=$L/.ref
K=/mnt/e/RE4DC-Lanes/eng-ref/build
mkdir -p "$R" "$K"
rm -rf "$R/tree" "$R/tree0"; mkdir -p "$R/tree" "$R/tree0"
cd "$L"
git archive HEAD | tar -x -C "$R/tree"
# the SH4ZAM submodule (pinned commit, as checked out in this worktree)
test "$(git -C port/dreamcast/game/third_party/sh4zam rev-parse HEAD)" = "$(git ls-tree HEAD port/dreamcast/game/third_party/sh4zam | cut -d' ' -f3 | cut -c1-40)"
rm -rf "$R/tree/port/dreamcast/game/third_party/sh4zam"; cp -a port/dreamcast/game/third_party/sh4zam "$R/tree/port/dreamcast/game/third_party/sh4zam"
git archive HEAD src include port/dreamcast/game | tar -x -C "$R/tree0"
python3 "$L/port/dreamcast/tools/plays_right/refsplit/refsplit.py" "$R/tree" --list "$K/refsplit-sites.tsv" ${RSMASK:+--mask $RSMASK}
( cd "$R" && diff -ruN tree0/src tree/src; diff -ruN tree0/include tree/include; diff -ruN -x third_party tree0/port/dreamcast/game tree/port/dreamcast/game ) > "$K/refsplit.patch" || true
rm -rf "$R/tree0"
grep -c '^+++ ' "$K/refsplit.patch"
export T=$R/tree
export ROUTE_OUT_ROOT="$R/route" ROUTE_PROGRAMS_JSON="" ROUTE_PROGRAMS_DIR="$R/route/programs"
export LP=refsplit JOBS=6 MAKEFLAGS=-j6
mkdir -p "$ROUTE_OUT_ROOT"
cd "$T"
. port/dreamcast/tools/d367/rr/recipe.conf
export CH2
sed '/^b() {/,$d' port/dreamcast/tools/d367/test15/t15-build.sh > "$K/ref-flags.sh"
. "$K/ref-flags.sh"
export TREE=$T
date
bash port/dreamcast/tools/d367/route/route-build.sh refsplit $F $LOOK $BASE $T13 $T14 $T15REC $CH2 IMAGE_PAD_BYTES=0 $WP LOGIC_TRACE=1 LOGIC_TRACE_EM_FROM=185 LOGIC_TRACE_EM_TO=1100 > "$K/ref.log" 2>&1 || { tail -30 "$K/ref.log" | cut -c1-250; exit 1; }
if grep -q re4ref "$ROUTE_OUT_ROOT/out-refsplit/missing.txt" 2>/dev/null; then echo "refsplit: unresolved split symbols"; cat "$ROUTE_OUT_ROOT/out-refsplit/missing.txt"; exit 1; fi
/opt/toolchains/dc/sh-elf/bin/sh-elf-nm "$ROUTE_OUT_ROOT/out-refsplit/re4dc-game.elf" | grep re4ref
cat "$ROUTE_OUT_ROOT/out-refsplit/elf.sha256"
cat "$ROUTE_OUT_ROOT/out-refsplit/candidate.txt" | md5sum
date
