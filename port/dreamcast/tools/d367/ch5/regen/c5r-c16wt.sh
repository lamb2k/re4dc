#!/bin/bash
# ch5regen: cast16 island replay worktrees (recorded tool states), lane-local.
#  t5   = 04ef5558 (conv5 ps2_cast + specs, committed 10-16 23:35 right after the final conv5 pack)
#  ch5t = lane/ch5found16 d334422c (tip at c5w.sh 21:23) + cherry-pick 2f4a731e (game tree for --tree)
#  c5m  = t15/int 0d64dbf6 (tip at k9wt.sh 07:51) merged with lane/ch5found16 865c67d7 (r315 pack, conv6 --tree)
#  t6   = df054fec (land18: conv6 boss tools + specs)
set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
C=$L/c16
mkdir -p "$C"/conv5 "$C"/conv6
add() { if [ ! -d "$C/$1" ]; then git -C "$L/tree" worktree add -q --detach "$C/$1" "$2"; git -C "$C/$1" submodule update --init -q || true; fi; echo "$1 $(git -C "$C/$1" log -1 --format='%h %cI')"; }
add t5 04ef5558
add t6 df054fec
add ch5t d334422c
if ! git -C "$C/ch5t" log -1 --format=%s | grep -q "em16 type 11"; then
  git -C "$C/ch5t" -c user.name=lamb2k -c user.email=nansenlamb1@gmail.com cherry-pick 2f4a731e >/dev/null 2>&1 && echo picked || { git -C "$C/ch5t" cherry-pick --abort; echo PICKFAIL; }
fi
add c5m 0d64dbf6
if ! git -C "$C/c5m" log -1 --format=%s | grep -q "^Merge lane/ch5found16"; then
  git -C "$C/c5m" -c user.name=lamb2k -c user.email=nansenlamb1@gmail.com merge -q --no-edit 865c67d7 -m "Merge lane/ch5found16 (865c67d7) into cast16 island check tree" 2>&1 | tail -3 || true
  git -C "$C/c5m" status --short | grep -v '^??' | head
fi
git -C "$C/c5m" log --oneline -2
