set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; T=$L/t-int/port/dreamcast/tools/d367; mkdir -p $L/fix
for r in r113 r11c r11d r11e r11f r10f r111 r112 r200; do
  python3 $T/test11/t11-fix.py crmW $L/fix/e-$r-crmW.json --data ch2,cast16 --warp $T/ch2/warps/e-$r.txt 2>&1 | tail -1 | cut -c1-200
done
