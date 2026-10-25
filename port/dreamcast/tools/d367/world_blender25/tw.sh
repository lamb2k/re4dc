#!/bin/bash
# world-blender25 twin builds (serial, lane tree). usage: tw.sh <arm> [r101crc r101bytes] [r103crc r103bytes]
set -euo pipefail
ARM=${1:?}; shift
TR=/root/work/lanes/world-blender25; X=/root/work/lanes/world-blender25-scratch
BASE=7250e5c6b652d97b2413d7b5762e22a24043307c
REL=/root/probe/lanes/route/out-rr7250e5crP
INC=$TR/port/dreamcast/tools/d367/texture_rect21/provenance_certificates_n256.inc
cd $TR
[ -z "$(git status --short --untracked-files=no)" ] || { echo dirty; exit 1; }
git checkout -q --detach $BASE
if [ $# -ge 2 ]; then sed -i "s/0x4ec31f36U,1223744U/$1U,$2U/" $INC; fi
if [ $# -ge 4 ]; then sed -i "s/0x11b076c6U,1031104U/$3U,$4U/" $INC; fi
if ! git diff --quiet; then git diff --stat; git -c user.name=wb25 -c user.email=noreply@anthropic.com commit -q -am "wb25 measurement twin $ARM (local only)"; fi
SHA=$(git rev-parse HEAD)
O=$X/relout-$ARM; rm -rf "${O:?}"; mkdir -p $O
for f in re4dc-game.elf candidate.txt resolved-knobs.txt syms.txt end.txt; do cp --remove-destination "$REL/$f" "$O/$f"; done
echo "$SHA" > $O/stack.txt
rm -rf "/root/probe/lanes/route/out-fpwb25${ARM:?}W"
C="QA_MENU=1 WARP_AFTER_RESET=1 WORLD_CENSUS24=1 WORLD_CENSUS24_WINDOW=300 SCENERY_N256=1"
env FP_TREE=$TR FP_SKIP_IDENTITY=1 bash $TR/port/dreamcast/tools/d367/fullplay/fp_twin.sh $O wb25$ARM $C > $X/twin-$ARM.log 2>&1 || { tail -15 $X/twin-$ARM.log; git checkout -q --detach $BASE; exit 1; }
grep -E "TWIN|built" $X/twin-$ARM.log | cut -c1-200
git checkout -q --detach $BASE
