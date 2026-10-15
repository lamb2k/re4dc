#!/bin/bash
# bench-run.sh <scene> <arm label> <run name> [seconds]  (Git Bash): one benchmark run (lane crowd12, 2026-10-14).
#   scene     r101 (benchmark-r101-warp.txt: r101 burning cross, crowd alerted, god; window room frames 300..1200)
#   label     a W build (DBG_WARP=1 PC_SAMPLER=1, the recipe's pacing), e.g. c12tW from test11/t11-build.sh tW
#   name      single-use; evidence C:\Flycast-Evidence\re4-dreamcast\bench-20261014\<name> (BENCH_EV overrides)
# Fixture = the test 11 package fixture (t11-fix.py, data T11_DATA = the release set) with the scene's warp, so every
# lane's numbers come from the same scene and data. Stages through the harness (stage-scenario.py), runs ONE Flycast
# (run-emulator-novsync-i26.py), deletes the staged disc (disc.sha256 kept) and prints the bench-ms.py row.
# BENCH_DATA_EXTRA (lane objs): extra t11-fix.py data sets appended to T11_DATA, e.g. ",objs-r101" (test arm).
# Refuses to stage when C: has less than BENCH_MIN_GB (default 19) GB free.
# Repeatability: run the same arm twice (names x-a, x-b) and pass both to bench-ms.py: fps / CPU within a few %.
set -u
SC=$1; L=$2; N=$3; SECS=${4:-220}
HERE=$(cd "$(dirname "$0")" && pwd)
KW=$(cygpath -m "$HERE" | sed 's#^//wsl.localhost/Ubuntu-24.04##')   # the kit as a WSL path
case "$KW" in /root/*) ;; *) echo "run bench-run.sh from the WSL tree (\\\\wsl.localhost\\Ubuntu-24.04\\root\\...)"; exit 1 ;; esac
T11=$(dirname "$KW")/test11
W="$KW/benchmark-$SC-warp.txt"
BW=$(grep -m1 "^# bench-window" "$HERE/benchmark-$SC-warp.txt" | awk '{print "--from "$3" --to "$4}')
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
E=${BENCH_EV:-/c/Flycast-Evidence/re4-dreamcast/bench-20261014}
EW=$(echo "$E" | sed 's#^/c/#/mnt/c/#')
ST=/root/probe/bench-stage; FIXD=/root/probe/bench-stage/fix
mkdir -p "$E/_tools"
# coordinator hold: no new staging while BENCH_HOLD_FILE (default the crowd12 tmp HOLD) holds a future epoch
HF=${BENCH_HOLD_FILE:-/c/Users/lambd/.claude/jobs/1e668c67/tmp/crowd12/HOLD}
while [ -f "$HF" ] && [ "$(date +%s)" -lt "$(cat "$HF")" ]; do sleep 30; done
free=$(powershell -NoProfile -Command "[int]((Get-PSDrive C).Free/1GB)" | tr -d '\r')
[ "$free" -ge "${BENCH_MIN_GB:-19}" ] || { echo "C: has $free GB free (< ${BENCH_MIN_GB:-19}): not staging"; exit 1; }
cd "$H" || exit 1
S=scenarios/route-bench-$N
[ ! -e "$S" ] || { echo "$S exists (names are single-use)"; exit 1; }
[ ! -e "$E/$N" ] || { echo "$E/$N exists"; exit 1; }
cat > "$E/_tools/stage-$N.sh" <<EOS
set -e; mkdir -p $ST $FIXD
D=\$(python3 -c "import re;print(re.search(r\"^T11_DATA = '([^']*)'\", open('$T11/t11-fix.py').read(), re.M).group(1))")
[ -z "${BENCH_DATA:-}" ] || D='${BENCH_DATA:-}'   # BENCH_DATA: the whole data set (e.g. T121_DATA's list), not T11_DATA
python3 $T11/t11-fix.py $L $FIXD/$N.json --data \$D${BENCH_DATA_EXTRA:-} --warp $W > $ST/fix-$N.txt
python3 $KW/fix-replace.py $FIXD/$N.json $W >> $ST/fix-$N.txt
cd "$HW" && python3 stage-scenario.py route-bench-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIXD/$N.json > $ST/run-$N.json 2>&1 || true
python3 -c "import json;d=json.load(open('$ST/run-$N.json'));print(d['status'],d['disc_sha256'])" || tail -5 $ST/run-$N.json
EOS
D=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash "$EW/_tools/stage-$N.sh")
rm -f "$E/_tools/stage-$N.sh"
echo "stage $D"
case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "stage failed"; exit 1 ;; esac
echo "benchmark-$SC: arm $L, scene $W, $SECS s, window ${BW:-room frames 300..1200} (MODELLED, Flycast runner)" > $S/PURPOSE.txt
C=$S/capture
for try in $(seq 1 30); do   # the runner refuses at its Flycast ceiling: wait and retry
  python ${RUNNER:-run-emulator-novsync-i26.py} route-bench-$N --seconds $SECS --period ${PERIOD:-30} > $S-run-stdout.txt 2>&1
  grep -q "Emulator queue occupied" $S-run-stdout.txt || break
  sleep 60
done
python -c "import json;d=json.load(open('$C/run-result.json'));print(d['status'],d.get('errors'))"
echo "$(echo $D | awk '{print $2}')  disc.bin (deleted after run)" > $S/disc.sha256
rm -f $C/disc.bin $S/disc/disc.bin
cp "//wsl.localhost/Ubuntu-24.04$FIXD/$N.json" $S/fixture.json 2>/dev/null
mv $S "$E/$N" && mv $S-run-stdout.txt "$E/$N/run-stdout.txt"
echo "$N halt=$(grep -ac HALT $E/$N/capture/run-output.txt) fault=$(grep -ac FAULT $E/$N/capture/run-output.txt) last=$(grep -a '^warp: frame' $E/$N/capture/run-output.txt | tail -1 | cut -c1-40)"
python "$HERE/bench-ms.py" "$E/$N/capture/run-output.txt" $BW
# VRAM gaps gate (CLAUDE.md graphics memory rule; vram/vram_gate.py): the per-room VRAM table and FAIL on refusals,
# thrash-guard skips under pressure, "no contiguous block" and GameCube effect pictures not listed as ps2lib NONE rows.
python "$HERE/../vram/vram_gate.py" "$E/$N/capture/run-output.txt" || echo "VRAM gate: FAIL ($N)"
