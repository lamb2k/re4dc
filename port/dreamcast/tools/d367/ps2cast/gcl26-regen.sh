#!/bin/bash
# gcl26-regen.sh <final disc tree> <out store dir>   (WSL; lane gcleft26 2026-10-26, no-GameCube-assets rule)
# Rebuilds data set gcl26 from a release disc's FINAL files (fp_iso.py extract of the candidate's track03, i.e. after every
# other set composed): the Ganado archives em11..em17 with every GameCube BIN member that has a PS2 BIN at the same ARC
# rebuilt with the PS2 geometry (ps2_ganado_bins.py), and dc/tex.pak with the Ganado EFF pictures (03d1e9a5 195b4634
# 41e0ece4) and the core.das entry-25 pictures (89f1808c c703f665) as PS2 pixels under their keys (em_eff_pics.py).
# Inputs: GC emNN.drs (/root/probe/lanes/ps2cast/inputs), PS2 BIO4DAT.AFS emNN.dat / core.dat and GC etc/core.das in
# $GCL26_SRC (default /root/re4data/private/gcl26-src). gcl26 must stage after every set that writes these paths
# (t11-fix.py AFTER rows); regenerate it whenever such a set changes.
set -euo pipefail
X=${1:?final disc tree}; O=${2:?out store}
H=$(cd "$(dirname "$0")" && pwd)
I=${GCL26_GC:-/root/probe/lanes/ps2cast/inputs}
S=${GCL26_SRC:-/root/re4data/private/gcl26-src}
[ ! -e "$O" ] || { echo "gcl26-regen: $O exists" >&2; exit 1; }
mkdir -p "$O/em" "$O/report"
for em in em11 em12 em13 em15 em16 em17; do
  python3 "$H/ps2_ganado_bins.py" build --release "$X/em/$em.drs" --gc "$I/$em.drs" --ps2 "$S/$em.dat" \
    --out "$O/em/$em.drs" --json "$O/report/$em.json" > "$O/report/$em.log" &
done
wait
grep -h TOTAL "$O"/report/*.log
python3 "$H/em_eff_pics.py" "$X/dc/tex.pak" "$O/pak" \
  --pair "$I/em12.drs" "$S/em12.dat" 03d1e9a5-755b258f:5 195b4634-d9ddabb6:6 41e0ece4-322c9fcc:32 \
  --pair "$S/gc-core.das" "$S/core.dat" 89f1808c-21b55a55:288 c703f665-e374813c:306t | tail -n 1
mkdir -p "$O/dc"; mv "$O/pak/dc/tex.pak" "$O/dc/tex.pak"; mv "$O/pak/pak-derived.json" "$O/pak-derived.json"
mv "$O/pak/report.json" "$O/report/pics.json"; rmdir "$O/pak/dc" "$O/pak"
(cd "$O" && find em dc -type f | sort | xargs sha256sum > SHA256SUMS.txt)
echo "gcl26-regen: $(wc -l < "$O/SHA256SUMS.txt") files in $O"
