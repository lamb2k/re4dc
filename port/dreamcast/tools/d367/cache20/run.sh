#!/bin/bash
# run.sh <name> <arm label> <fixture (WSL path)> [seconds] (Git Bash; lane cache20, after logiclod20/run.sh): one Flycast
# run of a warp fixture on a scenario disc. Evidence C:\Flycast-Evidence\re4-dreamcast\cache20-20261020\<name>; the disc is
# deleted after the run (disc.sha256 kept).
set -euo pipefail
N=${1:?}; L=${2:?}; FIX=${3:?}; SECS=${4:-60}
TR=/root/work/lanes/cache20-scratch/tree
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
E=/c/Flycast-Evidence/re4-dreamcast/cache20-20261020
SP=$E/_tools
ST=/root/work/lanes/cache20-scratch/stage
mkdir -p "$SP"
cd "$H" || exit 1
S=scenarios/route-c20-$N
[ ! -e "$S" ] || { echo "$S exists"; exit 1; }
[ ! -e "$E/$N" ] || { echo "$E/$N exists"; exit 1; }
cat > "$SP/stage-$N.sh" <<EOS
set -euo pipefail
cd "$HW" && mkdir -p $ST && python3 $TR/port/dreamcast/tools/d367/stage_ext4/stage_scenario.py route-c20-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $ST/run-$N.json 2>&1; python3 -c "import json;d=json.load(open('scenarios/route-c20-$N/stage.json'));print(d['status'],d['disc_sha256'])" || tail -5 $ST/run-$N.json
EOS
D=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Flycast-Evidence/re4-dreamcast/cache20-20261020/_tools/stage-$N.sh)
rm -f "$SP/stage-$N.sh"
case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "$N stage failed: $D"; exit 1 ;; esac
echo "${PURPOSE:-cache20 run $N: arm $L, $SECS s}" > $S/PURPOSE.txt
C=$S/capture
for try in $(seq 1 30); do
  printf 'set -euo pipefail\ncd "%s"\nexport TRACE_LOCK_OWNER=cache20-%s\nexec bash %s/port/dreamcast/tools/d367/trace_lock.sh /mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe %s route-c20-%s --seconds %s --period %s\n' "$HW" "$N" "$TR" "${RUNNER:-run-emulator-novsync-i26.py}" "$N" "$SECS" "${PERIOD:-30}" > "$SP/tl-$N.sh"
  MSYS_NO_PATHCONV=1 TRACE_SLOTS=12 WSLENV=TRACE_SLOTS/u wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Flycast-Evidence/re4-dreamcast/cache20-20261020/_tools/tl-$N.sh > $S-run-stdout.txt 2>&1 || true
  grep -q "Emulator queue occupied" $S-run-stdout.txt || break
  sleep 60
done
rm -f "$SP/tl-$N.sh"
echo "$N halt=$(grep -ac HALT $C/run-output.txt) fault=$(grep -ac FAULT $C/run-output.txt)"
echo "$(echo $D | awk '{print $2}')  disc.bin (deleted after run)" > $S/disc.sha256
rm -f $C/disc.bin $S/disc/disc.bin
mv $S $E/$N && mv $S-run-stdout.txt $E/$N/run-stdout.txt && echo "moved to $E/$N"
