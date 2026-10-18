set -uo pipefail
cd /root/work/re4-dreamcast
B=origin/wip/ch3regen-20261018:port/dreamcast/tools/d367/ch3/regen
git show $B/c3r-aica.sh
echo =====
git show $B/aica_search4k.py | head -80
echo =====
git ls-tree -r --name-only origin/wip/ch2regen-20261017 | grep -i 'regen' | head -40
ls /root/probe/lanes-20261018/ch3regen/aica /root/probe/lanes-20261018/ch3regen/aica-cache | head
