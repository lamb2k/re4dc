set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5tex
W=/root/probe/lanes-20261018/ch5tex
G="/mnt/c/Game Dev/Emulators"
python3 - $W/vq1/missing.txt $W/fx-d12/zz-extra.armed.json <<'PY'
import sys,os,json,hashlib,collections
miss=[l.split()[0] for l in open(sys.argv[1])]
found=collections.defaultdict(list)
for root,_,fs in os.walk('/root/probe/lanes-20261018/ch5regen'):
    for f in fs:
        if f.endswith('.re4tex') and f[:-7] in miss: found[f[:-7]].append(os.path.join(root,f))
rep={}
for k in miss:
    ps=sorted(found[k], key=lambda p:(0 if '/rooms/' in p else 1, p))
    shas={hashlib.sha256(open(p,'rb').read()).hexdigest()[:8] for p in ps}
    if len(shas)>1: print('VARIANTS',k,shas)
    rep['dc/tex/%s/%s.re4tex'%(k[0],k)]=ps[0]
json.dump({'replace':rep},open(sys.argv[2],'w'),indent=1)
PY
export PYTHONDONTWRITEBYTECODE=1
rm -rf "${W:?}/vq1"/{src-packages,vq-packages,previews}
FX=$(ls $W/fx-d12/cx-r3*-walk-*.armed.json $W/fx-d12/zz-extra.armed.json)
mapfile -t LA < <(ls "$G"/re4-rfp-20261015-st3d12/scenarios/*/capture/run-output.txt "$G"/re4-rfp-20261015-st3d13/scenarios/*/capture/run-output.txt)
cd /tmp
python3 $S/c5t_vqroom.py $W/vq1/tex-st3vq.pak $W/vq1 /root/probe/lanes-20261018/ch5regen/tex-t10.pak --fixtures $FX --logs "${LA[@]}" > $W/vq1/log.txt 2>&1
tail -1 $W/vq1/log.txt | grep -o "out_sha256.*"
grep -E "^[0-9a-f]{8}-" $W/vq1/log.txt | sort > $W/vq1/mine.txt
{ diff $W/vq1/ref.txt $W/vq1/mine.txt || true; } | head
