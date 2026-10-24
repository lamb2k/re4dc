#!/usr/bin/env bash
set -euo pipefail
ARM=${1:?on/off}
case "$ARM" in
on) TREE=/root/work/lanes/audits23-target-on;OUT=/root/probe/lanes/route/out-fpau23on5e4dgW;SOURCE=5e4de9a0262d3629c9833c959557de198b2e9f0c;LEASE=/root/work/lanes/audits23-takeover-scratch/tree-on.lock;;
off) TREE=/root/work/lanes/stat-bytes23-complete;OUT=/root/probe/lanes/route/out-fpsb23on2a14gW;SOURCE=2a14662d4b025031cd93f64eed6a5d8159d473b7;LEASE=/root/work/lanes/stat-bytes23-complete-scratch/tree-on.lock;;
*)exit 2;;esac
exec 7>"$LEASE"
flock -n 7 || { echo 'target tree lease held; no compiler started';exit 3; }
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
export PATH=/root/work/kos-re4dc-d367/utils/build_wrappers:/opt/toolchains/dc/sh-elf/bin:/usr/bin:/bin
source "$TREE/port/dreamcast/kos-env.sh"
exec bash /root/probe/d367-buildslot.sh python3 '/mnt/c/Game Dev/Emulators/codex-lanes/audits23/event-fixtures/probe-target-abi-v3.py' --tree "$TREE" --output "$OUT" --source "$SOURCE" --scratch "/dev/shm/aud23-abi-v3-$ARM"
