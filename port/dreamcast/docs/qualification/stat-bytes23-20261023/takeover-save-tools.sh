#!/usr/bin/env bash
set -euo pipefail
B=/root/work/lanes/stat-bytes23-complete
S=/root/work/lanes/stat-bytes23-evidence-tools
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
[ ! -e "$S" ]
git -C "$B" worktree add -b wip/stat-bytes23-evidence-tools-20261023 "$S" 2a14662d4b025031cd93f64eed6a5d8159d473b7
python3 - "$S" "$D" <<'PY'
import pathlib,sys,shutil,hashlib,json
s=pathlib.Path(sys.argv[1])/'port/dreamcast/docs/qualification/stat-bytes23-20261023';s.mkdir(parents=True)
r=pathlib.Path(sys.argv[2]);out={}
for p in sorted(r.iterdir()):
 if not p.is_file() or p.suffix not in ('.py','.sh','.md','.json','.patch'):continue
 b=p.read_bytes();(s/p.name).write_bytes(b);out[p.name]=hashlib.sha256(b).hexdigest()
(s/'tools-snapshot.json').write_text(json.dumps(out,indent=2)+'\n')
(s/'README.md').write_text('Saved qualification tooling and notes for source 2a14662d4. This branch contains no asset payloads and is not the production landing branch. Historical failed fixtures and experimental camera control are retained for evidence; do not execute all scripts in sequence. The camera-control branch must never be merged or shipped. Large logs, screenshots and private discs remain on C: under Flycast-Evidence. See STATUS.md for current qualification limits.\n')
PY
git -C "$S" diff --check
git -C "$S" add port/dreamcast/docs/qualification/stat-bytes23-20261023
git -C "$S" commit -m 'Save stat audit qualification tools and evidence notes'
git -C "$S" push -u origin HEAD:refs/heads/wip/stat-bytes23-evidence-tools-20261023
git -C "$S" status --short --branch