#!/bin/bash
# build.sh <LP> <arm> [XON knobs...]: lane final16 build of a t15-build.sh arm into the lane's own build dir (-j4).
set -u
LANE=/root/probe/lanes-20261016/final16
LP=$1; ARM=$2; shift 2
export T=${T:-$LANE/tree} K=$LANE/k LP
export XON="$*"
export ROUTE_OUT_ROOT=$LANE/build ROUTE_PROGRAMS_DIR=$LANE/build/programs ROUTE_PROGRAMS_JSON=$LANE/build/programs-route.json ROUTE_REGISTRY_LOCK=$LANE/build/programs-route.lock JOBS=4
mkdir -p $LANE/build $K
for v in MAKEFLAGS MFLAGS MAKEOVERRIDES GNUMAKEFLAGS; do unset $v || true; done
bash $T/port/dreamcast/tools/d367/test15/t15-build.sh $ARM > $LANE/build/build-$LP$ARM.log 2>&1
echo "rc=$?"; grep -v 'No such file' $LANE/build/build-$LP$ARM.log | tail -4
O=$LANE/build/out-$LP$ARM
end=$(/opt/toolchains/dc/sh-elf/bin/sh-elf-nm $O/re4dc-game.elf 2>/dev/null | awk '$3=="_end"{print $1}')
echo "end=$end missing=[$(cat $O/missing.txt 2>/dev/null | head -5 | tr '\n' ' ')]"
ls -la $O/*.ovl 2>/dev/null | awk '{print $5, $9}' | sed 's#.*/##' | tr '\n' ' '; echo
