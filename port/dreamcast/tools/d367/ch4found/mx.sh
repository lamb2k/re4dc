set -e
bash /mnt/c/tmp/ch4/mkh.sh cxc4xmW | tail -1
cd /mnt/c/tmp/ch4
echo "r229 t6 $(ARM=cxc4xmW bash mkfix.sh r229 t6 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
