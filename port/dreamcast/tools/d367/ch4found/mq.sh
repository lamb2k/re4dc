set -e
bash /mnt/c/tmp/ch4/mkh.sh cxc4qmW | tail -1
cd /mnt/c/tmp/ch4
echo "r229 t2 $(ARM=cxc4qmW bash mkfix.sh r229 t2 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
