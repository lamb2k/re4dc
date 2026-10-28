#!/bin/bash
# fullplay.sh <release-zip-or-gdemu-dir> [--label L] [--evidence DIR] [--only seg,seg] [--jobs N] [--keep-discs]
# (Git Bash on the Windows host.) The full-play release gate: boots the actual release disc, plays the route
# title -> New Game -> r100 ... chapter 2-1 end in parallel Flycast segments, and exits non-zero with a one-page
# REPORT.md on any crash, hang, HALT, MISSING, misalignment, dropped free, GameCube fallback, texture or allocation
# failure, log overrun, s30 movie drop, memory trend on repeated visits or boot/title regression.
# See port/dreamcast/tools/d367/README.md "Full-play gate" and fp_gate.py.
set -u
[ $# -ge 1 ] || { sed -n '2,7p' "$0"; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) ;;
  *) echo "fullplay.sh: run it from Git Bash on the Windows host (Flycast is a Windows program)" >&2; exit 2 ;;
esac
src=$1; shift
case "$src" in /*|[A-Za-z]:*) ;; *) src="$PWD/$src" ;; esac
exec python "$(cygpath -w "$here/fp_gate.py")" "$(cygpath -w "$src")" "$@"
