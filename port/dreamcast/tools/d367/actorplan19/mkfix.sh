set -euo pipefail
K=/root/work/lanes/actorplan19/k
SEG=/root/work/lanes/actorplan19/tree/port/dreamcast/tools/d367/fullplay/segments
for a in k p; do
  bash $K/fix.sh a9${a}rT h2-$a $SEG/h2-warp.txt $SEG/h2-pad.txt
  bash $K/fix.sh a9${a}rT bell-$a $SEG/bell-warp.txt
  bash $K/fix.sh a9${a}rT door-$a $SEG/door103-warp.txt
  bash $K/fix.sh a9${a}hrW st101-$a $K/still-r101-warp.txt
  bash $K/fix.sh a9${a}hrW st103-$a $K/still-r103-warp.txt
  bash $K/fix.sh a9${a}hrW stleon-$a $K/still-leon-warp.txt
  bash $K/fix.sh a9${a}mW m101-$a $K/hwcross-warp.txt
  bash $K/fix.sh a9${a}mW m103-$a $K/hw103-warp.txt
done
echo FIX DONE
