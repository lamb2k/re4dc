#!/bin/bash
# cloth_key_test.sh <out dir>: the cloth service's chain key, (PenCloth, model) (lane eng-cloth1; cloth_key_test.cpp).
# Two builds of the test with the host's g++: the service's key (must PASS) and the control CLOTH_KEY_CONTROL_OLD, the
# old key on the PenCloth alone (must FAIL: the second set-up of a shared PenCloth takes the first model's chain over).
# Exit 0 when both end as they must, 1 otherwise; the table to stdout and <out dir>/cloth_key_test.md.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
mkdir -p "$OUT"
INC="-I$ROOT/include -I$HERE"
echo 0 > "$OUT/.status"
{
echo "| Build | Must | Result | Output |"
echo "|---|---|---|---|"
for b in key control; do
    def=; must=PASS
    [ $b = control ] && { def=-DCLOTH_KEY_CONTROL_OLD; must=FAIL; }
    if ! g++ -std=gnu++17 -fpermissive -w $def $INC "$HERE/cloth_key_test.cpp" -o "$OUT/cloth_key_test-$b" > "$OUT/build-$b.log" 2>&1; then
        echo "| $b | $must | ERROR (build: $OUT/build-$b.log) | |"; echo 1 > "$OUT/.status"; continue
    fi
    got=PASS
    "$OUT/cloth_key_test-$b" > "$OUT/run-$b.txt" 2>&1 || got=FAIL
    ok="$got (as it must)"; [ $got = $must ] || { ok="$got (WRONG: must $must)"; echo 1 > "$OUT/.status"; }
    echo "| $b | $must | $ok | $(tr '\n' ' ' < "$OUT/run-$b.txt") |"
done
} | tee "$OUT/cloth_key_test.md"
exit $(cat "$OUT/.status")
