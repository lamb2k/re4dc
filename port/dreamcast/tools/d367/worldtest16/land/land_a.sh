#!/bin/bash
# land_a.sh (WSL): A landing branch without the B tool import: 5197fa04 + the KNOWN_ISSUES split (e7062d8a), merged
# with origin/t15/int. Worktree /root/probe/worldtest16-20261016/landA (branch lane/worldtest16-land).
set -u
cd /root/probe/worldtest16-20261016/tree
git worktree remove --force /root/probe/worldtest16-20261016/landA 2>/dev/null
git branch -D lane/worldtest16-land 2>/dev/null
git worktree add -q -b lane/worldtest16-land /root/probe/worldtest16-20261016/landA 5197fa04
cd /root/probe/worldtest16-20261016/landA
G="git -c user.name=lamb2k -c user.email=nansenlamb1@gmail.com"
$G cherry-pick e7062d8a >/dev/null && echo "picked"
$G merge --no-edit origin/t15/int -m "lane/worldtest16: merge origin t15/int $(git rev-parse --short origin/t15/int)" 2>&1 | tail -5
git status --short | head
git diff --name-only --diff-filter=U
