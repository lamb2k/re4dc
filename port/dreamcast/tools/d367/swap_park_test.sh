#!/bin/bash
# swap_park_test.sh <out dir>  (SS_CERT host gate): builds swap_park_test.cpp against the real game/actor_lifetime.inc
# and game/actor_swap_park.inc with ASan/UBSan in three variants (knob off: the gap reproduction only; knob on with two
# role words / 32-bit BlobMask; knob on with the widened three words / 64-bit mask and the registry room rows) and runs
# each. Exits 1 on any failure.
set -euo pipefail
OUT=$1
HERE=$(cd "$(dirname "$0")" && pwd); GAME=$HERE/../../game
mkdir -p "$OUT"
# 4th variant (PS2_CAST_MERCHANT, 2026-10-14): RE4DC_NMR_PARK_UNRELOCATED=1 (an archive adopted but not relocated
# when the screen opens is republished, not revoked).
for v in "0 0 0" "1 0 0" "1 1 0" "1 1 1"; do
  set -- $v
  bin=$OUT/swap_park_test-cert$1-wide$2-unrel$3
  g++ -std=gnu++20 -O1 -g -Wall -Wextra -Wno-unused-function -Wno-misleading-indentation -Wno-missing-field-initializers -fsanitize=address,undefined -fno-sanitize-recover=all \
      -DRE4DC_SS_CERT=$1 -DTEST_WIDE=$2 -DRE4DC_NMR_PARK_UNRELOCATED=$3 -I"$GAME" -I"$GAME/platform/include" "$HERE/swap_park_test.cpp" -o "$bin"
  "$bin"
done
echo "SS_CERT HOST GATES PASS"
