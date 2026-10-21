set -euo pipefail
# mkfix.sh <program label> <out json> <warp.txt> (WSL; lane cache20, after logiclod20/gates.sh): a stage_scenario fixture
# for one Flycast run: the release data set (rr/recipe.conf DATA via test11/t11-fix.py --warp) bound to that program's
# overlays (texchk/fixture_arm.py).
L=${1:?label}; OUT=${2:?out}; W=${3:?warp}
T=/root/work/lanes/cache20-scratch/tree/port/dreamcast/tools/d367
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export RE4DC_PROGRAMS_DIR=$HW/programs RC19D=/root/re4data/private/rc19s-20261019
eval "$(grep '^DATA=' $T/rr/recipe.conf)"
python3 $T/test11/t11-fix.py $L $OUT.raw --base payload --data "$DATA" --warp $W > $OUT.log 2>&1 || { tail -3 $OUT.log; exit 1; }
python3 $T/texchk/fixture_arm.py $OUT.raw $OUT $L --programs-dir "$RE4DC_PROGRAMS_DIR" >> $OUT.log 2>&1
rm -f $OUT.raw
echo "fixture $OUT"
