#!/usr/bin/env bash
set -euo pipefail
# Worker-private serialization precedes shared pool and trace locks.
exec 7>/root/probe/.world-emit23-runtime-support.lock
flock 7
ARM=${1:?arm}; TYPE=${2:?n/m}; SCENE=${3:?b1/s2}; TAG=${4:?unique-tag}
case "$ARM-$TYPE-$SCENE" in R-n-b1|R-n-s2|R-m-b1|R-m-s2|L-m-b1|L-m-s2|E-m-b1|E-m-s2|B-m-b1|B-m-s2);;*)exit 2;;esac
SHA=7a3af776ff8c14070f96272cd48074e5895d0490
T=/root/work/lanes/world-emit23-target-$ARM/port/dreamcast/tools/d367
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
E=/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/7a3af776
FIX='/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/fixtures/'$SCENE.txt
BASE=$E/_discs/$ARM-$TYPE
CAP=$E/runtime-support/$TAG
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
[ "$(git -C "$T" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$T" status --porcelain)" ]
[ ! -e "$CAP" ]
[ "$(df --output=avail -B1 /mnt/c |tail -1|tr -d ' ')" -ge 23622320128 ]
KN=$E/identities/$ARM-$TYPE-resolved-knobs.txt
for K in SCENERY_SELECT_ONLY=1 SCENERY_REPLAY_LEAN=1 SCENERY_SUBMIT_BATCH=1 PS2_PVS=0 SCENERY_DEDUP=0 STAT_ROUTINE_BYTES=1 R101_ALIVE_CAP=4 QUALITY=1 QUALITY_LOD_PX=5 SCENERY_FAR_LOD=4 CPU_BACKFACE=0 ACTOR_BACKFACE=0 ACTOR_SETUP_LEAN=0 PC_SAMPLER=0;do grep -qx "$K" "$KN";done
if [ "$TYPE" = n ];then grep -qx SCENERY_EMIT_CENSUS=1200 "$KN";grep -qx WORLD_METER=0 "$KN";else grep -qx SCENERY_EMIT_CENSUS=0 "$KN";grep -qx WORLD_METER=1 "$KN";grep -qx GAME_TICK_LOG=60 "$KN";grep -qx PHASE_METER=1 "$KN";fi
mkdir -p "$E/runtime-support/launch-receipts"
RP=$E/runtime-support/launch-receipts/$TAG.txt
{
 date -u +%FT%TZ
 printf 'source=%s arm=%s type=%s scene=%s request_seconds=40\n' "$SHA" "$ARM" "$TYPE" "$SCENE"
 sha256sum "$FIX" "$KN" "$BASE/base.json" "$BASE/base-manifest.json" "$BASE/track03.sha256" "$E/identities/$ARM-$TYPE-programmes.sha256" "$T/fullplay/fp_run.py" "$D/census-bound-run.py"
 cat "$E/identities/$ARM-$TYPE-stack.txt"
 sha256sum -c "$E/identities/$ARM-$TYPE-programmes.sha256"
 python3 - "$BASE" <<'PY'
import hashlib,pathlib,sys
p=pathlib.Path(sys.argv[1]); expected=(p/'track03.sha256').read_text().split()[0]
h=hashlib.file_digest((p/'track03.iso').open('rb'),'sha256').hexdigest();assert h==expected,(h,expected)
print('base_track03_verified='+h)
PY
} > "$RP"
SYMS=$(cat "$E/identities/$ARM-$TYPE-syms.txt")
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=world-emit23-runtime-support-$TAG
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$BASE")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$FIX")" --seconds 40 --period 0 --name worldemit-$TAG