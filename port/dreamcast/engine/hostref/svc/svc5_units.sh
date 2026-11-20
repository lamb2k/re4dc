#!/bin/bash
# svc5_units.sh [unit...]: which original functions of the round-5 units the native re4ref link still keeps (lane
# eng-svc5). Reads build/hostref/native/re4ref.map (MAP=<map> to read another) with tools/engine/check_link.py; every
# code section kept from the original objects of the named units is listed: game units (math_sub, sub2, pl_cloth, ...,
# from plain/game or native/weak4), the SDK's C math (sdk_mtx, sdk_vec, ... from plain/sdk) and the game's fdlibm (from
# plain/libm). Default units: svc.mk's SVC5_UNITS. 0 kept = the unit is fully native in re4ref.
# Fails closed: a missing or unreadable map, a map that names none of the units' objects at all (the link was not
# made from this build), or no unit to check, each exit 2. Exit 1 when any function is kept.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
MAP=${MAP:-$ROOT/build/hostref/native/re4ref.map}
UNITS=${*:-$(make -s -C "$HERE/.." -p -n native 2>/dev/null | sed -n 's/^SVC5_UNITS := //p' | head -1)}
[ -n "$UNITS" ] || { echo "svc5_units: no unit to check"; exit 2; }
[ -r "$MAP" ] && [ -s "$MAP" ] || { echo "svc5_units: no map at $MAP"; exit 2; }
grep -q "^Linker script and memory map" "$MAP" || { echo "svc5_units: $MAP is not a GNU ld map"; exit 2; }
L=$(mktemp)
trap 'rm -f "$L"' EXIT
echo "## other: every other unit is not checked here" > "$L"
echo "* *" >> "$L"
for u in $UNITS; do echo "!$u *" >> "$L"; done
# the map must name the objects these units come from (native or original): a link of another build fails closed
seen=0
for u in $UNITS; do
    grep -qE "/(plain/game|native/weak4?|native/svc5|plain/sdk|plain/libm)/$u\.o|/native/svc5/" "$MAP" && seen=1
done
[ $seen -eq 1 ] || { echo "svc5_units: the map names none of the units' objects ($UNITS)"; exit 2; }
python3 "$ROOT/port/dreamcast/tools/engine/check_link.py" "$MAP" --allowed "$L" \
    --orig-pattern '/(plain/game|native/weak4?|svc/ref|plain/sdk|plain/libm|native/weak5)/([^/]+)\.o$' --quiet --list > "$L.out"
rc=$?
[ $rc -le 1 ] || { echo "svc5_units: check_link failed ($rc)"; cat "$L.out"; rm -f "$L.out"; exit 2; }
grep " SERVICE " "$L.out" | awk -v units="$UNITS" 'BEGIN {print "units: " units} {n++; print "  kept: " $0} END {print (n ? n : 0) " original functions kept"; exit (n > 0)}'
rc=$?
rm -f "$L.out"
exit $rc
