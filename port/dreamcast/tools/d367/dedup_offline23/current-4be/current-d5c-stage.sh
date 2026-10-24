#!/bin/bash
set -euo pipefail
TR=/root/work/lanes/dedup-offline23-current-d5c
T=$TR/port/dreamcast/tools/d367
SHA=4be08e0110592510e3630c01fa9f49b3ac2fed3d
ASSETS=/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023
EV=/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01
ROOT=/root/work/lanes/dedup-offline23-current-d5c-scratch/standard
[ ! -e "$ROOT" ]
[ "$(git -C "$TR" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$TR" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
export PYTHONDONTWRITEBYTECODE=1 SOURCE_DATE_EPOCH=1760000000 PRUNE_AUTO=0
export RE4DC_HARNESS=/root/work/lanes/dedup-offline23-current-d5c-scratch
export RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018 PKG_SRC=/root/re4payload/t164-20261018/tree
. "$T/rr/recipe.conf"
mkdir -p "$ROOT"
exec 7>"$ROOT/owned-stage.lock";flock -n 7
for ARM in off on;do
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
 [ "$(git -C "$TR" rev-parse HEAD)" = "$SHA" ]
 LABEL=fpdd23cur4be08e01${ARM}gW
 O=/root/probe/lanes/route/out-$LABEL
 R=$ROOT/$ARM
 DEST=$EV/base-standard-current4be-$ARM-r1
 [ ! -e "$R" ] && [ ! -e "$DEST" ]
 [ "$(cat "$O/stack.txt")" = "$SHA" ] && [ ! -s "$O/missing.txt" ]
 mkdir -p "$R/fix" "$R/logs"
 cp "$T/rr/recipe.conf" "$R/recipe-source4be.conf"
 SETS=()
 if [ "$ARM" = on ];then
  SETS=(--set "dc/native/r100/ps2-dd3.re4mesh=$ASSETS/r100-stripshare-v1/ps2-dd3.re4mesh"
        --set "dc/native/r101/ps2-dd3.re4mesh=$ASSETS/r101-stripshare-v1/ps2-dd3.re4mesh"
        --set "dc/native/r103/ps2-dd3.re4mesh=$ASSETS/r103-stripshare-v1/ps2-dd3.re4mesh"
        --set "dc/native/r101/ps2-dd3.r4sg=$ASSETS/r101-stripshare-v1/ps2-dd3.r4sg")
 fi
 RE4DC_RESIDENT_STRICT=1 python3 "$T/test11/t11-fix.py" "$LABEL" "$R/fix/pkg.json" --base payload --data "$DATA" "${SETS[@]}" > "$R/logs/t11-fix.txt" 2>&1
 PKG_K="$R" python3 "$T/test8/t8-pkgtree.py" "$LABEL" "$R/fix/pkg.json" > "$R/logs/pkgtree.txt" 2>&1
 grep -q PKGTREE_OK "$R/logs/pkgtree.txt"
 python3 - "$EV/current4be-preflight-r1.json" "$ARM" "$R" <<'PY'
import sys,json,hashlib
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text());arm=sys.argv[2];r=Path(sys.argv[3]);tree=r/'pkgtree'
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()
for room,x in p['original_packages'].items():assert sha(tree/'dc/native'/room/'ps2-world.re4mesh')==x['sha256']
for name,x in p['programs'][arm]['overlays'].items():assert sha(tree/'dc'/name)==x['sha256']
expected={}
if arm=='on':
 for x in p['compact_alternates']:
  src=Path(x['path']);room=src.parent.name.split('-')[0];dst=tree/'dc/native'/room/src.name
  assert sha(dst)==x['sha256'];expected[str(dst.relative_to(tree))]=x['sha256']
else:assert not list((tree/'dc/native').glob('r*/ps2-dd3.*'))
for f in ('warp.txt','padscript.txt','crashtest.txt'):assert not (tree/'dc'/f).exists()
(r/'stage-identity.json').write_text(json.dumps({'source':p['source'],'arm':arm,'programme':p['programs'][arm],'original_packages':p['original_packages'],'compact_files':expected,'off_original_only':arm=='off','actual_standard_native_files':{str(x.relative_to(tree)):{'bytes':x.stat().st_size,'sha256':sha(x)} for x in sorted((tree/'dc/native').glob('r*/ps2-world.r4sg'))}},indent=2)+'\n')
PY
 (cd "$T" && LAYOUT=standard TITLE=RE4DC PRODUCT=T0000 bash mkgdi.sh "$O/re4dc-game.elf" "$R/pkgtree" "$R/gdemu") > "$R/logs/mkgdi.txt" 2>&1
 for PROFILE in loader standard;do python3 "$T/disc_lint.py" --profile "$PROFILE" "$R/gdemu/disc.gdi" > "$R/logs/disc-lint-$PROFILE.txt";done
 python3 "$T/fullplay/fp_iso.py" manifest "$R/gdemu/track03.bin" -o "$R/manifest.json" > "$R/logs/manifest.txt"
 python3 - "$R/manifest.json" "$R/stage-identity.json" <<'PY'
from pathlib import Path
import json,sys
m=json.loads(Path(sys.argv[1]).read_text());p=json.loads(Path(sys.argv[2]).read_text())
assert m['1ST_READ.BIN']['sha256']==p['programme']['main_raw']['sha256']
for name,x in p['programme']['overlays'].items():assert m['dc/'+name]['sha256']==x['sha256']
for name,x in p['compact_files'].items():assert m[name]['sha256']==x
PY
 PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$R/pkgtree" "$R/manifest.json" "$R/gdemu/IP.BIN" "$DEST" "$O" > "$R/logs/fp-master.txt" 2>&1
 cp "$R/stage-identity.json" "$DEST/owned-stage-identity.json"
 cp "$R/recipe-source4be.conf" "$DEST/recipe-source4be.conf"
 cp "$R/logs/disc-lint-loader.txt" "$DEST/disc-lint-loader.txt"
 cp "$R/logs/disc-lint-standard.txt" "$DEST/disc-lint-standard.txt"
 printf 'OWNED_FRESH_BASE_READY arm=%s programme=%s source=%s\n' "$ARM" "$LABEL" "$SHA"
 tail -n 1 "$R/logs/fp-master.txt"
done
python3 - "$ROOT" "$EV" <<'PY'
from pathlib import Path
import json,sys,hashlib
root,ev=map(Path,sys.argv[1:]);a=json.loads((root/'off/stage-identity.json').read_text());b=json.loads((root/'on/stage-identity.json').read_text())
assert a['actual_standard_native_files']==b['actual_standard_native_files']
report={'status':'FRESH_STANDARD_BASES_READY_RUNTIME_GATES_PENDING','source':a['source'],'off_original_only':True,'on_exact4_compact':True,'standard_r4sg_identical':True,'programmes':{n:json.loads((root/n/'stage-identity.json').read_text())['programme'] for n in ('off','on')},'bases':{n:{'path':str(ev/('base-standard-current4be-'+n+'-r1')),'track03_sha256':(ev/('base-standard-current4be-'+n+'-r1')/'track03.sha256').read_text().strip()} for n in ('off','on')}}
(ev/'current4be-bases-r1.json').write_text(json.dumps(report,indent=2)+'\n')
print('MATCHED_ORIGINAL_DATA_AND_FRESH_BASES_VERIFIED')
PY