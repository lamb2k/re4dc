#!/bin/bash
# scenario19/disc.sh <program label> <scenario file> <out dir> [extra warp line...]  (WSL; lane scenario19, 2026-10-19)
# A scenario disc: the Test 18/19 release data (payload root + data line D18, as the Test 18 release package) with this
# program and its own overlays, plus two fixtures under /dc/:
#   warp.txt     the scenario (warp rig, DBG_WARP=1 programs): the room, Leon's spot, flags, rig kills
#   quality.txt  speed=screen (the speed display on from boot, as R + START turns it on)
# Standard GD-ROM layout (mkgdi.sh LAYOUT=standard), checked by disc_lint.py (standard profile).
# Output <out dir>/gdemu (disc.gdi track01.bin track02.raw track03.bin) + gdemu-sha256.txt, on ext4.
# Extra arguments are appended to warp.txt as lines (check twins: `squeeze 49152 0`).
set -euo pipefail
LAB=${1:?program label}; SCN=${2:?scenario file}; D=${3:?out dir}; shift 3
HERE=$(cd "$(dirname "$0")" && pwd)
T=$HERE/..
O=/root/probe/lanes/route/out-$LAB
export RE4DC_PAYLOAD_ROOT=${RE4DC_PAYLOAD_ROOT:-/root/re4payload/t164-20261018}
export PKG_SRC=$RE4DC_PAYLOAD_ROOT/tree
export B18G50D=${B18G50D:-/root/probe/lanes-20261019/rel18/b18g50}
DATA=${SCN_DATA:-fsh,ch2,cast16,r108p,pak17,zr17,zr17b,v101,stump17,res17g,trans17,res17b,res18f,boss18g50r,garr18h}
[ -s "$O/re4dc-game.elf" ] || { echo "no build $O" >&2; exit 1; }
[ ! -s "$O/missing.txt" ] || { echo "$LAB has missing symbols" >&2; exit 1; }
grep -q 'DBG_WARP=1' "$O/candidate.txt" || { echo "$LAB is not a DBG_WARP=1 program" >&2; exit 1; }
case "$D" in /root/work/lanes/*|/root/probe/*) ;; *) echo "out dir must be under /root/work/lanes or /root/probe" >&2; exit 1;; esac
rm -rf "${D:?}"; mkdir -p "$D/fix" "$D/harness/programs/candidate-route$LAB"
# t11-fix's payload base takes route overlays from <harness>/programs/candidate-route<label>: this program's own.
for o in "$O"/*.ovl; do ln "$o" "$D/harness/programs/candidate-route$LAB/"; done
RE4DC_HARNESS=$D/harness python3 "$T/test11/t11-fix.py" "$LAB" "$D/pkg.json" --base payload --data "$DATA" > "$D/fix.log"
PKG_K=$D python3 "$T/test8/t8-pkgtree.py" "$LAB" "$D/pkg.json" > "$D/pkgtree.txt"
tail -1 "$D/pkgtree.txt" | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 "$D/pkgtree.txt"; exit 1; }
# every overlay on the disc is this program's (fixture overlay trap, 805fb9cd)
for o in "$O"/*.ovl; do cmp -s "$o" "$D/pkgtree/dc/$(basename "$o")" || { echo "overlay mismatch $(basename "$o")" >&2; exit 1; }; done
{ tr -d '\r' < "$SCN"; for l in "$@"; do echo "$l"; done; } | grep -v '^#' > "$D/fix/warp.txt"
printf 'speed=screen\n' > "$D/fix/quality.txt"
[ "$(stat -c %s "$D/fix/warp.txt")" -lt 2048 ] || { echo "warp.txt too long" >&2; exit 1; }
TITLE=${SCN_TITLE:-RE4DC SCENARIO (NOT THE GAME)}
(cd "$T" && LAYOUT=standard TITLE="$TITLE" PRODUCT=T0019 bash mkgdi.sh "$O/re4dc-game.elf" "$D/pkgtree" "$D/gdemu" "$D/fix" | tail -2)
rm -f "$D/gdemu/IP.BIN"
(cd "$D/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin) > "$D/gdemu-sha256.txt"
rm -rf "${D:?}/pkgtree" "${D:?}/harness"
cat "$D/gdemu-sha256.txt"
echo "DISC $D/gdemu"
