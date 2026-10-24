#!/usr/bin/env bash
set -euo pipefail
B=/root/work/lanes/world-emit23-target-R
T=/root/work/lanes/world-emit23-current-R
E='/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/7a3af776'
[ ! -e "$T" ];[ -z "$(git -C "$B" status --porcelain)" ];[ "$(git -C "$B" rev-parse HEAD)" = 7a3af776ff8c14070f96272cd48074e5895d0490 ]
git -C "$B" fetch origin t15/int
[ "$(git -C "$B" rev-parse origin/t15/int)" = d5c1ceab9e06461462669b3ce1d28a379747a74a ]
git -C "$B" worktree add -b wip/world-emit23-current-20261023 "$T" origin/t15/int
git -C "$T" merge --no-ff 7a3af776ff8c14070f96272cd48074e5895d0490 -m 'Compose reviewed world census with the current qualified audit recipe'
python3 - "$T" "$B" "$E" <<'PY'
import pathlib,hashlib,json,sys,subprocess
p,b,e=map(pathlib.Path,sys.argv[1:]);paths=['port/dreamcast/game/platform/native_static.cpp','port/dreamcast/game/platform/include/scenery_emit_census.hpp','port/dreamcast/tools/d367/world_emit23/census.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for x in paths:assert (p/x).read_bytes()==(b/x).read_bytes(),x
r={'source':subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip(),'base':'d5c1ceab9e06461462669b3ce1d28a379747a74a','previous':'7a3af776ff8c14070f96272cd48074e5895d0490','world_source_unchanged':{x:sha(p/x) for x in paths},'recipe_sha256':sha(p/'port/dreamcast/tools/d367/rr/recipe.conf'),'previous_measurement_scope':'Old seven-a-source four audit knobs OFF; fresh qualification/QA will use all4 audit knobs ON. No timing carryover to new recipe claimed.'}
(e/'CURRENT-COMPOSITION.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
PY
git -C "$T" push -u origin HEAD:refs/heads/wip/world-emit23-current-20261023