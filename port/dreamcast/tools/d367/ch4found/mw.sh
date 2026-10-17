set -e
bash /mnt/c/tmp/ch4/mkh.sh cxc4wmW | tail -1
cd /mnt/c/tmp/ch4
echo "r229 t5 $(ARM=cxc4wmW bash mkfix.sh r229 t5 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
