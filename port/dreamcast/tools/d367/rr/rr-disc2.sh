#!/bin/bash
# rr-disc2.sh <work> <tree A> <tree B> <sha7> <evidence (WSL)>   (WSL; lane castle-disc2-26, 2026-11-01)
# The Disc 2 arm of an rr cycle (recipe.conf RR_DISC2=1; user 10-26 "Disc 2, one zip": the castle starts on Disc 2, both
# game discs ship in the one game zip). Run by rr-cycle.sh after the Disc 1 candidate is packaged (cand.txt) and its bases.
#   1. the Disc 2 program: castle31/build-disc2.sh rP at the built commit (release recipe CH2 + the castle line CH4REC +
#      DISC_SET=1 WEAPON_WEP05=1 SS11_ROOM_EVICT=1) -> out-<pfx><sha7>d2rP;
#   2. the Disc 2 tree: the Disc 1 candidate's own track03 (extracted) + the castle content (D2_CASTLE_TREE, castle31/
#      castle_fixture.py: castle-owned files, tex.pak = Disc 1's pack + castle-only keys) - the village rooms
#      (discsets/mkdisc2.py) + this program; mastered with mkgdi.sh LAYOUT=standard into <cand>/disc2/gdemu, disc_lint
#      loader + standard, boot file = this program;
#   3. twins and bases for the Disc 2 Flycast jobs (rr-jobs.sh d2-*): d2c (census + KOS squeeze) -> _discs/d2c and the
#      GC-ASSET gate twin d2a (catalog of the Disc 2 image) -> _discs/d2a.
# Writes <work>/disc2.env (program sha, image sha, sectors) and <work>/disc2.ok on success. Never touches Disc 1's files.
set -euo pipefail
W=${1:?work}; TA=${2:?tree A}; TB=${3:?tree B}; S7=${4:?sha7}; EVU=${5:?evidence}
# shellcheck source=/dev/null
. "$W/recipe.conf"
P=${RR_PFX:-rr}; L=$P$S7; ROUTE=/root/probe/lanes/route
D=$TA/port/dreamcast/tools/d367; F=$D/fullplay; TOOL=/opt/toolchains/dc/sh-elf/bin
CAND=$(cat "$W/cand.txt"); S8=$(sed -n 's/^sha=//p' "$W/cycle.env" | cut -c1-8)
CT=${D2_CASTLE_TREE:?recipe.conf D2_CASTLE_TREE (the castle content tree)}
[ -d "$CT" ] || { echo "rr-disc2: castle tree $CT is missing"; exit 1; }
rm -f "$W/disc2.ok"; mkdir -p "$W/d2"
O=$ROUTE/out-${L}d2rP
if [ "${D2_MODE:-}" = bases ]; then
  # full tier: the packaged Disc 2 of the last good candidate, its twins (kept) and fresh bases; no rebuild
  [ -s "$O/re4dc-game.elf" ] && [ -s "$CAND/disc2/gdemu/track03.bin" ] || { echo "rr-disc2: no Disc 2 build / disc to re-check"; exit 1; }
  rm -rf "${W:?}/d2/out" "${W:?}/d2/d1"; mkdir -p "$W/d2/d1"
  python3 "$F/fp_iso.py" extract "$CAND/disc2/gdemu/track03.bin" "$W/d2/out/tree" --manifest "$W/d2/out/manifest.json" --ipbin "$W/d2/d1/IP.BIN" | tail -1
else
# 1. program
K=$W/k2 T=$TA LP=${L}d2 bash "$D/castle31/build-disc2.sh" rP 2>&1 | grep '^rc=' | cut -c1-200 | tee "$W/build-d2rP.txt"
grep -q '^rc=0 ' "$W/build-d2rP.txt" && [ -s "$O/re4dc-game.elf" ] || { echo "rr-disc2: Disc 2 build failed"; exit 1; }
[ ! -s "$O/missing.txt" ] || { echo "rr-disc2: missing.txt not empty"; head "$O/missing.txt"; exit 1; }
$TOOL/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$W/d2/img.bin"
IMG=$(sha256sum < "$W/d2/img.bin" | cut -c1-64); rm -f "$W/d2/img.bin"
# 2. tree: Disc 1 candidate tree + castle fixture - village, this program
rm -rf "${W:?}/d2/d1"
python3 "$F/fp_iso.py" extract "$CAND/gdemu/track03.bin" "$W/d2/d1/tree" --manifest "$W/d2/d1/manifest.json" --ipbin "$W/d2/d1/IP.BIN" | tail -1
python3 "$D/castle31/castle_fixture.py" "$W/d2/d1/tree" "$CT" "$W/d2/fx" | tail -2
python3 "$D/discsets/mkdisc2.py" "$W/d2/d1/tree" "$W/d2/fx/castle-fixture.json" "$O" "$W/d2/out" "$S8" | tail -1
rm -rf "${W:?}/d2/gdemu"
(cd "$D" && LAYOUT=standard bash mkgdi.sh "$O/re4dc-game.elf" "$W/d2/out/tree" "$W/d2/gdemu" | tail -1)
for prof in loader standard; do
  python3 "$D/disc_lint.py" --profile $prof "$W/d2/gdemu/disc.gdi" > "$W/d2/disc_lint-$prof.txt" ||
    { grep -vE '^(ok|WARN) ' "$W/d2/disc_lint-$prof.txt" | head; echo "rr-disc2: disc_lint $prof FAILED"; exit 1; }
  echo "Disc 2 disc_lint $prof: $(tail -1 "$W/d2/disc_lint-$prof.txt")"
