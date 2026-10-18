#!/bin/bash
# ch5regen: ps2_cast_native.sh over member dirs (as c5n3.sh / k10n2.sh did). usage: c5r-c16nat.sh <t5|t6> <dir>...
set -euo pipefail
C=/root/probe/lanes-20261018/ch5regen/c16
TREE=$C/$1; shift
export PS2CAST_HOSTCHECK=$C/host-check
mkdir -p "$PS2CAST_HOSTCHECK/host/dc"
[ -f "$PS2CAST_HOSTCHECK/host/dc/pvr.h" ] || cp /root/probe/lanes-20261017r/ch2regen/ps2cast/host-check2/host/dc/pvr.h "$PS2CAST_HOSTCHECK/host/dc/pvr.h"
grep -c strip64 "$TREE/port/dreamcast/tools/ps2_cast_native.sh" || true
for d in "$@"; do
  log="$d.native.log"
  PS2CAST_HOST_WORKSPACE_KB=512 bash "$TREE/port/dreamcast/tools/ps2_cast_native.sh" "$d" > "$log" 2>&1 || true
  echo "$(basename "$d") pass=$(grep -cE '^PASS' "$log" || true) $(grep -E 'FAIL|Error' "$log" | head -1 | cut -c1-120)"
done
