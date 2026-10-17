set -e
L=/root/probe/lanes-20261016/ch4found; W=$L/warps
bash /mnt/c/tmp/ch4/mkh.sh cxc4lmW | tail -1
bash /mnt/c/tmp/ch4/mkh.sh cxc4mmW | tail -1
python3 - <<'P'
import json
L='/root/probe/lanes-20261016/ch4found/'
a=json.load(open(L+'fix/ch4-add-s.json'))
a['all']['bgm/aica_str.dat']=L+'snd/str-castle/bgm/aica_str.dat'
json.dump(a,open(L+'fix/ch4-add-c.json','w'),indent=1,sort_keys=True)
P
ls -d /root/probe/codex-cx-fixtures-20261013/output/r208 /root/probe/codex-cx-fixtures-20261013/output/r209 2>&1 | head -2
cd /mnt/c/tmp/ch4
echo "r226 e1 $(ARM=cxc4lmW WARPTXT=$W/dec3-r226.txt bash mkfix.sh r226 e1 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
for r in r218 r222 r208; do echo "$r c1 $(ADD=$L/fix/ch4-add-c.json ARM=cxc4lmW bash mkfix.sh $r c1 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"; done
echo "r229 t1 $(ARM=cxc4mmW bash mkfix.sh r229 t1 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|PACK_AUDIT.*\|exists.*\|Error.*' | tr '\n' ' ')"
