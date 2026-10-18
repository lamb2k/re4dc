#!/bin/bash
# cr-run.sh <name> <label> <fixture> [seconds] (Git Bash; lane ch2regen): stage through the harness stager, run Flycast,
# summarise gates, delete the disc. Adapted copy of the ch2code16 t-run.sh. Evidence C:\Flycast-Evidence\re4-dreamcast\ch2regen-20261018\<name>.
set -uo pipefail
N=${1:?name}; L=${2:?label}; FIX=${3:?fixture}; SECS=${4:-60}
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
E=/c/Flycast-Evidence/re4-dreamcast/ch2regen-20261018
SP=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen/stage
ST=/root/probe/lanes-20261017r/ch2regen/stage
mkdir -p "$SP" "$E"
cd "$H" || exit 1
S=scenarios/route-cr-$N
[ ! -e "$S" ] || { echo "$S exists"; exit 1; }
[ ! -e "$E/$N" ] || { echo "$E/$N exists"; exit 1; }
cat > "$SP/stage-$N.sh" <<EOS
set -uo pipefail
cd "$HW" && mkdir -p $ST && python3 stage-scenario.py route-cr-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $ST/run-$N.json 2>&1; python3 -c "import json;d=json.load(open('$ST/run-$N.json'));print(d['status'],d['disc_sha256'])" || tail -5 $ST/run-$N.json
EOS
D=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash "/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen/stage/stage-$N.sh")
echo "stage $D"
case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "stage failed"; exit 1 ;; esac
echo "ch2regen $N: arm $L, fixture $FIX, $SECS s" > $S/PURPOSE.txt
C=$S/capture
for try in $(seq 1 30); do
  python run-emulator-novsync-i26.py route-cr-$N --seconds $SECS --period 30 > $S-run-stdout.txt 2>&1
  grep -q "Emulator queue occupied" $S-run-stdout.txt || break
  sleep 60
done
echo "$N halt=$(grep -ac HALT $C/run-output.txt) missing=$(grep -ac 'RE4DC MISSING' $C/run-output.txt) fault=$(grep -ac FAULT $C/run-output.txt) leongc=$(grep -ac '^LEONGC f=' $C/run-output.txt) texfail=$(grep -ac 'texchk: FAIL' $C/run-output.txt) rooms=$(grep -aoE 'room enter [0-9a-f]+' $C/run-output.txt | awk '{print $3}' | tr '\n' ',')"
echo "$(echo $D | awk '{print $2}')  disc.bin (deleted after run)" > $S/disc.sha256
rm -f $C/disc.bin $S/disc/disc.bin
mv $S $E/$N && mv $S-run-stdout.txt $E/$N/run-stdout.txt && echo "moved to $E/$N"
