#!/usr/bin/env bash
set -euo pipefail
LAND=/root/work/lanes/dedup-offline23-land
BASE=d5c1ceab9e06461462669b3ce1d28a379747a74a
ROOT=/root/work/lanes/dedup-offline23-land-scratch
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01/root-landing'
if [ "${1:-}" = --after-slot ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ] || exit 3
 exec "$@"
fi
MODE=${1:-off}
case "$MODE" in off) DD=0;;on) DD=3;;*)exit 2;;esac
[ -f "$E/merge-source.txt" ]
SOURCE=$(cat "$E/merge-source.txt")
[ "$(git -C "$LAND" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$LAND" status --porcelain)" ]
git -C "$LAND" diff --exit-code "$BASE" HEAD -- port/dreamcast/tools/d367/rr/recipe.conf
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 26843545600 ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' > "$E/release-process-check.txt";then
 echo RELEASE_PRIORITY_HOLD;exit 3
fi
mkdir -p "$ROOT"
exec 7>"$LAND.build.lock";flock -n 7 || exit 2
T=$LAND/port/dreamcast/tools/d367
git -C "$LAND" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
. "$T/rr/recipe.conf"
export JOBS=4 SOURCE_DATE_EPOCH=1760000000 PRUNE_AUTO=0 PYTHONDONTWRITEBYTECODE=1
export RE4DC_HARNESS="$ROOT" ROUTE_PROGRAMS_DIR="$ROOT/programs" ROUTE_PROGRAMS_JSON='' ROUTE_REGISTRY_LOCK="$ROOT/programs.lock"
LABEL=dd23land${SOURCE:0:8}${MODE}rP
O=/root/probe/lanes/route/out-$LABEL
[ ! -e "$O" ]
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$E/kos-$MODE-before.sha256"
bash /root/probe/d367-buildslot.sh bash "$OWN/takeover-land-build-v1.sh" --after-slot env K="$ROOT/k-$MODE" T="$LAND" LP="dd23land${SOURCE:0:8}${MODE}" CH2="$CH2 SCENERY_DEDUP=$DD" XON='' bash "$T/ch2/ch2-build.sh" rP
[ ! -s "$O/missing.txt" ]
[ "$(cat "$O/stack.txt")" = "$SOURCE" ]
for KV in SCENERY_DEDUP=$DD SCENERY_EMIT_PREFETCH=0 SCENERY_SELECT_LEAN2=0 STAT_ROUTINE_BYTES=1 STAT_DIAG=0 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 EM_READ_RETRY=1 KOS_CACHE_P2_DIAG=0 VRAM_ROOM_ARENA=0;do
 grep -qx "$KV" "$O/resolved-knobs.txt"
done
R=/root/probe/lanes/route/out-au23ld5c1rP
[ "$MODE" != on ] || R=/root/probe/lanes/route/out-dd23cur4be08e01onrP
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$ROOT/landing-$MODE.bin"
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$R/re4dc-game.elf" "$ROOT/reference-$MODE.bin"
cmp "$ROOT/landing-$MODE.bin" "$ROOT/reference-$MODE.bin"
python3 - "$O" "$R" "$ROOT" "$E" "$SOURCE" "$MODE" <<'PY'
from pathlib import Path
import hashlib,json,sys
o,r,w,e=map(Path,sys.argv[1:5]);source,mode=sys.argv[5:7]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a,b=sorted(o.glob('*.ovl')),sorted(r.glob('*.ovl'))
assert len(a)==len(b)==14
for p,q in zip(a,b):assert p.name==q.name and p.read_bytes()==q.read_bytes(),p.name
expected={'off':'49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b','on':'1077a1386ac3431b97d069291424a14117adf55f267aff78fbedf166bdc6df09'}
assert sha(w/f'landing-{mode}.bin')==expected[mode]
j=dict(source=source,baseline='d5c1ceab9e06461462669b3ce1d28a379747a74a',mode=mode,raw_sha256=sha(w/f'landing-{mode}.bin'),all14_identical=True,elf_sha256=sha(o/'re4dc-game.elf'),profile_sha256=sha(o/'resolved-knobs.txt'),production_dedup=0,production_prefetch=0,physical_acceptance=False)
(e/f'landing-build-{mode}-identity.json').write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps(j,indent=2))
PY
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$E/kos-$MODE-after.sha256"
cmp "$E/kos-$MODE-before.sha256" "$E/kos-$MODE-after.sha256"
printf 'LANDING_BUILD_IDENTICAL; source=%s mode=%s\n' "$SOURCE" "$MODE"
