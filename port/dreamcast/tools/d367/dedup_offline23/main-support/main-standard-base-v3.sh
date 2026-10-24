#!/bin/bash
set -euo pipefail
TR=/root/work/lanes/dedup-offline23-next
T=$TR/port/dreamcast/tools/d367
ROOT=/root/work/lanes/dedup-offline23-main
EV='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023'
ARM=${1:?off or on}
case "$ARM" in
 off|on) LABEL=fpdd23std${ARM}542gW;;
 *)exit 2;;
esac
O=/root/probe/lanes/route/out-$LABEL
DEST=$EV/base-standard-$ARM
[ -s "$O/re4dc-game.elf" ] && [ -s "$O/syms.txt" ] && [ ! -s "$O/missing.txt" ]
[ "$(cat "$O/stack.txt")" = 54240115d1949243752c7052d22db2c4e0308826 ]
for K in QA_MENU=0 WORLD_METER=0 PC_SAMPLER=0 DBG_WARP=1 WARP_JUMP=1;do grep -qx "$K" "$O/resolved-knobs.txt";done
[ ! -e "$DEST" ]
# Exact base and one temporary guest are each 1028724736 bytes. A 23 GiB admission leaves over 20 GiB plus 1 GiB for bounded logs and concurrent drift.
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 24696061952 ]
. "$T/rr/recipe.conf"
python3 - "$T/rr/recipe.conf" "$ROOT/stage-on" <<'PY'
from pathlib import Path
import json,re,hashlib,sys
recipe,stage=map(Path,sys.argv[1:])
# Compare the staging recipe's DATA against the actual build recipe before
# reusing its immutable assets. Locate the original saved staging recipe.
options=[stage/'recipe-original.conf',Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-assets23/recipe.conf')]
def data(p):
 m=re.search(r'^DATA=(.*)$',p.read_text(),re.M)
 if not m: raise RuntimeError('No DATA in '+str(p))
 return m.group(1).strip().strip('"').strip("'").split(',')
current=data(recipe)
old=next((p for p in options if p.exists() and data(p)==current),None)
if old is None: raise RuntimeError('Saved DATA differs from current recipe; cannot reuse stage')
r={'source': '54240115d1949243752c7052d22db2c4e0308826','current_recipe':str(recipe),'current_recipe_sha256':hashlib.sha256(recipe.read_bytes()).hexdigest(),'saved_recipe':str(old),'saved_recipe_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'data':current,'identical':True,'note':'Private alternate files remain unused in dedup-off arm; only programme and overlays change in fp_master.'}
(Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023')/'standard-base-asset-reuse-v2.json').write_text(json.dumps(r,indent=2)+'\n')
print('DATA_REUSE_IDENTICAL',len(current))
PY
mkdir -p "$EV/standard-base-logs"
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$ROOT/stage-on/pkgtree" "$ROOT/stage-on/manifest.json" "$ROOT/stage-on/gdemu/IP.BIN" "$DEST" "$O" > "$EV/standard-base-logs/$ARM.txt" 2>&1
tail -3 "$EV/standard-base-logs/$ARM.txt"
printf 'STANDARD_BASE_READY %s\n' "$ARM"