#!/usr/bin/env bash
set -euo pipefail
FROM=/root/work/lanes/stat-bytes23-takeover
TO=/root/work/lanes/stat-bytes23-complete
[ ! -e "$TO" ]
git -C "$FROM" worktree add -b wip/stat-bytes23-complete-20261023 "$TO" 66f098ed842d05cca196a1ef3facb9249ee88eed
python3 - "$TO/port/dreamcast/game/vmu_context.cpp" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]);s=p.read_text()
old='if(re4vmu::ammo_visible(pG->pl_type,pPL->stat,weapon)){'
assert s.count(old)==1
new='// The portable VMU helper takes the original big-endian routine word.\n    // Normalize the native four-byte union under the same audit switch as the HUD.\n    if(re4vmu::ammo_visible(pG->pl_type,STAT_BE(pPL->stat),weapon)){'
p.write_text(s.replace(old,new))
PY
git -C "$TO" diff --check
git -C "$TO" add port/dreamcast/game/vmu_context.cpp
git -C "$TO" commit -m 'Include the VMU routine-word consumer in the stat byte-order audit'
git -C "$TO" push -u origin HEAD:refs/heads/wip/stat-bytes23-complete-20261023
git -C "$TO" rev-parse HEAD
