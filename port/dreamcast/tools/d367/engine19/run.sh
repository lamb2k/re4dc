#!/bin/bash
# run.sh <name> <arm label> <fixture json (WSL path)> [seconds] (Git Bash): one engine19 Flycast run (<= 60 s).
# Evidence C:\Flycast-Evidence\re4-dreamcast\engine19-20261019\<name>; disc deleted after the run (disc.sha256 kept).
# Trace runs: set RE4DC_LOG_STOP_TICK; the emulator run itself goes through trace_lock.sh (TRACE=1).
set -uo pipefail
N=${1:?}; L=${2:?}; FIX=${3:?}; SECS=${4:-60}
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
E=/c/Flycast-Evidence/re4-dreamcast/engine19-20261019
SP=$E/_tools
ST=/root/probe/lanes-20261019/engine19/k/stage
mkdir -p "$SP"
cd "$H" || exit 1
S=scenarios/route-e19-$N
[ ! -e "$S" ] || { echo "$S exists"; exit 1; }
[ ! -e "$E/$N" ] || { echo "$E/$N exists"; exit 1; }
cat > "$SP/stage-$N.sh" <<EOS
set -euo pipefail
cd "$HW" && mkdir -p $ST && python3 /root/work/lanes/engine19/port/dreamcast/tools/d367/stage_ext4/stage_scenario.py route-e19-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $ST/run-$N.json 2>&1; python3 -c "import json;d=json.load(open('scenarios/route-e19-$N/stage.json'));print(d['status'],d['disc_sha256'])" || tail -5 $ST/run-$N.json
EOS
D=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Flycast-Evidence/re4-dreamcast/engine19-20261019/_tools/stage-$N.sh)
rm -f "$SP/stage-$N.sh"
echo "stage $D"
case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "stage failed"; exit 1 ;; esac
echo "${PURPOSE:-engine19 $N: arm $L, $SECS s}" > $S/PURPOSE.txt
C=$S/capture
[ "$SECS" -le 60 ] || { echo "runs are <= 60 s"; exit 1; }
for try in $(seq 1 30); do
  # the emulator run (only) holds a trace_lock.sh slot; Windows python through WSL interop, cwd = the harness dir
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root --cd "$HW" -- env RE4DC_LOG_STOP_TICK=${RE4DC_LOG_STOP_TICK:-} WSLENV=RE4DC_LOG_STOP_TICK \
    bash /root/work/lanes/engine19/port/dreamcast/tools/d367/trace_lock.sh python.exe ${RUNNER:-run-emulator-novsync-i26.py} route-e19-$N --seconds $SECS --period ${PERIOD:-30} > $S-run-stdout.txt 2>&1
  grep -q "Emulator queue occupied" $S-run-stdout.txt || break
  sleep 60
done
python -c "import json;d=json.load(open('$C/run-result.json'));print(d['status'],d.get('errors'))"
echo "$N halt=$(grep -ac HALT $C/run-output.txt) fault=$(grep -ac FAULT $C/run-output.txt) overrun=$(grep -ac 'LOG OVERRUN' $C/run-output.txt)"
echo "$(echo $D | awk '{print $2}')  disc.bin (deleted after run)" > $S/disc.sha256
rm -f $C/disc.bin $S/disc/disc.bin
mv $S $E/$N && mv $S-run-stdout.txt $E/$N/run-stdout.txt && echo "moved to $E/$N"
