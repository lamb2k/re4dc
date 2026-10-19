set -euo pipefail
# scenery19 gate fixtures: STRICT bell / door103 (rT arms), TEXCHK / CAST-GC r101 cross + r103 (mW arms), k and p.
D=/root/work/lanes/scenery19/port/dreamcast/tools/d367/scenery19/k
SEG=/root/work/lanes/scenery19/port/dreamcast/tools/d367/fullplay/segments
for a in k p; do
  bash $D/fix.sh s9${a}rT bell-$a $SEG/bell-warp.txt
  bash $D/fix.sh s9${a}rT door-$a $SEG/door103-warp.txt
  bash $D/fix.sh s9${a}mW m101-$a $D/hwcross-warp.txt
  bash $D/fix.sh s9${a}mW m103-$a $D/hw103-warp.txt
done
echo FIX DONE
