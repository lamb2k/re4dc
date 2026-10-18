#!/bin/bash
# test 10 (small) run fixtures, all from the 9.1 release fixture pkg-r91tP.json
set -eu
K=${T10S_K:-/root/probe/lanes-20261014/t10s}
D=$(cd "$(dirname "$0")" && pwd)
mkdir -p $K/fix
cp $D/t10s-fix.py $D/pakdiff.py $D/elfdiff.py $K/   # in Git (the job tmp copies are gone)
P=/root/probe/lanes-20261013/rel91/fix/pkg-r91tP.json
# payload root (lane payroot18, 10-18): the 9.1 fixture went in the 10-17 /root wipe; without it the base is the payload
# root's fixture (RE4DC_PAYLOAD_ROOT, t11-fix.py --base payload), which already carries the release data.
if [ ! -f $P ]; then
  python3 $D/../test11/t11-fix.py r91tP $K/fix/payload-base-r91tP.json --base payload
  P=$K/fix/payload-base-r91tP.json
fi
FX="python3 $K/t10s-fix.py $P r91tP"
H2W=/root/probe/impl-20261003/fixtures/h2-late-00-warp.txt
H2P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/tour/padscript.txt"
BW=/root/probe/lanes-20261014/i26esp-work/fx/warp-boat.txt
BP=/root/probe/lanes-20261014/i26esp-work/fx/pad-boat3.txt
SQ=/root/probe/lanes-20261011/test8/fix/warps/st-square.txt
FW=/root/probe/lanes-20261014/oldvis-work/w-face.txt
# play package (released)
$FX t10stP $K/fix/pkg-t10stP.json --pak gc --hands 1
# H2 STRICT pair: same data both arms (candidate data)
$FX t10stT $K/fix/h2-t10stT.json --pak gc --hands 1 --warp $H2W --pad "$H2P"
$FX t10scT $K/fix/h2-t10scT.json --pak gc --hands 1 --warp $H2W --pad "$H2P"
# MCHECK_LEONGC + TEX_CHECK=2
$FX t10smW $K/fix/mh2-t10smW.json --pak gc --hands 1 --warp $H2W --pad "$H2P"
$FX t10smW $K/fix/mboat-t10smW.json --pak gc --hands 1 --warp $BW --pad $BP
$FX t10smW $K/fix/msq-t10smW.json --pak gc --hands 1 --warp $SQ
# face B (A = oldvis faceA, 9.1 ovtW + 9.1 pak)
$FX t10stW $K/fix/faceB-t10stW.json --pak gc --hands 1 --warp $FW
# hair: 9.1 (t10scW from rel91, 9.1 data) vs candidate, h2 tour
$FX t10scW $K/fix/hair91-t10scW.json --pak 9.1 --hands 0 --warp $H2W --pad "$H2P"
$FX t10stW $K/fix/hairC-t10stW.json --pak gc --hands 1 --warp $H2W --pad "$H2P"
# hair with the hands package on 9.1 atlases (= i26esp tch2 data) on the candidate code: isolates the atlas effect
$FX t10stW $K/fix/hairH-t10stW.json --pak 9.1 --hands 1 --warp $H2W --pad "$H2P"
for f in $K/fix/*.json; do python3 /mnt/c/Users/lambd/.claude/jobs/1e668c67/tmp/fixdiff.py $P $f | grep -v '^remove only A \[\]' | sed "s#^#${f##*/}: #" | grep -v 'candidate-route\*/' ; done
