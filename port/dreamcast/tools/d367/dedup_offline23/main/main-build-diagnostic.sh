#!/bin/bash
set -euo pipefail
TR=/root/work/lanes/dedup-offline23-integration
ROOT=/root/work/lanes/dedup-offline23-main
O=/root/probe/lanes/route/out-dd23af09on2rW
T=$TR/port/dreamcast/tools/d367
[ "$(git -C "$TR" rev-parse HEAD)" = af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34 ]
[ -z "$(git -C "$TR" status --porcelain)" ]
[ ! -e /root/probe/lanes/route/out-fpdd23diagW ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
exec 9>"$ROOT/tree.lock"
flock -n 9 || exit 2
exec > >(tee "$ROOT/diagnostic-build.log") 2>&1
export JOBS=1 SOURCE_DATE_EPOCH=1760000000 FP_TREE=$TR
bash "$T/fullplay/fp_twin.sh" "$O" dd23diag KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150
