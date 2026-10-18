set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261018/ch4regen
for v in c3 b47; do
  cp $S/cx_room_dependencies.py $L/cxtree-$v/port/dreamcast/tools/d367/cx_room_dependencies.py
  O=$L/cxdeps-$v; rm -rf "${O:?}"
  python3 $L/cxtree-$v/port/dreamcast/tools/d367/cx_room_dependencies.py --iso /root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso --fixture-index $S/cx-roomindex.json --out $O > $O.log 2>&1 || { echo "$v FAIL"; tail -3 $O.log; }
  echo "== $v"
  grep 'dependencies/prepared' $S/cx-targets.tsv | while IFS=$'\t' read src s z h lane p; do
    f=$O/prepared/${src#*/dependencies/prepared/}
    if [ -f "$f" ]; then [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$s" ] && echo "exact $p" || echo "diff $p"; else echo "absent $p"; fi
  done | sort | uniq -c | awk '{print $2}' | sort | uniq -c
done
