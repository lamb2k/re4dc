#!/usr/bin/env bash
set -euo pipefail
A='/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/current-gates'
E='/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9'
mkdir -p "$E/root-helper"
python3 - "$A" "$E/root-helper" <<'PY'
import pathlib,sys,hashlib,ast,json
p,e=map(pathlib.Path,sys.argv[1:]);a=p/'current_gates.py';b=p/'current_gates_root_v1.py';s=a.read_text();t=b.read_text();assert s.count("E/'worker.lock'")==1 and t==s.replace("E/'worker.lock'","E/'root-worker.lock'")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for f in [a,b]: (e/f.name).write_bytes(f.read_bytes())
r={'original_sha256':sha(a),'root_copy_sha256':sha(b),'only_change':'owned serialization lock filename worker.lock to root-worker.lock','shared_limits_unchanged':'stat3 then trace16 then exact-owned55s console','scopes':'root L/E oneguest, seed worker B oneguest, Dedup oneguest'};(e/'source-delta.json').write_text(json.dumps(r,indent=2)+'\n')
print('ROOT_HELPER_ONLY_LOCK_SCOPE_CHANGE')
PY
python3 -B "$A/test_current_gates.py"
F=$A/current_gates_root_v1.py
for arm in L E; do
 for p in g c t;do python3 -B "$F" stage "$arm" "$p";done
 for gate in h2 kos0 kos1 gd1 bench100 bench101;do python3 -B "$F" run "$arm" "$gate" "${arm}-${gate}-root-r1";done
done