#!/bin/bash
# gen.sh [work dir] [tag]   (WSL; lane world-ch31 11-03, chapter 3-2 GC-ASSET for r20a / r20b, Disc 2 only)
# Builds the Disc 2 data sets cgca32 + cpic32b on top of world-ch32's cw32 / pmcw32 / cpic32 (recipe.conf D2_DATA, after
# them and after cpic27). Inputs: the PS2 USA ISO, pmcw32's room archives, the castle content's r201 Ashley partner.
#   1. objects   ps2_objects.py room on pmcw32's st2/r205 r20a r20b.dar: --etm-empty for the etc models the PS2 version
#                deleted from every ETM (et1400 = the castle torch, as castlegca26 does for r201 / r202; et0c00 = absent
#                from every PS2 ETM, its GC bytes = GC r113 et0c00). Every other byte of the archive is kept.
#   2. partner   ps2cast/ashley_reroom.py make: Ashley's PS2 partner package (dc/native/rNNN/partner.re4nmr, PS2_ASHLEY_ROOMS)
#                for r20a / r20b from the castle r201 package (only the room word and the header crc change), so she
#                draws the PS2 model there instead of the GameCube em/pl01 / pl11 models and pictures.
#   3. pictures  ps2cast/em_eff_pics.py: 5 tex.pak keys as PS2 pixels under the GC key (cpic32b).
#   4. store     mk.py: cgca32 (st2 .dar + the .arc beside it for r205 r209 r20a r20b, the partner packages,
#                provenance.tsv) and cpic32b (dc/tex.pak, pak-derived.json, report.json), RECIPE + SHA256SUMS.
set -euo pipefail
WK=${1:-/root/work/lanes/world-ch31-scratch/gca32}; TAG=${2:-20261103}
H=$(cd "$(dirname "$0")" && pwd); TW=$(cd "$H/../.." && pwd)
ISO=${PS2_ISO:-/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso}
PM=${PMCW32D:-/root/re4data/private/pmcw32-20261102}
CT=${D2_CASTLE_TREE:-/root/re4data/private/castle-d2-j-20261021}
PK=${CPIC27D:-/root/re4data/private/cpic27-20261102}/dc/tex.pak
S1=/root/re4data/private/cgca32-$TAG; S2=/root/re4data/private/cpic32b-$TAG
case "$WK" in /root/work/lanes/world-ch31-scratch/*) rm -rf "${WK:?}";; *) echo "refusing work dir $WK"; exit 1;; esac
mkdir -p "$WK/obj" "$WK/ps2"
python3 "$H/afsx.py" "$ISO" "$WK/ps2" em23.dat r20a.dat r20b.dat
cd "$TW"
# (r203's torch: lane assets-dc's cgca27b, byte-identical to what this step made; D2_DATA carries it before cgca32)
for spec in r205:et1400.bin,et0c00.bin r20a:et1400.bin r20b:et1400.bin,et0c00.bin; do
  r=${spec%%:*}; e=${spec#*:}
  python3 ps2_objects.py room --dar "$PM/st2/$r.dar" --room "$r" --etm "$e" --etm-empty "$e" \
    --out "$WK/obj/$r.dar" --json "$WK/obj/$r.json" > "$WK/obj/$r.log" 2>&1 || { tail -5 "$WK/obj/$r.log"; exit 1; }
  echo "$r: $(tail -1 "$WK/obj/$r.log")"
done
python3 d367/ps2cast/ashley_reroom.py make "$CT/dc/native/r201/partner.re4nmr" "$WK/partner" r20a r20b
python3 d367/ps2cast/em_eff_pics.py "$PK" "$WK/cpic" \
  --pair - "$WK/ps2/em23.dat" 3d9d333a-125fadf1:1 \
  --pair - "$WK/ps2/r20b.dat" e75f4f42-b5f65a4f:108 \
  --pair - "$WK/ps2/r20a.dat" fcb60a5d-e940e957:157 7b86c92d-e0871570:2 db1febac-00a38398:52 | tail -6
for s in "$S1" "$S2"; do case "$s" in /root/re4data/private/cgca32-2*|/root/re4data/private/cpic32b-2*) rm -rf "${s:?}";; *) exit 1;; esac; done
python3 "$H/mk.py" "$S1" "$S2" "$WK" "$PM" "$CT"
for s in "$S1" "$S2"; do (cd "$s" && find . -type f ! -name SHA256SUMS.txt | sort | xargs sha256sum > SHA256SUMS.txt); done
echo "stores: $S1 $S2"
