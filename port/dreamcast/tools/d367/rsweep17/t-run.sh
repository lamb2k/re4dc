#!/bin/bash
# t-run.sh <name> <label> <fixture> [seconds]  (Git Bash): lane rsweep17 runs (copy of s30movie t-run.sh).
# Evidence C:\Flycast-Evidence\re4-dreamcast\rsweep17-20261017\<name>; the disc is deleted after the run (disc.sha256 kept).
# RUNNER (default run-emulator-novsync-i26.py, the 9.1/10 release gate runner), PERIOD, PURPOSE, RE4DC_LOG_STOP_TICK pass through.
set -u
N=$1; L=$2; FIX=$3; SECS=${4:-100}
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
E=/c/Flycast-Evidence/re4-dreamcast/rsweep17-20261017
SP=$E/_tools
ST=/root/probe/d367-agents/rsweep17/stage
mkdir -p $SP
cd "$H" || exit 1
S=scenarios/route-rs-$N
[ ! -e "$S" ] || { echo "$S exists (names are single-use)"; exit 1; }
[ ! -e "$E/$N" ] || { echo "$E/$N exists"; exit 1; }
cat > $SP/stage-$N.sh <<EOS
cd "$HW" && mkdir -p $ST && python3 stage-scenario.py route-rs-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $ST/run-$N.json 2>&1; python3 -c "import json;d=json.load(open('$ST/run-$N.json'));print(d['status'],d['disc_sha256'])" || tail -5 $ST/run-$N.json
EOS
D=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Flycast-Evidence/re4-dreamcast/rsweep17-20261017/_tools/stage-$N.sh)
rm -f $SP/stage-$N.sh
echo "stage $D"
case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "stage failed"; exit 1 ;; esac
echo "${PURPOSE:-ch2 $N: arm $L, fixture $FIX, $SECS s} stop_tick=${RE4DC_LOG_STOP_TICK:-none}" > $S/PURPOSE.txt
C=$S/capture
for try in $(seq 1 30); do   # the runner refuses at its Flycast ceiling (RE4DC_MAX_FLYCASTS): wait and retry
  if [ "${TRACE:-0}" = 1 ]; then   # one host trace slot (trace_lock.sh) around the run
    MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Flycast-Evidence/re4-dreamcast/rsweep17-20261017/_tools/trace-run.sh       route-rs-$N $SECS ${RE4DC_LOG_STOP_TICK:-999999}
  else
  python ${RUNNER:-run-emulator-novsync-i26.py} route-rs-$N --seconds $SECS --period ${PERIOD:-30} > $S-run-stdout.txt 2>&1
  fi
  grep -q "Emulator queue occupied" $S-run-stdout.txt || break
  sleep 60
done
python -c "import json;d=json.load(open('$C/run-result.json'));print(d['status'],d.get('errors'))"
grep -a -E 'warp:|room |route movie|HALT|RE4DC MISSING|FAULT|LHPACK|LEONGC|texchk|LOG OVERRUN|alivecap|PS2_ENEMY|heap4|does not fit|DVD: |failed|card-vmu|chap0|DOORDEMO|PS2MESH room|NMRS|aica:|stream sbb|MOVIEARENA|motion bind|overlay' $C/run-output.txt > $S/route.txt
echo "$N halt=$(grep -ac HALT $C/run-output.txt) missing=$(grep -ac 'RE4DC MISSING' $C/run-output.txt) fault=$(grep -ac FAULT $C/run-output.txt) leongc=$(grep -ac '^LEONGC f=' $C/run-output.txt) overrun=$(grep -ac 'LOG OVERRUN' $C/run-output.txt) texfail=$(grep -ac 'texchk: FAIL' $C/run-output.txt) nofit=$(grep -ac 'does not fit' $C/run-output.txt) rooms=$(grep -aoE 'room enter [0-9a-f]+' $C/run-output.txt | awk '{print $3}' | tr '
' ',')"
echo "$(echo $D | awk '{print $2}')  disc.bin (deleted after run)" > $S/disc.sha256
rm -f $C/disc.bin $S/disc/disc.bin
mkdir -p $E; mv $S $E/$N && mv $S-run-stdout.txt $E/$N/run-stdout.txt && echo "moved to $E/$N"
