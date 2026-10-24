#!/usr/bin/env bash
set -euo pipefail
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/audits23/takeover-build-v1.sh'
if [ "${1:-}" = --after-slot ];then shift;[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ];exec "$@";fi
ARM=${1:?off/on};SOURCE=${2:?frozen source}
[[ "$SOURCE" =~ ^[0-9a-f]{40}$ ]]
case "$ARM" in off)V=0;;on)V=1;;*)exit 2;;esac
B=/root/work/lanes/audits23
TR=/root/work/lanes/audits23-target-$ARM
ROOT=/root/work/lanes/audits23-takeover-scratch
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
[ ! -e "$TR" ];git -C "$B" worktree add --detach "$TR" "$SOURCE"
[ "$(git -C "$TR" rev-parse HEAD)" = "$SOURCE" ];[ -z "$(git -C "$TR" status --porcelain)" ]
mkdir -p "$ROOT/$ARM";exec 7>"$ROOT/tree-$ARM.lock";flock -n 7 || exit 2
exec > >(tee "$ROOT/$ARM/build.log") 2>&1
git -C "$TR" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
T=$TR/port/dreamcast/tools/d367
export JOBS=4 SOURCE_DATE_EPOCH=1760000000
. "$T/rr/recipe.conf"
CH2="$CH2 EM_READ_RETRY=1 ESP_POOL_RECYCLE=$V R117_EFFECT_FAILURE_SAFE=$V KOS_CACHE_P2=$V R10C_SPAWN_LIVE_GUARD=$V KOS_CACHE_P2_DIAG=0"
cp "$T/rr/recipe.conf" "$ROOT/$ARM/recipe.conf"
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/$ARM/kos-before.sha256"
LP=au23${ARM}${SOURCE:0:4}
O=/root/probe/lanes/route/out-${LP}rP
[ ! -e "$O" ]
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot env K="$ROOT/$ARM/k" T="$TR" LP="$LP" CH2="$CH2" XON="" bash "$T/ch2/ch2-build.sh" rP
[ -s "$O/re4dc-game.elf" ];[ ! -s "$O/missing.txt" ]
for K in STAT_ROUTINE_BYTES=1 STAT_DIAG=0 "ESP_POOL_RECYCLE=$V" "R117_EFFECT_FAILURE_SAFE=$V" "KOS_CACHE_P2=$V" "R10C_SPAWN_LIVE_GUARD=$V" EM_READ_RETRY=1 KOS_CACHE_P2_DIAG=0 VRAM_ROOM_ARENA=0 CPU_BACKFACE=0 ACTOR_BACKFACE=0;do
 grep -qx "$K" "$O/resolved-knobs.txt"
done
# The make inventory must resolve diagnostics to zero; no observer symbol may enter the image.
/opt/toolchains/dc/sh-elf/bin/sh-elf-nm "$O/re4dc-game.elf" > "$ROOT/$ARM/symbols.txt"
! grep -q 're4dc_cache_p2_diag_' "$ROOT/$ARM/symbols.txt"
if [ "$ARM" = off ];then
 BASE=/root/probe/lanes/route/out-sb23on2a14rP
 TOOL=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
 "$TOOL" -R .stack -O binary "$O/re4dc-game.elf" "$ROOT/$ARM/program.bin"
 "$TOOL" -R .stack -O binary "$BASE/re4dc-game.elf" "$ROOT/$ARM/baseline.bin"
 cmp "$ROOT/$ARM/program.bin" "$ROOT/$ARM/baseline.bin"
 python3 - "$O" "$BASE" <<'PY'
import pathlib,sys,hashlib,json
x,y=map(pathlib.Path,sys.argv[1:]);a=sorted(x.glob('*.ovl'));b=sorted(y.glob('*.ovl'));assert len(a)==len(b)==14
for p,q in zip(a,b):assert p.name==q.name and p.read_bytes()==q.read_bytes(),p.name
print('OFF current production raw and14overlay identity PASS')
PY
else
 export FP_TREE=$TR
 bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$T/fullplay/fp_twin.sh" "$O" ${LP}g
 export FP_SKIP_IDENTITY=1
 bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$T/fullplay/fp_twin.sh" "$O" ${LP}c KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150
 bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot env K="$ROOT/$ARM/kt" T="$TR" LP="$LP" CH2="$CH2" XON="PC_SAMPLER=0" bash "$T/ch2/ch2-build.sh" rT
fi
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/$ARM/kos-after.sha256"
cmp "$ROOT/$ARM/kos-before.sha256" "$ROOT/$ARM/kos-after.sha256"
printf 'AUDIT_BUILD_COMPLETE arm=%s source=%s\n' "$ARM" "$SOURCE"