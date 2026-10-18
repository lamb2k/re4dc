set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
find "$L/extra" -name '*c34*.pak' | while read -r f; do echo "$f $(sha256sum "$f" | cut -c1-8)"; done
git -C "$L/git" cat-file -t 035c58e2
git -C "$L/git" show 035c58e2:port/dreamcast/tools/d367/vram/vq16-r204.txt | head -4
