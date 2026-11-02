#!/bin/bash
# rr-disc3.sh <work> <tree A> <tree B> <sha7> <evidence (WSL)>   (WSL; lane world-ch5, 2026-11-02)
# The Disc 3 arm of an rr cycle (recipe.conf RR_DISC3=1; settled layout user 10-16: Disc 3 = island + final chapter; all
# game discs ship in the one game zip). The twin of rr-disc2.sh. Run by rr-cycle.sh after the Disc 1 candidate is
# packaged (cand.txt). Never touches Disc 1's or Disc 2's files.
#   1. the Disc 3 program: island5/build-disc3.sh rP (release recipe CH2 + D3REC) -> out-<pfx><sha7>d3rP;
#   2. the Disc 3 tree: the Disc 1 candidate's track03 (extracted) + the island content (D3_ISLAND_TREE, discsets/
#      d3-content.sh; discsets/disc3_fixture.py: island-owned files, tex.pak = Disc 1's pack + island-only keys) - the
#      village and castle rooms (discsets/mkdisc3.py; r22c stays) + this program; mkgdi.sh LAYOUT=standard into
#      <cand>/disc3/gdemu, disc_lint loader + standard;
#   3. the census + KOS twin d3c and the GC-ASSET gate twin d3a, with their bases in _discs/d3c and _discs/d3a.
# Writes <work>/disc3.env and <work>/disc3.ok on success.
set -euo pipefail
W=${1:?work}; TA=${2:?tree A}; TB=${3:?tree B}; S7=${4:?sha7}; EVU=${5:?evidence}
# shellcheck source=/dev/null
. "$W/recipe.conf"
P=${RR_PFX:-rr}; L=$P$S7; ROUTE=/root/probe/lanes/route
D=$TA/port/dreamcast/tools/d367; F=$D/fullplay; TOOL=/opt/toolchains/dc/sh-elf/bin
CAND=$(cat "$W/cand.txt"); S8=$(sed -n 's/^sha=//p' "$W/cycle.env" | cut -c1-8)
IT=${D3_ISLAND_TREE:?recipe.conf D3_ISLAND_TREE (the island content tree, discsets/d3-content.sh)}
[ -d "$IT" ] || { echo "rr-disc3: island tree $IT is missing"; exit 1; }
rm -f "$W/disc3.ok"; mkdir -p "$W/d3"
O=$ROUTE/out-${L}d3rP
K=$W/k3 T=$TA LP=${L}d3 bash "$D/island5/build-disc3.sh" rP 2>&1 | grep '^rc=' | cut -c1-200 | tee "$W/build-d3rP.txt"
grep -q '^rc=0 ' "$W/build-d3rP.txt" && [ -s "$O/re4dc-game.elf" ] || { echo "rr-disc3: Disc 3 build failed"; exit 1; }
[ ! -s "$O/missing.txt" ] || { echo "rr-disc3: missing.txt not empty"; head "$O/missing.txt"; exit 1; }
$TOOL/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$W/d3/img.bin"
IMG=$(sha256sum < "$W/d3/img.bin" | cut -c1-64); rm -f "$W/d3/img.bin"
rm -rf "${W:?}/d3/d1"
python3 "$F/fp_iso.py" extract "$CAND/gdemu/track03.bin" "$W/d3/d1/tree" --manifest "$W/d3/d1/manifest.json" --ipbin "$W/d3/d1/IP.BIN" | tail -1
python3 "$D/discsets/disc3_fixture.py" "$W/d3/d1/tree" "$IT" "$W/d3/fx" | tail -2
python3 "$D/discsets/mkdisc3.py" "$W/d3/d1/tree" "$W/d3/fx/island-fixture.json" "$O" "$W/d3/out" "$S8" | tail -1
rm -rf "${W:?}/d3/gdemu"
(cd "$D" && LAYOUT=standard bash mkgdi.sh "$O/re4dc-game.elf" "$W/d3/out/tree" "$W/d3/gdemu" | tail -1)
for prof in loader standard; do
  python3 "$D/disc_lint.py" --profile $prof "$W/d3/gdemu/disc.gdi" > "$W/d3/disc_lint-$prof.txt" ||
    { grep -vE '^(ok|WARN) ' "$W/d3/disc_lint-$prof.txt" | head; echo "rr-disc3: disc_lint $prof FAILED"; exit 1; }
  echo "Disc 3 disc_lint $prof: $(tail -1 "$W/d3/disc_lint-$prof.txt")"
