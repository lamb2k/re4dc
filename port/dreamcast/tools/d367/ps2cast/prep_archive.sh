#!/bin/bash
# prep_archive.sh <name> <GC LE-mirror .drs> <release .drs> <work dir>   (lane ps2cast2, 2026-10-14)
# Texture-prepares one enemy archive for the registry owner path (R4NREF descriptors; ATX_INFO why=6 otherwise) the
# way the release's own prepared archives are made, then carries the release's converted AICA sound banks over:
#   1. prepare_native_ui.py: the archive's GC textures -> <work>/tex-<name> (.re4tex packages; reports which are
#      already on the release disc, loose or in dc/tex.pak);
#   2. prepare_enemy_motions.py --textures --keep-motion-resident (the archive must be in SMALL / GANADO /
#      MOTION_SMALL; a textures-only contract);
#   3. aica_transplant.py: the release archive's AICA-converted type-2 bank parts copied bank by bank into the
#      prepared archive (refuses on any shape / MRAM-part mismatch).
# Output <work>/<name>.drs (disc path em/<name>.drs). Example (PS2_CAST_MERCHANT):
#   prep_archive.sh em18 /root/probe/lanes/ps2cast/inputs/em18.drs <release tree>/em/em18.drs work/em18prep
set -euo pipefail
N=$1; SRC=$2; REL=$3; W=$4
HERE=$(cd "$(dirname "$0")" && pwd); T=$HERE/../..
rm -rf "$W"; mkdir -p "$W/src/em"; cd "$W"
cp "$SRC" src/em/$N.drs
echo em/$N.drs > files.txt
python3 $T/prepare_native_ui.py src files.txt tex-$N > tex.log 2>&1 || { tail tex.log; exit 1; }
echo "textures: $(ls tex-$N | wc -l) packages"
python3 $T/prepare_enemy_motions.py --source src/em/$N.drs --output prep-$N --textures tex-$N --keep-motion-resident > prep.log 2>&1 || { tail -20 prep.log; exit 1; }
python3 $HERE/aica_transplant.py "$REL" - prep-$N/$N.drs $N.drs
RD=$(dirname "$(dirname "$REL")")/dc
python3 - "$W/tex-$N" "$RD" <<'P'
import os, struct, sys
tex, rd = sys.argv[1], sys.argv[2]
pak = open(rd + '/tex.pak', 'rb').read(8 << 20) if os.path.exists(rd + '/tex.pak') else b''
miss = []
for f in sorted(x for x in os.listdir(tex) if x.endswith('.re4tex')):
    k = f[:-7]; c, v = [int(x, 16) for x in k.split('-')]
    if not os.path.exists('%s/tex/%s/%s' % (rd, k[0], f)) and struct.pack('<II', c, v) not in pak: miss.append(f)
print('textures not on the release disc:', len(miss), ' '.join(miss))
P
sha256sum $N.drs
