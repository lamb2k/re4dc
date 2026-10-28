#!/bin/bash
# cast-ps2-25 r18: LEON_PS2_RIG builds. $1 = on (gate twin + disc) | id (knob-off identity vs rr5affe6erP)
set -euo pipefail
L=/root/work/lanes/cast-ps2-25; S=$L/_s/r18; mkdir -p $S
W=/root/rr/work/1026-0940-179e01e7; ROUTE=/root/probe/lanes/route
D=$L/port/dreamcast/tools/d367
export SOURCE_DATE_EPOCH=1760000000
REC=$(cat $L/_s/r17/cand-22c6a1c9.txt)
RIG=${RIG-"PS2_LEON_DIR=/root/re4data/private/ps2leon-rig-20261026 LEON_PS2_RIG=1"}
MODE=${1:?mode}
if [ "$MODE" = id ]; then
  (cd $L && TREE=$L bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh cp25id $REC $RIG) | tail -1
  T=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
  for x in rr5affe6erP cp25id; do $T -R .stack -O binary $ROUTE/out-$x/re4dc-game.elf $S/$x.bin; done
  sha256sum $S/rr5affe6erP.bin $S/cp25id.bin | sed 's#  .*/#  #'
  for o in $ROUTE/out-rr5affe6erP/*.ovl; do n=$(basename $o); cmp -s $o $ROUTE/out-cp25id/$n && echo "same" || echo "DIFF $n"; done | sort | uniq -c
  exit 0
fi
G=$S/gca; rm -rf "${G:?}"; mkdir -p $G; cp -r $W/gca/catalog $W/gca/gc-assets.pin $G/
TAG=${2:-cp25rigW}
(cd $L && TREE=$L bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh $TAG $REC $RIG DBG_WARP=1 WARP_JUMP=1 PC_SAMPLER=0 TEX_CHECK=1 GC_ASSET_GATE=1 GC_ASSET_PROF=1 GC_ASSET_CATALOG_PIN_FILE=$G/gc-assets.pin) > $S/twin-$TAG.txt 2>&1 || { tail -15 $S/twin-$TAG.txt; exit 1; }
O=$ROUTE/out-$TAG; [ -s $O/re4dc-game.elf ] && [ ! -s $O/missing.txt ]
tail -1 $S/twin-$TAG.txt
CAND=$(for d in "/mnt/c/Game Dev/Emulators/RE4DC-RR"/cand-*; do [ -f "$d/gdemu/track03.bin" ] && echo "$d" || true; done | tail -1)
R=$S/rel; rm -rf "${R:?}"; mkdir -p $R
python3 $D/fullplay/fp_iso.py extract "$CAND/gdemu/track03.bin" $R/tree --manifest $R/manifest.json --ipbin $R/IP.BIN | tail -1
EV=/mnt/c/Flycast-Evidence/re4-dreamcast/cast-ps2-25/_discs/r18-$TAG
FP_GC_CATALOG=$G/catalog/gc-assets.idx bash $D/fullplay/fp_master.sh $R/tree $R/manifest.json $R/IP.BIN $EV $O 2>&1 | tail -1
rm -rf "${R:?}/tree"
N=/opt/toolchains/dc/sh-elf/bin/sh-elf-nm; E=$O/re4dc-game.elf
for s in _re4dc_logbuf _re4dc_log_head _re4dc_stage; do printf '0x%x ' $(( 0x$($N $E | awk -v s=$s '$3==s{print $1}') - 0x8c000000 )); done; echo
