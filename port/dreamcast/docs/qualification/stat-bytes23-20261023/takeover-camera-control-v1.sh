#!/usr/bin/env bash
set -euo pipefail
BASE=/root/work/lanes/stat-bytes23-complete
TR=/root/work/lanes/stat-bytes23-camera-control
ROOT=/root/work/lanes/stat-bytes23-camera-control-scratch
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
F='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23-20261023/mendez-bounded-itemack-r3'
[ ! -e "$TR" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
git -C "$BASE" worktree add -b wip/stat-bytes23-camera-control-20261023 "$TR" 2a14662d4b025031cd93f64eed6a5d8159d473b7
python3 - "$TR/src/game/player.cpp" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]);s=p.read_text();old='&& (stat & STAT_BE(0xFFFFFF00)) == STAT_BE(0x100) && !(pG->Status_flg[0] & 0x20)) {'
new='&& (stat & 0xFFFFFF00) == 0x100 && !(pG->Status_flg[0] & 0x20)) {'
assert s.count(old)==1;p.write_text(s.replace(old,new))
PY
git -C "$TR" diff --check
git -C "$TR" add src/game/player.cpp
git -C "$TR" commit -m 'Test control only: isolate legacy camera moved predicate from the stat audit'
git -C "$TR" push -u origin HEAD:refs/heads/wip/stat-bytes23-camera-control-20261023
SHA=$(git -C "$TR" rev-parse HEAD)
git -C "$TR" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
mkdir -p "$ROOT"
exec 7>"$ROOT/tree.lock";flock -n 7 || exit 2
exec > >(tee "$ROOT/launch.log") 2>&1
T=$TR/port/dreamcast/tools/d367
export JOBS=4 SOURCE_DATE_EPOCH=1760000000
. "$T/rr/recipe.conf"
LP=sb23camctrl
O=/root/probe/lanes/route/out-${LP}rT
[ ! -e "$O" ]
bash /root/probe/d367-buildslot.sh env K="$ROOT/k" T="$TR" LP="$LP" CH2="$CH2 STAT_ROUTINE_BYTES=1 STAT_DIAG=0" XON="PC_SAMPLER=0" bash "$T/ch2/ch2-build.sh" rT
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
for K in STAT_ROUTINE_BYTES=1 STAT_DIAG=0 LOGIC_TRACE=1 GAME_DECISION_TRACE=1 PC_SAMPLER=0;do grep -qx "$K" "$O/resolved-knobs.txt";done
R=/root/work/lanes/stat-bytes23-takeover-scratch/release
B=$E/_discs/camera-control-t
[ ! -e "$B" ]
mkdir -p "$E/camera-control-identity"
cp "$O/stack.txt" "$O/resolved-knobs.txt" "$O/syms.txt" "$E/camera-control-identity/"
git -C "$TR" diff 2a14662d4b025031cd93f64eed6a5d8159d473b7..HEAD > "$E/camera-control-identity/test-only.patch"
sha256sum "$O/re4dc-game.elf" "$O"/*.ovl > "$E/camera-control-identity/programmes.sha256"
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$R/tree" "$R/manifest.json" "$R/IP.BIN" "$B" "$O" > "$E/camera-control-identity/master.log" 2>&1
P=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
CAP=$E/mendez-camera-control-r1
[ ! -e "$CAP" ]
export RE4DC_EMU=console RE4DC_MAX_FLYCASTS=16 FP_NOLIMIT=1 TRACE_SLOTS=16 TRACE_LOCK_OWNER=stat23-camera-control
export WSLENV="${WSLENV:+${WSLENV}:}RE4DC_EMU:RE4DC_MAX_FLYCASTS:FP_NOLIMIT"
SYMS=$(cat "$O/syms.txt")
bash "$D/stat-guest-slot.sh" bash "$T/trace_lock.sh" "$P" "$(wslpath -w "$D/census-bound-run.py")" "$(wslpath -w "$T/fullplay/fp_run.py")" --base "$(wslpath -w "$B")" --cap "$(wslpath -w "$CAP")" --syms "$SYMS" --warp "$(wslpath -w "$F/mendez-bounded-warp.txt")" --pad "$(wslpath -w "$F/mendez-bounded-pad.txt")" --seconds 53 --period 0 --stop 'phase=enter room=10f' --grace 2 --name stat23-camera-control
printf 'CAMERA_CONTROL_COMPLETE source=%s\n' "$SHA"
