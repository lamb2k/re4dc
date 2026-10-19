#!/bin/bash
# Test18 only: existing CH2REC executable plus the user-approved boss18g50 data.
# Build with ch2-build.sh; this stages the same measured full+g50 registries.
# Usage: ch2-gigante-g50.sh LABEL OUT.json --base CHAPTER_FIXTURE --base-label ARM [t11-fix pairs...]
# Selects data last; T15REC, CH2REC and the frozen Test17 data line stay unchanged.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
if [ "$#" -lt 6 ] || [ $(( $# % 2 )) -ne 0 ]; then
  echo 'usage: ch2-gigante-g50.sh LABEL OUT.json --base CHAPTER_FIXTURE --base-label ARM [pairs...]' >&2
  exit 2
fi
has_base=0
has_label=0
for arg in "$@"; do
  [ "$arg" != --base ] || has_base=1
  [ "$arg" != --base-label ] || has_label=1
done
[ "$has_base" = 1 ] && [ "$has_label" = 1 ] || { echo 'an explicit qualified chapter base and label are required' >&2; exit 2; }
exec python3 "$HERE/../test11/t11-fix.py" "$@" --data boss18g50
