#!/bin/bash
set -euo pipefail
REPO=/root/work/lanes/dedup-offline23-next
SHA=54240115d1949243752c7052d22db2c4e0308826
REF=refs/heads/wip/dedup-offline23-standard-support-20261023
[ "$(git -C "$REPO" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$REPO" status --porcelain)" ]
! git -C "$REPO" show-ref --verify --quiet "$REF"
IDX=$(mktemp /dev/shm/dd23-support-index.XXXXXX)
unlink "$IDX"
trap 'test ! -e "$IDX" || unlink "$IDX"' EXIT
export GIT_INDEX_FILE=$IDX
git -C "$REPO" read-tree "$SHA"
for f in main-standard-memory-build.sh main-standard-memory-build-v2.sh main-standard-memory-build-v3.sh main-prepare-twin-off-v3.sh;do
 INPUT="/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/$f"
 BLOB=$(git -C "$REPO" hash-object -w "$INPUT")
 git -C "$REPO" update-index --add --cacheinfo 100755,"$BLOB",port/dreamcast/tools/d367/dedup_offline23/main-support/$f
done
TREE=$(git -C "$REPO" write-tree)
COMMIT=$(printf 'Preserve corrected standard-memory gate helpers and historical first attempt\n\nV1 retains its invalid libkos.a check for provenance; v2/v3 use the actual libkallisti archive and explicit rP SCENERY_DEDUP candidate token. No runtime or production recipe change.\n' | git -C "$REPO" commit-tree "$TREE" -p "$SHA")
git -C "$REPO" update-ref "$REF" "$COMMIT"
git -C "$REPO" push origin "$REF:$REF"
printf 'SUPPORT_PUSHED %s\n' "$COMMIT"
TOOL=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
EV='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023'
BASE=/root/probe/lanes/route/out-dd23stdbase831rP
OFF=/root/probe/lanes/route/out-dd23stdoff542rP
TMP=$(mktemp -d /dev/shm/dd23-off-id.XXXXXX)
"$TOOL" -R .stack -O binary "$BASE/re4dc-game.elf" "$TMP/base.bin"
"$TOOL" -R .stack -O binary "$OFF/re4dc-game.elf" "$TMP/off.bin"
python3 - "$BASE" "$OFF" "$TMP" "$EV" <<'PY'
from pathlib import Path
import hashlib,json,sys
base,off,tmp,ev=map(Path,sys.argv[1:])
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'base_source':(base/'stack.txt').read_text().strip(),'off_source':(off/'stack.txt').read_text().strip(),'base_raw_sha256':h(tmp/'base.bin'),'off_raw_sha256':h(tmp/'off.bin'),'raw_identical':(tmp/'base.bin').read_bytes()==(tmp/'off.bin').read_bytes(),'overlays':[]}
for p in sorted(base.glob('*.ovl')):
 q=off/p.name
 r['overlays'].append({'name':p.name,'base_sha256':h(p),'off_sha256':h(q),'identical':p.read_bytes()==q.read_bytes()})
r['pass']=r['raw_identical'] and len(r['overlays'])==14 and all(x['identical'] for x in r['overlays'])
(ev/'current-standard-off-identity.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
assert r['pass']
PY
unlink "$TMP/base.bin"
unlink "$TMP/off.bin"
rmdir "$TMP"