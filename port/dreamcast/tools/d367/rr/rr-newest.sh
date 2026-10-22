#!/bin/bash
# rr-newest.sh <dir regex> <file name> <out>   (WSL; lane rr)
# Writes the newest committed copy of tools/d367/<dir>/<file> on origin/t15/int (the one whose last commit is newest:
# directory names do not sort, test122 is 12.2) to <out> and prints its repo path. Example:
#   rr-newest.sh 'test[^/]*' README-package.txt /tmp/README.txt   -> port/dreamcast/tools/d367/test21/README-package.txt
set -euo pipefail
RX=${1:?dir regex}; F=${2:?file}; OUT=${3:?out}
MAIN=/root/work/re4-dreamcast; REF=origin/t15/int
D=port/dreamcast/tools/d367
best=; bt=0
while read -r p; do
  t=$(git -C "$MAIN" log -1 --format=%ct "$REF" -- "$p")
  if [ "${t:-0}" -gt "$bt" ]; then bt=$t; best=$p; fi
done < <(git -C "$MAIN" ls-tree -r --name-only "$REF" -- "$D" | grep -E "^$D/$RX/$F\$")
[ -n "$best" ] || { echo "rr-newest: no $D/$RX/$F on $REF" >&2; exit 1; }
git -C "$MAIN" show "$REF:$best" > "$OUT"
echo "$best"
