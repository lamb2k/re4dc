set -euo pipefail
cd /root/work/re4-dreamcast
for b in ch3regen-20261018 ch4regen-20261018 ch2regen-20261017; do
  echo "=== $b"
  git grep -n -e '\.assets' -e 'bc4523fb' -e 'run_rooms' -e 'venv' origin/wip/$b -- 'port/dreamcast/tools/d367/ch*' | head -20 || true
done
echo === c3r-tex1
git show origin/wip/ch3regen-20261018:port/dreamcast/tools/d367/ch3/regen/c3r-tex1.sh | head -60
echo === cxrun
git show origin/wip/ch4regen-20261018:port/dreamcast/tools/d367/ch4found/regen/cxfix/cxrun.py | head -80
ls /root/probe/lanes-20261018/ch4regen/cxtree-b47 | head; ls /root/probe/lanes-20261018/ch4regen/cxtree-b47/.assets 2>/dev/null | head
