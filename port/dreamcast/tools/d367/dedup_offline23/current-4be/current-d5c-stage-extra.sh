#!/bin/bash
set -euo pipefail
MODE=${1:?diag or trace};case "$MODE" in diag|trace);;*)exit 2;;esac
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
. "$OWN/current-d5c-pins.sh"
T=$TREE/port/dreamcast/tools/d367
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain --untracked-files=no)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
R=$WORK/$MODE
DEST=$EVIDENCE/base-$MODE-current4be-r1
[ ! -e "$R" ];[ ! -e "$DEST" ]
LABEL=fpdd23cur${S8}diagW;[ "$MODE" != trace ] || LABEL=dd23cur${S8}onrT
O=/root/probe/lanes/route/out-$LABEL
[ "$(cat "$O/stack.txt")" = "$SOURCE" ];[ ! -s "$O/missing.txt" ]
grep -qx SCENERY_DEDUP=3 "$O/resolved-knobs.txt"
mkdir -p "$R/fix" "$R/logs"
exec 7>"$WORK/stage.lock";flock -n 7 || exit 2
export PYTHONDONTWRITEBYTECODE=1 SOURCE_DATE_EPOCH=1760000000 PRUNE_AUTO=0
export RE4DC_HARNESS="$WORK" RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018 PKG_SRC=/root/re4payload/t164-20261018/tree
. "$T/rr/recipe.conf"
SETS=(--set "dc/native/r100/ps2-dd3.re4mesh=$ASSETS/r100-stripshare-v1/ps2-dd3.re4mesh" --set "dc/native/r101/ps2-dd3.re4mesh=$ASSETS/r101-stripshare-v1/ps2-dd3.re4mesh" --set "dc/native/r103/ps2-dd3.re4mesh=$ASSETS/r103-stripshare-v1/ps2-dd3.re4mesh" --set "dc/native/r101/ps2-dd3.r4sg=$ASSETS/r101-stripshare-v1/ps2-dd3.r4sg")
RE4DC_RESIDENT_STRICT=1 python3 "$T/test11/t11-fix.py" "$LABEL" "$R/fix/pkg.json" --base payload --data "$DATA" "${SETS[@]}" > "$R/logs/t11-fix.txt" 2>&1
PKG_K="$R" python3 "$T/test8/t8-pkgtree.py" "$LABEL" "$R/fix/pkg.json" > "$R/logs/pkgtree.txt" 2>&1
grep -q PKGTREE_OK "$R/logs/pkgtree.txt"
(cd "$T" && LAYOUT=standard TITLE=RE4DC PRODUCT=T0000 bash mkgdi.sh "$O/re4dc-game.elf" "$R/pkgtree" "$R/gdemu") > "$R/logs/mkgdi.txt" 2>&1
for PROFILE in loader standard;do python3 "$T/disc_lint.py" --profile "$PROFILE" "$R/gdemu/disc.gdi" > "$R/logs/disc-lint-$PROFILE.txt";done
python3 "$T/fullplay/fp_iso.py" manifest "$R/gdemu/track03.bin" -o "$R/manifest.json" > "$R/logs/manifest.txt"
python3 - "$WORK" "$MODE" "$O" "$R" "$SOURCE" <<'PY'
from pathlib import Path
import json,hashlib,subprocess,sys
work,mode,o,r,source=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]),sys.argv[5]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((r/'manifest.json').read_text());base=json.loads((work/'standard/on/manifest.json').read_text())
allowed={'1ST_READ.BIN'}|{'dc/'+f.name for f in o.glob('*.ovl')}
different=[n for n in m.keys()|base.keys() if m.get(n,{}).get('sha256')!=base.get(n,{}).get('sha256')]
assert not set(different)-allowed,sorted(set(different)-allowed)
for f in o.glob('*.ovl'):assert m['dc/'+f.name]['sha256']==sha(f)
raw=Path('/dev/shm')/('dedup4be-'+mode+'-stage-main.bin');assert not raw.exists()
subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(o/'re4dc-game.elf'),str(raw)],check=True)
assert m['1ST_READ.BIN']['sha256']==sha(raw)
for f in ('warp.txt','padscript.txt','crashtest.txt'):assert not (r/'pkgtree/dc'/f).exists()
report=dict(source=source,mode=mode,programme=str(o),elf_sha256=sha(o/'re4dc-game.elf'),main_raw_sha256=sha(raw),resolved_sha256=sha(o/'resolved-knobs.txt'),all14=14,standard_on_manifest_sha256=sha(work/'standard/on/manifest.json'),data_equal_except_programme=True,different_paths=different)
(r/'stage-identity.json').write_text(json.dumps(report,indent=2)+'\n')
PY
bash "$T/fullplay/fp_master.sh" "$R/pkgtree" "$R/manifest.json" "$R/gdemu/IP.BIN" "$DEST" "$O" > "$R/logs/fp-master.txt" 2>&1
cp "$R/stage-identity.json" "$DEST/owned-stage-identity.json"
cp "$R/logs/disc-lint-loader.txt" "$DEST/disc-lint-loader.txt"
cp "$R/logs/disc-lint-standard.txt" "$DEST/disc-lint-standard.txt"
echo "OWNED_CURRENT_EXTRA_BASE_READY mode=$MODE label=$LABEL"
