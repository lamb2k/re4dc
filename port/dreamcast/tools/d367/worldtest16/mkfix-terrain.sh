#!/bin/bash
# mkfix-terrain.sh (WSL): worldtest16 B fixtures. A = t15/int data as is (these rooms ship level 0 only, no strip groups);
# T = A + the terrain-only variant 5 (ps2_world_vert_ladder.py --mode terrain --keep-walk-mm 1500 --keep-pieces).
# Same ELF (w16mrT, WORLD_VERT=1 LEVEL=5) for both arms. Private data: re4-assets-private/worldtest-20261016/terrain-<room>.
set -eu
TR=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/d367/test11/t11-fix.py
OUT=/root/probe/worldtest16-20261016/fix-terrain; mkdir -p $OUT
WD=/mnt/c/Flycast-Evidence/re4-dreamcast/worldtest-20261016/_tools/w
PRIV="/mnt/c/Game Dev/Emulators/re4-assets-private/worldtest-20261016"
TW=/root/probe/worldtest16-20261016/terrain
DATA=cast15,glod,res16,snd16,res16h,vq16cs,water16h,wt16r101,fsh
# private copies (once)
for r in r100 r102 r103 r104 r105 r106 r107 r108 r109 r10a; do
  P="$PRIV/terrain-$r"; mkdir -p "$P"
  cp $TW/$r/out/ps2-wv5.re4mesh $TW/$r/class.json $TW/$r/L2.json $TW/$r/job.log "$P/"
  (cd "$P" && sha256sum ps2-wv5.re4mesh class.json L2.json job.log > SHA256SUMS)
done
for cam in ${CAMS:-r100-c1 r100-c2 r102-c1 r102-c2b r103-c1 r103-c2 r104-c1 r104-c2 r105-c1 r105-c2 r106-c1 r106-c3 r107-c1 r107-c2 r108-c1 r108-c2 r10a-c1 r10a-c2}; do
  r=${cam%-*}
  for arm in A T; do
    S=()
    [ $arm = T ] && S+=(--set "dc/native/$r/ps2-wv5.re4mesh=$PRIV/terrain-$r/ps2-wv5.re4mesh")
    python3 $TR w16mrT $OUT/$cam-$arm.json --base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP \
      --data $DATA --warp $WD/$cam.txt "${S[@]}" > $OUT/$cam-$arm.log 2>&1 || { echo "FAIL $cam-$arm"; tail -3 $OUT/$cam-$arm.log; }
  done
done
ls $OUT/*.json | wc -l
