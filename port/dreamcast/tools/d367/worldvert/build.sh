#!/bin/bash
# build.sh <label> [extra knobs...]: worldvert cost arm = the worldlod lane's wlcrW recipe (test 13 + PACE_MODE=off cost) + extras
K=/root/probe/lanes-20261015/worldvert-work; T=/root/probe/lanes-20261015/worldvert
ARGS=$(grep -m1 "^== wlcrW " /root/probe/lanes-20261015/worldlod-work/logs-build.txt | sed 's/^== wlcrW [0-9:]* tree=[^ ]* //')
F="PACE_DEBUG=1 ROUTE_CH13=1 ROUTE_CH21=1 SBB_STUB=1 PVR_READY_STRICT=1 ACT_CAP=0 PS2_INTERIOR_ACTORS=2 GAME_ATLIST_OVERFLOW=1 GAME_ATLIST_512=1 LEON_NATIVE_PIPE=0 LEON_FACE_LAZY=0 NATIVE_LASER=1 ACTOR_GANADO_SOURCE_LIGHT=0 PRIM_CAP_R10B=327680"
LOOK="EFFECT_PS2_TOGGLE=1 LOOK_TOGGLE=1 FILTER00_DC=1 CHARBAKE_TOGGLE=1 CHARBAKE_HAIR=0"
export SOURCE_DATE_EPOCH=1760000000
lab=$1; shift
[ "${BASE:-cost}" = play ] && ARGS=$(grep -m1 "^== wlirP " /root/probe/lanes-20261015/worldlod-work/logs-build.txt | sed 's/^== wlirP [0-9:]* tree=[^ ]* //')
t0=$(date +%s); echo "== $lab $(date +%T) $ARGS $*" >> $K/logs-build.txt
(cd $T && TREE=$T bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh $lab $F $LOOK $ARGS "$@" >> $K/logs-build.txt 2>&1)
rc=$?; O=/root/probe/lanes/route/out-$lab
end=$(/opt/toolchains/dc/sh-elf/bin/sh-elf-nm $O/re4dc-game.elf 2>/dev/null | awk '$3=="_end"{print $1}')
echo "rc=$rc $lab $(cut -c1-16 $O/elf.sha256 2>/dev/null) $(( $(date +%s) - t0 ))s missing=$(wc -c < $O/missing.txt 2>/dev/null) end=$end $*" | tee -a $K/logs-build.txt
