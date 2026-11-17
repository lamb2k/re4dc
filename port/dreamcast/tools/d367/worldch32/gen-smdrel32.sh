set -u
# lane world-ch32: smdrel32 store = convert_room_bins summaries of the GC r205 r209 r20a r20b (arcuse26 smdrel26b method)
T=/root/work/lanes/world-ch32/port/dreamcast/tools
SRCD=/root/re4data/private/cxfix-replay-20261018/output
ST=/root/re4data/private/smdrel32-20261117
W=/root/work/lanes/world-ch32-scratch/smdgen
mkdir -p $ST $W
for r in r205 r209 r20a r20b; do
 (
  S=$(ls $SRCD/$r/ancillary-*/source/st2/$r.das | head -1)
  mkdir -p $W/$r $ST/$r
  python3 $T/convert_room_bins.py $W/$r/MAINSCENARIO.re4mesh --owner 0xff --smd $S --lod --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > $W/$r/pkg.log 2>&1
  echo "$r rc=$?" >> $W/done.txt
  cp $W/$r/MAINSCENARIO.re4mesh.json $ST/$r/ 2>/dev/null
  sha256sum $S >> $ST/SOURCES.txt
 ) &
done
wait
echo ALLDONE >> $W/done.txt