done
python3 "$F/fp_iso.py" manifest "$W/d2/gdemu/track03.bin" -o "$W/d2/manifest-disc.json"
have=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['1ST_READ.BIN']['sha256'])" "$W/d2/manifest-disc.json")
[ "$IMG" = "$have" ] || { echo "rr-disc2: Disc 2 boot file $have is not out-${L}d2rP ($IMG)"; exit 1; }
grep -q 'disc=2 ' "$W/d2/out/tree/dc/disc.id" || { echo "rr-disc2: no dc/disc.id disc=2"; exit 1; }
rm -rf "$CAND/disc2"; mkdir -p "$CAND/disc2/gdemu"
for f in disc.gdi track01.bin track02.raw track03.bin; do cp "$W/d2/gdemu/$f" "$CAND/disc2/gdemu/"; done
(cd "$CAND/disc2/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin | sed 's#  #  disc2/gdemu/#') > "$CAND/disc2/SHA256SUMS.txt"
cmp <(cut -c1-64 "$CAND/disc2/SHA256SUMS.txt") <(cd "$W/d2/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin | cut -c1-64) \
  && echo "Disc 2 tracks match the ext4 build"
rm -rf "${W:?}/d2/gdemu" "${W:?}/d2/d1/tree"
{ echo "prog=$IMG"; echo "end=$(cat "$O/end.txt")"; echo "build=out-${L}d2rP"; echo "disc=$CAND/disc2/gdemu";
  python3 -c "import json,sys;r=json.load(open(sys.argv[1]));print('files=%d'%r['files']);print('sectors=%d'%r['data_sectors']);print('village_pruned=%d'%r['village_pruned'])" "$W/d2/out/report.json"; } > "$W/disc2.env"
fi
# 3. twins (B: census + KOS; A: GC-ASSET gate on the Disc 2 catalog), then their bases
[ -s "$ROUTE/out-fp${L}d2cW/re4dc-game.elf" ] && [ "${D2_MODE:-}" = bases ] && pb= || { FP_TREE=$TB FP_SKIP_IDENTITY=1 bash "$F/fp_twin.sh" "$O" ${L}d2c KOS_WATCH=1 KOS_SQUEEZE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 \
  NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150 > "$W/twin-d2c.txt" 2>&1 & pb=$!; }
G=$W/gca2; rm -rf "${G:?}"; ga=0
{ bash "$D/gc_port23/make_catalog.sh" "$CAND/disc2/gdemu/track03.bin" "$W/recipe.conf" "$G" | tail -1 &&
  FP_TREE=$TA FP_SKIP_IDENTITY=1 bash "$F/fp_twin.sh" "$O" ${L}d2a GC_ASSET_GATE=1 "GC_ASSET_CATALOG_PIN_FILE=$G/gc-assets.pin" > "$W/twin-d2a.txt" 2>&1; } || ga=1
[ -z "$pb" ] || wait $pb || { echo "rr-disc2: census twin failed"; tail -3 "$W/twin-d2c.txt"; exit 1; }
rc=0
bash "$F/fp_master.sh" "$W/d2/out/tree" "$W/d2/out/manifest.json" "$W/d2/d1/IP.BIN" "$EVU/_discs/d2c" "$ROUTE/out-fp${L}d2cW" > "$W/master-d2c.txt" 2>&1 || rc=1
tail -n 1 "$W/master-d2c.txt" | cut -c1-200
if [ $ga = 0 ] && [ -s "$ROUTE/out-fp${L}d2aW/re4dc-game.elf" ]; then
  FP_GC_CATALOG=$G/catalog/gc-assets.idx bash "$F/fp_master.sh" "$W/d2/out/tree" "$W/d2/out/manifest.json" "$W/d2/d1/IP.BIN" \
    "$EVU/_discs/d2a" "$ROUTE/out-fp${L}d2aW" > "$W/master-d2a.txt" 2>&1 || echo "rr-disc2: GC-ASSET base failed (its row reports it)"
  tail -n 1 "$W/master-d2a.txt" | cut -c1-200
else echo "rr-disc2: GC-ASSET twin failed (its row reports it)"; tail -3 "$W/twin-d2a.txt" 2>/dev/null || true; fi
rm -rf "${W:?}/d2/out/tree"
[ $rc = 0 ] && touch "$W/disc2.ok"
exit $rc
