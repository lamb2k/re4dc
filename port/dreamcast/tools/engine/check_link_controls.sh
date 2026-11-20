#!/bin/bash
# check_link_controls.sh: the link check's own proof (lane eng-svc4; check_link.py, engine/game/allowed_original.txt).
#
#   check_link_controls.sh <image OUT dir> [extra service symbol]
#
# <image OUT dir> is a built E1 image (engine/game: make OUT=<dir>, so <dir>/e1.map exists; the objects are reused).
#   1. today's image against the allowed list: FAIL (the original service units still linked) -> <dir>/link-waive.txt
#   2. the same image with today's service functions waived: PASS
#   3. control: the image relinked with ONE more original service function kept (-Wl,-u, default At_box_sphere_ck,
#      an at_sub.cpp predicate the image does not link today), checked with the same waive list: must FAIL and name it
#   4. control: an allowed list without the player units: must FAIL (behaviour is not allowed by default)
# Exit status 0 when every line ends as it must. The kos environment must be set (kos-env.sh) for step 3.
set -u
OUT=$(cd "${1:?image OUT dir}" && pwd)
SYM=${2:-At_box_sphere_ck}
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
GAME=$ROOT/port/dreamcast/engine/game
CL="python3 $HERE/check_link.py"
LIST=$GAME/allowed_original.txt
status=0
row() {   # row <name> <must> <rc> <detail>
    local got=PASS
    [ "$3" -eq 1 ] && got=FAIL
    [ "$3" -gt 1 ] && got="ERROR(rc $3)"
    local ok="$got (as it must)"
    [ "$got" = "$2" ] || { ok="$got (WRONG: must $2)"; status=1; }
    echo "| $1 | $2 | $ok | $4 |"
}
echo "| Check | Must | Result | Detail |"
echo "|---|---|---|---|"
$CL "$OUT/e1.map" --allowed "$LIST" --write-waive "$OUT/link-waive.txt" --json "$OUT/link.json" > "$OUT/link.txt"; rc=$?
row "today's image" FAIL $rc "$(head -1 "$OUT/link.txt" | sed 's/^check_link: [^:]*: //')"
$CL "$OUT/e1.map" --allowed "$LIST" --waive "$OUT/link-waive.txt" > "$OUT/link-waived.txt"; rc=$?
row "today's image, today's service functions waived" PASS $rc "$(head -1 "$OUT/link-waived.txt" | sed 's/^check_link: [^:]*: //')"
# 3. one more service function linked: a hard-linked copy of the objects, relinked with -u
C=$OUT-ctl
rm -rf "$C"
cp -al "$OUT" "$C"
rm -f "$C/e1.elf" "$C/e1.map"
W=$(make -s -C "$GAME" OUT="$C" -p -n 2>/dev/null | sed -n 's/^WRAPS := //p' | head -1)
if make -s -C "$GAME" OUT="$C" WRAPS="$W -Wl,-u,_$SYM" > "$C/ctl-make.log" 2>&1; then
    $CL "$C/e1.map" --allowed "$LIST" --waive "$OUT/link-waive.txt" > "$C/link.txt"; rc=$?
    row "control: $SYM linked as well" FAIL $rc "$(head -1 "$C/link.txt" | sed 's/^check_link: [^:]*: //'); $(grep -o "[^ ]*: 1 functions.*$SYM.*" "$C/link.txt" | head -1)"
else
    row "control: $SYM linked as well" FAIL 0 "relink failed: $C/ctl-make.log"
fi
# 4. the allowed list without the player group
grep -v -E "^game/(player|pl_class|pl_body|pl_sub|pl_leon|pl_dmg|pl_push|pl_knife|pl_event|pl_debug) " "$LIST" > "$C/allowed-noplayer.txt"
$CL "$OUT/e1.map" --allowed "$C/allowed-noplayer.txt" --waive "$OUT/link-waive.txt" > "$C/link-noplayer.txt"; rc=$?
row "control: player units not on the list" FAIL $rc "$(head -1 "$C/link-noplayer.txt" | sed 's/^check_link: [^:]*: //')"
exit $status
