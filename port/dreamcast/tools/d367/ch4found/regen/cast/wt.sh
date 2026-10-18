#!/bin/bash
# ch4regen: extra recorded tool-state worktrees under the cast16 shim. usage: c4r-wt.sh <name> <commit>
set -euo pipefail
O=/root/probe/lanes-20261016/cast16
if [ ! -d "$O/$1" ]; then git -C /root/probe/lanes-20261018/ch4regen/tree worktree add -q --detach "$O/$1" "$2"; git -C "$O/$1" submodule update --init -q || true; fi
echo "$1 $(git -C "$O/$1" log -1 --format='%h %cI')"
