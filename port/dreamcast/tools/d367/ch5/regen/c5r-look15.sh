set -uo pipefail
cd /root/work/re4-dreamcast
git fetch -q origin wip/ch4regen-20261018 lane/geodrop17 2>&1 | tail -1
B=origin/wip/ch4regen-20261018
git log --oneline -6 $B
git ls-tree -r --name-only $B -- port/dreamcast/tools/d367/ch4found/regen/cast | head -40
git show $B:port/dreamcast/tools/d367/ch4found/regen/cast/README.md 2>/dev/null | head -80
ls /root/probe/lanes-20261016/cast16
