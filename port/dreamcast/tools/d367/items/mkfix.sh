#!/bin/bash
# mkfix.sh <name> <room> <warp file> <control label> <test label>: lane items fixture pair (WSL).
#   control = the test 11 data + objs-<room> (lane objs' t11-fix.py data set; r119: none) + the warp
#   test    = control + the items dar of <room> (objs + items, in place), tex-items.pak (tex-t11.pak + 71 PS2
#             item / debris pictures), core.das (core EFF debris) and the SS/cmn pick-up zoom models
# Writes /root/probe/lanes-20261014/items/fix/<name>-c-<control>.json and <name>-i-<test>.json.
set -eu
N=$1; R=$2; WARP=$3; LC=$4; LT=$5
W=/root/probe/lanes-20261014/items/work
F=/root/probe/lanes-20261014/items/fix
FX=/root/probe/lanes-20261014/objs/tree/port/dreamcast/tools/d367/test11/t11-fix.py
mkdir -p $F
D='r119c,em29,fbec,r100tr4,smx101,blackgc14p'
[ $R != r119 ] && D="$D,objs-$R"
P=""; [ -n "${PAD:-}" ] && P="--pad $PAD"
python3 $FX $LC $F/$N-c-$LC.json --data $D --warp $WARP $P | tail -1
SS=""
for f in $W/out/sscmn/*; do SS="$SS --set ss/cmn/$(basename $f)=$f"; done
python3 $FX $LT $F/$N-i-$LT.json --data $D --warp $WARP $P --set st1/$R.dar=$W/out/$R/$R.dar \
  --set dc/tex.pak=$W/out/tex-items.pak --set etc/core.das=$W/out/core/core.das $SS | tail -1
