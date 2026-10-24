#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/interior-world49ad-qa
WORK=/root/work/lanes/interior-world49ad-qa-scratch
EV=/mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/world49ad-qa-programmes
OWN=/root/work/lanes/interior-vis23/port/dreamcast/tools/d367/interior_vis23/world49ad_qa
SELF=$OWN/build.sh
if [ "${1:-}" != --worker ];then
 ARM=${1:?reference/off/both}
 case "$ARM" in reference|off|both);;*)exit 2;;esac
 exec 7>"$TREE.build.lock";flock -n 7 || { echo OWN_TREE_LEASE_BUSY;exit 2; }
 exec bash /root/probe/d367-buildslot.sh bash "$SELF" --worker "$ARM"
fi
ARM=${2:?reference/off/both}
mkdir -p "$WORK/build/$ARM"
exec > >(tee "$WORK/build/$ARM/launch.log") 2>&1
python3 - <<'PY'
import subprocess,shutil,json
win=int(subprocess.check_output(['/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe','-c',"import shutil;print(shutil.disk_usage('C:/').free)"],text=True).strip())
wsl=shutil.disk_usage('/mnt/c').free
assert min(win,wsl)>=24*(1<<30),(win,wsl)
print(json.dumps(dict(after_slot=True,windows_free=win,wsl_free=wsl,minimum=24*(1<<30))))
PY
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' > "$WORK/build/$ARM/release-processes.txt";then
 echo RELEASE_PRIORITY_HOLD;exit 3
fi
[ "$(git -C "$TREE" rev-parse HEAD)" = 49ad20f9932d638ddb7becf5db6f86b92e0a76a2 ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
mapfile -t CFG < <(python3 - "$EV/plan.json" "$ARM" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));c=p['commands'][sys.argv[2]]
for k in ('prefix','CH2','XON','output'):print(c[k])
PY
)
[ "${#CFG[@]}" -eq 4 ];[ ! -e "${CFG[3]}" ]
export JOBS=1 SOURCE_DATE_EPOCH=1760000000 PYTHONDONTWRITEBYTECODE=1 PRUNE_AUTO=0
export ROUTE_PROGRAMS_DIR="$WORK/programs" ROUTE_PROGRAMS_JSON='' ROUTE_REGISTRY_LOCK="$WORK/programs.lock"
export RE4DC_HARNESS="$WORK/programme-harness"
export RE4DC_KOS_BASE=/root/work/kos-re4dc-d367
export PATH=$RE4DC_KOS_BASE/utils/build_wrappers:/opt/toolchains/dc/sh-elf/bin:/usr/bin:/bin
. "$TREE/port/dreamcast/kos-env.sh"
sha256sum "$KOS_BASE/lib/dreamcast/libkallisti.a" > "$WORK/build/$ARM/kos-before.sha256"
env K="$WORK/build/$ARM/k" T="$TREE" LP="${CFG[0]}" CH2="${CFG[1]}" XON="${CFG[2]}" bash "$TREE/port/dreamcast/tools/d367/ch2/ch2-build.sh" rW
python3 "$OWN/programme.py" check "$ARM"
sha256sum "$KOS_BASE/lib/dreamcast/libkallisti.a" > "$WORK/build/$ARM/kos-after.sha256"
cmp "$WORK/build/$ARM/kos-before.sha256" "$WORK/build/$ARM/kos-after.sha256"
python3 - "$EV" "$ARM" <<'PY'
import json,pathlib,shutil,sys
root=pathlib.Path(sys.argv[1]);arm=sys.argv[2];receipt=json.loads((root/arm/'receipt.json').read_text())
out=pathlib.Path(receipt['output']);obj=out/'obj'
assert out.parent==pathlib.Path('/root/probe/lanes/route') and out.name.startswith('out-ivwe49ad')
assert obj.resolve()==obj and obj.is_dir() and (out/'stack.txt').read_text().strip()==receipt['source']
rows=list(obj.rglob('*'));total=sum(p.stat().st_size for p in rows if p.is_file());count=sum(p.is_file() for p in rows)
shutil.rmtree(obj)
manifest=dict(kind='deleted owned rebuildable object directory after programme receipt',path=str(obj),files=count,bytes=total,source=receipt['source'],programme_receipt=str(root/arm/'receipt.json'),wsl_free_after=shutil.disk_usage('/mnt/c').free)
with (root/arm/'DELETED-OBJECTS.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
print(json.dumps(manifest))
PY
printf 'WORLD49AD_QA_PROGRAMME_COMPLETE arm=%s source=49ad20f9932d638ddb7becf5db6f86b92e0a76a2\n' "$ARM"
