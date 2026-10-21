set -euo pipefail
# gates.sh (WSL; lane lake20): fixtures for the lake gates. Arms <label><arm> from b.sh.
#   STRICT pair (rT): gL = r10b lake to Del Lago's kill and the chapter end (fullplay lake), gB = the boat loop (fullplay
#   boat), gN = the r11b night shore walk (fullplay r11b). KOS (rW + KOS_SQUEEZE): the same three with "squeeze 49152 0".
#   Stills (rW): stillA/B/C. Usage: gates.sh <arm label (e.g. lkgkrT)> <scene...>; fixture JSONs in $W/<arm>-<scene>.json
D=/root/work/lanes/lake20/port/dreamcast/tools/d367
W=/root/work/lanes/lake20-scratch/gates; mkdir -p $W
SEG=$D/fullplay/segments
L=${1:?arm label}; shift
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export RE4DC_PROGRAMS_DIR=$HW/programs RC19D=/root/re4data/private/rc19s-20261019
eval "$(grep '^DATA=' $D/rr/recipe.conf)"
for g in "$@"; do
  P=
  case $g in
    gL|qL) cp $SEG/lake-warp.txt $W/$g.txt; P=$SEG/lake-pad.txt ;;
    gB|qB) cp $SEG/boat-warp.txt $W/$g.txt; P=$SEG/boat-pad.txt ;;
    gN|qN) cp $SEG/r11b-warp.txt $W/$g.txt ;;
    still*) cp $D/lake20/$g-warp.txt $W/$g.txt ;;
    hwD) cp $D/lake20/hwdellago-warp.txt $W/$g.txt; P=$D/lake20/hwdellago-pad.txt ;;
    *) echo "unknown scene $g"; exit 1 ;;
  esac
  case $g in q*) sed -i '1a squeeze 49152 0' $W/$g.txt ;; esac
  RAW=$W/$L-$g.raw.json
  python3 $D/test11/t11-fix.py $L $RAW --base payload --data "$DATA" --warp $W/$g.txt ${P:+--pad $P} > $W/$L-$g.log 2>&1 || { tail -3 $W/$L-$g.log; exit 1; }
  python3 $D/texchk/fixture_arm.py $RAW $W/$L-$g.json $L --programs-dir "$RE4DC_PROGRAMS_DIR" >> $W/$L-$g.log 2>&1
  echo "fix $L-$g $W/$L-$g.json"
done
