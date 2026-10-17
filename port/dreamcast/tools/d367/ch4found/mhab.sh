set -e
L=/root/probe/lanes-20261016/ch4found; W=$L/warps
for t in a b; do python3 - $t <<'P'
import json,sys
t=sys.argv[1]; L='/root/probe/lanes-20261016/ch4found/'
a=json.load(open(L+'fix/ch4-add.json')); a['all']['em/em11.drs']=L+'snd/aica-c4%s/em/em11.drs'%t
json.dump(a,open(L+'fix/ch4-add-h%s.json'%t,'w'),indent=1,sort_keys=True)
P
cd /mnt/c/tmp/ch4; echo "r226 h$t $(ADD=$L/fix/ch4-add-h$t.json ARM=cxc4vmW WARPTXT=$W/dec3-r226.txt bash mkfix.sh r226 h$t walk 2>&1 | grep -o 'ch4 keys [0-9]*\|exists.*\|Error.*' | tr '\n' ' ')"; done
