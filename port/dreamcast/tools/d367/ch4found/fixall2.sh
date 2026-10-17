sed -i 's/\r$//' /mnt/c/tmp/ch4/mkfix.sh
ARMX=$1; TAG=$2; shift 2
for r in "$@"; do echo "$r $(ARM=$ARMX bash /mnt/c/tmp/ch4/mkfix.sh $r $TAG walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"; done
