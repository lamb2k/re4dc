set -euo pipefail
W=/root/probe/lanes-20261018/ch5tex; C=/root/probe/lanes-20261018/ch5regen
mkdir -p $W/gate/fix $W/gate/logs $W/stage
for r in r307 r310 r31b r31c; do
python3 - $C/gate/fix/$r.json $W/gate/fix/$r.json $W/paks/tex-ch5e.pak <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); old=d['replace'].get('dc/tex.pak')
d['replace']['dc/tex.pak']=sys.argv[3]
d['provenance']['ch5tex']='dc/tex.pak = rebuilt tex-ch5e d5986c3e (was %s)'%old
json.dump(d,open(sys.argv[2],'w'),indent=1,sort_keys=True); print(sys.argv[2],'was',old)
PY
done
