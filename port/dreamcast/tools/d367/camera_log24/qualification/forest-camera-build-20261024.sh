#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/dedup-offline23-land
SOURCE=fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
ROOT=/root/work/lanes/dedup-offline23-land-scratch/forest-camera
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/restrip23-fb254/root-forest-camera'
if [ "${1:-}" = --worker ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ] || exit 3
 exec "$@"
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 27917287424 ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' > /dev/shm/restrip-camera-release-check.txt;then
 echo RELEASE_PRIORITY_HOLD;exit 3
fi
mkdir -p "$ROOT" "$E"
exec 7>"$TREE.build.lock";flock -n 7 || exit 2
T=$TREE/port/dreamcast/tools/d367
. "$T/rr/recipe.conf"
export JOBS=2 SOURCE_DATE_EPOCH=1760000000 PRUNE_AUTO=0 PYTHONDONTWRITEBYTECODE=1
export RE4DC_HARNESS="$ROOT" ROUTE_PROGRAMS_DIR="$ROOT/programs" ROUTE_PROGRAMS_JSON='' ROUTE_REGISTRY_LOCK="$ROOT/programs.lock"
LABEL=rs24fb254camrW
O=/root/probe/lanes/route/out-$LABEL
[ ! -e "$O" ]
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$E/kos-before.sha256"
cp "$T/rr/recipe.conf" "$E/recipe.conf"
# Camera measurement only. PVS mode2 disables visibility sets/cuts. The existing
# make guard excludes PVS+SUBMIT_BATCH; retain its guard and declare batch0 here.
bash /root/probe/d367-buildslot.sh bash "$OWN/forest-camera-build-20261024.sh" --worker env K="$ROOT/k" T="$TREE" LP=rs24fb254cam CH2="$CH2" XON='SCENERY_SUBMIT_BATCH=0 PS2_PVS=1 PS2_PVS_DEFAULT=2 SCENERY_DEDUP=0 PC_SAMPLER=0 QA_MENU=0 GAME_TICK_LOG=60' bash "$T/ch2/ch2-build.sh" rW
[ ! -s "$O/missing.txt" ]
[ "$(cat "$O/stack.txt")" = "$SOURCE" ]
for KV in SCENERY_SUBMIT_BATCH=0 PS2_PVS=1 PS2_PVS_DEFAULT=2 SCENERY_DEDUP=0 PC_SAMPLER=0 QA_MENU=0 SCENERY_SELECT_ONLY=1 SCENERY_REPLAY_LEAN=1 SCENERY_FAR_LOD=4;do grep -qx "$KV" "$O/resolved-knobs.txt";done
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$E/kos-after.sha256"
cmp "$E/kos-before.sha256" "$E/kos-after.sha256"
python3 - "$O" "$E" "$SOURCE" <<'PY'
from pathlib import Path
import hashlib,json,sys
o,e=map(Path,sys.argv[1:3]);s=sys.argv[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=['re4dc-game.elf','resolved-knobs.txt','syms.txt','stack.txt']+[p.name for p in sorted(o.glob('*.ovl'))]
assert len(list(o.glob('*.ovl')))==14
(e/'PROGRAMME-PINS.json').write_text(json.dumps(dict(source=s,label=o.name,scope='Camera-only diagnostic; PVS mode2/no cuts; batch0 due existing guard; not performance or production-image qualification.',files={n:dict(size=(o/n).stat().st_size,sha256=sha(o/n)) for n in files}),indent=2)+'\n')
PY
echo FOREST_CAMERA_BUILD_COMPLETE
