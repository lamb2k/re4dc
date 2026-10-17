set -e
W=/root/probe/lanes-20261016/ch4found/warps
bash /mnt/c/tmp/ch4/mkh.sh cxc4smW | tail -1
bash /mnt/c/tmp/ch4/mkh.sh cxc4tmW | tail -1
cd /mnt/c/tmp/ch4
echo "r226 e2 $(ARM=cxc4smW WARPTXT=$W/dec3-r226.txt bash mkfix.sh r226 e2 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
echo "r226 e3 $(ARM=cxc4tmW WARPTXT=$W/dec3-r226.txt bash mkfix.sh r226 e3 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
