set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
for f in vq16-c31 vq16-c32 vq16-c33; do
  echo "== $f"; git -C "$L/git" show "origin/lane/castle-1015:port/dreamcast/tools/d367/vram/$f.txt" | grep -c .
  git -C "$L/git" show "origin/lane/castle-1015:port/dreamcast/tools/d367/vram/$f.txt" | grep '^#'
done
git -C "$L/git" show origin/lane/castle-1015:port/dreamcast/tools/d367/vram/vq16-c31.txt | sed -n '3,5p'
