#!/bin/bash
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
I=/root/probe/lanes/ps2cast/inputs
python3 - <<'P'
import sys, os
sys.path.insert(0, '/root/probe/lanes-20261018/ch4regen/tree/port/dreamcast/tools')
from assetpipe.rooms import GcIso
iso = GcIso('/mnt/c/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso')
for n in ('em11', 'em14', 'em16', 'em19', 'em1a', 'em1b', 'em1c', 'em2d'):
    p = '/root/probe/lanes/ps2cast/inputs/%s.drs' % n
    if not os.path.exists(p): open(p, 'wb').write(iso.read('em/%s.drs' % n))
P
sha256sum $I/em11.drs $I/em14.drs $I/em16.drs $I/em1c.drs $I/em2d.drs | cut -c1-16
C=/root/probe/lanes-20261018/ch3regen
python3 $S/c4r-compall.py \
  em14=$C/aica/em/em14.drs:$C/prepem/origin_lane_castle-1015/prep-em14 \
  em19=$C/aica/em/em19.drs:$C/prepem/origin_lane_castle-1015/prep-em19 \
  em1b=$C/aica/em/em1b.drs:$C/prepem/origin_lane_castle-1015/prep-em1b \
  em2d=$C/prepem/origin_wip_ch3found16-20261017/prep-em2d/em2d.drs:$C/prepem/origin_wip_ch3found16-20261017/prep-em2d
