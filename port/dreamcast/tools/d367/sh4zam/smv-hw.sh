#!/bin/bash
# smv-hw.sh <trace arm label> <name> <fixture> <count A:B> <trace A:B:S> [seconds]   (WSL; tools/d367/sh4zam)
# lane skin-movca copy of poc101/poc-hw.sh: own work dir (K) and evidence root (ROOT, C:), trace lock owner skinmovca-<name>.
# MODELLED numbers of one POC row on the POC image itself (coordinator 10-15: the combined ALL ON vs ALL OFF number,
# ~120 frames inside room frames 500-799, the same window for both rows, at most 2 trace slots). The hwcal method
# (HWMODEL-CALIBRATION-20261015 section 2): hwtrace the disc, hwsim-ph splits cycles by the bench's own parts.
#   - the trace arm = the console image's knobs + BENCH_AUTO_S=1 (start screen 1 s; one constant, same layout: checked
#     by poc-hw-layout below against the console arm when CONSOLE_ARM is set)
#   - a GDI per row (bench-package.sh FIXDIR: warp.txt = the row's fixture), mastered on ext4, crossed to C: once
#   - frame address = bench.cpp g_room_frame (the room frame the bench measures), physical
# Output: $ROOT/hw-<name>/proj/{nominal,low,high}.phases.tsv; an.py summary in $ROOT/hw-<name>/an.txt
set -u
L=$1; N=$2; FX=$3; COUNT=$4; TRACE=$5; SECS=${6:-240}
here=$(cd "$(dirname "$0")" && pwd)
K=${K:-/root/probe/lanes-20261015/sh4zam/movwork}
ROOT=${ROOT:-/mnt/c/Flycast-Evidence/re4-dreamcast/skinmovca-20261015/hw}
CAL=/mnt/d/Flycast-Evidence/re4-dreamcast/hwcal-20261015/tools
W=/root/probe/hwcal-20261015
O=/root/probe/lanes/route/out-$L
E=$ROOT/hw-$N
TL=$here/../trace_lock.sh
PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
TOOL=/opt/toolchains/dc/sh-elf/bin
[ ! -e "$E/trace/hwtrace.log" ] || { echo "$E has a trace already"; exit 1; }
mkdir -p $E $K/hwfix-$N
cp "$FX" $K/hwfix-$N/warp.txt
export PKG_JSON=${PKG_JSON:-/root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json} K
FIXDIR=$K/hwfix-$N FIXTAG=hw-$N bash $here/../benchpub/bench-package.sh $L > $K/hwpkg-$N.log 2>&1 || { tail $K/hwpkg-$N.log; exit 1; }
D=$K/disc-$L-hw-$N
mkdir -p $E/disc && cp $D/gdemu/{disc.gdi,track01.bin,track02.raw,track03.bin} $E/disc/ && rm -rf $D
cp -r /mnt/d/Flycast-Evidence/re4-dreamcast/hwmodel-bin/. $E/
cp $O/syms.txt $O/re4dc-game.elf $O/elf.sha256 $O/candidate.txt $E/
cp $CAL/hwrun.ps1 $E/
FA=$($TOOL/sh-elf-nm $O/re4dc-game.elf | awk '/g_room_frame/ {print $1; exit}')
FA=$(printf '%08x' $(( 0x$FA & 0x1fffffff )))
echo "poc101 hw model: $N, arm $L, fixture $FX, count $COUNT trace $TRACE, frame address $FA" > $E/PURPOSE.txt
echo "[$(date -Is)] trace $N fa=$FA count=$COUNT trace=$TRACE"
TRACE_LOCK_OWNER="skinmovca-$N" bash $TL "$PS" -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$E/hwrun.ps1")" \
  -Dir "$(wslpath -w "$E")" -Disc "$(wslpath -w "$E/disc/disc.gdi")" -FrameAddr "$FA" -Count "$COUNT" -Trace "$TRACE" \
  -Exit 1 -Seconds "$SECS" </dev/null | tr -d '\r'
echo "[$(date -Is)] trace done: $(ls $E/trace/trace-*.bin 2>/dev/null | wc -l) traces, $(cat $E/trace/elapsed.txt 2>/dev/null | tr -d '\r')"
rm -f $E/disc/track03.bin $E/disc/track01.bin $E/disc/track02.raw
$TOOL/sh-elf-objdump -d $O/re4dc-game.elf > $K/hw-$N.dis
python3 $CAL/phase_sites.py $K/hw-$N.dis $E/phase-sites.txt > /dev/null
rm -f $K/hw-$N.dis
P=$E/proj; mkdir -p $P
TR=$(ls $E/trace/trace-*.bin)
cd $P
$W/hwsim-ph --elf $E/re4dc-game.elf --out nominal --phase $E/phase-sites.txt $TR > nominal.log 2>&1
python3 $CAL/an.py $P --k ${KSKIP:-1.0} > $E/an.txt 2>&1
cat $E/an.txt
rm -f $E/trace/trace-*.bin
echo "[$(date -Is)] sim done (traces dropped after the simulation)"
