set -e
L=/root/probe/lanes-20261016/ch4found; W=$L/warps
cd /root/probe/lanes-20261016/ch4found/tree/port/dreamcast/tools/d367/vram && RE4DC_RESIDENT_STRICT=1 python3 resident_keys.py check $L/../ch3found/vram/resident-ch3.bin resident/*.tsv
cd /mnt/c/tmp/ch4
for t in w1 w0; do
  AD=$L/fix/ch4-add.json; [ $t = w0 ] && AD=$L/fix/ch4-add-v0.json
  for r in r101 r104 r119; do echo "$t $r $(ADD=$AD ARM=cxc4qmW WARPSRC=/root/probe/codex-cx-fixtures-20261013/output/r102/cx-r102-walk.armed.json WARPTXT=$W/vq-$r.txt bash mkfix.sh $r $t walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"; done
  for r in r102 r10f r112; do echo "$t $r $(ADD=$AD ARM=cxc4qmW bash mkfix.sh $r $t walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"; done
done
echo "r229 t4 $(ARM=cxc4umW bash mkfix.sh r229 t4 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
