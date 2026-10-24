#!/usr/bin/env bash
set -euo pipefail
L=/root/work/lanes/dedup-offline23-land
BASE=d5c1ceab9e06461462669b3ce1d28a379747a74a
SOURCE=fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01'
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
[ "$(git -C "$L" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$L" status --porcelain)" ]
[ "$(git -C "$L" remote get-url origin)" = 'https://github.com/lamb2k/re4dc.git' ]
git -C "$L" diff --exit-code "$BASE" HEAD -- port/dreamcast/tools/d367/rr/recipe.conf
git -C "$L" diff --check
git -C "$L" merge-base --is-ancestor 0d30bd83098af2bcd5e9ca2197ffd4cd926e73c4 HEAD
python3 - "$E" "$OWN" "$SOURCE" <<'PY'
from pathlib import Path
import json,hashlib,sys
e,o=map(Path,sys.argv[1:3]);source=sys.argv[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(o/'root-qa-review4be/REVIEW.md')=='4e799aa3a8dc9051819ec77148f2be88067a0d18beff3579b3a643b05e733317'
assert sha(o/'root-review4be/ROOT-RUNTIME-REVIEW.md')=='f6e5fc7ba92d96496ab73b64d22e693f7676e1405daf0e915231a13429f0f703'
assert json.loads((e/'root-private-delivery/ROOT-ACCEPTANCE.json').read_text())['status']=='ACCEPTED_FOR_PRIVATE_CONSOLE_FEEDBACK'
for mode in ['off','on']:
 r=json.loads((e/f'root-landing/landing-build-{mode}-identity.json').read_text())
 assert r['source']==source and r['all14_identical'] and r['production_dedup']==0
 assert (e/f'root-landing/kos-{mode}-before.sha256').read_bytes()==(e/f'root-landing/kos-{mode}-after.sha256').read_bytes()
PY
git -C "$L" fetch origin t15/int
[ "$(git -C "$L" rev-parse origin/t15/int)" = "$BASE" ]
git -C "$L" merge-base --is-ancestor origin/t15/int HEAD
git -C "$L" push origin HEAD:refs/heads/wip/dedup-offline23-land-20261023
git -C "$L" push origin HEAD:refs/heads/t15/int
[ "$(git -C "$L" ls-remote origin refs/heads/t15/int | cut -f1)" = "$SOURCE" ]
git -C "$L" ls-remote origin refs/heads/t15/int refs/heads/wip/dedup-offline23-land-20261023 > "$E/root-landing/pushed-refs.txt"
printf 'LANDED_DEFAULT_OFF_DEDUP_UNIT source=%s\n' "$SOURCE"
