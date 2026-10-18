set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
mkdir -p "$L"
if [ ! -d "$L/git" ]; then
  git clone -q --bare /root/work/re4-dreamcast "$L/git"
  git -C "$L/git" remote set-url origin "$(git -C /root/work/re4-dreamcast remote get-url origin)"
fi
cd "$L/git"
git fetch -q /root/work/re4-dreamcast 'refs/remotes/origin/*:refs/remotes/origin/*'
for b in /mnt/c/Game\ Dev/Emulators/re4dc-recovery/gitdig18/*.bundle "/mnt/c/Game Dev/Emulators/re4-cx-ch23-20261013/codex-archive-20261014.bundle"; do
  n=$(basename "$b" .bundle)
  git fetch -q "$b" "+refs/*:refs/dig/$n/*" 2>/dev/null || git bundle list-heads "$b" | while read -r sha ref; do git fetch -q "$b" "$sha" 2>/dev/null && git update-ref "refs/dig/$n/$(echo $sha | cut -c1-8)" "$sha" || true; done
done
f=port/dreamcast/tools/d367/cx_room_fixtures.py
git for-each-ref --format='%(refname)' refs/dig | while read -r r; do
  if git cat-file -e "$r:$f" 2>/dev/null; then echo "$r $(git rev-parse --short $r) blob $(git rev-parse --short $r:$f) $(git log -1 --format=%ci $r)"; fi
done | sort -k4 -u
