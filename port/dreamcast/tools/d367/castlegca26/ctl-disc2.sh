#!/bin/bash
# ctl-disc2.sh <rr work dir> <evidence dir (WSL)> <name>   (WSL; lane castle-gca-26)
# A CONTROL Disc 2 base for A/B runs (stills, gameplay equivalence): the same rr cycle's Disc 1 candidate tree + the castle
# content WITHOUT D2_DATA (castle31 Disc 2 as before) + the same Disc 2 census twin program (out-fp<pfx><s7>d2cW), mastered
# by fp_master.sh into <evidence>/_discs/<name>. Delete the base after its runs. CTL_D2_DATA=<sets> builds the lane arm
# the same way (still pairs: the recipe D2_DATA).
set -euo pipefail
W=${1:?rr work}; EVU=${2:?evidence}; N=${3:?name}
H=$(cd "$(dirname "$0")" && pwd); D=$(cd "$H/.." && pwd); F=$D/fullplay
. "$W/recipe.conf"
S8=$(sed -n 's/^sha=//p' "$W/cycle.env" | cut -c1-8); S7=${S8:0:7}; L=${RR_PFX:-rr}$S7
ROUTE=/root/probe/lanes/route; CAND=$(cat "$W/cand.txt")
X=$W/ctl; rm -rf "${X:?}"; mkdir -p "$X/d1"
python3 "$F/fp_iso.py" extract "$CAND/gdemu/track03.bin" "$X/d1/tree" --manifest "$X/d1/manifest.json" --ipbin "$X/d1/IP.BIN" | tail -1
D2_DATA=${CTL_D2_DATA:-} python3 "$D/castle31/castle_fixture.py" "$X/d1/tree" "$D2_CASTLE_TREE" "$X/fx" | tail -1
python3 "$D/discsets/mkdisc2.py" "$X/d1/tree" "$X/fx/castle-fixture.json" "$ROUTE/out-${L}d2rP" "$X/out" "$S8" | tail -1
bash "$F/fp_master.sh" "$X/out/tree" "$X/out/manifest.json" "$X/d1/IP.BIN" "$EVU/_discs/$N" "$ROUTE/out-fp${L}d2cW" | tail -1
rm -rf "${X:?}/d1/tree" "${X:?}/out/tree"
