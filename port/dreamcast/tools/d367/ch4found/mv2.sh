set -e
bash /mnt/c/tmp/ch4/mkh.sh cxc4vmW | tail -1
cd /mnt/c/tmp/ch4
echo "r226 e5 $(ARM=cxc4vmW WARPTXT=/root/probe/lanes-20261016/ch4found/warps/dec3-r226.txt bash mkfix.sh r226 e5 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
