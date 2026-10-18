# reg113p-a.sh (WSL): replay of ps2cast s152 (regcast-ch2) for lane ch2regen. Paths re-rooted to the lane.
set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen
W=$L/ps2cast/conv-ch2; mkdir -p "$W" "$L/ps2cast/inputs-ch2" "$L/ps2cast/host-check2/host/dc"
cp "$L/tools/pvr.h" "$L/ps2cast/host-check2/host/dc/pvr.h"
S="/mnt/c/Game Dev/Emulators/re4-assets-private/p2b-20261011/regcast-r108"
rm -rf "${W:?}/regcast-ch2"; cp -a "$S" "$W/regcast-ch2"
python3 - "$W" "$S" <<'P'
import json, glob, sys
W = sys.argv[1] + '/regcast-ch2'; S = sys.argv[2]
add = {'r111', 'r113'}; n = 0
for p in glob.glob(W + '/**/*.json', recursive=True):
    s = open(p).read().replace(S, W); d = json.loads(s)
    def fix(x):
        global n
        if isinstance(x, dict):
            if isinstance(x.get('rooms'), list) and x['rooms'] and all(isinstance(r, str) and r.startswith('r') for r in x['rooms']):
                x['rooms'] = sorted(set(x['rooms']) | add); n += 1
            for v in x.values(): fix(v)
        elif isinstance(x, list):
            for v in x: fix(v)
    fix(d); open(p, 'w').write(json.dumps(d, indent=1))
print('rooms updated', n)
P
# GC em17 input (PS2 em17.dat is read from the ISO by ps2_cast.py itself)
python3 "$L/tools/gcx.py" "$L/ps2cast/gcx" em/em17.drs
cp "$L/ps2cast/gcx/em/em17.drs" "$L/ps2cast/inputs-ch2/em17.drs"
sha256sum "$L/ps2cast/inputs-ch2/em17.drs"
echo "expect a90a688bf47e31e2 (10-15 inputs-ch2/em17.drs)"
