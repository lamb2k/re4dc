#!/bin/bash
# ch4regen: cast16-ch4 replay scaffolding. Worktrees for the recorded tool states + lane-local path shims.
set -euo pipefail
L=/root/probe/lanes-20261018/ch4regen
C=$L/cast16
REPO=$L/tree
mkdir -p "$C"/conv "$C"/conv3 "$C"/conv4
add() { # add <dir> <commit>
  if [ ! -d "$C/$1" ]; then git -C "$REPO" worktree add -q --detach "$C/$1" "$2"; git -C "$C/$1" submodule update --init -q || true; fi
  echo "$1 $(git -C "$C/$1" log -1 --format='%h %cI')"
}
add tree 710cfa49
add c4m origin/lane/ch4found16
# shims (lane-local scaffolding; listed in the report)
[ -e /root/probe/lanes-20261016/cast16 ] || ln -s "$C" /root/probe/lanes-20261016/cast16
mkdir -p /root/probe/lanes/ps2cast
[ -e /root/probe/lanes/ps2cast/inputs ] || ln -s "$L/ps2cast-inputs" /root/probe/lanes/ps2cast/inputs
ls -la /root/probe/lanes-20261016/ /root/probe/lanes/ps2cast/
grep -n "INPUTS = \|PS2_ISO\|GC_ISO\|DEFAULT_ISO" "$C/tree/port/dreamcast/tools/ps2_cast.py" | head
