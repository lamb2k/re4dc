#!/bin/bash
# lane bakeall: step A (Git Bash + Windows Python, the converter's numpy/PIL): one room's baked 256-vertex PS2 world.
#   conv_room.sh <room> <out root (Windows path)> [tier: 0 recorded recipe (repro) | 1 | 2 (default)] [meshlet vertices: 64 (default, the release since n256off27) | 256]
# Arguments = the room's recorded n256 recipe (world-n256all-scratch/rc-<room>-256/ps2-world.json, the release lineage)
# + --bake-static (+ --bake-rows <tier-2 json> for tier 2) + the r10dbake23 LOD settings (3 m clusters, min gain 0.8,
# floor 60). The UV guard stays the room's own.
set -euo pipefail
R=${1:?room}; OUT=${2:?out root}; TIER=${3:-2}; MV=${4:-64}; CELL=${5:-}; mkdir -p "$OUT"
# CELL (variant, coordinator 11-03): merge only within CELL-sized XZ cells (--bake-cell) and keep the recipe's own
# LOD settings (no bake LOD clustering).
T='//wsl.localhost/Ubuntu-24.04/root/work/lanes/bakeall/port/dreamcast/tools'
J="//wsl.localhost/Ubuntu-24.04/root/probe/lanes/bakeall/rc/rc-$R-$MV/ps2-world.json"   # lane-recovered recipes (r119: ps2rooms args + uv guard 0.002 + cutout 224 + tr4 reproduce the release mesh 9dd036b3)
[ -f "$J" ] || J="//wsl.localhost/Ubuntu-24.04/root/work/lanes/world-n256all-scratch/rc-$R-$MV/ps2-world.json"
ROWS='//wsl.localhost/Ubuntu-24.04/root/probe/lanes/bakeall/bake-rows.json'
ARGS=$(python - "$J" "$TIER" "$CELL" <<'PY'
import json, sys, shlex
a = json.load(open(sys.argv[1]))['args']
skip = {'room', 'src', 'out', 'bake_static', 'bake_rows', 'meshlet_vertices'} | (set() if sys.argv[2] == '0' or sys.argv[3] else {'lod_cluster', 'lod_min_gain', 'lod_floor'})
out = []
for k, v in a.items():
    if k in skip or v in ('None', None, 'False'):
        continue
    flag = '--' + k.replace('_', '-')
    out += [flag] if v == 'True' else [flag, v]
print(shlex.quote(a['src']))
print(' '.join(shlex.quote(x) for x in out))
PY
)
EXTRA="--bake-static --lod-cluster 3000 --lod-min-gain 0.8 --lod-floor 60"     # tier 0: the recipe as recorded (repro check)
[ -n "$CELL" ] && EXTRA="--bake-static --bake-cell $CELL"
[ "$TIER" = 0 ] && EXTRA=""
[ "$TIER" = 2 ] && EXTRA="$EXTRA --bake-rows $ROWS"
SRC=$(echo "$ARGS" | head -n1); OPTS=$(echo "$ARGS" | tail -n +2)
eval python "$T/ps2_room_r4im.py" "$R" "$SRC" '"$OUT/$R"' $OPTS --meshlet-vertices $MV $EXTRA > "$OUT/$R.log" 2>&1
tail -c 300 "$OUT/$R.log"; echo
