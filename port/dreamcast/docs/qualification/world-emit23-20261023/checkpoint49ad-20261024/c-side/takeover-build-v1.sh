#!/usr/bin/env bash
set -euo pipefail
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/takeover-build-v1.sh'
if [ "${1:-}" = --after-slot ];then shift;[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ];exec "$@";fi
ARM=${1:?R/L/E/B};SHA=7a3af776ff8c14070f96272cd48074e5895d0490
case "$ARM" in R)S=0;P=0;;L)S=1;P=0;;E)S=0;P=1;;B)S=1;P=1;;*)exit 2;;esac
T=/root/work/lanes/world-emit23-target-$ARM
B=/root/work/lanes/world-emit23-target-R
ROOT=/root/work/lanes/world-emit23-takeover-scratch/$ARM
if [ ! -e "$T" ];then git -C "$B" worktree add --detach "$T" "$SHA";fi
[ "$(git -C "$T" rev-parse HEAD)" = "$SHA" ];[ -z "$(git -C "$T" status --porcelain)" ]
mkdir -p "$ROOT";exec 7>"$ROOT/tree.lock";flock -n 7 || exit 2
exec > >(tee "$ROOT/build.log") 2>&1
git -C "$T" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
D=$T/port/dreamcast/tools/d367
export JOBS=4 SOURCE_DATE_EPOCH=1760000000
. "$D/rr/recipe.conf"
CH2="$CH2 SCENERY_SELECT_LEAN2=$S SCENERY_EMIT_PREFETCH=$P SCENERY_EMIT_CENSUS=0"
LP=we23${ARM}7a3a;O=/root/probe/lanes/route/out-${LP}rP
[ ! -e "$O" ]
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/kos-before.sha256"
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot env K="$ROOT/k" T="$T" LP="$LP" CH2="$CH2" XON="" bash "$D/ch2/ch2-build.sh" rP
[ -s "$O/re4dc-game.elf" ];[ ! -s "$O/missing.txt" ]
for K in "SCENERY_SELECT_LEAN2=$S" "SCENERY_EMIT_PREFETCH=$P" SCENERY_EMIT_CENSUS=0 SCENERY_SELECT_ONLY=1 SCENERY_REPLAY_LEAN=1 SCENERY_SUBMIT_BATCH=1 ACTOR_SETUP_LEAN=0 SCENERY_UV_SNAPSHOT=0 SCENERY_DEDUP=0 PS2_PVS=0 STAT_ROUTINE_BYTES=1;do grep -qx "$K" "$O/resolved-knobs.txt";done
if [ "$ARM" = R ];then
 REF=/root/probe/lanes/route/out-rra5e972erP
 /opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$ROOT/program.bin"
 /opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$REF/re4dc-game.elf" "$ROOT/reference.bin"
 cmp "$ROOT/program.bin" "$ROOT/reference.bin"
 python3 - "$O" "$REF" <<'PY'
import pathlib,sys
x,y=map(pathlib.Path,sys.argv[1:]);a=sorted(x.glob('*.ovl'));b=sorted(y.glob('*.ovl'));assert len(a)==len(b)==14
for p,q in zip(a,b):assert p.name==q.name and p.read_bytes()==q.read_bytes(),p.name
print('WORLD_CENSUS_OFF current production raw/14overlay IDENTITY PASS')
PY
fi
export FP_TREE=$T
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$D/fullplay/fp_twin.sh" "$O" ${LP}g
export FP_SKIP_IDENTITY=1
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$D/fullplay/fp_twin.sh" "$O" ${LP}c KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot env K="$ROOT/kt" T="$T" LP="$LP" CH2="$CH2" XON="PC_SAMPLER=0" bash "$D/ch2/ch2-build.sh" rT
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$D/fullplay/fp_twin.sh" "$O" ${LP}m WORLD_METER=1 GAME_TICK_LOG=60 PHASE_METER=1 PC_SAMPLER=0
if [ "$ARM" = R ];then
 bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$D/fullplay/fp_twin.sh" "$O" ${LP}n SCENERY_EMIT_CENSUS=1200 KOS_WATCH=1
fi
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/kos-after.sha256"
cmp "$ROOT/kos-before.sha256" "$ROOT/kos-after.sha256"
printf 'WORLDEMIT_RELEASE_G_C_TRACE_METER_READY arm=%s source=%s\n' "$ARM" "$SHA"