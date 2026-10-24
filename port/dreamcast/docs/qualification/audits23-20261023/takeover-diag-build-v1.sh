#!/usr/bin/env bash
set -euo pipefail
B=/root/work/lanes/audits23
TR=/root/work/lanes/audits23-target-diag
ROOT=/root/work/lanes/audits23-takeover-scratch/diag
O=/root/probe/lanes/route/out-au23on5e4drP
[ ! -e "$TR" ];[ -s "$O/re4dc-game.elf" ]
git -C "$B" worktree add --detach "$TR" 5e4de9a0262d3629c9833c959557de198b2e9f0c
mkdir -p "$ROOT";exec 7>"$ROOT/tree.lock";flock -n 7 || exit 2
exec > >(tee "$ROOT/build.log") 2>&1
git -C "$TR" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/kos-before.sha256"
export FP_TREE=$TR FP_SKIP_IDENTITY=1 JOBS=4 SOURCE_DATE_EPOCH=1760000000
bash /root/probe/d367-buildslot.sh bash "$TR/port/dreamcast/tools/d367/fullplay/fp_twin.sh" "$O" au23diag5e4dc KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150 KOS_CACHE_P2_DIAG=1
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/kos-after.sha256"
cmp "$ROOT/kos-before.sha256" "$ROOT/kos-after.sha256"
printf 'AUDIT_DIAG_BUILD_COMPLETE\n'