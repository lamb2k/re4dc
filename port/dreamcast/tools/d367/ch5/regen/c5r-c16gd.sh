#!/bin/bash
# ch5regen: geodrop17 worktree (origin lane/geodrop17 7f13fa14) for the r320 heli package replay.
set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
[ -d "$L/c16/gd" ] || git -C "$L/tree" worktree add -q --detach "$L/c16/gd" 7f13fa14
git -C "$L/c16/gd" submodule update --init -q || true
git -C "$L/c16/gd" log -1 --format="%h %s"
