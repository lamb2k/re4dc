#!/usr/bin/env bash
set -euo pipefail
B=/root/work/lanes/audits23-land
M=/root/work/lanes/audits23-readme-mirror
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
[ ! -e "$M" ]
git -C "$B" fetch origin dreamcast-port
git -C "$B" worktree add -b wip/audits23-readme-20261023 "$M" origin/dreamcast-port
OLD=$(git -C "$M" rev-parse HEAD)
python3 - "$M" "$E" <<'PY'
import pathlib,sys
p,e=map(pathlib.Path,sys.argv[1:]);r=p/'README.md';s=r.read_text();anchor='## Coming soon: Test 23';start=s.index(anchor);end=s.index('\n## ',start+len(anchor));b=(e/'landing-bullets.txt').read_text();assert 'Effect and puzzle safety' not in s;r.write_text(s[:end]+'\n'+b+s[end:])
PY
git -C "$M" diff --check
git -C "$M" add README.md
git -C "$M" commit -m 'Mark the qualified effect, puzzle and dam safety fixes in Test 23 notes'
git -C "$M" fetch origin dreamcast-port
[ "$(git -C "$M" rev-parse origin/dreamcast-port)" = "$OLD" ]
git -C "$M" merge-base --is-ancestor origin/dreamcast-port HEAD
git -C "$M" push -u origin HEAD:refs/heads/wip/audits23-readme-20261023
git -C "$M" push origin HEAD:refs/heads/dreamcast-port
git -C "$M" rev-parse HEAD > "$E/readme-mirror-source.txt"