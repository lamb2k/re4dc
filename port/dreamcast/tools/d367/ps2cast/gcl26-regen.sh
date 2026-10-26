#!/bin/bash
# gcl26-regen.sh <final disc tree> <out store dir>   (WSL; lane gcleft26 2026-10-26, no-GameCube-assets rule)
# Rebuilds data set gcl26 from a release disc's FINAL files (fp_iso.py extract of the candidate's track03, i.e. after every
# other set composed): the Ganado archives em11..em17 with every GameCube BIN member that has a PS2 BIN at the same ARC
# rebuilt with the PS2 geometry (ps2_ganado_bins.py). The pictures are set gcl26p (em_eff_pics.py,
# its RECIPE.txt has the command).
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
(cd "$O" && find em -type f | sort | xargs sha256sum > SHA256SUMS.txt)
echo "gcl26-regen: $(wc -l < "$O/SHA256SUMS.txt") files in $O"
