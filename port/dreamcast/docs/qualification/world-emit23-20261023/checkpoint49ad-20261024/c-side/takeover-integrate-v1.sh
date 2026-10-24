#!/usr/bin/env bash
set -euo pipefail
B=/root/work/lanes/stat-bytes23-complete
T=/root/work/lanes/world-emit23-target-R
[ ! -e "$T" ];git -C "$B" fetch origin t15/int
BASE=$(git -C "$B" rev-parse origin/t15/int)
[ "$BASE" = a5e972e44096410253ad93164b84d92e3c22655a ]
git -C "$B" worktree add -b wip/world-emit23-qualify-20261023 "$T" "$BASE"
git -C "$T" merge --no-ff f2b290b285116d0a440aa4557a09acdd7a29c20e -m 'Integrate the reviewed one-frame world census for private qualification'
git -C "$T" push -u origin HEAD:refs/heads/wip/world-emit23-qualify-20261023
SHA=$(git -C "$T" rev-parse HEAD)
python3 - "$BASE" "$SHA" <<'PY'
import sys,json,pathlib
p=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/SOURCE-QUALIFICATION.json')
assert not p.exists();p.write_text(json.dumps({'base':sys.argv[1],'source':sys.argv[2],'census_source':'f2b290b285116d0a440aa4557a09acdd7a29c20e','branch':'wip/world-emit23-qualify-20261023','recipe_changed':False,'cloud_queue_touched':False,'audit_four_knobs':'current recipe remains all0'},indent=2)+'\n')
PY