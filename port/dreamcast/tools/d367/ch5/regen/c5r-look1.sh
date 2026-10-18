set -euo pipefail
cd /root/work/re4-dreamcast
git fetch -q origin wip/ch4regen-20261018 wip/ch3regen-20261018 wip/ch2regen-20261017 2>&1 | tail -2
git ls-tree -r --name-only FETCH_HEAD -- tools/d367/ch4found/regen | head -50
echo ---
for b in ch4regen-20261018 ch3regen-20261018; do
  git ls-tree -r --name-only origin/wip/$b | grep -E 'regen/' | head -60; echo ===
done
git show origin/wip/ch4regen-20261018:tools/d367/ch4found/regen/README.md 2>/dev/null | head -150 || true
ls /root/work/lanes 2>/dev/null | head
