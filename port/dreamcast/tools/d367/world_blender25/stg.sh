#!/bin/bash
# world-blender25: master Flycast bases per arm from the rr candidate 7250e5c6 + the arm's r101 (and r103) world files.
# usage: stg.sh <arm> <r101 final dir or -> [r103 dir or -]
set -euo pipefail
ARM=${1:?}; D101=${2:?}; D103=${3:--}
TR=/root/work/lanes/world-blender25; X=/root/work/lanes/world-blender25-scratch
F=$TR/port/dreamcast/tools/d367/fullplay; ROUTE=/root/probe/lanes/route
EVU=/mnt/c/Flycast-Evidence/re4-dreamcast/world-blender25; mkdir -p "$EVU/fixtures" "$EVU/_discs"
CAND="/mnt/c/Game Dev/Emulators/RE4DC-RR/cand-7250e5c6/gdemu/track03.bin"
S=$X/rel-$ARM; rm -rf "${S:?}"; mkdir -p "$S"
python3 "$F/fp_iso.py" extract "$CAND" "$S/tree" --manifest "$S/manifest.json" --ipbin "$S/IP.BIN" | tail -1
d=$S/tree/dc/native
[ "$D101" = - ] || cp --remove-destination $D101/ps2-world.re4mesh $D101/ps2-world.r4sg $d/r101/
[ "$D103" = - ] || cp --remove-destination $D103/ps2-world.re4mesh $d/r103/
sha256sum $d/r101/ps2-world.re4mesh $d/r101/ps2-world.r4sg $d/r103/ps2-world.re4mesh | cut -c1-16
FM=$X/fp_master_$ARM.sh
sed "s#^here=.*#here=$F#" $F/fp_master.sh > $FM
python3 - "$FM" <<'PY'
import sys
p=sys.argv[1]; s=open(p).read()
a="ALLOW=(--allow 'dc/warp\.txt'"
assert s.count(a)==1
s=s.replace(a,"ALLOW=(--allow 'dc/native/r10[13]/ps2-world\.(re4mesh|r4sg)' "+a[7:])
open(p,'w').write(s)
PY
grep -q "r10\[13\]" $FM; echo "# arm $ARM" >> $FM
rm -rf "${EVU:?}/_discs/$ARM"
bash $FM "$S/tree" "$S/manifest.json" "$S/IP.BIN" "$EVU/_discs/$ARM" $ROUTE/out-fpwb25${ARM}W 2>&1 | tail -1 | cut -c1-200
cp $ROUTE/out-fpwb25${ARM}W/syms.txt "$EVU/fixtures/syms-$ARM.txt"
rm -rf "${S:?}"
T=$TR/port/dreamcast/tools/d367
for n in hwcross hwfarm; do tr -d '\r' < $T/logiclod20/$n-warp.txt > "$EVU/fixtures/$n.txt"; done
for n in hwcross hwfarm; do { grep -v '^alivelog' "$EVU/fixtures/$n.txt"; echo "freeze 600"; } > "$EVU/fixtures/still-$n.txt"; done
tr -d '\r' < $F/segments/bell-trg-warp.txt > "$EVU/fixtures/bell.txt"
tr -d '\r' < $F/segments/door103-warp.txt > "$EVU/fixtures/door103-warp.txt"
echo STAGED $ARM
