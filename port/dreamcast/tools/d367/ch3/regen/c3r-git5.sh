set -euo pipefail
cd /root/probe/lanes-20261018/ch3regen/git
f=port/dreamcast/tools/aica_banks.py
git for-each-ref --format='%(refname)' | while read -r r; do
  b=$(git rev-parse -q --verify "$r:$f" 2>/dev/null) || continue
  echo "$b $(git log -1 --format=%ct "$r") $r"
done | sort -k1,1 -u | sort -k2n | while read -r b ts r; do
  echo "$(date -d @$ts +%m%d-%H%M) ${b:0:10} $r :: $(git cat-file -p $b | grep -E '^CAPS|^FILTER_VERSION|4000' | head -3 | tr '\n' ' ' | cut -c1-160)"
done
