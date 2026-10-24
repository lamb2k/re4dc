#!/usr/bin/env bash
set -euo pipefail
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
F='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/fixtures'
ARM=${1:?off or on}
case "$ARM" in off) PPL=0x8c363080;PG=0x8c2b28dc;;on) PPL=0x8c363020;PG=0x8c2b287c;;*)exit 2;;esac
[ "$(git -C /root/work/lanes/stat-bytes23-complete rev-parse HEAD)" = 2a14662d4b025031cd93f64eed6a5d8159d473b7 ]
[ "$(head -1 "$E/identities/$ARM-g-source.txt" | tr -d '\r')" = 2a14662d4b025031cd93f64eed6a5d8159d473b7 ]
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
SYMS=$(cat "$E/identities/$ARM-g-syms.txt" | tr -d '\r')
CAP="$E/boat-repro-20261023/$ARM"
[ ! -e "$CAP" ]
exec bash "$D/stat-guest-slot.sh" env TRACE_LOCK_OWNER="stat23-boat-$ARM" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$D/boat-repro-observer.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" "$PPL" "$PG" --base "$(wslpath -w "$E/_discs/$ARM-g")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$F/boat-warp.txt")" --pad "$(wslpath -w "$F/boat-pad.txt")" --seconds 48 --period 10 --name "stat23-boat-$ARM"
