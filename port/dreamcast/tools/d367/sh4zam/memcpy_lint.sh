#!/bin/bash
# memcpy_lint.sh [--update]  (lane sh4zam-adopt 2026-10-15; user rule: the port copies with SH4ZAM's shz_memcpy /
# shz_memmove / shz_memset*, never newlib's memcpy). Fails when game or port code gains a raw memcpy / memmove call
# that is not in the baseline (memcpy_lint.baseline: the calls that existed when the rule was adopted; the
# GAME_SHZ_MEM link wraps cover those until they are converted). Counts per file, so moving a call within a file passes.
# REPORT ONLY (coordinator 10-15): exits 0 unless MEMCPY_LINT_STRICT=1, until shz_memcpy beats newlib here.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../../.." && pwd)
B=$here/memcpy_lint.baseline
cur=$(cd "$root" && grep -rnwE 'memcpy|memmove' src port/dreamcast/game port/dreamcast/room \
        --include=*.c --include=*.cpp --include=*.cc --include=*.h --include=*.hpp 2>/dev/null \
      | grep -v third_party | grep -vE '^[^:]+:[0-9]+:\s*(//|\*|/\*)' | grep -E '\b(memcpy|memmove)\s*\(' \
      | grep -v '__real_\|__wrap_' | cut -d: -f1 | sort | uniq -c | awk '{print $2" "$1}')
if [ "${1:-}" = --update ]; then echo "$cur" > "$B"; echo "baseline: $(echo "$cur" | awk '{s+=$2} END {print s}') calls in $(echo "$cur" | wc -l) files"; exit 0; fi
fail=0
while read -r f n; do
  [ -z "$f" ] && continue
  b=$(awk -v f="$f" '$1==f{print $2}' "$B"); b=${b:-0}
  [ "$n" -gt "$b" ] && { echo "memcpy_lint: $f has $n raw memcpy/memmove calls (baseline $b): use shz_memcpy / shz_memmove"; fail=1; }
done <<< "$cur"
[ $fail = 0 ] && echo "memcpy_lint: PASS" || { echo "memcpy_lint: REPORT ONLY (coordinator 10-15: not failing until shz_memcpy wins)"; [ "${MEMCPY_LINT_STRICT:-0}" = 1 ] && exit 1; exit 0; }
