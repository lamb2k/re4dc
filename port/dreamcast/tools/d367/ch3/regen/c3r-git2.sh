set -euo pipefail
cd /root/work/re4-dreamcast
ls -la orig/G4BE08/ 2>&1 | head; ls /root/re4data 2>&1 | head
git log --oneline -3 origin/dreamcast-port
for f in port/dreamcast/tools/d367/cx_room_fixtures.py port/dreamcast/tools/prepare_native_ui.py port/dreamcast/tools/le_mirror.py; do
  echo "== $f"; git log --format='%h %ad %s' --date=iso origin/dreamcast-port -- $f | head -8
done
git cat-file -t 90606dcf 2>&1 || true
git worktree list | head -30
