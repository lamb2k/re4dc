#!/bin/bash
# make_catalog.sh <track03.bin|.iso | extracted dir> <recipe.conf> <out dir>   (lane cast-ps2-25, 2026-10-26)
# The GC-ASSET catalog of one release disc, regenerated from the recipe in one command:
#   1. fp_iso.py extract the disc's data track (tree + manifest), or use an already extracted dir (<dir>/tree +
#      <dir>/manifest.json, e.g. a candidate tree with an overlay; it is left in place);
#   2. build_catalog.py: every payload the gate binds (disc rows + harvest.tsv runtime rows + compiled.tsv program rows);
#   3. provenance.py: each row's provenance from the recipe's data-set stores and provenance-reviewed.tsv;
#   4. build_catalog.py --proofs: the final catalog.
# Outputs <out>/catalog/{gc-assets.idx,catalog.json,catalog-report.json}, <out>/provenance/{proofs.json,unknown-rows.tsv,...}
# and <out>/gc-assets.pin (the 64-hex pin; game/gc_asset_gate.mk reads it with GC_ASSET_CATALOG_PIN_FILE=<out>/gc-assets.pin).
# A gate-ON twin stages <out>/catalog/gc-assets.idx as dc/gc-assets.idx (fullplay/fp_master.sh FP_GC_CATALOG).
# The extracted tree is deleted at the end (rebuildable); the out dir must not exist.
set -euo pipefail
TRACK=${1:?track03}; RECIPE=${2:?recipe.conf}; OUT=${3:?out dir}
H=$(cd "$(dirname "$0")" && pwd)
[ ! -e "$OUT" ] || { echo "make_catalog: $OUT exists" >&2; exit 1; }
mkdir -p "$OUT"
if [ -d "$TRACK" ]; then
  X=$TRACK; KEEP=1
else
  X="$OUT/extract"; KEEP=0
  python3 "$H/../fullplay/fp_iso.py" extract "$TRACK" "$X/tree" --manifest "$X/manifest.json" --ipbin "$X/IP.BIN" > "$OUT/extract.log"
fi
MS=$(sha256sum "$X/manifest.json" | cut -c1-64)
HS=$(sha256sum "$H/harvest.tsv" | cut -c1-64)
python3 "$H/build_catalog.py" --disc-dir "$X/tree" --manifest "$X/manifest.json" --manifest-sha256 "$MS" \
  --harvest "$H/harvest.tsv" --harvest-sha256 "$HS" --compiled "$H/compiled.tsv" --out-dir "$OUT/raw" > "$OUT/raw.log"
python3 "$H/provenance.py" "$OUT/raw/catalog.json" "$RECIPE" "$OUT/provenance" > "$OUT/provenance.log"
PS=$(sha256sum "$OUT/provenance/proofs.json" | cut -c1-64)
python3 "$H/build_catalog.py" --disc-dir "$X/tree" --manifest "$X/manifest.json" --manifest-sha256 "$MS" \
  --harvest "$H/harvest.tsv" --harvest-sha256 "$HS" --compiled "$H/compiled.tsv" \
  --proofs "$OUT/provenance/proofs.json" --proofs-sha256 "$PS" --out-dir "$OUT/catalog" > "$OUT/catalog.log"
python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['pin'])" "$OUT/catalog/catalog-report.json" > "$OUT/gc-assets.pin"
[ "$KEEP" = 1 ] || rm -rf "${X:?}"
echo "make_catalog: rows $(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['rows'])" "$OUT/catalog/catalog-report.json") unknown $(($(wc -l < "$OUT/provenance/unknown-rows.tsv") - 1)) pin $(cat "$OUT/gc-assets.pin")"
