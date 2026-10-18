set -euo pipefail
cd /root/work/re4-dreamcast
f=port/dreamcast/tools/d367/cx_room_fixtures.py
for b in $(git branch -r --format='%(refname:short)'); do
  if git cat-file -e "$b:$f" 2>/dev/null; then echo "$b $(git rev-parse --short $b) $(git log -1 --format=%h $b -- $f) $(git rev-parse --short $b:$f)"; fi
done | sort -k4 | head -60
