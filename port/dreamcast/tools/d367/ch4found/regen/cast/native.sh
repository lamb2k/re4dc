#!/bin/bash
# ch4regen: ps2_cast_native.sh over member dirs (as /c/tmp/c4n2.sh did). usage: c4r-native.sh <tools tree root> <dir>...
# Host check dir is lane-local (pvr.h stub copied from the ch2regen lane, sha 4b0a2036).
set -euo pipefail
TREE=$1; shift
export PS2CAST_HOSTCHECK=/root/probe/lanes-20261018/ch4regen/host-check
mkdir -p "$PS2CAST_HOSTCHECK/host/dc"
[ -f "$PS2CAST_HOSTCHECK/host/dc/pvr.h" ] || cp /root/probe/lanes-20261017r/ch2regen/ps2cast/host-check2/host/dc/pvr.h "$PS2CAST_HOSTCHECK/host/dc/pvr.h"
for d in "$@"; do
  log="$d.native.log"
  PS2CAST_HOST_WORKSPACE_KB=512 bash "$TREE/port/dreamcast/tools/ps2_cast_native.sh" "$d" > "$log" 2>&1 || true
  echo "$(basename "$d") pass=$(grep -cE '^PASS' "$log" || true) $(tail -1 "$log" | cut -c1-120)"
done
