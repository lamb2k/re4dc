#!/bin/bash
# lane bakeall: step B (WSL) for one room converted by conv_room.sh: every sidecar the runtime keys to the package,
# regenerated so the baked room takes no fallback (WORLD_BAKE=1 certificate row maps the shipped, rekeyed R4PW to the
# converter's own R4PW crc, the policy source crc every sidecar below is bound to, as the release lineage does).
#   post_room.sh <room> <conv dir> <set dir> <lineage R4PW (pre-rekey)> <shipped R4PW (rekeyed)> <tex.pak> <shipped r4tc or "">
#                <shipped room.r4rc> <R4SG 0|1 (only where the release ships one)>
# Writes <set>/dc/native/<room>/{ps2-world.re4mesh,r4pw,ids,r4sg[,r4tc]} and room.r4rc, and appends <set>/cert-rows.txt
# (one provenance_certificates row) and <set>/sizes.tsv.
set -euo pipefail
R=${1:?}; C=${2:?}; SET=${3:?}; LIN=${4:?}; SHIP=${5:?}; PAK=${6:?}; HAS_TC=${7:?}; RC=${8:?}; SG=${9:?}
T=/root/work/lanes/bakeall/port/dreamcast/tools
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
D="$SET/dc/native/$R"; W="$SET/work/$R"
mkdir -p "$D" "$W/own/$R" "$W/rc0" "$W/rc1" "$W/tc/$R" "$W/tco"
# 1 strip groups only where the release ships an R4SG (r109, sg109: --preserve-order); sidecar crc = own R4PW crc
if [ "$SG" = 1 ]; then
    python3 "$T/ps2_strip_groups.py" "$C/ps2-world.re4mesh" "$C/ps2-world.r4pw" "$D/ps2-world.re4mesh" "$D/ps2-world.r4sg" \
        --preserve-order --report "$W/sg.json" > "$W/sg.log"
else
    cp "$C/ps2-world.re4mesh" "$D/ps2-world.re4mesh"
fi
# 2 the shipped texture keys on the R4PW (geometry, placements and policy unchanged)
python3 "$T/d367/ps2world/r4pw_rekey.py" "$C/ps2-world.r4pw" "$LIN" "$SHIP" "$D/ps2-world.r4pw" > "$W/rekey.log"
# 3 ids: the converter's own (bound to its own R4PW crc, the certified policy source)
cp "$C/ps2-world.ids" "$D/ps2-world.ids"
# 4 room file: GRID + OCCL from the baked world (own R4PW + ids, strip-grouped mesh), then SCDD for that mesh
cp "$D/ps2-world.re4mesh" "$C/ps2-world.r4pw" "$C/ps2-world.ids" "$W/own/$R/"
python3 - "$RC" <<'PY' > "$W/rc-sections.txt"
import struct, sys
d = open(sys.argv[1], 'rb').read(); n = struct.unpack_from('<I', d, 12)[0]
print(' '.join(d[64 + 32 * i:68 + 32 * i].decode() for i in range(n)))
PY
if grep -q OCCL "$W/rc-sections.txt"; then
    python3 "$T/enginebake/room_compile.py" --iso "$ISO" --out "$W/rc0" --world "$W/own" "$R" > "$W/rc.log" 2>&1
else
    python3 "$T/enginebake/room_compile.py" --iso "$ISO" --out "$W/rc0" "$R" > "$W/rc.log" 2>&1
fi
if grep -q SCDD "$W/rc-sections.txt"; then
    python3 "$T/d367/scenery19/scdd_compile.py" "$W/own" "$W/rc0" "$W/rc1" "$R" > "$W/scdd.log"
    cp "$W/rc1/$R/room.r4rc" "$D/room.r4rc"
else
    cp "$W/rc0/$R/room.r4rc" "$D/room.r4rc"
fi
# 5 transparency classes from the shipped texture keys, bound to the policy source crc
# (a part whose texture key the shipped package classified keeps the shipped class, so the release look holds; a key the
# shipped package lacks gets tr_classify's class from the shipped pack)
if [ -n "$HAS_TC" ]; then
    cp "$D/ps2-world.re4mesh" "$D/ps2-world.r4pw" "$W/tc/$R/"
    python3 "$T/d367/tr_classify.py" "$W/tc/$R" --pak "$PAK" --out "$W/tco" > "$W/tc.log"
    python3 - "$W/tco/$R/ps2-world.r4tc" "$C/ps2-world.r4pw" "$D/ps2-world.r4tc" "$HAS_TC" "$SHIP" "$D/ps2-world.r4pw" \
        "$W/tc-keys.txt" <<'PY'
import struct, sys, zlib, collections
new, own, out, stc, spw, npw, rep = sys.argv[1:8]
def keys(p):
    d = open(p, 'rb').read(); n = struct.unpack_from('<I', d, 12)[0]
    return [struct.unpack_from('<IIHH', d, 32 + 16 * i) for i in range(n)]
t = bytearray(open(new, 'rb').read()); s = open(stc, 'rb').read()
ship = collections.defaultdict(set)
for i, k in enumerate(keys(spw)):
    ship[k].add(s[24 + i])
kept = fresh = 0
for i, k in enumerate(keys(npw)):
    if len(ship.get(k, ())) == 1:
        t[24 + i] = next(iter(ship[k])); kept += 1
    else:
        fresh += 1
n = struct.unpack_from('<I', t, 12)[0]
struct.pack_into('<I', t, 16, struct.unpack_from('<I', open(own, 'rb').read(), 20)[0])
struct.pack_into('<I', t, 20, zlib.crc32(bytes(t[24:24 + n])))
open(out, 'wb').write(t)
open(rep, 'w').write('parts %d: shipped class kept %d, classified fresh %d\n' % (n, kept, fresh))
PY
fi
# 6 the certificate row (provenance_certificates field order) and sizes
python3 - "$R" "$D" "$C/ps2-world.r4pw" "$SET" "$RC" <<'PY'
import struct, sys
room, d, own, s, rc = sys.argv[1:6]
w = open(d + '/ps2-world.r4pw', 'rb').read(); m = open(d + '/ps2-world.re4mesh', 'rb').read()
def fnv(b):
    h = 2166136261
    for x in b: h = ((h ^ x) * 16777619) & 0xffffffff
    return h
_, _, npl, nparts, nmesh, crc = struct.unpack_from('<4s5I', w, 0)
src = struct.unpack_from('<I', open(own, 'rb').read(), 20)[0]
mcrc = struct.unpack_from('<I', m, 12)[0]
open(s + '/cert-rows.txt', 'a').write('{0x%sU,%dU,%dU,%dU,%dU,0x%08xU,0x%08xU,0x%08xU,%dU,0x%08xU},\n' % (
    room[1:], len(w), npl, nparts, nmesh, crc, fnv(w), mcrc, len(m), src))
import os
open(s + '/sizes.tsv', 'a').write('%s\tmesh=%d\tr4pw=%d\tr4sg=%d\troom.r4rc=%d (shipped %d)\n' % (
    room, len(m), len(w), os.path.getsize(d + '/ps2-world.r4sg') if os.path.exists(d + '/ps2-world.r4sg') else 0, os.path.getsize(d + '/room.r4rc'), os.path.getsize(rc)))
PY
echo "$R done"
