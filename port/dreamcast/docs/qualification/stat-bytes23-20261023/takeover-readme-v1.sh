#!/usr/bin/env bash
set -euo pipefail
B=/root/work/lanes/stat-bytes23-complete
L=/root/work/lanes/stat-bytes23-readme
[ ! -e "$L" ]
git -C "$B" fetch origin dreamcast-port
git -C "$B" worktree add -b wip/stat-bytes23-readme-20261023 "$L" origin/dreamcast-port
python3 - "$L/README.md" <<'PY'
import pathlib,sys
p=pathlib.Path(sys.argv[1]);s=p.read_text();a='## Coming soon: Test 23';i=s.index(a);end=s.index('\n## ',i+len(a));b='- [x] **Boat weapon display:** boarding the boat shows the harpoon and hides handgun ammunition.\n';assert b not in s;p.write_text(s[:end]+'\n'+b+s[end:])
PY
git -C "$L" diff --check
git -C "$L" add README.md
git -C "$L" commit -m 'README: mark the qualified Test23 boat weapon display fix'
git -C "$L" fetch origin dreamcast-port
git -C "$L" merge-base --is-ancestor origin/dreamcast-port HEAD
git -C "$L" push -u origin HEAD:refs/heads/wip/stat-bytes23-readme-20261023
git -C "$L" push origin HEAD:refs/heads/dreamcast-port
/root/rr/bin/rr.sh status