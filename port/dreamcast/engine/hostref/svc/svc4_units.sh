#!/bin/bash
# svc4_units.sh [unit...]: which original functions of the round-4 units the native re4ref link still keeps (lane
# eng-svc4) and the native functions of the split units (svc4_split.txt). Reads build/hostref/native/re4ref.map with tools/engine/check_link.py: every code section kept from the
# original objects of the named units (default: svc.mk's SVC4_UNITS) is listed; 0 kept = the unit is fully native in
# re4ref. Exit status 1 when any is kept; 2 when the check cannot be made (lane eng-e1e: a missing or unreadable map,
# no unit list, the link checker failing, or a map in which no original function at all is found, which is not a
# native re4ref link). Control: MAP=/nonexistent svc4_units.sh must exit 2, never report "0 original functions kept".
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
MAP=${MAP:-$ROOT/build/hostref/native/re4ref.map}
if [ ! -s "$MAP" ]; then echo "svc4_units: no map at $MAP (build make native first): no check made" >&2; exit 2; fi
UNITS=${*:-$(make -s -C "$HERE/.." -p -n native 2>/dev/null | sed -n 's/^SVC4_UNITS := //p' | head -1)}
if [ -z "$UNITS" ]; then echo "svc4_units: no unit list (svc.mk SVC4_UNITS not found): no check made" >&2; exit 2; fi
L=$(mktemp); O=$(mktemp)
echo "## other: every other unit is not checked here" > "$L"
echo "* *" >> "$L"
for u in $UNITS; do echo "!$u *" >> "$L"; done
# the split units' native functions (svc4_split.txt), unless units were named
if [ -z "$*" ]; then
    grep -v '^#' "$HERE/svc4_split.txt" | while read -r u pats; do [ -n "$u" ] && echo "!$u $pats" >> "$L"; done
    UNITS="$UNITS (+ split: $(grep -v '^#' "$HERE/svc4_split.txt" | awk '{print $1}' | tr '\n' ' '))"
fi
python3 "$ROOT/port/dreamcast/tools/engine/check_link.py" "$MAP" --allowed "$L" \
    --orig-pattern '/(plain/game|native/weak4?|svc/ref)/([^/]+)\.o$' --quiet --list > "$O"
cl=$?
rm -f "$L"
if [ $cl -gt 1 ]; then echo "svc4_units: check_link.py failed (exit $cl) on $MAP: no check made" >&2; rm -f "$O"; exit 2; fi
# every original function the map keeps is listed with its group ("other") or SERVICE: none at all = not this build's map
if ! grep -q -E " (other|SERVICE) " "$O"; then
    echo "svc4_units: no original function found in $MAP (not a native re4ref map?): no check made" >&2; rm -f "$O"; exit 2
fi
grep " SERVICE " "$O" \
    | awk -v units="$UNITS" 'BEGIN {print "units: " units} {n++; print "  kept: " $0} END {print (n ? n : 0) " original functions kept"; exit (n > 0)}'
rc=$?
rm -f "$O"
exit $rc
