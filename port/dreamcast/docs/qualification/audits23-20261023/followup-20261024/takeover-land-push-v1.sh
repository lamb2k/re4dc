#!/usr/bin/env bash
set -euo pipefail
L=/root/work/lanes/audits23-land
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
BASE=a5e972e44096410253ad93164b84d92e3c22655a
SHA=d5c1ceab9e06461462669b3ce1d28a379747a74a
[ "$(git -C "$L" rev-parse HEAD)" = "$SHA" ];[ -z "$(git -C "$L" status --porcelain)" ]
python3 - "$E" "$SHA" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);j=json.loads((p/'landing-build-identity.json').read_text());assert j['source']==sys.argv[2] and j['all14_overlays_identical'] and j['raw_sha256']=='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
PY
git -C "$L" fetch origin t15/int
[ "$(git -C "$L" rev-parse origin/t15/int)" = "$BASE" ]
git -C "$L" merge-base --is-ancestor origin/t15/int HEAD
git -C "$L" push -u origin HEAD:refs/heads/wip/audits23-land-20261023
git -C "$L" push origin HEAD:refs/heads/t15/int
[ "$(git -C "$L" ls-remote origin refs/heads/t15/int | cut -f1)" = "$SHA" ]
printf 'AUDITS_LANDED %s\n' "$SHA" | tee "$E/landing-push.txt"