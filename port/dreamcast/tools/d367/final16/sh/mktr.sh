# mktr.sh <variant> <prep dir> <snd dir> <world 1|0> [warp]: STRICT trace fixture fx-r332-<variant> on arm f3rT (lane final16)
L=/root/probe/lanes-20261016/final16
V=$1 W2=${5:-m3} ARM=${ARM:-f3rT} PREP=$2 bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/fx4.sh" 2>&1 | tail -1
F=$L/fixtures/r332/fx-r332-$1.armed.json
python3 "/mnt/c/Game Dev/Emulators/final16-20261016/py/addsnd2.py" $F --snd $3
python3 - $F $4 <<'PY'
import json,sys
f,w=sys.argv[1],sys.argv[2]; j=json.load(open(f)); r=j['replace']
if w=='0':
    for k in [k for k in r if k.startswith('dc/native/r332/ps2-world')]: del r[k]
json.dump(j,open(f,'w'),indent=1,sort_keys=True)
print(f.split('/')[-1],'em31',r['em/em31.drs'],'world',sum(1 for k in r if k.startswith('dc/native/r332/ps2-world')),'em31.ovl',r['dc/em31.ovl'])
PY
