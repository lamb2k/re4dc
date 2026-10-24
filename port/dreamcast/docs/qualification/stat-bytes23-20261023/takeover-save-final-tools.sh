#!/usr/bin/env bash
set -euo pipefail
S=/root/work/lanes/stat-bytes23-evidence-tools
D='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23'
[ -z "$(git -C "$S" status --porcelain)" ]
python3 - "$S" "$D" <<'PY'
import pathlib,sys,hashlib,json
s=pathlib.Path(sys.argv[1])/'port/dreamcast/docs/qualification/stat-bytes23-20261023';r=pathlib.Path(sys.argv[2]);out={}
(s/'.gitattributes').write_text('* -text\n')
for p in sorted(r.iterdir()):
 if not p.is_file() or p.suffix not in ('.py','.sh','.md','.json','.patch'):continue
 b=p.read_bytes();(s/p.name).write_bytes(b);out[p.name]=hashlib.sha256(b).hexdigest()
(s/'tools-snapshot.json').write_text(json.dumps(out,indent=2)+'\n')
(s/'README.md').write_text('Saved byte-exact qualification tooling and notes for source2a14662d4, landed a5e972e44. This branch contains no asset payloads and is not the production landing branch. .gitattributes disables newline normalization so the snapshot manifest matches committed bytes. Historical failed fixtures and experimental camera control are retained for evidence; do not execute all scripts in sequence. The camera-control branch must never be merged or shipped. Large logs, screenshots and private discs remain on C: under Flycast-Evidence. See STATUS.md and HANDBACK.md for qualification limits.\n')
PY
git -C "$S" add port/dreamcast/docs/qualification/stat-bytes23-20261023
git -C "$S" diff --cached --check
git -C "$S" commit -m 'Save final stat landing and camera attribution; preserve exact tool bytes'
git -C "$S" push origin HEAD:refs/heads/wip/stat-bytes23-evidence-tools-20261023
python3 - "$S" <<'PY'
import pathlib,sys,json,hashlib,subprocess
s=pathlib.Path(sys.argv[1]);rel='port/dreamcast/docs/qualification/stat-bytes23-20261023/'
d=json.loads(subprocess.check_output(['git','-C',str(s),'show','HEAD:'+rel+'tools-snapshot.json']))
for p,h in d.items():assert hashlib.sha256(subprocess.check_output(['git','-C',str(s),'show','HEAD:'+rel+p])).hexdigest()==h,p
print('All',len(d),'committed snapshot file hashes verified.')
PY