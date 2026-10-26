#!/bin/bash
# rr-gca.sh <work> <tree> <sha7> <evidence (WSL)>   (WSL; lane cast-ps2-25, 2026-10-26)
# GC-ASSET gate prep for one rr cycle (no-GameCube-assets rule, user 10-23):
#   1. the candidate's catalog from its recipe (gc_port23/make_catalog.sh on cand-<sha8>/gdemu/track03.bin) -> <work>/gca/;
#   2. the gate-ON twin out-fprr<sha7>aW: the release recipe + GC_ASSET_GATE=1 and the catalog pin
#      (GC_ASSET_CATALOG_PIN_FILE); no GC_ASSET_MOTION_UNKNOWN / GC_ASSET_HARVEST (diagnostic builds, not gate runs);
#   3. its base <evidence>/_discs/a (fullplay/fp_master.sh with FP_GC_CATALOG = the catalog).
# rr-jobs.sh then adds the gca-* Flycast jobs (h2 + census r100 r101 r103 r11e r11f) and rr-judge.py judges them with
# gc_port23/judge.py against allowlist.json (baseline: the last good candidate's allowlist) and unwired-baseline.json.
set -euo pipefail
W=${1:?work}; T=${2:?tree}; S7=${3:?sha7}; EVU=${4:?evidence}
ROUTE=/root/probe/lanes/route
D=$T/port/dreamcast/tools/d367
CAND=$(cat "$W/cand.txt")
G=$W/gca
rm -rf "${G:?}"
bash "$D/gc_port23/make_catalog.sh" "$CAND/gdemu/track03.bin" "$W/recipe.conf" "$G" | tail -1
FP_TREE=$T FP_SKIP_IDENTITY=1 bash "$D/fullplay/fp_twin.sh" "$ROUTE/out-rr${S7}rP" "rr${S7}a" \
  GC_ASSET_GATE=1 "GC_ASSET_CATALOG_PIN_FILE=$G/gc-assets.pin" > "$W/twin-rr${S7}a.txt" 2>&1
O=$ROUTE/out-fprr${S7}aW
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ] || { echo "rr-gca: gate twin failed"; tail -5 "$W/twin-rr${S7}a.txt"; exit 1; }
grep -q "GC_ASSET_CATALOG_PIN_FILE=$G/gc-assets.pin" "$O/candidate.txt" || { echo "rr-gca: twin lacks the catalog pin"; exit 1; }
F=$D/fullplay
python3 "$F/fp_iso.py" extract "$CAND/gdemu/track03.bin" "$W/gca-rel/tree" --manifest "$W/gca-rel/manifest.json" --ipbin "$W/gca-rel/IP.BIN" | tail -1
rc=0
FP_GC_CATALOG=$G/catalog/gc-assets.idx bash "$F/fp_master.sh" "$W/gca-rel/tree" "$W/gca-rel/manifest.json" "$W/gca-rel/IP.BIN" \
  "$EVU/_discs/a" "$O" > "$W/master-a.txt" 2>&1 || rc=1
tail -n 1 "$W/master-a.txt" | cut -c1-200
rm -rf "${W:?}/gca-rel/tree"
exit $rc
