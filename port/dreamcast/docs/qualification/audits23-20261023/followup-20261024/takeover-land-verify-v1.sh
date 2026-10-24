#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-land
S=d5c1ceab9e06461462669b3ce1d28a379747a74a
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
ROOT=/root/work/lanes/audits23-land-scratch
[ "$(git -C "$T" rev-parse HEAD)" = "$S" ];[ -z "$(git -C "$T" status --porcelain)" ];mkdir -p "$ROOT"
exec 7>"$ROOT/tree.lock";flock -n 7 || exit 2
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
git -C "$T" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
D=$T/port/dreamcast/tools/d367
. "$D/rr/recipe.conf"
export JOBS=4 SOURCE_DATE_EPOCH=1760000000
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/kos-before.sha256"
bash /root/probe/d367-buildslot.sh env K="$ROOT/k" T="$T" LP=au23ld5c1 CH2="$CH2" XON="" bash "$D/ch2/ch2-build.sh" rP
O=/root/probe/lanes/route/out-au23ld5c1rP
R=/root/probe/lanes/route/out-au23on5e4drP
for K in ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 EM_READ_RETRY=1 KOS_CACHE_P2_DIAG=0 STAT_ROUTINE_BYTES=1 STAT_DIAG=0 VRAM_ROOM_ARENA=0;do grep -qx "$K" "$O/resolved-knobs.txt";done
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$ROOT/landing.bin"
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$R/re4dc-game.elf" "$ROOT/qualified.bin"
cmp "$ROOT/landing.bin" "$ROOT/qualified.bin"
python3 - "$O" "$R" "$E" "$ROOT" "$S" <<'PY'
import hashlib,json,pathlib,sys
o,r,e,x=map(pathlib.Path,sys.argv[1:5]);source=sys.argv[5]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a,b=sorted(o.glob('*.ovl')),sorted(r.glob('*.ovl'));assert len(a)==len(b)==14
for p,q in zip(a,b):assert p.name==q.name and p.read_bytes()==q.read_bytes(),p.name
h=sha(x/'landing.bin');assert h=='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
j={'source':source,'qualified_source':'5e4de9a0262d3629c9833c959557de198b2e9f0c','raw_sha256':h,'all14_overlays_identical':True,'elf_sha256':sha(o/'re4dc-game.elf'),'knobs_sha256':sha(o/'resolved-knobs.txt'),'local_gates_sha256':sha(e/'LOCAL-GATE-RECEIPT.json'),'physical_acceptance':False,'fresh_full_release':False}
(e/'landing-build-identity.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
PY
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/kos-after.sha256"
cmp "$ROOT/kos-before.sha256" "$ROOT/kos-after.sha256"
printf 'AUDITS_LANDING_IMAGE_IDENTITY_PASS\n'