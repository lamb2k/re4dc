set -euo pipefail
# c3g-fx.sh: armed gate fixtures = t11-fix.py on the c3g_gfix base (--data ch2,cast16, castle --set, git warp).
G=/root/probe/lanes-20261018/ch3gate/gfix2
T=/root/probe/lanes-20261018/ch3gate/tree/port/dreamcast/tools/d367
W=$T/castle/warps
declare -A WP=([r201]=cx-r201-mov [r203]=cx-r203-mov [r204]=cx-r204-mov [r20b]=cx-r20b-mov [r206]=cx-r206-s10 [r20d]=cx-r20d-s20 [r221]=cx-r221-entry [r228]=cx-r228-entry)
for r in r201 r202 r203 r204 r205 r206 r207 r208 r209 r20a r20b r20c r20d r20e r20f r216 r221 r228; do
  w=${WP[$r]:-cx-$r-walk}
  args=()
  while IFS= read -r l; do [ -n "$l" ] && args+=(--set "$l"); done < "$G/$r/set.txt"
  python3 -B "$T/test11/t11-fix.py" c3gmW "$G/$r/cx-$r-g.armed.json" --base "$G/$r/base.json" --base-label c3gmW \
    --data ch2,cast16 "${args[@]}" --warp "$W/$w.txt" 2>&1 | tail -1 | cut -c1-200
done
