#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/camera-log24
SOURCE=c2f0d82e95050a708d0b977f94fad34890cbc279
ROOT=/root/work/lanes/camera-log24-scratch/off-identity
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/restrip23-fb254/root-forest-camera-v2'
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
if [ "${1:-}" = --worker ];then shift;[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ];exec "$@";fi
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 26843545600 ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' >/dev/null;then echo RELEASE_PRIORITY_HOLD;exit 3;fi
exec 7>"$TREE.build.lock";flock -n 7 || exit 2
T=$TREE/port/dreamcast/tools/d367
. "$T/rr/recipe.conf"
git -C "$TREE" diff --exit-code fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2 HEAD -- "$T/rr/recipe.conf"
export JOBS=2 SOURCE_DATE_EPOCH=1760000000 PRUNE_AUTO=0 PYTHONDONTWRITEBYTECODE=1
export RE4DC_HARNESS="$ROOT" ROUTE_PROGRAMS_DIR="$ROOT/programs" ROUTE_PROGRAMS_JSON='' ROUTE_REGISTRY_LOCK="$ROOT/programs.lock"
O=/root/probe/lanes/route/out-cam24c2f0offrP
[ ! -e "$O" ];mkdir -p "$ROOT"
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$E/off-kos-before.sha256"
bash /root/probe/d367-buildslot.sh bash "$OWN/camera-v2-off-identity-20261024.sh" --worker env K="$ROOT/k" T="$TREE" LP=cam24c2f0off CH2="$CH2" XON='' bash "$T/ch2/ch2-build.sh" rP
[ ! -s "$O/missing.txt" ];[ "$(cat "$O/stack.txt")" = "$SOURCE" ]
for KV in PS2_PVS=0 SCENERY_DEDUP=0 SCENERY_EMIT_PREFETCH=0 SCENERY_SUBMIT_BATCH=1;do grep -qx "$KV" "$O/resolved-knobs.txt";done
R=/root/probe/lanes/route/out-dd23landfb254e82offrP
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$ROOT/new.bin"
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$R/re4dc-game.elf" "$ROOT/reference.bin"
cmp "$ROOT/new.bin" "$ROOT/reference.bin"
python3 - "$O" "$R" "$ROOT" "$E" "$SOURCE" <<'PY'
from pathlib import Path
import hashlib,json,sys
o,r,w,e=map(Path,sys.argv[1:5]);source=sys.argv[5];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a,b=sorted(o.glob('*.ovl')),sorted(r.glob('*.ovl'));assert len(a)==len(b)==14
for p,q in zip(a,b):assert p.name==q.name and p.read_bytes()==q.read_bytes(),p.name
assert sha(w/'new.bin')=='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
j=dict(status='PASS_OFF_TARGET_IMAGE_IDENTITY',source=source,reference_source='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',new_main_raw_sha256=sha(w/'new.bin'),main_identical=True,all14_identical=True,elf_sha256=sha(o/'re4dc-game.elf'),resolved_profile_sha256=sha(o/'resolved-knobs.txt'),scope='Actual normal recipe OFF link identity only; camera diagnostic capture separately qualified; no hardware claim.',overlays={p.name:sha(p) for p in a})
(e/'OFF-IDENTITY.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
PY
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$E/off-kos-after.sha256"
cmp "$E/off-kos-before.sha256" "$E/off-kos-after.sha256"
echo CAMERA_V2_OFF_IDENTITY_COMPLETE