done
python3 "$F/fp_iso.py" manifest "$W/d3/gdemu/track03.bin" -o "$W/d3/manifest-disc.json"
have=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['1ST_READ.BIN']['sha256'])" "$W/d3/manifest-disc.json")
[ "$IMG" = "$have" ] || { echo "rr-disc3: Disc 3 boot file $have is not out-${L}d3rP ($IMG)"; exit 1; }
grep -q 'disc=3 ' "$W/d3/out/tree/dc/disc.id" || { echo "rr-disc3: no dc/disc.id disc=3"; exit 1; }
rm -rf "$CAND/disc3"; mkdir -p "$CAND/disc3/gdemu"
for f in disc.gdi track01.bin track02.raw track03.bin; do cp "$W/d3/gdemu/$f" "$CAND/disc3/gdemu/"; done
(cd "$CAND/disc3/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin | sed 's#  #  disc3/gdemu/#') > "$CAND/disc3/SHA256SUMS.txt"
rm -rf "${W:?}/d3/gdemu" "${W:?}/d3/d1/tree"
{ echo "prog=$IMG"; echo "end=$(cat "$O/end.txt")"; echo "build=out-${L}d3rP"; echo "disc=$CAND/disc3/gdemu";
  python3 -c "import json,sys;r=json.load(open(sys.argv[1]));[print('%s=%d'%(k,r[k])) for k in ('files','data_sectors','village_pruned','castle_pruned')]" "$W/d3/out/report.json"; } > "$W/disc3.env"
if [ "${D3_NO_TWINS:-0}" = 1 ]; then touch "$W/disc3.ok"; exit 0; fi   # disc only (island5/disc3-lane.sh build)
FP_TREE=$TB FP_SKIP_IDENTITY=1 bash "$F/fp_twin.sh" "$O" ${L}d3c KOS_WATCH=1 KOS_SQUEEZE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 \
  NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150 > "$W/twin-d3c.txt" 2>&1 || { echo "rr-disc3: census twin failed"; tail -3 "$W/twin-d3c.txt"; exit 1; }
G=$W/gca3; rm -rf "${G:?}"; ga=0
{ PROVENANCE_D3=1 bash "$D/gc_port23/make_catalog.sh" "$CAND/disc3/gdemu/track03.bin" "$W/recipe.conf" "$G" | tail -1 &&
  FP_TREE=$TA FP_SKIP_IDENTITY=1 bash "$F/fp_twin.sh" "$O" ${L}d3a GC_ASSET_GATE=1 GC_ASSET_CKPT_FIRST=30 "GC_ASSET_CATALOG_PIN_FILE=$G/gc-assets.pin" > "$W/twin-d3a.txt" 2>&1; } || ga=1
rc=0
bash "$F/fp_master.sh" "$W/d3/out/tree" "$W/d3/out/manifest.json" "$W/d3/d1/IP.BIN" "$EVU/_discs/d3c" "$ROUTE/out-fp${L}d3cW" > "$W/master-d3c.txt" 2>&1 || rc=1
tail -n 1 "$W/master-d3c.txt" | cut -c1-200
if [ $ga = 0 ] && [ -s "$ROUTE/out-fp${L}d3aW/re4dc-game.elf" ]; then
  FP_GC_CATALOG=$G/catalog/gc-assets.idx bash "$F/fp_master.sh" "$W/d3/out/tree" "$W/d3/out/manifest.json" "$W/d3/d1/IP.BIN" \
    "$EVU/_discs/d3a" "$ROUTE/out-fp${L}d3aW" > "$W/master-d3a.txt" 2>&1 || echo "rr-disc3: GC-ASSET base failed"
else echo "rr-disc3: GC-ASSET twin failed"; tail -3 "$W/twin-d3a.txt" 2>/dev/null || true; fi
rm -rf "${W:?}/d3/out/tree"
[ $rc = 0 ] && touch "$W/disc3.ok"
exit $rc
