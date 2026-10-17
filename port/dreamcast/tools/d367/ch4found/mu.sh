set -e
bash /mnt/c/tmp/ch4/mkh.sh cxc4umW | tail -1
cd /mnt/c/tmp/ch4
echo "r229 t3 $(ARM=cxc4umW bash mkfix.sh r229 t3 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
