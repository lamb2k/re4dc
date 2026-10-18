#!/bin/bash
# ch5regen: lane-local ps2_cast inputs for the island cast (GC review disc 2 .drs + PS2 .dat), own dir.
set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
I=$L/c16/inputs
mkdir -p "$I"
T=$L/tools
GCM="/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm"
USA2=$(ls /mnt/c/Game\ Dev/Emulators/*/*Disc\ 2*.iso 2>/dev/null | head -1 || true)
echo "usa2=$USA2"
cd "$T/port/dreamcast/tools"
"$L/venv/bin/python" - "$GCM" "$I" "$USA2" <<'PY'
import sys, hashlib
sys.path.insert(0, '.')
from assetpipe.rooms import GcIso
gcm, out, usa2 = sys.argv[1:4]
g = GcIso(gcm)
for a in ('em1d', 'em1e', 'em1f', 'em36', 'em32', 'em3a', 'em3d'):
    try:
        b = g.read(f'em/{a}.drs')
    except Exception as e:
        print(a, 'review ERR', e); continue
    open(f'{out}/{a}.drs', 'wb').write(b)
    print(a, len(b), hashlib.sha256(b).hexdigest()[:20])
if usa2:
    u = GcIso(usa2)
    for a in ('em1d', 'em36'):
        try:
            b = u.read(f'em/{a}.drs'); print('usa2', a, len(b), hashlib.sha256(b).hexdigest()[:20])
        except Exception as e:
            print('usa2', a, 'ERR', e)
PY
