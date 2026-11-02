#!/bin/bash
# gen-all.sh <Disc 2 tex.pak (WSL)> <Disc 1 release tree (WSL)> [date tag]   (Git Bash on the Windows host; lane castle-gca-26)
# Regenerates the three Disc 2 data sets of the castle GC-ASSET convert (user 11-01 "Convert in Test 26") from scratch:
#   cgca26     gen-objects.sh: castle room objects r201 r202 r204 r208 (ETM all + room BIN pairs) -> PS2 geometry + pictures
#   cgca26 em  gen-em.sh: em1b / em14 PS2 BIN geometry;  pmcgca26: PS2 motion (em1b, em3b, room FCV / SEQ)
#   sndcgca26  ps2_audio.py banks (PS2 PCM in place) on pmcgca26's room archives + em19, snd28_store.py layout
# Stores under /root/re4data/private/<set>-<tag> (default tag 20261101); copy to re4-assets-private afterwards (README).
set -euo pipefail
PAK=${1:?Disc 2 tex.pak}; D1=${2:?Disc 1 tree}; TAG=${3:-20261101}
H=$(cd "$(dirname "$0")" && pwd)
W() { MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root -- bash "$@"; }
TW=/root/work/lanes/castle-gca-26/port/dreamcast/tools/d367/castlegca26
S1=/root/re4data/private/cgca26-$TAG; S2=/root/re4data/private/pmcgca26-$TAG; S3=/root/re4data/private/sndcgca26-$TAG
W "$TW/step.sh" clean "$S1" "$S2" "$S3"
bash "$H/gen-objects.sh" "$S1" "$PAK" r201:all:22:22 r202:all:1f:1f,2a:2a r204:all:1f:1f,2d:2d r208:all:28:28
W "$TW/gen-em.sh" "$S1" "$S2" "$D1" /root/work/lanes/castle-gca-26-scratch/gen-em
W "$TW/step.sh" snd "$S2" "$S3" "${BASECAT:-/root/work/lanes/castle-disc2-26/rrhome/work/1101-1407-1409ac5e/gca2/catalog/catalog.json}"
W "$TW/step.sh" seal "$S1" "$S2" "$S3"
