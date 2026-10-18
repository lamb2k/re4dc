#!/bin/bash
# ch4regen: cast16 conv3 em1b-07p/08p (10-16 21:58Z, tools 9b4cb31f) + conv gigante-em2b-01/03 (10-16 20:14Z, tools 8d401351).
set -euo pipefail
S=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
R=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261016/cast16
P="C:/Game Dev/Emulators/re4-assets-private/cast-20260925/ganado-em15-00/pose-samples.json"
NAT=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen/c4r-native.sh
cd /c/tmp
# em1b.drs for the conv3 masks (raw GC em/em1b.drs, as c16x3.py)
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash -c "cp -n /root/probe/lanes/ps2cast/inputs/em1b.drs /root/probe/lanes-20261016/cast16/conv3/em1b.drs 2>/dev/null || python3 -c \"import sys;sys.path.insert(0,'/root/probe/lanes-20261016/cast16/tree/port/dreamcast/tools');from assetpipe.rooms import GcIso;open('/root/probe/lanes-20261016/cast16/conv3/em1b.drs','wb').write(GcIso('/mnt/c/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso').read('em/em1b.drs'))\"; sha256sum /root/probe/lanes-20261016/cast16/conv3/em1b.drs | cut -c1-16"
T=$R/t9b4/port/dreamcast/tools; W=$R/conv3
for p in zealot-em1b-07p zealot-em1b-08p; do rm -rf "$W/${p:?}"; python $T/ps2_cast.py convert $p "$W/$p" --bone-tol 0.05 > /dev/null 2>&1 || echo "conv FAIL $p"; done
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash $NAT /root/probe/lanes-20261016/cast16/t9b4 /root/probe/lanes-20261016/cast16/conv3/zealot-em1b-07p /root/probe/lanes-20261016/cast16/conv3/zealot-em1b-08p | cut -c1-90
for p in zealot-em1b-07p zealot-em1b-08p; do python $T/ps2_cast.py finish "$W/$p" >/dev/null 2>&1 || echo "finish FAIL $p"; done
for x in "07 0x1fd" "08 0x21a"; do set -- $x; t=$1; tp=$2
  for y in "13 0x202 $tp hood" "16 0x20f 0x210 acc1" "20 0x217 0x218 acc5"; do set -- $y
    python $T/ps2_mask_runs.py $W/zealot-em1b-${t}p $W/em1b.drs $2 $3 $1 $W/mask-em1b-$t-$4 > /dev/null 2>&1 && echo "mask em1b $t $4 ok" || echo "mask em1b $t $4 FAIL"
  done
done
T=$R/t8d4/port/dreamcast/tools; W=$R/conv
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- mkdir -p /root/probe/lanes-20261016/cast16/conv
for p in gigante-em2b-01 gigante-em2b-03; do rm -rf "$W/${p:?}"; python $T/ps2_cast.py convert $p "$W/$p" --poses "$P" --bone-tol 0.05 > /dev/null 2>&1 || echo "conv FAIL $p"; done
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash $NAT /root/probe/lanes-20261016/cast16/t8d4 /root/probe/lanes-20261016/cast16/conv/gigante-em2b-01 /root/probe/lanes-20261016/cast16/conv/gigante-em2b-03 | cut -c1-90
for p in gigante-em2b-01 gigante-em2b-03; do python $T/ps2_cast.py finish "$W/$p" >/dev/null 2>&1 || echo "finish FAIL $p"; done
rm -rf "$W/regcast-gig13"
python $R/tree/port/dreamcast/tools/ps2_cast.py regcast "$W/regcast-gig13" ps2-overlay $W/gigante-em2b-01 $W/gigante-em2b-03 2>&1 | tail -1 | cut -c1-90
echo C3G-DONE
