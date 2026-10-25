#!/bin/bash
# rr-qa.sh <work dir> <tree> <sha> <test name> <zip dir|-> [evidence dir (WSL)]   (WSL; lane rr, standing rule 8)
# The QA disc of a candidate: the same release recipe (W tree, recipe.conf CH2) as a warp build plus the QA knobs,
# mkqa.py presets as dc/qa, mkgdi (standard layout), disc_lint loader + standard, and a zip with the newest committed
# qa*/README-package.txt. Model: lane release-test21's qapkg.sh + zips.sh.
#   <zip dir> -   : zip written to <work>/qa, tested (testzip) and deleted (full tier: the zip step is checked only)
#   <zip dir> DIR : zip kept as DIR/RE4DC-QA-Test<N>-<sha8>-<date>-GDEMU.zip (rr.sh package)
#   [evidence]    : also master an fp_master.sh base at <evidence>/_discs/qa for the QA Flycast jobs (rr-jobs.sh full)
# The QA build out-rr<sha7>qrW is reused when it exists (rr-clean-builds.sh deletes it with the cycle's other builds).
set -euo pipefail
W=${1:?work}; TR=${2:?tree}; SHA=${3:?sha}; TN=${4:?test name}; ZD=${5:?zip dir or -}; EVU=${6:-}
BIN=$(cd "$(dirname "$0")" && pwd)
S7=${SHA:0:7}; S8=${SHA:0:8}
T=$TR/port/dreamcast/tools/d367
if [ -s "$W/recipe.conf" ]; then . "$W/recipe.conf"; else . "$BIN/recipe.conf"; fi
L=rr${S7}qrW
O=/root/probe/lanes/route/out-$L
R=$W/qa
export RE4DC_PAYLOAD_ROOT=${RE4DC_PAYLOAD_ROOT:-/root/re4payload/t164-20261018}
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
rm -rf "${R:?}"; mkdir -p "$R/fix" "$R/logs" "$R/qa"
if [ ! -s "$O/re4dc-game.elf" ]; then
  K=$W/kq T=$TR LP=rr${S7}q CH2="$CH2" \
    XON="QA_MENU=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=$TN QA_SRC=$S8" \
    bash "$T/ch2/ch2-build.sh" rW 2>&1 | grep '^rc=' | cut -c1-200 | tee "$R/logs/build.txt"
  grep -q '^rc=0 ' "$R/logs/build.txt" && [ -s "$O/re4dc-game.elf" ] || { echo "QA build failed"; exit 1; }
fi
[ ! -s "$O/missing.txt" ] || { echo "QA build missing.txt not empty"; head "$O/missing.txt"; exit 1; }
RE4DC_RESIDENT_STRICT=1 python3 "$T/test11/t11-fix.py" "$L" "$R/fix/pkg-$L.json" --base payload --data "$DATA" | tail -1 | cut -c1-200
PKG_K=$R python3 "$T/test8/t8-pkgtree.py" "$L" "$R/fix/pkg-$L.json" > "$R/logs/pkgtree.txt" 2>&1
grep -q PKGTREE_OK "$R/logs/pkgtree.txt" || { tail -20 "$R/logs/pkgtree.txt"; exit 1; }
python3 "$T/stage_route.py" --stage 1 --json "$R/sr1.json" > /dev/null
python3 "$T/qa20/mkqa.py" "$R/qa" --sr1 "$R/sr1.json" | tail -2
mkdir -p "$R/pkgtree/dc/qa"; cp "$R"/qa/* "$R/pkgtree/dc/qa/"
[ ! -e "$R/pkgtree/dc/warp.txt" ] || { echo "warp.txt on the QA disc"; exit 1; }
(cd "$T" && LAYOUT=standard bash mkgdi.sh "$O/re4dc-game.elf" "$R/pkgtree" "$R/gdemu" | tail -1)
for prof in loader standard; do
  python3 "$T/disc_lint.py" --profile $prof "$R/gdemu/disc.gdi" > "$R/logs/disc_lint-$prof.txt" \
    || { grep -vE '^(ok|WARN) ' "$R/logs/disc_lint-$prof.txt" | head; exit 1; }
  echo "QA disc_lint $prof: $(tail -1 "$R/logs/disc_lint-$prof.txt")"
done
rm -rf "${R:?}/pkgtree"
# zip: tracks + newest qa*/README-package.txt + SHA256SUMS.txt
QR=$(bash "$BIN/rr-newest.sh" 'qa[^/]*' README-package.txt "$R/README.lf")
echo "QA README: $QR"
# TN_PLACEHOLDER in the README = the test name this zip is packaged with (rr.sh package <tag> <N>)
tr -d '\r' < "$R/README.lf" | sed "s/TN_PLACEHOLDER/$TN/g" | sed 's/$/\r/' > "$R/README.txt"
! grep -q PLACEHOLDER "$R/README.txt" || { echo "QA README: unfilled placeholder"; exit 1; }
(cd "$R/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin | sed 's#  #  gdemu/#') > "$R/SHA256SUMS.txt"
Z=RE4DC-QA-Test$TN-$S8-$(date +%Y%m%d)-GDEMU.zip
if [ "$ZD" = - ]; then ZP=$R/$Z; else mkdir -p "$ZD"; ZP=$ZD/$Z; fi
python3 - "$R/gdemu" "$ZP" "$R/README.txt" "$R/SHA256SUMS.txt" <<'P'
import sys, zipfile, os
g, dst, rd, sm = sys.argv[1:5]
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for f in ('disc.gdi', 'track01.bin', 'track02.raw', 'track03.bin'):
        z.write(os.path.join(g, f), 'gdemu/' + f)
    z.write(rd, 'README.txt'); z.write(sm, 'SHA256SUMS.txt')
with zipfile.ZipFile(dst) as z:
    bad = z.testzip()
print('QA zip %s testzip %s' % (os.path.basename(dst), 'ok' if bad is None else 'BAD ' + bad))
sys.exit(0 if bad is None else 1)
P
[ "$ZD" != - ] || rm -f "${ZP:?}"
# Flycast base for the QA jobs (full tier)
if [ -n "$EVU" ]; then
  F=$T/fullplay
  python3 "$F/fp_iso.py" extract "$R/gdemu/track03.bin" "$R/tree" --manifest "$R/man.json" --ipbin "$R/IP.BIN" | tail -1
  bash "$F/fp_master.sh" "$R/tree" "$R/man.json" "$R/IP.BIN" "$EVU/_discs/qa" > "$R/logs/master.txt" 2>&1 || { tail -5 "$R/logs/master.txt"; exit 1; }
  tail -1 "$R/logs/master.txt" | cut -c1-200
  rm -rf "${R:?}/tree"
fi
rm -rf "${R:?}/gdemu"
echo QA_OK
