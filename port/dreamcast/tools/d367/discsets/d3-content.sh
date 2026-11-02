#!/bin/bash
# d3-content.sh <out tree>  (WSL; lane world-ch5, 2026-11-02): the Disc 3 (island, chapter 5) content tree, the island
# counterpart of recipe.conf D2_CASTLE_TREE. Only island-owned files; discsets/disc3_fixture.py lays it over the Disc 1
# candidate tree and discsets/mkdisc3.py prunes the village and castle rooms. Later rows win (cp over earlier rows).
# Sources (private, never committed; C: mirrors in re4-assets-private):
#   ch5regen-20261018/files      the 33 island rooms r300-r330: st3 room archives, rel/st3_0..3, evd, dc/movie (12),
#                                dc/native/r3xx PS2 worlds, island enemy archives em1d em1e em1f em32 em36 em39 em3a em3d,
#                                loose PS2 textures dc/tex, motion keys dc/mot, dc/resident.bin (island lists)
#   ch5regen-20261018/paks       tex-ch5e (the island pack; disc3_fixture.py takes its island-only keys)
#   island18-resident-20261018   resident.bin: the 10-18 union (1371 island records + every base / core record)
#   island18-r333-route-streams  bgm/aica_str.dat: CH5F41 island streams + r333 (needs AICA_STR_ENT_MAX >= its count)
#   island18-r300-sound          r300.dar + bio4midi.dat (island BGM0 tracks)
#   island18-room-sound          em36.drs + st3/r30f.dar (sound range only)
#   island18-r317-sound          st3/r317.dar (sound range only)
#   island18-u3sound             em32.drs (U-3: u3large motion body + sound fit; program MOTION_LARGE_CLIPS=1)
#   island18-u3large/prepared    dc/mot keys of em32 (cold clips)
#   island18-krauser-triplets    em39.drs (Krauser hot set: 8 DRS bytes over ch5regen)
#   island18-r317-movies         dc/movie/r317s00..s14.seq (Krauser knife QTE)
# Not in this tree yet (final chapter r331-r333, lane stress16b/final16 data): see docs/lanes/world-ch5.md.
set -euo pipefail
OUT=${1:?out tree}
PA=${PA:-/mnt/c/Game Dev/Emulators/re4-assets-private}
REGEN=${REGEN:-/root/probe/lanes-20261018/ch5regen/out/files}
[ -d "$REGEN" ] || REGEN="$PA/ch5regen-20261018/files"
I=/root/re4data/private
rm -rf "${OUT:?}"; mkdir -p "$OUT"
cp -a "$REGEN"/. "$OUT"/
put() { mkdir -p "$(dirname "$OUT/$2")"; rm -f "$OUT/$2"; cp "$1" "$OUT/$2"; }
src() { if [ -e "$I/$1" ]; then echo "$I/$1"; else echo "$PA/$1"; fi; }
put "$(src island18-resident-20261018)/resident.bin" dc/resident.bin
put "$(src island18-r333-route-streams-20261018)/bgm/aica_str.dat" bgm/aica_str.dat
put "$(src island18-r300-sound-20261018)/r300.dar" st3/r300.dar
put "$(src island18-r300-sound-20261018)/bio4midi.dat" bgm/bio4midi.dat
put "$(src island18-room-sound-20261018)/em/em36.drs" em/em36.drs
put "$(src island18-room-sound-20261018)/st3/r30f.dar" st3/r30f.dar
put "$(src island18-r317-sound-20261018)/r317.dar" st3/r317.dar
put "$(src island18-u3sound-20261018)/em32.drs" em/em32.drs
for f in "$(src island18-u3large-20261018)"/prepared/mot/*.fcv; do put "$f" "dc/mot/$(basename "$f")"; done
put "$(src island18-krauser-triplets-20261018)/em39.drs" em/em39.drs
for d in "$(src island18-r317-movies-20261018)"/r317s*; do put "$d/$(basename "$d").seq" "dc/movie/$(basename "$d").seq"; done
put "$PA/ch5regen-20261018/paks/tex-ch5e-d5986c3e.pak" dc/tex.pak
(cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
echo "d3-content: $(wc -l < "$OUT/SHA256SUMS") files, $(du -sm "$OUT" | cut -f1) MB, SHA256SUMS $(sha256sum < "$OUT/SHA256SUMS" | cut -c1-16)"
