set -euo pipefail
# fx.sh <arm label> <rig name...>: fixtures for rigs in scratch/rigs
D=/root/work/lanes/shotfx20/port/dreamcast/tools/d367
W=/root/work/lanes/shotfx20-scratch/rigs
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export RE4DC_PROGRAMS_DIR=$HW/programs RC19D=/root/re4data/private/rc19s-20261019
eval "$(grep '^DATA=' $D/rr/recipe.conf)"
L=${1:?}; shift
for g in "$@"; do
  RAW=$W/$L-$g.raw.json
  python3 $D/test11/t11-fix.py $L $RAW --base payload --data "$DATA" --warp $W/$g.txt > $W/$L-$g.log 2>&1 || { tail -3 $W/$L-$g.log; exit 1; }
  python3 $D/texchk/fixture_arm.py $RAW $W/$L-$g.json $L --programs-dir "$RE4DC_PROGRAMS_DIR" >> $W/$L-$g.log 2>&1
  echo "fix $W/$L-$g.json"
done
