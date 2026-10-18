set -euo pipefail
cd /root/probe/lanes-20261018/ch3regen/git
for f in port/dreamcast/tools/prepare_native_ui.py port/dreamcast/tools/le_mirror.py port/dreamcast/tools/convert_tpl.py; do
 for c in $(git log --all --format=%h -- $f | head -60); do
   s=$(git show $c:$f 2>/dev/null | sha256sum | cut -c1-12) || continue
   echo "$f $c $s $(git log -1 --format=%ci $c)"
 done
done | grep -E 'c3d2f4cd6f00|b47c37112cf4' || echo NOHASHMATCH
git show origin/wip/ch2regen-20261017:port/dreamcast/tools/d367/ch2/regen/recovered/ch22w-tools/room.sh
