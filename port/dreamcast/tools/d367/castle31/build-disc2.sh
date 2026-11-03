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
  case " $CH2 " in *" DISC_SET=1 "*) ;; *) export CH2="$CH2 DISC_SET=1" ;; esac   # rr recipe RR_DISC2=1 already has it
else
  PE2=${PE2:-/root/re4data/private/ps2enemy-ch2-20261016}
  PE3=${PE3:-/root/re4data/private/ps2enemy-ch34-20261018/PE3}
  PE4=${PE4:-/root/re4data/private/ps2enemy-ch34-20261018/PE4}
  eval "$(sed -n '/^CH4REC=/p' "$T/port/dreamcast/tools/d367/ch4found/ch4-build.sh")"
  # SS11_ROOM_EVICT=1: the Disc 2 load comes from the title (SS heap 11 preload pass); without the evict the title's
  # 1.08 MB dynamic set stays beside r200's preload and 6 entries are evicted (castle31 10-26, c31-d2fast).
  case " $CH2 " in *" DISC_SET=1 "*) ;; *) CH2="$CH2 DISC_SET=1" ;; esac
  # EFM_PS2_CUT=2 (lane castle-gca-26 11-01): + the castle debris rows the PS2 deleted (r202 0x5a / 0x5b); the release
  # recipe's EFM_PS2_CUT=1 earlier on the line, this later value wins.
  # D2_EXTRA (lane world-ch31 11-02): Disc 2 only knobs on trial (e.g. ALIVE_CAP_DEFER_GOTO_R207=1: held r207 hall
  # Ganados keep their walk-upstairs command, CASTLE_DEFERRED_GOTO_CONTROL_AUDIT_20261019.md). Empty = as before.
  export CH2="$CH2 $CH4REC WEAPON_WEP05=1 SS11_ROOM_EVICT=1 EFM_PS2_CUT=2${D2_EXTRA:+ $D2_EXTRA}"
fi
export CH2
mkdir -p "$K"
printf '%s\n' "$CH2" > "$K/disc-knobs-$LP.txt"
bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" "$@"
