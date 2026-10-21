set -euo pipefail
# scn-fix.sh <arm label...> (WSL; lane lake20): harness fixtures for the scenario check arms (lksc<k><f>rW): warp.txt =
# scene 1, plus dc/bench2..5.txt and dc/quality.txt (speed=screen) through fix-replace's "# bench-replace" lines.
D=/root/work/lanes/lake20/port/dreamcast/tools/d367
S=$D/lake20/scenario
W=/root/work/lanes/lake20-scratch/scnfix; mkdir -p $W
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export RE4DC_PROGRAMS_DIR=$HW/programs RC19D=/root/re4data/private/rc19s-20261019
eval "$(grep '^DATA=' $D/rr/recipe.conf)"
printf 'speed=screen\n' > $W/quality.txt
{ cat $S/scene1-warp.txt; for k in 2 3 4 5; do grep -v '^#' $S/scene$k-warp.txt > $W/bench$k.txt; echo "# bench-replace dc/bench$k.txt=$W/bench$k.txt"; done
  echo "# bench-replace dc/quality.txt=$W/quality.txt"; } > $W/warp.txt
for L in "$@"; do
  RAW=$W/$L.raw.json
  python3 $D/test11/t11-fix.py $L $RAW --base payload --data "$DATA" --warp $W/warp.txt > $W/$L.log 2>&1 || { tail -3 $W/$L.log; exit 1; }
  python3 $D/benchmark/fix-replace.py $RAW $W/warp.txt >> $W/$L.log 2>&1
  python3 $D/texchk/fixture_arm.py $RAW $W/$L.json $L --programs-dir "$RE4DC_PROGRAMS_DIR" >> $W/$L.log 2>&1
  echo "fix $W/$L.json"
done
