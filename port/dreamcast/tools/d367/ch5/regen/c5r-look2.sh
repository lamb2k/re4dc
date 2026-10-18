set -euo pipefail
cd /root/work/re4-dreamcast
git show origin/wip/ch3regen-20261018:port/dreamcast/tools/d367/ch3/regen/README.md
echo =====CH4
B=origin/wip/ch4regen-20261018:port/dreamcast/tools/d367/ch4found/regen
git show $B/cxfix/README.md
echo ====chap4
git show $B/chap4.sh
echo ====paths
git show $B/paths.sh
git log --oneline -8 origin/wip/ch4regen-20261018
git log --oneline -5 origin/wip/ch3regen-20261018
cat /root/re4data/private/cxfix-replay-20261018/README* 2>/dev/null | head -60
