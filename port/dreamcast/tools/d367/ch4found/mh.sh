set -e
L=/root/probe/lanes-20261016/ch4found; W=$L/warps
python3 - <<'P'
import json
L='/root/probe/lanes-20261016/ch4found/'
a=json.load(open(L+'fix/ch4-add.json'))
print('had em11', a['all'].get('em/em11.drs'))
a['all']['em/em11.drs']=L+'snd/aica-c4h/em/em11.drs'
json.dump(a,open(L+'fix/ch4-add-h.json','w'),indent=1,sort_keys=True)
P
cd /mnt/c/tmp/ch4
echo "r226 h1 $(ADD=$L/fix/ch4-add-h.json ARM=cxc4vmW WARPTXT=$W/dec3-r226.txt bash mkfix.sh r226 h1 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|exists.*\|Error.*' | tr '\n' ' ')"
for r in r222 r212; do echo "$r h1 $(ADD=$L/fix/ch4-add-h.json ARM=cxc4vmW WARPTXT=$W/em11-$r.txt bash mkfix.sh $r h1 walk 2>&1 | grep -o 'ch4 keys [0-9]*\|exists.*\|Error.*' | tr '\n' ' ')"; done
python3 -c "
import json;d=json.load(open('$L/fixtures/r226/cx-r226-h1.armed.json'));print(d['replace']['em/em11.drs'])"
