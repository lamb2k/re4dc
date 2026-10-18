set -euo pipefail
# c3r-commit.sh MSG: copy the lane scripts into lane/ch3regen, commit, push wip/ch3regen-20261018
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
W=$L/lane
if [ ! -d "$W" ]; then
  git -C "$L/git" worktree add -q -b lane/ch3regen "$W" origin/dreamcast-port
fi
D=$W/port/dreamcast/tools/d367/ch3/regen; mkdir -p "$D"
cp "$S"/c3r*.sh "$S"/c3r*.py "$D"/
cp "$L/aica_search4k.py" "$D/aica_search4k.py"
[ -e "$S/README.md" ] && cp "$S/README.md" "$D/README.md"
cd "$W"
git add port/dreamcast/tools/d367/ch3/regen
git -c user.name="$(git -C /root/work/re4-dreamcast config user.name)" -c user.email="$(git -C /root/work/re4-dreamcast config user.email)" \
  commit -q -m "$1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0161knP9yvavohe6o4n2fpoV" || echo "nothing to commit"
git push -q origin HEAD:refs/heads/wip/ch3regen-20261018 2>&1 | tail -2
git log --oneline -1
