#!/bin/bash
# arun.sh <name> <label> <warp.txt (WSL path)> <seconds> [pad (WSL path)]  (Git Bash; lane sh4zam-direct 2026-10-15)
# One Flycast run of route arm <label> on the test 13 data (t11-fix.py T13_DATA) with the given warp fixture.
# Staged through the harness (stage-scenario.py, ext4 disc cache), run with run-emulator-novsync-i26.py, evidence in
# D:\Flycast-Evidence\re4-dreamcast\sh4zam-20261015\<name>; the staged disc is deleted after (disc.sha256 kept).
# Env: STOP (RE4DC_LOG_STOP_TICK), PURPOSE, PERIOD (shot period, default 30), TRACE=1 (run under trace_lock.sh, WSL).
set -u
N=$1; L=$2; W=$3; SECS=$4; PAD=${5:-}
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
E=/d/Flycast-Evidence/re4-dreamcast/sh4zam-20261015
SP=$E/_tools
ST=/root/probe/lanes-20261015/sh4zam/stage
T11=/root/probe/lanes-20261015/sh4zam/tree/port/dreamcast/tools/d367/test11
cd "$H" || exit 1
S=scenarios/route-sz-$N
[ ! -e "$S" ] || { echo "$S exists (names are single-use)"; exit 1; }
[ ! -e "$E/$N" ] || { echo "$E/$N exists"; exit 1; }
PADOPT=""; [ -n "$PAD" ] && PADOPT="--pad '$PAD'"
cat > $SP/stage-$N.sh <<EOS
set -e; mkdir -p $ST/fix
D=r119c,em29,fbec,r100tr4,smx101,sg101,t12tex,objs12b,merchant,items12,acc12d,blackps2w,t121tex,objs13d,ashley13,bake13,t13tex
python3 $T11/t11-fix.py $L $ST/fix/$N.json --data \$D --warp $W $PADOPT > $ST/fix-$N.txt
cd "$HW" && python3 stage-scenario.py route-sz-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $ST/fix/$N.json > $ST/run-$N.json 2>&1 || true
python3 -c "import json;d=json.load(open('$ST/run-$N.json'));print(d['status'],d['disc_sha256'])" || tail -5 $ST/run-$N.json
EOS
D=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /mnt/d/Flycast-Evidence/re4-dreamcast/sh4zam-20261015/_tools/stage-$N.sh)
rm -f $SP/stage-$N.sh
echo "stage $D"
case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "stage failed"; exit 1 ;; esac
echo "${PURPOSE:-sh4zam $N: arm $L, warp $W, $SECS s} stop_tick=${STOP:-none}" > $S/PURPOSE.txt
C=$S/capture
cat > $SP/runpart-$N.sh <<EOS
cd "$H" || exit 1
${STOP:+export RE4DC_LOG_STOP_TICK=$STOP}
for try in \$(seq 1 30); do
  python ${RUNNER:-run-emulator-novsync-i26.py} route-sz-$N --seconds $SECS --period ${PERIOD:-30} > $S-run-stdout.txt 2>&1
  grep -q "Emulator queue occupied" $S-run-stdout.txt || break
  sleep 60
done
EOS
if [ -n "${TRACE:-}" ]; then
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- env TRACE_LOCK_OWNER=claude-sz-$N bash /root/probe/lanes-20261015/sh4zam/tree/port/dreamcast/tools/d367/trace_lock.sh "/mnt/c/Program Files/Git/bin/bash.exe" /d/Flycast-Evidence/re4-dreamcast/sh4zam-20261015/_tools/runpart-$N.sh
else
  bash $SP/runpart-$N.sh
fi
rm -f $SP/runpart-$N.sh
python -c "import json;d=json.load(open('$C/run-result.json'));print(d['status'],d.get('errors'))"
echo "$N halt=$(grep -ac HALT $C/run-output.txt) missing=$(grep -ac 'RE4DC MISSING' $C/run-output.txt) fault=$(grep -ac FAULT $C/run-output.txt) misalign=$(grep -ac MISALIGN $C/run-output.txt) overrun=$(grep -ac 'LOG OVERRUN' $C/run-output.txt) frozen=$(grep -ac 'warp: frozen' $C/run-output.txt) last=$(grep -a '^LT t=' $C/run-output.txt | tail -1 | cut -c1-12)"
echo "$(echo $D | awk '{print $2}')  disc.bin (deleted after run)" > $S/disc.sha256
rm -f $C/disc.bin $S/disc/disc.bin
cp "//wsl.localhost/Ubuntu-24.04$ST/fix/$N.json" $S/fixture.json 2>/dev/null
mkdir -p $E; mv $S $E/$N && mv $S-run-stdout.txt $E/$N/run-stdout.txt && echo "moved to $E/$N"
