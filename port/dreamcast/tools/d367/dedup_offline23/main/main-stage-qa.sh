#!/bin/bash
set -euo pipefail
ARM=${1:?on or off}
TR=/root/work/lanes/dedup-offline23-integration
T=$TR/port/dreamcast/tools/d367
ROOT=/root/work/lanes/dedup-offline23-main
SOURCE='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023'
case "$ARM" in
  on) LABEL=dd23af09on2rW;;
  off) LABEL=dd23af09offrW;;
  *) exit 2;;
esac
O=/root/probe/lanes/route/out-$LABEL
R=$ROOT/stage-$ARM
[ "$(realpath -m "$R")" = "$ROOT/stage-$ARM" ]
[ ! -e "$R" ] && [ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 26843545600 ]
check(){ [ "$(sha256sum "$SOURCE/$1" | cut -d' ' -f1)" = "$2" ]; }
check r100-linear/ps2-dd3.re4mesh 19548f9d6b473b65ff634caefa45cdc907b86ec5a6f767357062c91ff2bd607b
check r101-linear/ps2-dd3.re4mesh 19c227e5215fcdf8935d24c091c16be4d7767a0b30beaeace2122b04d777bef5
check r103-linear/ps2-dd3.re4mesh 7785ad48983c33f0da8195453be0ba923acc5a1061036fce2d0bc3d11e241365
check r101-linear/ps2-dd3.r4sg c9b118b98a6c76fd8164d4b924be091342d4db3dd5ce89ecf30d9ae6cd8ff675
mkdir -p "$R/fix" "$R/logs" "$R/qa"
exec > >(tee "$R/stage.log") 2>&1
. "$T/rr/recipe.conf"
export RE4DC_PAYLOAD_ROOT=/root/re4payload/t164-20261018
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
RE4DC_RESIDENT_STRICT=1 python3 "$T/test11/t11-fix.py" "$LABEL" "$R/fix/pkg.json" --base payload --data "$DATA" \
  --set "dc/native/r100/ps2-dd3.re4mesh=$SOURCE/r100-linear/ps2-dd3.re4mesh" \
  --set "dc/native/r101/ps2-dd3.re4mesh=$SOURCE/r101-linear/ps2-dd3.re4mesh" \
  --set "dc/native/r103/ps2-dd3.re4mesh=$SOURCE/r103-linear/ps2-dd3.re4mesh" \
  --set "dc/native/r101/ps2-dd3.r4sg=$SOURCE/r101-linear/ps2-dd3.r4sg"
PKG_K="$R" python3 "$T/test8/t8-pkgtree.py" "$LABEL" "$R/fix/pkg.json" > "$R/logs/pkgtree.txt" 2>&1
grep -q PKGTREE_OK "$R/logs/pkgtree.txt"
python3 "$T/stage_route.py" --stage 1 --json "$R/sr1.json" > "$R/logs/stage-route.txt"
python3 "$T/qa20/mkqa.py" "$R/qa" --sr1 "$R/sr1.json" > "$R/logs/mkqa.txt"
mkdir -p "$R/pkgtree/dc/qa"
cp "$R"/qa/* "$R/pkgtree/dc/qa/"
[ ! -e "$R/pkgtree/dc/warp.txt" ]
(cd "$T" && LAYOUT=standard TITLE="QA23-Dedup-$ARM" PRODUCT=T0004 bash mkgdi.sh "$O/re4dc-game.elf" "$R/pkgtree" "$R/gdemu") > "$R/logs/mkgdi.txt" 2>&1
for profile in loader standard;do
    python3 "$T/disc_lint.py" --profile "$profile" "$R/gdemu/disc.gdi" > "$R/logs/disc-lint-$profile.txt"
done
(cd "$R/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin) > "$R/DISC-SHA256SUMS.txt"
printf 'PRIVATE_QA_STAGED arm=%s source=af09f0a2 programme=%s\n' "$ARM" "$LABEL"
printf 'Pending memory/look/runtime gates; no publication or console acceptance.\n'
