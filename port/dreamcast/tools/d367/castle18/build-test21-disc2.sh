#!/bin/bash
# Current release line plus the castle chapter line, for fresh Disc 2 programs.
# Usage: LP=c21a K=/absolute/logs bash build-test21-disc2.sh mW
# Private data is never copied into the source tree. See discsets/README.txt.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export T=${T:-$(cd "$HERE/../../../../.." && pwd)}
export K=${K:?Set K to this build's log directory}
export LP=${LP:?Set a fresh LP label}
source "$T/port/dreamcast/tools/d367/rr/recipe.conf"
PE2=${PE2:-/root/re4data/private/ps2enemy-ch2-20261016}
PE3=${PE3:-/root/re4data/private/ps2enemy-ch34-20261018/PE3}
PE4=${PE4:-/root/re4data/private/ps2enemy-ch34-20261018/PE4}
eval "$(sed -n '/^CH4REC=/p' "$T/port/dreamcast/tools/d367/ch4found/ch4-build.sh")"
export CH2="$CH2 $CH4REC DISC_SET=1"
mkdir -p "$K"
printf '%s\n' "$CH2" > "$K/chapter-disc2-knobs.txt"
bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" "$@"