#!/bin/bash
# build-disc2.sh <arm>...  (WSL; lane castle31, 2026-10-26): the Disc 2 (castle) program on the Test 25 line.
# User 10-26 "Disc 2, one zip": the castle starts on Disc 2 (as on the GameCube); both game discs ship in one game zip.
# Program = rr/recipe.conf CH2 (the release recipe) + CH4REC (ch4found/ch4-build.sh: ROUTE_CH31.., PS2_CH3_ENEMY, castle
# motion/stream knobs) + DISC_SET=1 + WEAPON_WEP05=1 (Broken Butterfly from chapter 3, merchant stock from r202).
# Disc 1's program needs only DISC_SET=1 on top of the release recipe (DISC1=1 below) so it asks for Disc 2 at the 2-3 end.
# Data: mkdisc2-t25.py (Disc 1 tree + castle content + pak union + castle resident). Successor of castle18/build-test21-disc2.sh.
# Usage: LP=<fresh label> K=/abs/logdir [DISC1=1] bash build-disc2.sh rP|rW|mW|rT
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export T=${T:-$(cd "$HERE/../../../../.." && pwd)}
export K=${K:?Set K to the build log directory}
export LP=${LP:?Set a fresh LP label}
source "$T/port/dreamcast/tools/d367/rr/recipe.conf"
if [ "${DISC1:-0}" = 1 ]; then
  export CH2="$CH2 DISC_SET=1"
else
  PE2=${PE2:-/root/re4data/private/ps2enemy-ch2-20261016}
  PE3=${PE3:-/root/re4data/private/ps2enemy-ch34-20261018/PE3}
  PE4=${PE4:-/root/re4data/private/ps2enemy-ch34-20261018/PE4}
  eval "$(sed -n '/^CH4REC=/p' "$T/port/dreamcast/tools/d367/ch4found/ch4-build.sh")"
  # SS11_ROOM_EVICT=1: the Disc 2 load comes from the title (SS heap 11 preload pass); without the evict the title's
  # 1.08 MB dynamic set stays beside r200's preload and 6 entries are evicted (castle31 10-26, c31-d2fast).
  export CH2="$CH2 $CH4REC DISC_SET=1 WEAPON_WEP05=1 SS11_ROOM_EVICT=1"
fi
mkdir -p "$K"
printf '%s\n' "$CH2" > "$K/disc-knobs-$LP.txt"
bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" "$@"
