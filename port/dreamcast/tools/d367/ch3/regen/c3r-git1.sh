set -euo pipefail
cd /root/work/re4-dreamcast
git fetch -q origin 2>/dev/null || true
for b in $(git branch -r --format='%(refname:short)' | grep -i -E 'castle|ch3|t15/int|ch4found16-land4'); do
  echo "== $b $(git rev-parse --short $b)"
  git ls-tree --name-only "$b" port/dreamcast/tools/d367/castle/ 2>/dev/null | tr '\n' ' ' | head -c 1500; echo
done
