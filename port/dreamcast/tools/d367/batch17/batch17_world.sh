#!/bin/bash
# batch17_world.sh <src dir> <out dir> [cell mm] [groups] [--spatial]   (WSL; lane batch17, 2026-10-16)
# LOSSLESS batching of a room's unreduced PS2 world (no vertex ladder): the world32 batching steps only.
#   1. ps2_world_batch.py: merge consecutive meshlets of one part / cluster / level that sit in the same <cell mm> cell,
#      up to 256 corners (strips copied byte for byte, nothing restripified);
#   2. ps2_strip_groups.py: <groups> strip groups per meshlet again (the source's groups do not survive the merge);
#   3. verify_groups.py: every level's strips (full vertex records, order inside each strip) equal the source's;
#   --spatial: 4. ps2_world_spatial_batch.py --cell-mm 32000 (whole static opaque parts of one 32 m cell and material
#      become one room-space part; positions/UVs requantized <= 2 mm: NOT bit-identical; changes the R4PW/ids, so the
#      set is six files with a padded level 0, world32 packaging).
# Output: <out dir>/ps2-wv5.re4mesh + ps2-wv5.r4sg (+ ps2-world.r4pw copied for the lost-part check; with --spatial the
# six files), report.json. Without --spatial the level-5 files must not be larger than level 0 (WORLD_VERT falls back).
# Then run tools/d367/lostpart/lostpart_gate.sh (required: 0 flagged) before staging.
# src dir: ps2-world.{re4mesh,r4pw,ids,r4sg} (+ append.json for --spatial: the baked live-object placements).
set -euo pipefail
S=${1:?src}; O=${2:?out}; C=${3:-4000}; G=${4:-4}; SP=${5:-}
here=$(cd "$(dirname "$0")" && pwd); T=$here/../..
W=$(mktemp -d); trap 'rm -rf $W' EXIT
mkdir -p "$O"
python3 $T/ps2_world_batch.py "$S/ps2-world.re4mesh" $W/flat.re4mesh --sidecar "$S/ps2-world.r4pw" --cell-mm $C \
  --max-vertices 256 --max-bytes 4000000 --report "$O/batch.json" > $W/batch.log
python3 $T/ps2_strip_groups.py $W/flat.re4mesh "$S/ps2-world.r4pw" $W/g.re4mesh $W/g.r4sg --groups $G --report "$O/groups.json" > $W/sg.log
python3 $here/verify_groups.py "$S/ps2-world.re4mesh" $W/g.re4mesh $T | tee "$O/verify.log"
if [ "$SP" = --spatial ]; then
  python3 $T/ps2_world_spatial_batch.py $W/g.re4mesh "$S/ps2-world.r4pw" "$S/ps2-world.ids" $W/probe --cell-mm 32000 \
    --max-bytes 4000000 --source-groups $W/g.r4sg --gated-manifest "$S/append.json" > $W/probe.log
  need=$(python3 -c "import json;b=json.load(open('$W/probe/report.json'))['bytes_out'];print((b+31)//32*32)")
  head -c $(stat -c %s $W/probe/ps2-wv5.r4sg) /dev/zero > $W/cap.r4sg
  python3 $T/ps2_world_spatial_batch.py $W/g.re4mesh "$S/ps2-world.r4pw" "$S/ps2-world.ids" $W/sp --cell-mm 32000 \
    --max-bytes $need --source-groups $W/cap.r4sg --gated-manifest "$S/append.json" > $W/sp.log
  cp $W/sp/ps2-world.re4mesh $W/sp/ps2-world.r4pw $W/sp/ps2-world.ids $W/sp/ps2-world.r4sg $W/sp/ps2-wv5.re4mesh \
     $W/sp/ps2-wv5.r4sg "$O/"; cp $W/sp/report.json "$O/report.json"
else
  [ $(stat -c %s $W/g.re4mesh) -le $(stat -c %s "$S/ps2-world.re4mesh") ] || { echo "level 5 mesh larger than level 0" >&2; exit 1; }
  [ $(stat -c %s $W/g.r4sg) -le $(stat -c %s "$S/ps2-world.r4sg") ] || { echo "level 5 groups larger than level 0's" >&2; exit 1; }
  cp $W/g.re4mesh "$O/ps2-wv5.re4mesh"; cp $W/g.r4sg "$O/ps2-wv5.r4sg"; cp "$S/ps2-world.r4pw" "$O/"
fi
(cd "$O" && sha256sum ps2-* > SHA256SUMS)
echo "batch17_world: $(python3 -c "import json;b=json.load(open('$O/batch.json'));print('meshlets',b['meshlets_in'],'->',b['meshlets_out'])") cell $C mm, $G groups${SP:+, spatial 32 m} -> $O"
