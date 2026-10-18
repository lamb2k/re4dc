#!/bin/bash
# Windows python cannot follow WSL symlinks: make the cast16 / ps2cast-inputs shims real directories (lane-local scaffolding).
set -euo pipefail
L=/root/probe/lanes-20261018/ch4regen
O=/root/probe/lanes-20261016/cast16
mkdir -p "$O"
for d in tree c4m; do
  if [ -d "$L/cast16/$d" ]; then rm -rf "${L:?}/cast16/${d:?}"; fi
done
git -C "$L/tree" worktree prune
add() { if [ ! -d "$O/$1" ]; then git -C "$L/tree" worktree add -q --detach "$O/$1" "$2"; git -C "$O/$1" submodule update --init -q || true; fi; echo "$1 $(git -C "$O/$1" log -1 --format='%h %cI')"; }
add tree 710cfa49
add c4m origin/lane/ch4found16
for d in conv conv3 conv4; do
  if [ -d "$L/cast16/$d" ] && [ ! -e "$O/$d" ]; then mv "$L/cast16/$d" "$O/$d"; fi
  mkdir -p "$O/$d"
done
rmdir "$L/cast16" 2>/dev/null || true
ln -sfn "$O" "$L/cast16-link"
I=/root/probe/lanes/ps2cast/inputs
if [ -L "$I" ]; then rm "$I"; fi
mkdir -p "$I"; cp -n "$L"/ps2cast-inputs/*.drs "$I"/
ls -la "$O"; ls "$I" | wc -l
