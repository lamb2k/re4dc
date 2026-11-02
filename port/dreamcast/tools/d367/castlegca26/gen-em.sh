#!/bin/bash
# gen-em.sh <cgca26 store> <pmcgca26 store> <Disc 1 release tree> <scratch>   (WSL; lane castle-gca-26, 2026-11-01)
# The castle enemy archives and the room motion (Disc 2 only, recipe.conf D2_DATA), after gen-objects.sh:
#   models  ps2cast/ps2_ganado_bins.py on em1b.drs (castle content) and em14.drs (Disc 1 release copy): every GameCube BIN
#           member with a PS2 BIN at the same ARC (BIO4DAT emNN.dat) rebuilt with the PS2 geometry; --cast-tree = the
#           Disc 1 dc/native packages + the castle ones (BINs the native cast acquires by exact bytes are kept);
#   motion  motion/ps2_motion_prepared.py rewrite (+ verify) of em1b.drs (on the models output), em3b.drs and the four
#           cgca26 room archives r201 r202 r204 r208 (every FCV / SEQ member = the PS2 entry of the same slot);
#   stores  cgca26: em/em1b.drs + em/em14.drs + provenance.tsv rows for their models (a model whose bytes the rebuild
#           changed = ps2, an unchanged one = gc); pmcgca26: the motion outputs (em1b, em3b, room archives as the motion
#           proof, graft.json = the room FCV / SEQ entries the rewrite changed) and the new dc/mot keys.
# Inputs: GC + PS2 enemy files in $EMIN (default /root/probe/lanes/ps2cast/inputs: emNN.drs, emNN.dat), PS2 ISO.
set -euo pipefail
S1=${1:?cgca26 store}; S2=${2:?pmcgca26 store}; D1=${3:?Disc 1 tree}; W=${4:?scratch}
H=$(cd "$(dirname "$0")" && pwd); D=$(cd "$H/.." && pwd)
CT=${D2_CASTLE_TREE:-/root/re4data/private/castle-d2-j-20261021}
I=${EMIN:-/root/probe/lanes/ps2cast/inputs}
ISO=${PS2_ISO:-/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso}
rm -rf "${W:?}"; mkdir -p "$W/cast/dc" "$W/em" "$S2/st2" "$S2/em" "$S2/dc/mot" "$S1/em" "$S1/reports" "$S2/reports"
cp -al "$D1/dc/native" "$W/cast/dc/native"; cp -a "$CT/dc/native/." "$W/cast/dc/native/"
python3 "$D/ps2cast/ps2_ganado_bins.py" build --release "$CT/em/em1b.drs" --gc "$I/em1b.drs" --ps2 "$I/em1b.dat" --cast-tree "$W/cast" \
  --out "$W/em/em1b.drs" --json "$S1/reports/em1b-bins.json" > "$S1/reports/em1b-bins.log"
python3 "$D/ps2cast/ps2_ganado_bins.py" build --release "$D1/em/em14.drs" --gc "$I/em14.drs" --ps2 "$I/em14.dat" --cast-tree "$W/cast" \
  --out "$W/em/em14.drs" --json "$S1/reports/em14-bins.json" > "$S1/reports/em14-bins.log"
tail -2 "$S1/reports/em1b-bins.log" | head -1; tail -2 "$S1/reports/em14-bins.log" | head -1
M=$D/motion/ps2_motion_prepared.py
python3 "$M" rewrite "$W/em/em1b.drs" "$ISO" em1b.dat "$W/m/em1b" --mot-dir "$CT/dc/mot" | tail -1
python3 "$M" verify "$W/m/em1b/em/em1b.drs" "$W/em/em1b.drs" "$ISO" em1b.dat "$W/m/em1b/dc/mot" "$CT/dc/mot" | tail -1
python3 "$M" rewrite "$D1/em/em3b.drs" "$ISO" em3b.dat "$W/m/em3b" --mot-dir "$D1/dc/mot" | tail -1
python3 "$M" verify "$W/m/em3b/em/em3b.drs" "$D1/em/em3b.drs" "$ISO" em3b.dat "$W/m/em3b/dc/mot" "$D1/dc/mot" | tail -1
for r in r201 r202 r204 r208; do
  python3 "$M" rewrite "$S1/st2/$r.dar" "$ISO" $r.dat "$W/m/$r" | tail -1
  python3 "$M" verify "$W/m/$r/em/$r.dar" "$S1/st2/$r.dar" "$ISO" $r.dat "$W/m/$r/dc/mot" | tail -1
  cp "$W/m/$r/em/$r.dar" "$S2/st2/$r.dar"
done
cp "$W/m/em1b/em/em1b.drs" "$S2/em/em1b.drs"; cp "$W/m/em1b/em/em1b.drs" "$S1/em/em1b.drs"
cp "$W/m/em3b/em/em3b.drs" "$S2/em/em3b.drs"; cp "$W/em/em14.drs" "$S1/em/em14.drs"
find "$W/m" -path '*/dc/mot/*.fcv' -exec cp {} "$S2/dc/mot/" \;
cp "$W"/m/*/report-*.json "$S2/reports/"
python3 "$H/mkem.py" "$S1" "$S2" "$CT/em/em1b.drs" "$D1/em/em14.drs"
