#!/bin/bash
# ch4regen: replay of the ch4found em3c.sh / em3c2.sh / mask / gen216 chain (10-17 17:04Z) -> ch4found/cast/reg-216.
set -euo pipefail
S=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
W=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch4regen/ch4found/cast
WL=/root/probe/lanes-20261018/ch4regen/ch4found/cast
P="/c/Game Dev/Emulators/re4-assets-private/cast-20260925/ganado-em15-00/pose-samples.json"
TL=/root/probe/lanes-20261018/ch4regen/tree/port/dreamcast/tools
cd /c/tmp
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- mkdir -p $WL/conv
for p in armor-em3c-00w armor-em3c-02w; do
  rm -rf "$W/conv/${p:?}"
  python $S/c4r-c4w.py convert $p "$W/conv/$p" --poses "$P" > $W/conv/$p.log 2>&1 || { echo "convert FAIL $p"; tail -3 $W/conv/$p.log; }
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- env PS2CAST_HOSTCHECK=/root/probe/lanes-20261018/ch4regen/host-check bash $TL/ps2_cast_native.sh $WL/conv/$p > $W/conv/$p.native.log 2>&1 || echo "native FAIL $p"
  python $S/c4r-c4w.py finish "$W/conv/$p" >> $W/conv/$p.native.log 2>&1 || echo "finish FAIL $p"
  echo "$p $(tail -1 $W/conv/$p.native.log | cut -c1-120)"
done
rm -rf "$W/regcast-em3c"
python $S/c4r-c4w.py regcast "$W/regcast-em3c" ps2-overlay "$W/conv/armor-em3c-00w" "$W/conv/armor-em3c-02w" 2>&1 | tail -1 | cut -c1-120
python $TL/ps2_mask_runs.py "$W/conv/armor-em3c-02w" //wsl.localhost/Ubuntu-24.04/root/probe/lanes/ps2cast/inputs/em3c.drs 0x9 0xa 0 "$W/conv/mask-armor-em3c-02w-s0" --size 32x64 > /dev/null 2>&1; echo "mask rc=$?"
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash -c 'set -euo pipefail; T=/root/probe/lanes-20261016/ch4found/tree; M=$T/port/dreamcast/tools/d367/model-registry; o=/root/probe/lanes-20261016/ch4found/cast/reg-216; rm -rf "${o:?}"; cd $T; python3 port/dreamcast/tools/d367/model_registry.py $M/ps2-ch4f-r216.json $o --tree $T --package-room 216 --pool --wide-identity --pack-bones 64 --roles5 > $o.log 2>&1 && sha256sum $o/package/r216/registry.re4nmr || tail -2 $o.log'
