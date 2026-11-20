#!/bin/bash
# svc4_units.sh [unit...]: which original functions of the round-4 units the native re4ref link still keeps (lane
# eng-svc4). Reads build/hostref/native/re4ref.map with tools/engine/check_link.py: every code section kept from the
# original objects of the named units (default: svc.mk's SVC4_UNITS) is listed; 0 kept = the unit is fully native in
# re4ref. Exit status 1 when any is kept.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
MAP=${MAP:-$ROOT/build/hostref/native/re4ref.map}
UNITS=${*:-$(make -s -C "$HERE/.." -p -n native 2>/dev/null | sed -n 's/^SVC4_UNITS := //p' | head -1)}
L=$(mktemp)
echo "## other: every other unit is not checked here" > "$L"
echo "* *" >> "$L"
for u in $UNITS; do echo "!$u *" >> "$L"; done
python3 "$ROOT/port/dreamcast/tools/engine/check_link.py" "$MAP" --allowed "$L" \
    --orig-pattern '/(plain/game|native/weak4?|svc/ref)/([^/]+)\.o$' --quiet --list | grep " SERVICE " \
    | awk -v units="$UNITS" 'BEGIN {print "units: " units} {n++; print "  kept: " $0} END {print (n ? n : 0) " original functions kept"; exit (n > 0)}'
rc=$?
rm -f "$L"
exit $rc
